"""phase4_graph.py - Phase 4 graph quality on synthetic DEV (CPU only; no model calls). DEV only (asserted via split.json).

Inputs ("link sources"), all through the same adapter (argdecisionlineage.linking.links_from_predictions), so the graph code works with any config:
  oracle          gold links of the set (main chain + distractor) as if extracted, confidence 1.0, no decision ids  -> isolates linking + versioning
  single_pass     Phase 3 candidate, uncapped
  single_pass_top4  Phase 3 capped candidate (P3-C kept K=4)
  single_pass_recap_roles (+ its cap), if the kernel output exists - exploratory until it qualifies under P3-B
Metrics (per set, pooled; bootstrap 95% CI over DEV sets, 1000 resamples, seed 0):
  linking     predicted links localized on a gold link (tol 1, role ignored) carry that gold link's decision (main / distractor). Pairwise same-decision
              precision / recall / F1 over those links; main-distractor false-merge pairs; fragmentation = graph decisions covering the main chain.
  anchor      the graph decision holding most localized main-chain links (ORACLE ANCHORING: Phase 5 does real anchoring from the question).
  link_to_decision  share of localized gold-chain links assigned to their chain's anchor (distractor links must not sit in the main anchor).
  as_of       the 28 DEV as_of questions + 14 lookup_final (as of the last meeting): graph version in force on the anchor, mapped to the nearest gold option
              of the set by EMBED_MODEL cosine, or "no decision yet"; exact key match.
  versions    change_over_time: graph version sequence (mapped keys) equals the gold sequence.
  supersession  SUPERSEDED_BY edges on the anchor as (meeting, mapped key) vs gold changes (at_meeting, key of to_version): P / R / F1.
Tuning (DEV only; objective fixed before running): linker grid link_at x gap and matcher grid, each scored by the MEAN over the two candidate sources
(single_pass, single_pass_top4) of (linking F1 + as_of accuracy) / 2. Oracle is never used for selection; it is reported as an upper reference.
  python eval/phase4_graph.py [--out results/phase4]
"""
import argparse
import itertools
import json
import pathlib
import random
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "synthgen"))
sys.path.insert(0, str(ROOT / "eval"))
from argdecisionlineage import schema as S                                                     # noqa: E402
from argdecisionlineage.graph import DecisionGraph, LexicalMatcher, Params, tokens                     # noqa: E402
from argdecisionlineage.linking import EmbeddingLinker, EmbeddingMatcher, Embedder, LinkParams, links_from_predictions  # noqa: E402
from score import gold_links, match_links                                                      # noqa: E402
from phase3_topk import topk                                                                    # noqa: E402
from phase3_caps import per_decision                                                            # noqa: E402

EMB = Embedder()
LINK_GRID = dict(link_at=[0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7], gap=[15, 30, 60], proposal_own=[False, True])
MATCH_GRID = [("lexical", s, m, r) for r in ("v1", "v2") for s in (0.4, 0.5, 0.6, 0.7, 0.8) for m in (0.2, 0.3, 0.4)if m < s] +              [("embedding", s, m, r) for r in ("v1", "v2") for s in (0.7, 0.8, 0.9) for m in (0.5, 0.6)]


def load(data):
    dev = json.loads((ROOT / data / "split.json").read_text(encoding="utf-8"))["dev"]
    G = {s: json.loads((ROOT / data / "gold" / f"{s}.json").read_text(encoding="utf-8")) for s in dev}
    T = {s: json.loads((ROOT / data / "transcripts" / f"{s}.json").read_text(encoding="utf-8")) for s in dev}
    return dev, G, T


