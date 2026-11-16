"""retrieve.py - Layer 4: lineage-aware retrieval over the temporal decision graph (pre-declared in reports/phase5.md section 0).

LineageSystem.index(corpus, links): builds the graph (rules v4, Phase 4 linker) from the extraction config's links for the corpus's meetings.
LineageSystem.retrieve(question): routes the question to an intent, anchors the decision, and returns a capped, chronological SUBGRAPH:
    dict(intent, anchor, anchor_score, as_of, versions=[...], items=[{link_id, meeting_id, meeting, date, speaker, role, idxs, text, version, source}],
         no_decision_yet, changed, fallback)
Nothing here reads gold, set ids or the harness's private map. The router regexes were written from the question templates (declared as part of the system).
"""
import math
import re
from collections import Counter

import numpy as np

from . import schema as S
from .graph import DecisionGraph, LexicalMatcher, Params, tokens
from .linking import Embedder, EmbeddingLinker, LinkParams, links_from_predictions, window

GRAPH_PARAMS = dict(rules="v4", same_at=0.4, modified_at=0.2, min_confidence=0.9, own_at=0.2, new_tokens=3)
LINK_PARAMS = dict(link_at=0.4, gap=60, team_at=0.2)          # team_at: linker revision L2 (phase5.md section 2)
CAP = 12
FALLBACK_AT = 0.35
FALLBACK_K = 4
PRIORITY = {"resolution": 0, "reconsideration": 1, "evidence": 2, "challenge": 3, "rationale": 4, "proposal": 5}

ROUTES = [  # (intent, regex with the topic as group 'topic'); first match wins
    ("as_of", r"^what was the decision about (?P<topic>.+?) as of the end of meeting (?P<k>\d+)\??$"),
    ("final", r"^what did the team finally decide about (?P<topic>.+?)\??$"),
    ("decisions_about", r"^what decisions were made about (?P<topic>.+?)\??$"),
    ("change_over_time", r"^how did the decision about (?P<topic>.+?) change over time\??$"),
    ("why_changed", r"^why did the team change its decision about (?P<topic>.+?)\??$"),
    ("why_changed", r"^why was the original decision about (?P<topic>.+?) changed\??$"),
    ("why_changed", r"^why did the decision about (?P<topic>.+?) change at meeting (?P<k>\d+)\??$"),          # RF1 (router fix after the P3-A numbers)
    ("who_proposed", r"^who proposed the original decision about (?P<topic>.+?)\??$"),
    ("evidence_to_reconsider", r"^what evidence caused the team to reconsider its decision about (?P<topic>.+?)\??$"),
    ("meetings_contributed", r"^which meetings contributed to the final decision about (?P<topic>.+?)\??$"),
    ("full_lineage", r"^show the complete lineage of the decision about (?P<topic>.+?) from proposal to final outcome\.?$"),
    ("final", r"^what was decided about (?P<topic>.+?)\??$"),
    ("who_proposed_option", r"^who proposed (?P<topic>.+?)\??$"),                                                # RF1: "Who proposed <option>?"
]


def route(question):
    q = question.strip()
    for intent, rx in ROUTES:
        m = re.match(rx, q, re.I)
        if m:
            return intent, m.group("topic"), int(m.group("k")) if "k" in m.groupdict() and m.group("k") else None
    return "other", q, None


def load_corpus(meeting_texts):
    """meeting_texts: list of 'Meeting: id / Date: ... / Participants: ... / blank / Speaker: text' strings (the plain-text transcript format)."""
    meetings = []
    for text in meeting_texts:
        meta, utts, body = {}, [], False
        for line in text.splitlines():
            if not body:
                if not line.strip():
                    body = True
                    continue
                k, _, v = line.partition(":")
                meta[k.strip().lower()] = v.strip()
                continue
            if line.strip():
                sp, _, tx = line.partition(": ")
                utts.append(dict(idx=len(utts), speaker=sp.strip(), text=tx.strip()))
        meetings.append(dict(meeting_id=meta.get("meeting"), date=meta.get("date"), utterances=utts))
    return dict(meetings=meetings)


