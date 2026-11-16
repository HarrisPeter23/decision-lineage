"""graph.py - Layer 3: the temporal decision graph (in memory, NetworkX; the interface hides the store so a graph database could replace it).

Input: typed links from the extraction layer, with the text of their utterances. Output: a graph with one Decision node per decision, one Version node per
version of it (validity window in meeting indexes), and typed edges to the links that justified, challenged, resolved or reopened it.

Versioning rules (each has a unit test in tests/test_versioning.py):
  R1  a resolution that differs from the current version supersedes it (SUPERSEDED_BY, validity windows close)
  R2  a resolution that matches the current version is a reaffirmation: no new version, RESOLVED_BY is added to the current one
  R3  a resolution that modifies the current version creates a version of kind 'modified'
  R4  a resolution that matches an EARLIER, non-current version creates a new version of kind 'restored' (A -> B -> A has three versions)
  R5  a decision with no resolution has no version (deferred, or a proposal that never won)
  R6  a tentative resolution (question, 'what if', 'should we', 'maybe we should', or confidence below the threshold) never creates or supersedes a version
Phase 4 revision, rules="v2" (each has a unit test in tests/test_versioning_v2.py; v1 stays available and is reported next to it):
  V2a the option an implicit or content-poor resolution adopts is the LATEST proposal of that decision since its last resolution, else the latest rationale
      (v1 took the FIRST rationale or evidence, which is often the evidence against the option)
  V2b option similarity is containment |A & B| / min(|A|, |B|) over content tokens, not Jaccard, so a short "we keep X" matches a long earlier statement of X
  V2c a resolution that says keep / stick with / stay with / still / remain and has no newer proposal is a reaffirmation (R2), whatever its similarity
rules="v3" = v2 + definition alignment with synthgen/assemble.py found by the gold-link diagnosis (eval/phase4_gold_diag.py; tests in tests/test_versioning_v3.py):
  V3a a question that is a REQUEST to a person ("Camila, can you sketch the plan?", "could you start the paperwork?") is an instruction that presupposes the
      decision, not a hypothetical: R6 ignores request sentences when it looks for question form. Hedges about the decision itself stay tentative.
  V3b option inference: the resolution's own words are the adopted option only if they overlap (containment >= own_at) with the pending option or the
      current version; an instruction or acknowledgement with no option words adopts the pending option (implicit agreement)
  V3c an explicit revert ("flip it back", "go back to", "switch back", "revert", "undo") with no newer proposal restores the previous version (R4)
  V3d a keep-resolution followed by a qualifier clause (", with ...", ", and the ... get ...", "except ...") that adds >= new_tokens content tokens absent from
      the current version is a partial override (R3, kind 'modified'), not a reaffirmation: assemble.py gives "keep A plus M" its own version A+M
rules="v4" = v3 + the tightening for system links (CHECKPOINT 4 review, item 4; one named config, thresholds tuned on DEV):
  V4a a new version needs: role resolution, an option that differs from the active version, not tentative, confidence >= min_confidence (grid-tuned)
  V4b one decision event per decision per meeting: a later decisive resolution in the meeting that already created a version replaces that version's option
      (or undoes it, if it returns to the previous version) instead of chaining another version; validity is "as of the end of meeting k", as in assemble.py
Decision linking and option comparison are pluggable (Linker, Matcher). The defaults here are lexical and cheap; they are tuned on DEV in Phase 4, with an
LLM adjudication for ambiguous pairs added as a separate named config. Nothing in this module reads gold files.
"""
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import networkx as nx

from . import schema as S

STOP = set("""a an the of to in on for and or with be is are was were will would shall should can could must may might this that these those it its as at by from we our us they their
them i you he she not no have has had do does did so if then than there here just very also about up out into over what which who when where how okay ok yeah right um uh like going
get got let lets thing things one two three""".split())
KEEP = re.compile(r"\b(keep|keeping|kept|stick with|sticking with|stay with|staying with|stays|still|remain|remains|no change)\b", re.I)
REVERT = re.compile(r"\b(flip (it|that|this|the \w+( \w+)?) back|go(ing)? back to|switch(ing)? back|change (it )?back|revert|undo)\b", re.I)
REQUEST = re.compile(r"^\W*(\w+,\s*)?(can|could|would|will) you\b|\b(can|could|would) you (please |maybe |just )?\w+", re.I)
QUALIFIER = re.compile(r",\s*(with|and|plus|but|except)\b|\b(except|apart from|plus|but with|only)\b", re.I)
FAMILY = {"v1": 1, "v2": 2, "v3": 3, "v4": 4, "last": 0, "static": 0}     # "last" / "static": Phase 7 ablations (FREEZE.md), not versions of the rules
TENTATIVE = re.compile(r"\b(maybe|perhaps)\s+(we|you|i)\s+(should|could|can|might)\b|\bwhat if\b|\bshould we\b|\bcould we\b|\bhow about\b|\bdo we want to\b|\?\s*$", re.I)