def sources(dev, G):
    out = {"oracle": {s: [dict(meeting_id=l["meeting_id"], role=l["role"], utterance_idxs=l["utterance_idxs"], speaker=l["speaker"], confidence=1.0)
                          for l in gold_links(G[s])] for s in dev}}
    sp = ROOT / "results/phase3/main/merged/single_pass/preds"
    out["single_pass"] = {s: json.loads((sp / f"{s}.json").read_text(encoding="utf-8"))["links"] for s in dev}
    out["single_pass_top4"] = {s: topk(out["single_pass"][s], 4) for s in dev}
    rp = ROOT / "results/phase3/recap/merged/single_pass_recap_roles/preds"
    if rp.exists():
        out["single_pass_recap_roles"] = {s: json.loads((rp / f"{s}.json").read_text(encoding="utf-8"))["links"] for s in dev}
        out["single_pass_recap_roles_top4"] = {s: topk(out["single_pass_recap_roles"][s], 4) for s in dev}
        out["single_pass_recap_roles_dec1"] = {s: per_decision(out["single_pass_recap_roles"][s], 1) for s in dev}
    return out


def option_keys(g):
    keys = list(g["options"])
    vecs = EMB([g["options"][k] for k in keys])
    return keys, vecs


def map_option(text, keys, vecs, g=None):
    """Evaluation-side mapping of a graph version's option text to a gold option key of the set: the option with the most DISTINCTIVE content tokens
    (tokens of that option text not in any other option) present in the text; no distinctive token, or a tie -> nearest option by EMBED_MODEL cosine."""
    if text is None:
        return None
    if g is not None and len(keys) > 1:
        toks = {k: set(tokens(g["options"][k])) for k in keys}
        t = set(tokens(text))
        sc = {k: len((toks[k] - set().union(*(toks[j] for j in keys if j != k))) & t) for k in keys}
        top = max(sc.values())
        if top > 0 and list(sc.values()).count(top) == 1:
            return max(sc, key=sc.get)
    (v,) = EMB([text])
    return keys[int(np.argmax(vecs @ v))]


def gold_key_at(g, k):
    for v in g["versions"]:
        if v["valid_from"] <= k and (v["valid_to"] is None or k < v["valid_to"]):
            return v["option"]
    return None


def eval_set(s, g, tr, preds, lp, matcher_spec):
    links = links_from_predictions(preds, tr)
    kind, same_at, mod_at, rules, *rest = matcher_spec
    kw = dict(rest[0]) if rest else {}
    p = Params(same_at=same_at, modified_at=mod_at, rules=rules, **kw) if kind == "lexical" else Params(rules=rules, **kw)
    matcher = LexicalMatcher(p) if kind == "lexical" else EmbeddingMatcher(EMB, same_at, mod_at)
    graph = DecisionGraph(p, matcher).build(links, EmbeddingLinker(links, lp, EMB))
    golds = gold_links(g)
    pd = [dict(meeting_id=l.meeting_id, role=l.role, utterance_idxs=l.idxs) for l in links]
    pairs = match_links(pd, golds, 1)
    loc = [(links[i], golds[j]["chain"]) for i, j in pairs]
    tp = fp = fn = merges = 0
    for (a, ca), (b, cb) in itertools.combinations(loc, 2):
        same_g, same_p = ca == cb, a.decision == b.decision
        tp += same_g and same_p
        fp += same_p and not same_g
        fn += same_g and not same_p
        merges += same_p and not same_g
    def anchor(chain):
        ds = [l.decision for l, c in loc if c == chain]
        return max(set(ds), key=ds.count) if ds else None
    am, ad = anchor("main"), anchor("distractor")
    l2d_ok = sum(1 for l, c in loc if (c == "main" and l.decision == am) or (c == "distractor" and l.decision == ad and ad != am))
    keys, vecs = option_keys(g)
    nm = g["meta"]["n_meetings"]
    qs = [q for q in g["questions"] if q["type"] in ("as_of", "lookup_final")]
    asof_ok = 0
    for q in qs:
        k = q["answer_facts"]["as_of"] if q["type"] == "as_of" else nm
        v = graph.as_of(am, k) if am else None
        asof_ok += map_option(v["option"] if v else None, keys, vecs, g) == gold_key_at(g, k)
    pv = [map_option(v["option"], keys, vecs, g) for v in graph.versions.get(am, [])] if am else []
    gv = [v["option"] for v in g["versions"]]
    gsup = {(c["at_meeting"], g["versions"][c["to_version"] - 1]["option"]) for c in g["changes"]}
    psup = {(graph.versions[am][i]["valid_from"], pv[i]) for i in range(1, len(pv))} if am else set()
    frag = len({l.decision for l, c in loc if c == "main"})
    return dict(set_id=s, n_links=len(links), n_decisions=len({l.decision for l in links}), n_loc=len(loc), pair_tp=tp, pair_fp=fp, pair_fn=fn, merges=merges,
                l2d_ok=l2d_ok, frag=frag, asof_n=len(qs), asof_ok=asof_ok, seq_ok=int(pv == gv), sup_tp=len(gsup & psup), sup_p=len(psup), sup_g=len(gsup),
                versions_pred=pv, versions_gold=gv)


