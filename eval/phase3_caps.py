"""phase3_caps.py - re-scores every Phase 3 DEV config (no new model calls) with the old metric and the NEW decision-scoped metric (eval/decision_scope.py),
under the widened cap grid requested at the CHECKPOINT 3 review:
    per-meeting cap K in {2, 3, 4, 6, 8} and no cap  (eval/phase3_topk.py rule: keep the K most confident links per meeting, ties: earlier utterance)
    per-decision cap K in {1, 2, 3}: keep the K most confident links per (meeting, role, system decision name); only for configs whose links carry a decision name
Span tolerance 1 (primary). Bootstrap over DEV sets, 1000 resamples, seed 0; old F1 and decision-scoped F1 are resampled together.
  python eval/phase3_caps.py [--out results/phase3/rescore]
DEV only (asserted). Writes table.md and results.json.
"""
import argparse
import collections
import json
import pathlib
import random
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "synthgen"))
sys.path.insert(0, str(ROOT / "eval"))
from score import ROLES, aggregate, score_set            # noqa: E402
from phase3_topk import topk                              # noqa: E402
import decision_scope as DS                               # noqa: E402

SOURCES = [  # (config, prediction dir, candidate?)  candidates are the configs that can be carried into Phase 5
    ("single_pass", "results/phase3/main/merged/single_pass/preds", True),
    ("mp_p123", "results/phase3/main/merged/mp_p123/preds", False),
    ("mp_p123_verify", "results/phase3/main/merged/mp_p123_verify/preds", False),
    ("single_pass_recap_roles", "results/phase3/recap/merged/single_pass_recap_roles/preds", True),
    ("single_pass [forced 1,200-token chunks; acceptance test only]", "results/phase3/chunk/merged/single_pass/preds", False),
]
MEETING_K = [None, 2, 3, 4, 6, 8]
DECISION_K = [1, 2, 3]


def norm(name):
    return " ".join(re.findall(r"[a-z0-9]+", (name or "").lower())) or "?"


def per_decision(links, k):
    by = collections.defaultdict(list)
    for l in links:
        by[(l["meeting_id"], norm(l.get("decision")))].append(l)
    out = []
    for ls in by.values():
        out += sorted(ls, key=lambda l: (-float(l.get("confidence", 0)), min(l["utterance_idxs"])))[:k]
    return out


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def summarize(rows):
    """rows: per-set (score_set result, decision-scope counts)."""
    a = aggregate([r for r, _ in rows])
    tp = sum(d["tp"] for _, d in rows)
    fps = sum(d["fp_scoped"] for _, d in rows)
    ng = sum(d["n_gold"] for _, d in rows)
    p_ds, _, f_ds = prf(tp, fps, ng - tp)
    return a, dict(p=p_ds, f1=f_ds, fp_scoped=fps, fp_all=sum(d["fp_all"] for _, d in rows))


