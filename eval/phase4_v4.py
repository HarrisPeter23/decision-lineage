"""phase4_v4.py - CHECKPOINT 4 review item 4: the tightened rule config v4 (argdecisionlineage/graph.py V4a-V4b on top of v3), tuned on DEV.
Objective pre-declared in reports/phase4.md section 8 (commit 297fbbb): mean supersession-edge F1 over the three extraction candidates; ties: mean as_of
accuracy, then the higher min_confidence. Linker fixed (link_at 0.4, gap 60). Oracle anchoring, as in Phase 4. DEV only.
  HF_HUB_OFFLINE=1 python eval/phase4_v4.py   -> results/phase4/v4/{table.md,results.json}
"""
import itertools
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "eval")]
import phase4_graph as P                                    # noqa: E402
from argdecisionlineage.linking import LinkParams           # noqa: E402

CANDS = ["single_pass", "single_pass_top4", "single_pass_recap_roles_top4"]
GRID = dict(min_confidence=[0.5, 0.6, 0.7, 0.8, 0.9], own_at=[0.1, 0.2, 0.3], same_at=[0.4, 0.5, 0.6])


def main():
    dev, G, T = P.load("data/synth")
    srcs = P.sources(dev, G)
    lp = LinkParams(link_at=0.4, gap=60)
    grid = []
    for mc, oa, sa in itertools.product(GRID["min_confidence"], GRID["own_at"], GRID["same_at"]):
        ms = ("lexical", sa, 0.2, "v4", dict(min_confidence=mc, own_at=oa))
        sc = {c: P.agg(P.run(srcs[c], dev, G, T, lp, ms)) for c in CANDS}
        grid.append(dict(min_confidence=mc, own_at=oa, same_at=sa, sup_F1=round(sum(sc[c]["sup_F1"] for c in CANDS) / 3, 4),
                         asof=round(sum(sc[c]["asof_acc"] for c in CANDS) / 3, 4), **{f"{c}_sup_F1": round(sc[c]["sup_F1"], 3) for c in CANDS}))
    best = max(grid, key=lambda r: (r["sup_F1"], r["asof"], r["min_confidence"]))
    print("selected:", best)
    configs = [("v1 (Phase 4 selection)", ("lexical", 0.4, 0.2, "v1")),
               ("v3 (gold-link alignment, defaults)", ("lexical", 0.4, 0.2, "v3")),
               ("v4 (tightened, tuned)", ("lexical", best["same_at"], 0.2, "v4", dict(min_confidence=best["min_confidence"], own_at=best["own_at"])))]
    rows = []
    for cname, ms in configs:
        for src in ["oracle"] + CANDS:
            rs = P.run(srcs[src], dev, G, T, lp, ms)
            A = P.agg(rs)
            rows.append(dict(rules=cname, source=src, sup_P=A["sup_P"], sup_R=A["sup_R"], sup_F1=A["sup_F1"], sup_ci=P.ci(rs, "sup_F1"), asof=A["asof_acc"],
                             asof_ci=P.ci(rs, "asof_acc"), seq=A["seq_acc"], n_sup_pred=sum(r["sup_p"] for r in rs), n_sup_gold=sum(r["sup_g"] for r in rs)))
    out = ROOT / "results/phase4/v4"
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(dict(selected=best, grid=grid, rows=rows), indent=1), encoding="utf-8")
    L = ["# Phase 4 versioning: v1 vs v3 vs v4 on synthetic DEV (oracle anchoring; 95% CI bootstrap over 14 sets)", "",
         f"v4 selected by the pre-declared objective (mean supersession-edge F1 over the three candidates): min_confidence={best['min_confidence']}, "
         f"own_at={best['own_at']}, same_at={best['same_at']} (modified_at 0.2; linker link_at 0.4, gap 60). Grid of {len(grid)} cells in `results.json`.", "",
         "| rules | source | supersession P / R / F1 [CI] | predicted / gold edges | as_of + final acc [CI] (n=42) | version seq exact |", "|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['rules']} | {r['source']} | {r['sup_P']:.2f} / {r['sup_R']:.2f} / {r['sup_F1']:.3f} {r['sup_ci']} | {r['n_sup_pred']} / {r['n_sup_gold']} | "
                 f"{r['asof']:.3f} {r['asof_ci']} | {r['seq']:.3f} |")
    (out / "table.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