def tokens(text):
    out = []
    for w in re.findall(r"[a-z0-9][a-z0-9\-']*", text.lower()):
        w = w.strip("'-")
        if len(w) < 3 or w in STOP:
            continue
        if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
            w = w[:-1]
        out.append(w)
    return out


@dataclass
class Link:
    link_id: str
    meeting: int                  # 1-based index of the meeting in the corpus order
    role: str
    speaker: str
    idxs: list
    text: str                     # the cited utterance(s), joined
    meeting_id: str = ""
    date: str = ""
    confidence: float = 1.0
    decision: str = None          # set by a linker, or given directly in tests

    @property
    def pos(self):
        return (self.meeting, min(self.idxs))


@dataclass
class Params:
    min_confidence: float = 0.5   # below this a resolution is tentative (R6)
    same_at: float = 0.6          # option similarity at or above: same option
    modified_at: float = 0.3      # between modified_at and same_at: a modification
    link_at: float = 0.12         # similarity needed to attach a link to an existing decision
    gap: int = 30                 # utterances: how far back the 'active decision' of the same meeting reaches
    rules: str = "v1"             # "v1" = CHECKPOINT 3 rules; "v2", "v3", "v4" = revisions (module docstring); each includes the previous one
    own_at: float = 0.2           # v3+: containment needed for a resolution's own words to count as the adopted option (V3b)
    new_tokens: int = 3           # v3+: new content tokens after a qualifier that turn "keep X, with Y" into a modification (V3d)

    @property
    def level(self):
        return FAMILY[self.rules]


class LexicalMatcher:
    """Compares two option texts. Returns 'same', 'modified' or 'different'."""

    def __init__(self, params=None):
        self.p = params or Params()

    def similarity(self, a, b):
        ta, tb = set(tokens(a)), set(tokens(b))
        if not ta or not tb:
            return 0.0
        if self.p.level >= 2:                                                          # V2b
            return len(ta & tb) / min(len(ta), len(tb))
        return len(ta & tb) / len(ta | tb)

    def relation(self, current, candidate):
        s = self.similarity(current, candidate)
        return "same" if s >= self.p.same_at else "modified" if s >= self.p.modified_at else "different"


class LexicalLinker:
    """Assigns each link to a decision by lexical overlap with what the decision has accumulated so far."""

    def __init__(self, links, params=None):
        self.p = params or Params()
        df = Counter(t for l in links for t in set(tokens(l.text)))
        n = max(1, len(links))
        self.idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}
        self.bags = defaultdict(Counter)
        self.last = {}                # decision -> position of its latest link

    def sim(self, text, did):
        t = set(tokens(text))
        bag = self.bags[did]
        if not t or not bag:
            return 0.0
        num = sum(self.idf.get(w, 1.0) for w in t if w in bag)
        den = sum(self.idf.get(w, 1.0) for w in t)
        return num / den

    def assign(self, link, order):
        known = list(self.bags)
        best, best_s = None, 0.0
        for d in known:
            s = self.sim(link.text, d)
            if s > best_s:
                best, best_s = d, s
        if best is not None and best_s >= self.p.link_at:
            return best
        if link.role != "proposal" and known:                      # a reaction without topic words belongs to what was just being discussed
            near = [(self.last[d], d) for d in known if self.last[d][0] == link.meeting and link.pos[1] - self.last[d][1] <= self.p.gap]
            if near:
                return max(near)[1]
        return f"D{len(known) + 1}"

    def note(self, link, did):
        self.bags[did].update(tokens(link.text))
        self.last[did] = link.pos


def containment(a, b):
    ta, tb = set(tokens(a)), set(tokens(b))
    return len(ta & tb) / min(len(ta), len(tb)) if ta and tb else 0.0


def is_tentative(link, params):
    text = link.text
    if getattr(params, "level", 1) >= 3:                                               # V3a: drop request sentences before looking for question form
        sents = re.findall(r"[^.!?]+[.!?]*", text)
        text = " ".join(s for s in sents if not REQUEST.search(s)) or ""
    return link.confidence < params.min_confidence or bool(TENTATIVE.search(text))