class LineageSystem:
    name = "lineage"

    ABLATIONS = (None, "no_typing", "no_conflict_resolution", "static_graph")       # FREEZE.md: Phase 7 ablations of the frozen system

    def __init__(self, embedder=None, cap=CAP, fallback=True, graph_params=None, link_params=None, ablation=None):
        assert ablation in self.ABLATIONS, ablation
        self.emb = embedder or Embedder()
        self.cap, self.fallback, self.ablation = cap, fallback, ablation
        self.gp = dict(GRAPH_PARAMS, **(graph_params or {}))
        if ablation == "no_conflict_resolution":
            self.gp["rules"] = "last"
        elif ablation == "static_graph":
            self.gp["rules"] = "static"
        self.lp = dict(LINK_PARAMS, **(link_params or {}))

    # ------------------------------------------------------------------ index
    def index(self, corpus, links):
        self.corpus = corpus
        self.mpos = {m["meeting_id"]: k for k, m in enumerate(corpus["meetings"], 1)}
        self.links = links_from_predictions(links, corpus)
        if self.ablation == "no_typing":                    # generic temporal graph: decisions and versions kept, argumentative roles collapsed
            for l in self.links:
                if l.role not in ("proposal", "resolution"):
                    l.role = "statement"
        p = Params(**self.gp)
        self.graph = DecisionGraph(p, LexicalMatcher(p)).build(self.links, EmbeddingLinker(self.links, LinkParams(**self.lp), self.emb))
        self.by_dec = {}
        for l in self.links:
            self.by_dec.setdefault(l.decision, []).append(l)
        cands = [d for d, ls in self.by_dec.items() if any(l.role in ("proposal", "resolution") for l in ls)]
        self.cands = cands or list(self.by_dec)
        self.desc = {d: self._describe(self.by_dec[d]) for d in self.cands}
        self.dvec = dict(zip(self.cands, self.emb([self.desc[d] for d in self.cands]))) if self.cands else {}
        self.dtok = {d: set(tokens(self.desc[d])) for d in self.cands}
        df = Counter(t for ts in self.dtok.values() for t in ts)
        n = max(1, len(self.cands))
        self.idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}
        self.windows = [(m["meeting_id"], [u["idx"]], window(m, [u["idx"]], 1)) for m in corpus["meetings"] for u in m["utterances"]]
        self.wvec = None
        return self

    @staticmethod
    def _describe(ls):
        # proposals and resolutions first (most topical), then the rest, in time order; the embedder truncates long texts
        key = lambda l: (l.role not in ("proposal", "resolution"), l.pos)
        return " ".join(l.text for l in sorted(ls, key=key))

    # ------------------------------------------------------------------ anchoring
    def anchor(self, topic):
        if not self.cands:
            return None, 0.0
        (qv,) = self.emb([topic])
        qt = set(tokens(topic))
        den = sum(self.idf.get(t, math.log(len(self.cands) + 1) + 1) for t in qt) or 1.0
        best, best_s = None, -1.0
        for d in self.cands:
            lex = sum(self.idf.get(t, 0) for t in qt if t in self.dtok[d]) / den
            s = 0.5 * float(qv @ self.dvec[d]) + 0.5 * lex
            if s > best_s:
                best, best_s = d, s
        return best, best_s

    # ------------------------------------------------------------------ retrieval
    def _item(self, l, source="graph"):
        v = self._version_at(l.decision, l.pos)
        return dict(link_id=l.link_id, meeting_id=l.meeting_id, meeting=l.meeting, date=l.date, speaker=l.speaker, role=l.role, idxs=l.idxs, text=l.text,
                    version=v["n"] if v else None, source=source)

    def _vpos(self, did):
        """[(version dict, position of the resolution that created it)]"""
        return [(v, self.graph.links[v["resolved_by"]].pos) for v in self.graph.versions.get(did, [])]

    def _version_at(self, did, pos):
        cur = None
        for v, p in self._vpos(did):
            if p <= pos:
                cur = v
        return cur

    def _cap(self, ls):
        ls = list({l.link_id: l for l in ls}.values())
        if len(ls) > self.cap:
            ls = sorted(ls, key=lambda l: (PRIORITY.get(l.role, 9), l.pos))[:self.cap]
        return sorted(ls, key=lambda l: l.pos)

    def retrieve(self, question):
        intent, topic, k = route(question)
        did, score = self.anchor(topic)
        out = dict(intent=intent, topic=topic, anchor=did, anchor_score=round(score, 4), as_of=None, versions=[], items=[], no_decision_yet=False,
                   changed=None, fallback=False)
        if did is None:
            return self._fallback(out, question) if self.fallback else out
        ls = sorted(self.by_dec[did], key=lambda l: l.pos)
        vp = self._vpos(did)
        out["versions"] = [dict(n=v["n"], kind=v["kind"], valid_from=v["valid_from"], valid_to=v["valid_to"], option=v["option"], resolved_by=v["resolved_by"]) for v, _ in vp]
        out["changed"] = len(vp) >= 2
        out["meetings"] = sorted({l.meeting for l in ls})
        ARG = ("rationale", "evidence", "challenge", "reconsideration")
        if self.ablation == "no_typing":                    # without typing, an argument-role filter can only ask for 'any statement'
            role = lambda *rs: [l for l in ls if l.role in rs or (l.role == "statement" and any(r in ARG for r in rs))]
        else:
            role = lambda *rs: [l for l in ls if l.role in rs]
        pick = []
        if self.ablation == "static_graph":                 # non-temporal graph: no versions; every intent reads the decision's links without time logic
            out.update(system="lineage_static", changed=None, versions=[],
                       header="The evidence below comes from a (non-temporal) graph of statements about this decision.")
            if intent in ("final", "other", "as_of"):
                pick = role("resolution") + role("rationale", "evidence")
            elif intent == "why_changed":
                pick = role("challenge", "evidence", "reconsideration", "rationale", "resolution")
            elif intent == "evidence_to_reconsider":
                pick = role("evidence", "challenge", "reconsideration")
            elif intent in ("full_lineage", "meetings_contributed"):
                pick = ls
            elif intent in ("change_over_time", "decisions_about"):
                pick = role("resolution")
            elif intent in ("who_proposed", "who_proposed_option"):
                pick = role("proposal")[:1]
            out["items"] = [self._item(l) for l in self._cap(pick)]
            if self.fallback and intent in ("final", "as_of", "who_proposed", "who_proposed_option") and (score < FALLBACK_AT or not pick):
                out = self._fallback(out, question)
            return out
        if intent in ("final", "other"):
            if vp:
                v, p = vp[-1]
                prev_p = vp[-2][1] if len(vp) >= 2 else (-1, -1)
                pick = [self.graph.links[v["resolved_by"]]] + [l for l in role("rationale", "evidence") if prev_p < l.pos <= p] + \
                       [l for l in role("resolution") if l.pos > p]
            else:
                out["no_decision_yet"] = True
                pick = role("proposal", "rationale")
        elif intent == "as_of":
            meetings = sorted({l.meeting for l in ls})
            m = meetings[min(k, len(meetings)) - 1] if meetings and k else None
            out["as_of"] = dict(ordinal=k, corpus_meeting=m)
            v = self.graph.as_of(did, m) if m else None
            if v is None:
                out["no_decision_yet"] = True
                pick = [l for l in role("proposal", "rationale", "challenge") if m and l.meeting <= m]
            else:
                rp = self.graph.links[v["resolved_by"]].pos
                earlier = [p for vv, p in vp if p < rp]
                lo = earlier[-1] if earlier else (-1, -1)
                pick = [self.graph.links[v["resolved_by"]]] + [l for l in role("rationale", "evidence") if lo < l.pos <= rp]
        elif intent == "why_changed":
            if len(vp) >= 2:
                pairs = list(zip(vp, vp[1:]))
                if k:                                                                                           # RF1: "change at meeting k"
                    meetings = sorted({l.meeting for l in ls})
                    mk = meetings[min(k, len(meetings)) - 1] if meetings else None
                    sel = [pr for pr in pairs if pr[1][0]["valid_from"] == mk]
                    pairs = sel or pairs
                for (v0, p0), (v1, p1) in pairs:
                    pre = [p for _, p in vp if p < p0]
                    lo = pre[-1] if pre else (-1, -1)
                    pick += [l for l in role("rationale") if lo < l.pos <= p0]                                  # why the old version was chosen (amendment)
                    pick += [l for l in role("challenge", "evidence", "reconsideration", "rationale") if p0 < l.pos < p1]
                    pick.append(self.graph.links[v1["resolved_by"]])
            else:
                pick = role("challenge", "evidence", "reconsideration") + [l for l in role("resolution") if not vp or l.link_id != vp[0][0]["resolved_by"]] + \
                       role("rationale")
        elif intent == "evidence_to_reconsider":
            if len(vp) >= 2:
                lo, hi = vp[-2][1], vp[-1][1]
            else:
                res = role("resolution")
                lo = vp[0][1] if vp else (-1, -1)
                hi = res[-1].pos if res and res[-1].pos > lo else (10 ** 6, 0)
            pick = [l for l in role("evidence", "challenge", "reconsideration") if lo < l.pos < hi] or role("evidence", "challenge", "reconsideration")
        elif intent in ("full_lineage", "meetings_contributed"):
            pick = ls
        elif intent in ("change_over_time", "decisions_about"):
            pick = role("resolution")
        elif intent == "who_proposed":
            pick = role("proposal")[:1]
        elif intent == "who_proposed_option":                                                                    # RF1: the link that put this option forward
            opts = role("proposal") or role("rationale") or ls
            qt = set(tokens(topic))
            (qv,) = self.emb([topic])
            vecs = self.emb([l.text for l in opts])
            sc = [0.5 * float(qv @ v) + 0.5 * (len(qt & set(tokens(l.text))) / max(len(qt), 1)) for l, v in zip(opts, vecs)]
            pick = [opts[int(np.argmax(sc))]]
        out["items"] = [self._item(l) for l in self._cap(pick)]
        if self.fallback and intent in ("final", "as_of", "who_proposed", "who_proposed_option") and (score < FALLBACK_AT or not vp):
            out = self._fallback(out, question)
        return out

    def _fallback(self, out, question):
        if self.wvec is None:
            self.wvec = self.emb([w[2] for w in self.windows])
        (qv,) = self.emb([question])
        top = np.argsort(-(self.wvec @ qv))[:FALLBACK_K]
        for i in sorted(top, key=lambda i: (self.mpos[self.windows[i][0]], self.windows[i][1][0])):
            mid, idxs, text = self.windows[i]
            m = self.corpus["meetings"][self.mpos[mid] - 1]
            out["items"].append(dict(link_id=f"U{self.mpos[mid]}-{idxs[0]}", meeting_id=mid, meeting=self.mpos[mid], date=m["date"],
                                     speaker=m["utterances"][idxs[0]]["speaker"], role=None, idxs=idxs, text=m["utterances"][idxs[0]]["text"], version=None,
                                     source="vector"))
        out["fallback"] = True
        return out
