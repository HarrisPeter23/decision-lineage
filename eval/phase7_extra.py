"""phase7_extra.py - the TEST analyses declared next to the primary test, using the FROZEN functions of eval/phase7_stats.py unchanged:
  (1) D-35: H1 recomputed on the failure-free subset (results/phase7/d35_subset.json; fixed before any TEST score). Same paired bootstrap
      (10,000 resamples, seed 0), Holm over the same 2 tests. Secondary analysis; it does not replace the primary test.
  (2) Ablations (FREEZE section 15): per-metric means with 95% CIs, and paired differences vs the full system with CIs. These are
      descriptive (no test is pre-registered for the ablations).
  (3) H2 (descriptive): correctness on lookup_final + as_of for every system, with 95% CIs over sets.
  python eval/phase7_extra.py -> results/phase7/extra_tests.json, results/phase7/extra_table.md
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "eval"), str(ROOT / "synthgen")]
import phase7_stats as S       # noqa: E402

ABL = {"no_typing": "no_typing@test_k1", "no_conflict_resolution": "no_conflict_resolution@test_k1", "static_graph": "static_graph@test_k1"}
METRICS = ["f1"] + S.SECONDARY


def main():
    K = S.LF.k_at_from_dev_gold()
    J = S.judge_verdicts()
    R = {s: S.per_question(t, K, J) for s, t in {**S.SYSTEMS, **ABL}.items()}
    sub = set(json.loads((ROOT / "results/phase7/d35_subset.json").read_text(encoding="utf-8"))["subset"])
    keep = lambda sm: {s: v for s, v in sm.items() if s in sub}
    d35 = S.holm([dict(family="D-35 failure-free subset", metric="f1", vs=b, **S.paired(keep(S.set_means(R["mine"], "f1")), keep(S.set_means(R[b], "f1"))))
                  for b in ("evowiki_style", "graphiti")])
    abl_means = {a: {m: S.boot_mean(S.set_means(R[a], m)) for m in METRICS} for a in ["mine"] + list(ABL)}
    abl_diff = {a: {m: S.paired(S.set_means(R["mine"], m), S.set_means(R[a], m)) for m in METRICS} for a in ABL}
    h2 = {}
    for s, t in {**S.SYSTEMS, **ABL}.items():          # ablation rows added 2026-11-10 at the user's request (descriptive, no test)
        A = [json.loads(l) for l in (S.SCORE / t / "answers.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        by = {}
        for a in A:
            if a["type"] in ("lookup_final", "as_of"):
                by.setdefault(a["set_id"], []).append(a["exact"] if a["parse_ok"] and a["exact"] is not None else 0.0)
        h2[s] = S.boot_mean({k: sum(v) / len(v) for k, v in by.items()}) + [sum(len(v) for v in by.values())]
    out = dict(d35=dict(n_sets=len(sub), tests=d35), ablations=dict(means=abl_means, diff_vs_full=abl_diff), h2_lookup_asof_correctness=h2)
    (ROOT / "results/phase7/extra_tests.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    L = [f"# D-35: H1 on the failure-free subset ({len(sub)} of 22 sets; Holm over 2)", "", "| mine vs | diff [95% CI] | one-sided p | Holm thr. | rejected | n sets |", "|---|---|---|---|---|---|"]
    for t in d35:
        L.append(f"| {t['vs']} | {t['diff']:+.3f} [{t['ci'][0]:+.3f}, {t['ci'][1]:+.3f}] | {t['p']:.4f} | {t['holm_threshold']} | {'yes' if t['reject_H0'] else 'no'} | {t['n_sets']} |")
    L += ["", "# Ablations (descriptive): means [95% CI]", "", "| config | " + " | ".join(METRICS) + " |", "|---|" + "---|" * len(METRICS)]
    for a, mm in abl_means.items():
        L.append(f"| {a} | " + " | ".join(f"{mm[m][0]:.3f} [{mm[m][1][0]:.2f}, {mm[m][1][1]:.2f}]" for m in METRICS) + " |")
    L += ["", "# Ablations: full system minus ablation, paired diff [95% CI]", "", "| ablation | " + " | ".join(METRICS) + " |", "|---|" + "---|" * len(METRICS)]
    for a, dd in abl_diff.items():
        L.append(f"| {a} | " + " | ".join(f"{dd[m]['diff']:+.3f} [{dd[m]['ci'][0]:+.2f}, {dd[m]['ci'][1]:+.2f}]" for m in METRICS) + " |")
    L += ["", "# H2 (descriptive): correctness on lookup_final + as_of, mean [95% CI] (n questions)", "", "| system | correctness | n |", "|---|---|---|"]
    for s, v in h2.items():
        L.append(f"| {s} | {v[0]:.3f} [{v[1][0]:.2f}, {v[1][1]:.2f}] | {v[2]} |")
    (ROOT / "results/phase7/extra_table.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