class DecisionGraph:
    def __init__(self, params=None, matcher=None):
        self.p = params or Params()
        self.matcher = matcher or LexicalMatcher(self.p)
        self.g = nx.MultiDiGraph()
        self.versions = defaultdict(list)       # decision -> [version dicts in order]
        self.links = {}

    # ---------------------------------------------------------------- building
    def build(self, links, linker=None):
        links = sorted(links, key=lambda l: l.pos)
        for l in links:
            self.links[l.link_id] = l
        linker = linker or LexicalLinker(links, self.p)
        pending = {}                            # decision -> option text most recently proposed or argued since the last resolution
        v2 = self.p.level >= 2
        proposed = {}                           # v2: decision -> latest proposal text since the last resolution
        for l in links:
            if l.decision is None:
                l.decision = linker.assign(l, links)
            did = l.decision
            linker.note(l, did)
            self._add_link_node(l)
            self.g.add_node(("decision", did), kind=S.DECISION)
            self.g.add_edge(("decision", did), ("meeting", l.meeting), key=f"disc{l.link_id}", etype=S.DISCUSSED_IN, meeting=l.meeting, date=l.date)
            cur = self.versions[did][-1] if self.versions[did] else None
            if l.role == "proposal":
                pending[did] = l.text
                proposed[did] = l.text
                self.g.add_edge(("decision", did), ("person", l.speaker), key=f"prop{l.link_id}", etype=S.PROPOSED_BY, meeting=l.meeting, date=l.date, confidence=l.confidence, refs=[l.link_id])
            elif l.role in ("rationale", "evidence"):
                if v2:
                    if l.role == "rationale" and did not in proposed:                  # V2a
                        pending[did] = l.text
                else:
                    pending.setdefault(did, l.text)
                self._attach(did, cur, l, S.JUSTIFIED_BY)
            elif l.role == "challenge":
                self._attach(did, cur, l, S.CHALLENGED_BY)
            elif l.role == "reconsideration":
                self._attach(did, cur, l, S.REOPENED_BY)
            elif l.role == "resolution":
                self._resolve(did, cur, l, pending.get(did), fresh=did in proposed)
                pending.pop(did, None)
                proposed.pop(did, None)
        return self

    def _add_link_node(self, l):
        self.g.add_node(("link", l.link_id), kind=S.LINK, role=l.role, speaker=l.speaker, meeting=l.meeting, idxs=l.idxs, text=l.text, confidence=l.confidence)

    def _attach(self, did, cur, l, etype):
        src = ("version", did, cur["n"]) if cur else ("decision", did)
        self.g.add_edge(src, ("link", l.link_id), key=f"{etype}{l.link_id}", etype=etype, meeting=l.meeting, date=l.date, confidence=l.confidence, refs=[l.link_id])

    def _resolve(self, did, cur, l, pending_text, fresh=False):
        if self.p.rules == "last":                                                      # ablation "no conflict resolution": the last statement wins
            if cur is None:
                self._new_version(did, l, l.text, S.INITIAL)
            else:
                self._new_version(did, l, l.text, S.CHANGED)                           # no R2 reaffirmation, no R6 tentative filter, no V2-V4 rules
            return
        if self.p.rules == "static":                                                    # ablation "static graph": no versions, windows or supersession
            self.g.add_edge(("decision", did), ("link", l.link_id), key=f"res{l.link_id}", etype=S.RESOLVED_BY, meeting=l.meeting, date=l.date, confidence=l.confidence, refs=[l.link_id])
            return
        if is_tentative(l, self.p):                                                     # R6
            self.g.nodes[("link", l.link_id)]["tentative"] = True
            return
        lv = self.p.level
        if lv >= 2 and cur is not None and not fresh and KEEP.search(l.text):          # V2c
            if lv >= 3 and self._keeps_with_change(l.text, cur["option"]):            # V3d: "keep X, with Y" is a partial override
                self._new_version(did, l, l.text, S.MODIFIED)
            else:
                self._reaffirm(did, cur, l)
            return
        vs = self.versions[did]
        if lv >= 3 and not fresh and len(vs) >= 2 and REVERT.search(l.text):            # V3c
            option = vs[-2]["option"]
        elif lv >= 3:                                                                   # V3b
            cands = [t for t in (pending_text, cur["option"] if cur else None) if t]
            own = not cands or max(containment(l.text, c) for c in cands) >= self.p.own_at
            option = l.text if own else pending_text or l.text
        else:
            # v1/v2: the resolution's own words if they carry content, else the last option proposed or argued (implicit agreement)
            option = l.text if (cur is None or self._carries_option(l, cur)) else (pending_text or l.text)
            if pending_text and len(tokens(l.text)) < 6:
                option = pending_text
        if lv >= 4 and cur is not None and cur["valid_from"] == l.meeting:              # V4b: one decision event per decision per meeting
            prev = vs[-2] if len(vs) >= 2 else None
            if self.matcher.relation(cur["option"], option) == "same":
                self._reaffirm(did, cur, l)
            elif prev is not None and self.matcher.relation(prev["option"], option) == "same":
                self._undo_last(did, l)
            else:
                cur["option"] = option
                self.g.nodes[("version", did, cur["n"])]["option"] = option
                self.g.add_edge(("version", did, cur["n"]), ("link", l.link_id), key=f"res{l.link_id}", etype=S.RESOLVED_BY, meeting=l.meeting, date=l.date, confidence=l.confidence, refs=[l.link_id], replaces_option=True)
            return
        if cur is None:                                                                 # first version
            self._new_version(did, l, option, S.INITIAL)
            return
        rel = self.matcher.relation(cur["option"], option)
        if rel == "same":                                                               # R2
            self._reaffirm(did, cur, l)
            return
        earlier = [v for v in self.versions[did][:-1] if self.matcher.relation(v["option"], option) == "same"]
        kind = S.RESTORED if earlier else (S.MODIFIED if rel == "modified" else S.CHANGED)          # R4, R3, R1
        self._new_version(did, l, option, kind)

    def _keeps_with_change(self, text, current):
        m = KEEP.search(text)
        tail = text[m.end():]
        q = QUALIFIER.search(tail)
        if not q:
            return False
        new = set(tokens(tail[q.end():])) - set(tokens(current))
        return len(new) >= self.p.new_tokens

    def _reaffirm(self, did, cur, l):
        self.g.add_edge(("version", did, cur["n"]), ("link", l.link_id), key=f"res{l.link_id}", etype=S.RESOLVED_BY, meeting=l.meeting, date=l.date, confidence=l.confidence, refs=[l.link_id], reaffirmation=True)
        cur["reaffirmed_in"].append(l.meeting)

    def _undo_last(self, did, l):
        """V4b: within one meeting the team went back to the previous option, so the version created earlier in this meeting never held at its end."""
        last = self.versions[did].pop()
        node = ("version", did, last["n"])
        for u, v, k in list(self.g.in_edges(node, keys=True)) + list(self.g.out_edges(node, keys=True)):
            if self.g.edges[u, v, k]["etype"] == S.SUPERSEDED_BY:
                self.g.remove_edge(u, v, k)
        self.g.nodes[node]["undone"] = True
        prev = self.versions[did][-1]
        prev["valid_to"] = None
        self._reaffirm(did, prev, l)

    def _carries_option(self, l, cur):
        return len(tokens(l.text)) >= 6 or self.matcher.relation(cur["option"], l.text) != "different"

    def _new_version(self, did, l, option, kind):
        prev = self.versions[did][-1] if self.versions[did] else None
        n = len(self.versions[did]) + 1
        v = dict(decision=did, n=n, option=option, kind=kind, valid_from=l.meeting, valid_to=None, reaffirmed_in=[], resolved_by=l.link_id)
        if prev:
            prev["valid_to"] = l.meeting
            self.g.add_edge(("version", did, prev["n"]), ("version", did, n), key="sup", etype=S.SUPERSEDED_BY, meeting=l.meeting, date=l.date, refs=[l.link_id], kind=kind)
        self.versions[did].append(v)
        self.g.add_node(("version", did, n), kind=S.VERSION, n=n, option=option, origin=kind, valid_from=l.meeting)
        self.g.add_edge(("version", did, n), ("link", l.link_id), key=f"res{l.link_id}", etype=S.RESOLVED_BY, meeting=l.meeting, date=l.date, confidence=l.confidence, refs=[l.link_id])

    # ---------------------------------------------------------------- queries
    def decisions(self):
        return sorted({d for d, v in self.versions.items() if v} | {n[1] for n in self.g.nodes if n[0] == "decision"})

    def current(self, did):
        v = self.versions.get(did) or []
        return v[-1] if v else None

    def as_of(self, did, meeting):
        """The version in force at the END of the given meeting, or None ('no decision yet')."""
        for v in self.versions.get(did, []):
            if v["valid_from"] <= meeting and (v["valid_to"] is None or meeting < v["valid_to"]):
                return v
        return None

    def edges_of(self, version_node, etype=None):
        return [(u, v, d) for u, v, d in self.g.out_edges(version_node, data=True) if etype is None or d["etype"] == etype]
