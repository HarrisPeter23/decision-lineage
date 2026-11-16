"""phase3f_eval.py - evaluation of the P3-F configs against single_pass_recap_roles_top4 (reports/phase3_configs.md P3-F), DEV only.
Per config and per half (tune / check / all): (i) decision-scoped role-typed F1 and (ii) headline retrieval lineage completeness at pool 1 through the frozen
Phase 4/5 system (graph v4, linker L2, router RF1, N=12), both with 95% CIs by bootstrap over the half's sets (1000, seed 0); plus role-typed F1, per-role
recall, implicit-resolution recall, links. Applies the pre-declared selection rule.
  HF_HUB_OFFLINE=1 python eval/phase3f_eval.py [--configs single_pass_recap_roles_top4,recap_roles_div4,recap_args_div4] [--tag p3f]
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "synthgen"), str(ROOT / "eval")]
import decision_scope as DS                                                     # noqa: E402
from argdecisionlineage.linking import Embedder                                 # noqa: E402
from phase3_caps import boot as ds_boot, summarize                              # noqa: E402
from phase5_retrieval import HEADLINE, boot as rc_boot, load_preds, run_pool    # noqa: E402
from score import ROLES, score_set                                              # noqa: E402

BASE = "single_pass_recap_roles_top4"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default=f"{BASE},recap_roles_div4,recap_args_div4")
    ap.add_argument("--tag", default="p3f")
    ap.add_argument("--tune-only", action="store_true", help="development stage: score the tune half only (the check half is not looked at)")
    a = ap.parse_args()
    split = json.loads((ROOT / "results/phase3/p3f_split.json").read_text(encoding="utf-8"))
    halves = dict(tune=split["tune"], check=split["check"], all=split["tune"] + split["check"])
    if a.tune_only:
        halves = dict(tune=split["tune"])
    dev = [s for h in halves.values() for s in h]
    dev = list(dict.fromkeys(dev))
    gold = {s: json.loads((ROOT / "data/synth/gold" / f"{s}.json").read_text(encoding="utf-8")) for s in dev}
    trs = {s: json.loads((ROOT / "data/synth/transcripts" / f"{s}.json").read_text(encoding="utf-8")) for s in dev}
    tau, _ = DS.calibrate(ROOT / "data/synth/gold", ROOT / "data/synth/transcripts", dev)
    scopes = {s: DS.Scope(gold[s], trs[s], tau, 1) for s in dev}
    index = json.loads((ROOT / "data/synth/pools/dev/index.json").read_text(encoding="utf-8"))
    pool_of = {index[p]["sets"][0]: p for p in index if p.startswith("dev_k1_")}
    emb = Embedder()
    res = {}
    for cfg in a.configs.split(","):
        try:
            preds = load_preds(cfg, dev)
        except FileNotFoundError:
            print("skip (no outputs yet):", cfg)
            continue
        rows = {s: (score_set(preds[s], gold[s], 1), scopes[s].score(preds[s])) for s in dev}
        rr = []
        for s in dev:
            rr += run_pool(ROOT / "data/synth/pools/dev" / pool_of[s], cfg, emb, gold)
        res[cfg] = {}
        for h, sets in halves.items():
            agg, ds = summarize([rows[s] for s in sets])
            _, ci_ds = ds_boot([rows[s] for s in sets])
            hc = rc_boot([r for r in rr if r["set_id"] in sets], sets, lambda r: r["type"] in HEADLINE)
            res[cfg][h] = dict(ds_f1=round(ds["f1"], 3), ds_f1_ci=ci_ds, headline_completeness=hc[0], headline_ci=hc[1], role_f1=round(agg["role_typed"]["f1"], 3),
                               links=agg["links_pred"], implicit=f"{round((agg['implicit_resolution_recall'] or 0) * agg['implicit_n'])}/{agg['implicit_n']}",
                               recall={r: round(agg["per_role"][r]["r"], 3) for r in ROLES})
        print(cfg, {h: (v["ds_f1"], v["headline_completeness"], v["role_f1"]) for h, v in res[cfg].items()})
    base = res[BASE]
    decision = {}
    if a.tune_only:
        (ROOT / "results/phase3" / f"{a.tag}_eval.json").write_text(json.dumps(dict(results=res), indent=1), encoding="utf-8")
        return
    for cfg, r in res.items():
        if cfg == BASE:
            continue
        c, t = r["check"], r["tune"]
        ok = (c["ds_f1"] > base["check"]["ds_f1"] and c["headline_completeness"] > base["check"]["headline_completeness"]
              and t["ds_f1"] >= base["tune"]["ds_f1"] and t["headline_completeness"] >= base["tune"]["headline_completeness"]
              and r["all"]["role_f1"] >= 0.554 - 0.02)
        decision[cfg] = "goes forward" if ok else "does not qualify"
    out = ROOT / "results/phase3" / f"{a.tag}_eval.json"
    out.write_text(json.dumps(dict(results=res, decision=decision), indent=1), encoding="utf-8")
    print("decision:", decision)


if __name__ == "__main__":
    main()