def agg(rs):
    S_ = lambda k: sum(r[k] for r in rs)
    pp = S_("pair_tp") / (S_("pair_tp") + S_("pair_fp")) if S_("pair_tp") + S_("pair_fp") else 0.0
    pr = S_("pair_tp") / (S_("pair_tp") + S_("pair_fn")) if S_("pair_tp") + S_("pair_fn") else 0.0
    sp = S_("sup_tp") / S_("sup_p") if S_("sup_p") else 0.0
    sr = S_("sup_tp") / S_("sup_g") if S_("sup_g") else 0.0
    f = lambda a, b: 2 * a * b / (a + b) if a + b else 0.0
    return dict(link_P=pp, link_R=pr, link_F1=f(pp, pr), merges=S_("merges"), link_to_decision=S_("l2d_ok") / max(S_("n_loc"), 1),
                frag_mean=S_("frag") / len(rs), asof_acc=S_("asof_ok") / max(S_("asof_n"), 1), asof_n=S_("asof_n"), seq_acc=S_("seq_ok") / len(rs),
                sup_P=sp, sup_R=sr, sup_F1=f(sp, sr), links=S_("n_links"), decisions=S_("n_decisions"), localized=S_("n_loc"))


def ci(rs, key, n=1000, seed=0):
    rng = random.Random(seed)
    xs = sorted(agg([rs[rng.randrange(len(rs))] for _ in rs])[key] for _ in range(n))
    return [round(xs[int(0.025 * n)], 3), round(xs[min(int(0.975 * n), n - 1)], 3)]


