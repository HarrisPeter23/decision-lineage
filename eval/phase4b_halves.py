"""phase4b_halves.py - Phase 4 follow-up (2026-11-07): versioning results by the fixed 7/7 tune/check split of results/phase3/p3f_split.json, for rules v1, v3
and v4, on (i) GOLD links with the gold decision assignment (versioning only), (ii) GOLD links through the frozen linker (L2), (iii) SYSTEM links of the final
extractor single_pass_recap_roles_top4 through the frozen linker. Primary: supersession-edge F1; secondary: as_of + lookup_final accuracy (oracle anchoring,
as in Phase 4); also exact version sequences. CPU only, no model calls; existing cached extraction. 95% CI by bootstrap over the half's sets.
NOTE: rules v3/v4 were developed on 2026-11-04 with all 14 DEV sets in view, before this split existed; the check half is therefore NOT held out for them.
  HF_HUB_OFFLINE=1 python eval/phase4b_halves.py -> results/phase4/halves.json
"""
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "eval"), str(ROOT / "synthgen")]
import phase4_graph as P                                    # noqa: E402
import phase4_gold_diag as GD                               # noqa: E402
from argdecisionlineage.linking import LinkParams           # noqa: E402

RULES = {"v1": ("lexical", 0.4, 0.2, "v1"), "v3": ("lexical", 0.4, 0.2, "v3"),
         "v4": ("lexical", 0.4, 0.2, "v4", dict(min_confidence=0.9, own_at=0.2))}
LP = LinkParams(link_at=0.4, gap=60, team_at=0.2)            # the frozen linker (Phase 4 + L2)


def ci(rs, key, n=1000, seed=0):
    rng = random.Random(seed)
    xs = sorted(P.agg([rs[rng.randrange(len(rs))] for _ in rs])[key] for _ in range(n))
    return [round(xs[int(0.025 * n)], 3), round(xs[min(int(0.975 * n), n - 1)], 3)]


def main():
    split = json.loads((ROOT / "results/phase3/p3f_split.json").read_text(encoding="utf-8"))
    halves = dict(tune=split["tune"], check=split["check"], all=split["tune"] + split["check"])
    dev, G, T = P.load("data/synth")
    srcs = P.sources(dev, G)
    out = {}
    for rname, ms in RULES.items():
        kw = ms[4] if len(ms) > 4 else {}
        seq_i = {s: GD.run_set(G[s], T[s], ms[3], True, kw)["ok"] for s in dev}           # (i) gold links + gold decision assignment
        res = {}
        for cond, src in (("gold_links_linker", "oracle"), ("system_links", "single_pass_recap_roles_top4")):
            rows = {r["set_id"]: r for r in P.run(srcs[src], dev, G, T, LP, ms)}
            res[cond] = {}
            for h, sets in halves.items():
                rs = [rows[s] for s in sets]
                A = P.agg(rs)
                res[cond][h] = dict(sup_P=round(A["sup_P"], 3), sup_R=round(A["sup_R"], 3), sup_F1=round(A["sup_F1"], 3), sup_ci=ci(rs, "sup_F1"),
                                    asof=round(A["asof_acc"], 3), asof_ci=ci(rs, "asof_acc"), seq_exact=f"{sum(r['seq_ok'] for r in rs)}/{len(rs)}",
                                    edges=f"{sum(r['sup_p'] for r in rs)} pred / {sum(r['sup_g'] for r in rs)} gold")
        res["gold_links_gold_assignment"] = {h: dict(seq_exact=f"{sum(seq_i[s] for s in sets)}/{len(sets)}") for h, sets in halves.items()}
        out[rname] = res
        for cond in ("gold_links_linker", "system_links"):
            print(rname, cond, {h: (v["sup_F1"], v["asof"], v["seq_exact"]) for h, v in res[cond].items()})
        print(rname, "gold assignment seq", {h: v["seq_exact"] for h, v in res["gold_links_gold_assignment"].items()})
    (ROOT / "results/phase4/halves.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