def boot(rows, n=1000, seed=0):
    rng = random.Random(seed)
    f, fds = [], []
    for _ in range(n):
        s = [rows[rng.randrange(len(rows))] for _ in rows]
        a, d = summarize(s)
        f.append(a["role_typed"]["f1"])
        fds.append(d["f1"])
    q = lambda xs: [round(sorted(xs)[int(0.025 * n)], 3), round(sorted(xs)[min(int(0.975 * n), n - 1)], 3)]
    return q(f), q(fds)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/phase3/rescore")
    ap.add_argument("--data", default="data/synth")
    ap.add_argument("--tol", type=int, default=1)
    a = ap.parse_args()
    dev = json.loads((ROOT / a.data / "split.json").read_text(encoding="utf-8"))["dev"]
    gold = {s: json.loads((ROOT / a.data / "gold" / f"{s}.json").read_text(encoding="utf-8")) for s in dev}
    trs = {s: json.loads((ROOT / a.data / "transcripts" / f"{s}.json").read_text(encoding="utf-8")) for s in dev}
    tau, cal = DS.calibrate(ROOT / a.data / "gold", ROOT / a.data / "transcripts", dev)
    scopes = {s: DS.Scope(gold[s], trs[s], tau, a.tol) for s in dev}
    cal["utterance_coverage_mean"] = round(sum(sc.utterance_coverage() for sc in scopes.values()) / len(scopes), 3)
    print("calibration:", cal)
    results = []
    for cfg, d, cand in SOURCES:
        pd = ROOT / d
        if not pd.exists():
            print("skip (not available yet):", cfg)
            continue
        preds = {}
        for s in dev:
            f = pd / f"{s}.json"
            assert f.exists(), f"{cfg}: missing {s}"
            preds[s] = json.loads(f.read_text(encoding="utf-8"))["links"]
        has_dec = all("decision" in l for ls in preds.values() for l in ls)
        caps = [("meeting", k) for k in MEETING_K] + ([("decision", k) for k in DECISION_K] if has_dec else [])
        variants = [(cfg, caps, dev)]
        if cfg == "single_pass":
            variants.append(("single_pass [sensitivity: set_01019 excluded, its m3 call failed]", [("meeting", None), ("meeting", 4)], [s for s in dev if s != "set_01019"]))
        for name, cs, sets in variants:
            for kind, k in cs:
                rows = []
                for s in sets:
                    ls = preds[s] if k is None else (topk(preds[s], k) if kind == "meeting" else per_decision(preds[s], k))
                    rows.append((score_set(ls, gold[s], a.tol), scopes[s].score(ls)))
                agg, ds = summarize(rows)
                ci, ci_ds = boot(rows)
                pr = agg["per_role"]
                results.append(dict(config=name, candidate=cand and name == cfg, cap="none" if k is None else f"{kind} K={k}", sets=len(sets), links=agg["links_pred"],
                                    P=round(agg["role_typed"]["p"], 3), R=round(agg["role_typed"]["r"], 3), F1=round(agg["role_typed"]["f1"], 3), F1_ci=ci,
                                    P_ds=round(ds["p"], 3), F1_ds=round(ds["f1"], 3), F1_ds_ci=ci_ds, fp_scoped=ds["fp_scoped"], fp_all=ds["fp_all"],
                                    implicit=f"{round(agg['implicit_resolution_recall'] * agg['implicit_n'])}/{agg['implicit_n']}",
                                    per_role={r: dict(f1=round(pr[r]["f1"], 3), r=round(pr[r]["r"], 3), support=pr[r]["support"]) for r in ROLES}))
                print(f"{name[:40]:<40} {results[-1]['cap']:<14} F1 {results[-1]['F1']:.3f} F1_ds {results[-1]['F1_ds']:.3f}")
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(dict(calibration=cal, tol=a.tol, rows=results), indent=1), encoding="utf-8")
    L = [f"# Phase 3 DEV re-score: old metric + NEW decision-scoped metric, widened cap grid (tol {a.tol}; bootstrap over {len(dev)} DEV sets)", "",
         "Generated by `eval/phase3_caps.py` from existing predictions (no new model calls). P/R/F1 = role-typed, as before (precision is a lower bound). "
         "P_ds/F1_ds = NEW decision-scoped metric (`eval/decision_scope.py`): an unmatched prediction is a false positive only if it is attached to a gold-annotated decision. "
         f"TAU = {cal['tau']} (10th percentile of gold-link-to-own-decision similarity, gold only); share of all DEV utterances in scope at this TAU: {cal['utterance_coverage_mean']}. "
         f"Gold links whose own decision is the most similar: {cal['own_decision_most_similar']}.", "",
         "| config | cap | links | P | R | F1 [95% CI] | P_ds | F1_ds [95% CI] | implicit | challenge F1 / R | reconsid. F1 / R | rationale F1 / R | evidence F1 / R |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        pr = r["per_role"]
        cell = lambda x: f"{pr[x]['f1']:.2f} / {pr[x]['r']:.2f}"
        L.append(f"| {r['config']} | {r['cap']} | {r['links']} | {r['P']:.3f} | {r['R']:.3f} | {r['F1']:.3f} [{r['F1_ci'][0]:.2f}, {r['F1_ci'][1]:.2f}] | {r['P_ds']:.3f} | "
                 f"{r['F1_ds']:.3f} [{r['F1_ds_ci'][0]:.2f}, {r['F1_ds_ci'][1]:.2f}] | {r['implicit']} | {cell('challenge')} | {cell('reconsideration')} | {cell('rationale')} | {cell('evidence')} |")
    sup = results[0]["per_role"] if results else {}
    L += ["", "Gold support per role (DEV): " + ", ".join(f"{k} {v['support']}" for k, v in sup.items()) + "."]
    (out / "table.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("wrote", out / "table.md")


if __name__ == "__main__":
    main()
