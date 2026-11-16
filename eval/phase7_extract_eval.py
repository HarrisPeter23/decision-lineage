"""phase7_extract_eval.py - extraction-level metrics of the final extractor on TEST pool 1 (and on DEV for comparison), with the frozen scorer
synthgen/score.py (tol 1, the primary matching, FREEZE section 7) and the frozen top-4 cap (eval/phase3_topk.topk).
  six roles : as scored since Phase 3 (localization, role-typed P/R/F1, per role, chain completeness, implicit-resolution recall)
  four class: the pre-registered secondary metric of FREEZE section 11. Rationale, evidence and challenge are merged into one class "argument"
              (classes: proposal, argument, reconsideration, resolution). Implemented by relabelling all three as "rationale" in BOTH the
              predictions and the gold before the unchanged scorer runs, so the scorer's "rationale" row is the "argument" class.
Bootstrap 1,000 over sets, seed 0 (the scorer's own). Prediction meeting ids are mapped back to set meeting ids through the pool's private map
(harness side; the system never sees it).
  python eval/phase7_extract_eval.py -> results/phase7/extract_eval.json, results/phase7/extract_eval.md
"""
import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "eval"), str(ROOT / "synthgen")]
import score as SC                      # noqa: E402
from phase3_topk import topk            # noqa: E402

ARG = {"rationale", "evidence", "challenge"}


def four(links):
    out = []
    for l in links:
        l = dict(l)
        if l["role"] in ARG:
            l["role"] = "rationale"
        out.append(l)
    return out


def four_gold(g):
    g = copy.deepcopy(g)
    g["chain"] = four(g["chain"])
    if g.get("distractor"):
        g["distractor"]["chain"] = four(g["distractor"]["chain"])
    return g


def test_pairs():
    P = ROOT / "data/synth/pools/test"
    out = []
    for pdir in sorted(P.glob("test_k1_*")):
        priv = json.loads((pdir / "private_map.json").read_text(encoding="utf-8"))
        (sid,) = priv["_sets"]
        pred = json.loads((ROOT / "results/phase7/extract/preds" / f"{pdir.name}.json").read_text(encoding="utf-8"))["links"]
        links = [dict(l, meeting_id=priv[l["meeting_id"]]["meeting_id"]) for l in topk(pred, 4)]
        gold = json.loads((ROOT / "data/synth/gold" / f"{sid}.json").read_text(encoding="utf-8"))
        out.append((links, gold))
    return out


def dev_pairs():
    out = []
    for f in sorted((ROOT / "results/phase3/recap/merged/single_pass_recap_roles/preds").glob("set_*.json")):
        links = topk(json.loads(f.read_text(encoding="utf-8"))["links"], 4)
        gold = json.loads((ROOT / "data/synth/gold" / f.name).read_text(encoding="utf-8"))
        out.append((links, gold))
    return out


def run(pairs, mode):
    rs = [SC.score_set(four(p) if mode == "four" else p, four_gold(g) if mode == "four" else g, 1) for p, g in pairs]
    res = SC.aggregate(rs)
    res["bootstrap_95ci"] = SC.bootstrap(rs, 1000)
    return res


def main():
    R = {}
    for split, pairs in (("test", test_pairs()), ("dev", dev_pairs())):
        for mode in ("six", "four"):
            R[f"{split}_{mode}"] = run(pairs, mode)
    (ROOT / "results/phase7/extract_eval.json").write_text(json.dumps(R, indent=1), encoding="utf-8")
    L = ["# Extraction-level metrics, single_pass_recap_roles_top4 (tol 1; bootstrap 1,000 over sets)", "",
         "| split / roles | sets | localization F1 | role-typed P | role-typed R | role-typed F1 [95% CI] | chain completeness | implicit-res. recall |", "|---|---|---|---|---|---|---|---|"]
    for k, r in R.items():
        ci = r["bootstrap_95ci"]["role_typed_f1_ci"]
        L.append(f"| {k} | {r['sets']} | {r['localization']['f1']:.3f} | {r['role_typed']['p']:.3f} | {r['role_typed']['r']:.3f} | {r['role_typed']['f1']:.3f} [{ci[0]:.2f}, {ci[1]:.2f}] | "
                 f"{r['chain_completeness']:.3f} | {r['implicit_resolution_recall'] if r['implicit_resolution_recall'] is None else round(r['implicit_resolution_recall'], 3)} (n={r['implicit_n']}) |")
    L += ["", "Per role (TEST, six roles): " + ", ".join(f"{k} F1 {v['f1']:.2f} (n={v['support']})" for k, v in R["test_six"]["per_role"].items()),
          "Per class (TEST, four classes; 'rationale' = argument): " + ", ".join(f"{k} F1 {v['f1']:.2f} (n={v['support']})" for k, v in R["test_four"]["per_role"].items() if v["support"])]
    (ROOT / "results/phase7/extract_eval.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