def run(src, dev, G, T, lp, ms):
    return [eval_set(s, G[s], T[s], src[s], lp, ms) for s in dev]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/phase4")
    ap.add_argument("--data", default="data/synth")
    a = ap.parse_args()
    dev, G, T = load(a.data)
    srcs = sources(dev, G)
    cands = ["single_pass", "single_pass_top4"]
    base_ms = ("lexical", 0.6, 0.3, "v1")                 # graph.py defaults, used while the linker is tuned
    grid1 = []
    for la, gap, po in itertools.product(LINK_GRID["link_at"], LINK_GRID["gap"], LINK_GRID["proposal_own"]):
        lp = LinkParams(link_at=la, gap=gap, proposal_own=po)
        sc = {c: agg(run(srcs[c], dev, G, T, lp, base_ms)) for c in cands}
        obj = sum((sc[c]["link_F1"] + sc[c]["asof_acc"]) / 2 for c in cands) / len(cands)
        grid1.append(dict(link_at=la, gap=gap, proposal_own=po, objective=round(obj, 4), **{f"{c}_link_F1": round(sc[c]["link_F1"], 3) for c in cands},
                          **{f"{c}_asof": round(sc[c]["asof_acc"], 3) for c in cands}))
        print("link", la, gap, po, round(obj, 3))
    best1 = max(grid1, key=lambda r: (r["objective"], r["link_at"]))
    lp = LinkParams(link_at=best1["link_at"], gap=best1["gap"], proposal_own=best1["proposal_own"])
    grid2 = []
    for ms in MATCH_GRID:
        sc = {c: agg(run(srcs[c], dev, G, T, lp, ms)) for c in cands}
        obj = sum((sc[c]["link_F1"] + sc[c]["asof_acc"]) / 2 for c in cands) / len(cands)
        grid2.append(dict(matcher=ms[0], same_at=ms[1], modified_at=ms[2], rules=ms[3], objective=round(obj, 4), **{f"{c}_asof": round(sc[c]["asof_acc"], 3) for c in cands},
                          **{f"{c}_seq": round(sc[c]["seq_acc"], 3) for c in cands}))
        print("match", ms, round(obj, 3))
    best2 = max(grid2, key=lambda r: (r["objective"], r["matcher"] == "lexical", r["rules"] == "v1"))
    ms = (best2["matcher"], best2["same_at"], best2["modified_at"], best2["rules"])
    v1 = [r for r in grid2 if r["rules"] == "v1"]
    best_v1 = max(v1, key=lambda r: (r["objective"], r["matcher"] == "lexical"))
    ms_v1 = (best_v1["matcher"], best_v1["same_at"], best_v1["modified_at"], "v1")
    final = {}
    runs = [(n, s_, ms) for n, s_ in srcs.items()] + ([(n + " [rules v1, best v1 matcher]", s_, ms_v1) for n, s_ in srcs.items()] if ms[3] != "v1" else [])
    for name, src, m_ in runs:
        rs = run(src, dev, G, T, lp, m_)
        A = agg(rs)
        A.update(link_F1_ci=ci(rs, "link_F1"), asof_ci=ci(rs, "asof_acc"), sup_F1_ci=ci(rs, "sup_F1"), link_to_decision_ci=ci(rs, "link_to_decision"))
        final[name] = dict(summary=A, per_set=rs)
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(dict(selected=dict(linker=best1, matcher=best2), grid_linker=grid1, grid_matcher=grid2, final=final), indent=1, default=str),
                                      encoding="utf-8")
    L = ["# Phase 4 graph quality on synthetic DEV (14 sets; tol 1; bootstrap over sets; ORACLE ANCHORING)", "",
         f"Selected on DEV by the pre-declared objective (mean over single_pass and single_pass_top4 of (linking F1 + as_of accuracy)/2): "
         f"linker link_at={best1['link_at']}, gap={best1['gap']}, proposal_own={best1['proposal_own']}; matcher {ms[0]} same_at={ms[1]} modified_at={ms[2]}, versioning rules {ms[3]}. "
         f"Best v1 matcher (reported for comparison): {ms_v1}. Grids: `results.json`. Linking pairs are dominated by within-main pairs (2 gold decisions a set), so linking P is high by construction; "
         f"read the false-merge column for distractor separation.", "",
         "| source | links | graph decisions | localized | linking P / R / F1 [CI] | main-distractor false merges | link-to-decision [CI] | main fragments | as_of+final acc [CI] (n) | version seq exact | supersession P / R / F1 [CI] |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, d in final.items():
        A = d["summary"]
        L.append(f"| {name} | {A['links']} | {A['decisions']} | {A['localized']} | {A['link_P']:.2f} / {A['link_R']:.2f} / {A['link_F1']:.3f} {A['link_F1_ci']} | {A['merges']} | "
                 f"{A['link_to_decision']:.3f} {A['link_to_decision_ci']} | {A['frag_mean']:.2f} | {A['asof_acc']:.3f} {A['asof_ci']} ({A['asof_n']}) | {A['seq_acc']:.3f} | "
                 f"{A['sup_P']:.2f} / {A['sup_R']:.2f} / {A['sup_F1']:.3f} {A['sup_F1_ci']} |")
    (out / "table.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
