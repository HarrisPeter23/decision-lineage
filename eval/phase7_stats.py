"""phase7_stats.py - the pre-registered H1 tests (FREEZE section 14), exactly as frozen. TEST, pool size 1, headline questions.
Per question, per system: cited-lineage F1 (primary), cited precision, cited recall (completeness), completeness@k (k from DEV gold), NLI supported-claim
rate, NLI citation precision, answer correctness (exact match, else the granite rubric 1 / 0.5 / 0, flag policy; unparsed = 0).
Per-set means, then a paired bootstrap over the 22 TEST sets: 10,000 resamples, seed 0, d = mean over drawn sets of (mine - baseline); one-sided
p = share of d <= 0; Holm at alpha 0.05 within the primary family (2 tests) and within the secondary family (19 tests). 95% percentile CIs.
  python eval/phase7_stats.py -> results/phase7/h1_tests.json, results/phase7/h1_table.md
"""
import json
import pathlib
import random
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "eval"), str(ROOT / "synthgen")]
import lineage_f1 as LF      # noqa: E402

HEADLINE = LF.HEADLINE
SYSTEMS = {"mine": "lineage@test_k1", "evowiki_style": "evowiki_style@test_k1", "graphiti": "graphiti@test_k1", "vector_rag": "vector_rag@test_k1"}
SCORE = ROOT / "results/phase7/score"
N_BOOT, SEED, ALPHA = 10_000, 0, 0.05
SECONDARY = ["r", "p", "r_at_k", "nli_supported", "nli_precision", "correct"]
VERD = {"correct": 1.0, "partial": 0.5, "incorrect": 0.0}


def judge_verdicts():
    J = {}
    for f in (ROOT / "results/phase7/judge").rglob("batch_out.jsonl"):
        for l in f.read_text(encoding="utf-8").splitlines():
            if l.strip():
                x = json.loads(l)
                m = re.search(r'"verdict"\s*:\s*"(correct|partial|incorrect)"', x.get("raw") or "", re.I)
                J[x["id"]] = VERD[m.group(1).lower()] if m else 0.0          # unparseable verdict = incorrect (as on DEV)
    return J


def per_question(tag, K, J):
    A = {json.loads(l)["qid"]: json.loads(l) for l in (SCORE / tag / "answers.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    cited = {q: ([(m, i) for s in a["sentences"] for m, i in s["cites"]] if a["parse_ok"] else []) for q, a in A.items()}
    rows = {r["qid"]: r for r in LF.rows_for(cited, "1", K, split="test")}
    for q, r in rows.items():
        a = A[q]
        ch = a["checks"] if a["parse_ok"] else []
        r["nli_supported"] = sum(c["supported"] for c in ch) / len(ch) if ch else 0.0
        nrel = sum(len(c["relevant"]) for c in ch)
        r["nli_precision"] = sum(sum(c["relevant"]) for c in ch) / nrel if nrel else 0.0
        if not a["parse_ok"]:
            r["correct"] = 0.0
        elif a["exact"] is not None:
            r["correct"] = a["exact"]
        else:
            r["correct"] = J.get(f"{q}@{tag}@flag", 0.0)
    return rows


def set_means(rows, key):
    by = {}
    for r in rows.values():
        by.setdefault(r["set_id"], []).append(r[key])
    return {s: sum(v) / len(v) for s, v in by.items()}


def paired(a, b):
    sets = sorted(set(a) & set(b))
    d = [a[s] - b[s] for s in sets]
    rng = random.Random(SEED)
    xs = sorted(sum(d[rng.randrange(len(d))] for _ in d) / len(d) for _ in range(N_BOOT))
    return dict(diff=round(sum(d) / len(d), 4), ci=[round(xs[int(0.025 * N_BOOT)], 4), round(xs[int(0.975 * N_BOOT) - 1], 4)],
                p=round(sum(x <= 0 for x in xs) / N_BOOT, 4), n_sets=len(sets))


def holm(tests):
    order = sorted(tests, key=lambda t: t["p"])
    m, stop = len(order), False
    for i, t in enumerate(order):
        thr = ALPHA / (m - i)
        t["holm_threshold"] = round(thr, 5)
        t["reject_H0"] = (not stop) and t["p"] <= thr
        stop = stop or not t["reject_H0"]
    return tests


def boot_mean(sm):
    sets = sorted(sm)
    rng = random.Random(SEED)
    xs = sorted(sum(sm[sets[rng.randrange(len(sets))]] for _ in sets) / len(sets) for _ in range(N_BOOT))
    return [round(sum(sm.values()) / len(sm), 4), [round(xs[int(0.025 * N_BOOT)], 4), round(xs[int(0.975 * N_BOOT) - 1], 4)]]


def main():
    K = LF.k_at_from_dev_gold()
    J = judge_verdicts()
    R = {s: per_question(t, K, J) for s, t in SYSTEMS.items()}
    means = {s: {m: boot_mean(set_means(R[s], m)) for m in ["f1"] + SECONDARY} for s in R}
    prim = holm([dict(family="primary", metric="f1", vs=b, **paired(set_means(R["mine"], "f1"), set_means(R[b], "f1"))) for b in ("evowiki_style", "graphiti")])
    sec = [dict(family="secondary", metric=m, vs=b, **paired(set_means(R["mine"], m), set_means(R[b], m))) for b in ("evowiki_style", "graphiti") for m in SECONDARY]
    sec += [dict(family="secondary", metric=m, vs="vector_rag", **paired(set_means(R["mine"], m), set_means(R["vector_rag"], m))) for m in ["f1"] + SECONDARY]
    sec = holm(sec)
    out = dict(k_at=K, n_questions={s: len(r) for s, r in R.items()}, means=means, primary=prim, secondary=sec)
    (ROOT / "results/phase7/h1_tests.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    L = ["# H1 tests on TEST (pool 1, headline questions; paired bootstrap over sets, 10,000 resamples, seed 0; Holm within family)", "",
         "| family | metric | mine vs | diff [95% CI] | one-sided p | Holm threshold | H0 rejected |", "|---|---|---|---|---|---|---|"]
    for t in prim + sec:
        L.append(f"| {t['family']} | {t['metric']} | {t['vs']} | {t['diff']:+.3f} [{t['ci'][0]:+.3f}, {t['ci'][1]:+.3f}] | {t['p']:.4f} | {t['holm_threshold']} | {'yes' if t['reject_H0'] else 'no'} |")
    L += ["", "| system | " + " | ".join(["f1"] + SECONDARY) + " |", "|---|" + "---|" * (1 + len(SECONDARY))]
    for s, mm in means.items():
        L.append(f"| {s} | " + " | ".join(f"{mm[m][0]:.3f} [{mm[m][1][0]:.2f}, {mm[m][1][1]:.2f}]" for m in ["f1"] + SECONDARY) + " |")
    (ROOT / "results/phase7/h1_table.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
