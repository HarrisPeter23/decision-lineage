"""decision_scope.py - NEW metric (added after CHECKPOINT 3 at the user's request): decision-scoped precision.

Why: gold annotates only the main decision and the distractor of each set, so the old precision (score.py) counts a correct link on any OTHER decision as a
false positive. Decision-scoped precision counts a predicted link as a false positive only if it is ATTACHED to a gold-annotated decision:
    TP  = role-typed matches (exactly as score.py, same tolerance, same one-to-one matching)
    FP' = unmatched predictions that are attached to an annotated decision
    P_ds = TP / (TP + FP');  R is unchanged (role-typed recall);  F1_ds from P_ds and R.
A prediction is attached to an annotated decision if
    (a) it is localized on a gold link of that set (any role, within the tolerance; a wrong role on an annotated utterance is always an FP), or
    (b) the text of its window (cited utterances plus one utterance before and after) is similar to a decision descriptor:
        cosine(EMBED_MODEL(window), EMBED_MODEL(descriptor)) >= TAU, where the descriptor is the decision's topic + option texts + the gists of its gold links.
TAU is fixed from GOLD ONLY, never from system output: TAU = the 10th percentile, over all DEV gold links, of the similarity between a gold link's window and
its own decision's descriptor with that link's own gist left out (so 90% of gold links would be attached to their own decision). The same TAU is used for every
config and system. The old metric is kept and reported next to this one. This metric still depends on gold, embeddings and TAU: it is an estimate, labelled so.
EMBED_MODEL = sentence-transformers/all-MiniLM-L6-v2 (the project's EMBED_MODEL), CPU, normalised embeddings.
"""
import functools
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "synthgen"))
from score import gold_links, match_links          # noqa: E402

EMBED = "sentence-transformers/all-MiniLM-L6-v2"
PCTL = 0.10


@functools.lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED, device="cpu")


_cache = {}


def embed(texts):
    todo = [t for t in dict.fromkeys(texts) if t not in _cache]
    if todo:
        for t, v in zip(todo, _model().encode(todo, batch_size=1, normalize_embeddings=True, show_progress_bar=False)):
            _cache[t] = v
    return [_cache[t] for t in texts]


def cos(a, b):
    return float((a * b).sum())


def window_text(meeting, idxs, ctx=1):
    us = meeting["utterances"]
    lo, hi = max(0, min(idxs) - ctx), min(len(us) - 1, max(idxs) + ctx)
    return " ".join(us[i]["text"] for i in range(lo, hi + 1))


def decisions(gold, leave_out=None):
    """[(name, descriptor)] for the annotated decisions of a set: 'main' and, if present, 'distractor'."""
    main_opts = " ".join(gold["options"].values()) if isinstance(gold.get("options"), dict) else ""
    out = [("main", " ".join([gold["topic"], main_opts] + [l["gist"] for l in gold["chain"] if l["link_id"] != leave_out]))]
    if gold.get("distractor"):
        d = gold["distractor"]
        out.append(("distractor", " ".join([d["topic"], d.get("option", "")] + [l["gist"] for l in d["chain"] if l["link_id"] != leave_out])))
    return out


def calibrate(gold_dir, transcript_dir, sets, pctl=PCTL):
    """TAU from gold only. Returns (tau, details)."""
    sims, own_best = [], 0
    for s in sets:
        g = json.loads((pathlib.Path(gold_dir) / f"{s}.json").read_text(encoding="utf-8"))
        tr = json.loads((pathlib.Path(transcript_dir) / f"{s}.json").read_text(encoding="utf-8"))
        ms = {m["meeting_id"]: m for m in tr["meetings"]}
        for gl in gold_links(g):
            name = "main" if gl["chain"] == "main" else "distractor"
            ds = decisions(g, leave_out=gl["link_id"])
            w, *dv = embed([window_text(ms[gl["meeting_id"]], gl["utterance_idxs"])] + [d for _, d in ds])
            ss = {n: cos(w, v) for (n, _), v in zip(ds, dv)}
            sims.append(ss[name])
            own_best += max(ss, key=ss.get) == name
    xs = sorted(sims)
    tau = xs[int(pctl * len(xs))]
    return tau, dict(n_gold_links=len(xs), pctl=pctl, tau=round(tau, 4), own_decision_most_similar=round(own_best / len(xs), 3),
                     sim_quartiles=[round(xs[int(q * (len(xs) - 1))], 3) for q in (0, 0.25, 0.5, 0.75, 1)])


class Scope:
    """Per-set attachment test. Built once per set (descriptor embeddings), reused across configs."""

    def __init__(self, gold, transcript, tau, tol=1):
        self.g, self.tau, self.tol = gold, tau, tol
        self.ms = {m["meeting_id"]: m for m in transcript["meetings"]}
        self.golds = gold_links(gold)
        self.dvecs = embed([d for _, d in decisions(gold)])

    def attached(self, p):
        if any(g["meeting_id"] == p.get("meeting_id") and min(abs(x - y) for x in p["utterance_idxs"] for y in g["utterance_idxs"]) <= self.tol for g in self.golds):
            return True
        m = self.ms.get(p.get("meeting_id"))
        if m is None:
            return False
        (w,) = embed([window_text(m, p["utterance_idxs"])])
        return max(cos(w, v) for v in self.dvecs) >= self.tau

    def utterance_coverage(self):
        """Share of all utterances of the set whose single-utterance window is attached: how much of the transcript the metric treats as in scope."""
        n = k = 0
        for mid, m in self.ms.items():
            for u in m["utterances"]:
                n += 1
                k += self.attached(dict(meeting_id=mid, utterance_idxs=[u["idx"]]))
        return k / n if n else 0.0

    def score(self, preds):
        """Returns dict(tp, fp_all, fp_scoped, n_gold) for role-typed matching at self.tol."""
        preds = [p for p in preds if p.get("utterance_idxs")]
        pairs = match_links(preds, self.golds, self.tol)
        ok = {i for i, j in pairs if preds[i].get("role") == self.golds[j]["role"]}
        fp = [p for i, p in enumerate(preds) if i not in ok]
        return dict(tp=len(ok), fp_all=len(fp), fp_scoped=sum(self.attached(p) for p in fp), n_gold=len(self.golds))
