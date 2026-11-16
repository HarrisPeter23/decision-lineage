"""linking.py - Layer 3 input adapter and cross-meeting decision entity linking.

Works with the output of ANY extraction config (single_pass, single_pass_topK, single_pass_recap_roles, mp_*): it needs only
meeting_id, role, utterance_idxs, speaker, confidence per link. If a config also emits a `decision` name (single_pass_recap_roles), the
EmbeddingLinker can optionally prepend it to the link text (use_names=True); by default it is ignored, so every config is linked the same way.

EmbeddingLinker (default for Phase 4): a link joins the existing decision whose centroid embedding is most similar, if that similarity is at least
`link_at`; a reaction with no match (rationale, evidence, challenge, reconsideration, resolution) joins the decision most recently active in the same
meeting within `gap` utterances (the same fallback as LexicalLinker); otherwise it opens a new decision. Embeddings: EMBED_MODEL over the link's window
(cited utterances plus `ctx` neighbours each side). Nothing here reads gold. Parameters are tuned on DEV only (eval/phase4_graph.py).
"""
import functools
from dataclasses import dataclass

import numpy as np

from .graph import Link

EMBED = "sentence-transformers/all-MiniLM-L6-v2"


@functools.lru_cache(maxsize=1)
def _st():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED, device="cpu")


class Embedder:
    """Cached sentence embeddings (normalised). Any callable texts -> array can replace it (tests use a toy one)."""

    def __init__(self, fn=None):
        self.fn = fn
        self.cache = {}

    def __call__(self, texts):
        todo = [t for t in dict.fromkeys(texts) if t not in self.cache]
        if todo:
            vs = self.fn(todo) if self.fn else _st().encode(todo, batch_size=1, normalize_embeddings=True, show_progress_bar=False)   # batch 1: padding makes batched vectors depend on batch-mates
            for t, v in zip(todo, vs):
                v = np.asarray(v, dtype=float)
                self.cache[t] = v / (np.linalg.norm(v) or 1.0)
        return np.stack([self.cache[t] for t in texts]) if texts else np.zeros((0, 1))


def window(meeting, idxs, ctx):
    us = meeting["utterances"]
    lo, hi = max(0, min(idxs) - ctx), min(len(us) - 1, max(idxs) + ctx)
    return " ".join(us[i]["text"] for i in range(lo, hi + 1))


def links_from_predictions(pred_links, transcript, ctx=1, prefix="P"):
    """Prediction dicts (any config) + the transcript the system saw -> graph Links, in corpus order.
    Link.text = the cited utterances (used by the versioning rules); Link.ctx_text = the window used for linking."""
    ms = {m["meeting_id"]: (k, m) for k, m in enumerate(transcript["meetings"], 1)}
    out = []
    for n, p in enumerate(sorted(pred_links, key=lambda p: (ms[p["meeting_id"]][0], min(p["utterance_idxs"]))), 1):
        k, m = ms[p["meeting_id"]]
        idxs = sorted(set(int(i) for i in p["utterance_idxs"]))
        l = Link(link_id=f"{prefix}{n:04d}", meeting=k, role=p["role"], speaker=str(p.get("speaker") or ""), idxs=idxs,
                 text=" ".join(m["utterances"][i]["text"] for i in idxs), meeting_id=p["meeting_id"], date=m.get("date", ""),
                 confidence=float(p.get("confidence", 1.0)))
        l.ctx_text = window(m, idxs, ctx)
        l.name = p.get("decision") or ""
        l.key_idx = int(p["utterance_idxs"][0])
        l.team = frozenset(u["speaker"] for u in m["utterances"])          # L2: the people in this meeting (from the transcript)
        out.append(l)
    return out


@dataclass
class LinkParams:
    link_at: float = 0.45         # centroid cosine needed to join an existing decision
    gap: int = 30                 # utterances: reach of the same-meeting fallback
    use_names: bool = False       # prepend the config's own decision name, if any, to the text that is embedded
    proposal_own: bool = False    # embed a proposal by its own words only (no neighbours): a proposal opens a topic, its neighbours may belong to the previous one
    team_at: float = 0.0          # L2: min Jaccard overlap of the meeting's speakers with the decision's speakers to join it (0 = off, the Phase 4 linker)


class EmbeddingLinker:
    def __init__(self, links, params=None, embedder=None):
        self.p = params or LinkParams()
        self.emb = embedder or Embedder()
        texts = [self._text(l) for l in links]
        self.vec = dict(zip((l.link_id for l in links), self.emb(texts)))
        self.sums = {}
        self.last = {}
        self.team = {}

    def _team_ok(self, link, d):
        if not self.p.team_at:
            return True
        a, b = getattr(link, "team", frozenset()), self.team.get(d, frozenset())
        return bool(a | b) and len(a & b) / len(a | b) >= self.p.team_at

    def _text(self, l):
        t = l.text if (self.p.proposal_own and l.role == "proposal") else (getattr(l, "ctx_text", None) or l.text)
        name = getattr(l, "name", "")
        return f"{name}. {t}" if self.p.use_names and name else t

    def assign(self, link, order=None):
        v = self.vec[link.link_id]
        best, best_s = None, -1.0
        for d, s in self.sums.items():
            if not self._team_ok(link, d):
                continue
            sim = float(v @ (s / (np.linalg.norm(s) or 1.0)))
            if sim > best_s:
                best, best_s = d, sim
        if best is not None and best_s >= self.p.link_at:
            return best
        if link.role != "proposal" and self.sums:
            near = [(self.last[d], d) for d in self.sums if self.last[d][0] == link.meeting and link.pos[1] - self.last[d][1] <= self.p.gap]
            if near:
                return max(near)[1]
        return f"D{len(self.sums) + 1}"

    def note(self, link, did):
        v = self.vec[link.link_id]
        self.sums[did] = self.sums.get(did, 0) + v
        self.last[did] = link.pos
        self.team[did] = self.team.get(did, frozenset()) | getattr(link, "team", frozenset())


class EmbeddingMatcher:
    """Option comparison by embedding cosine (alternative to graph.LexicalMatcher; same interface). Thresholds tuned on DEV."""

    def __init__(self, embedder=None, same_at=0.8, modified_at=0.6):
        self.emb = embedder or Embedder()
        self.same_at, self.modified_at = same_at, modified_at

    def similarity(self, a, b):
        va, vb = self.emb([a, b])
        return float(va @ vb)

    def relation(self, current, candidate):
        s = self.similarity(current, candidate)
        return "same" if s >= self.same_at else "modified" if s >= self.modified_at else "different"
