"""phase5_final.py - stage 2 of eval/phase5_score.py: joins the granite rubric verdicts, aggregates every pre-declared Phase 5 metric (section 0b), applies the
flagged-sentence policy rule, and writes results/phase5/score/<tag>/{summary.json, table.md}. Bootstrap over DEV sets (1000, seed 0)."""
import json
import pathlib
import random
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
HEADLINE = ("why_changed", "evidence_to_reconsider", "full_lineage")
SCORE = {"correct": 1.0, "partial": 0.5, "incorrect": 0.0}


def verdict(raw):
    m = re.search(r'"verdict"\s*:\s*"(correct|partial|incorrect)"', raw or "", re.I)
    return SCORE[m.group(1).lower()] if m else None


def boot(rows, f, sets, n=1000, seed=0):
    """f(row) -> value or None; mean over rows; CI by resampling sets."""
    by = {}
    for r in rows:
        v = f(r)
        if v is not None:
            by.setdefault(r["set_id"], []).append(v)
    ss = [s for s in sets if s in by]
    if not ss:
        return None
    mean = lambda xs: (lambda v: sum(v) / len(v) if v else 0.0)([x for s in xs for x in by[s]])
    rng = random.Random(seed)
    b = sorted(mean([ss[rng.randrange(len(ss))] for _ in ss]) for _ in range(n))
    return [round(mean(ss), 3), [round(b[int(0.025 * n)], 3), round(b[min(int(0.975 * n), n - 1)], 3)], sum(len(by[s]) for s in ss)]


def main(a):
    d = ROOT / (getattr(a, "score_root", None) or "results/phase5/score") / a.tag
    A = [json.loads(l) for l in (d / "answers.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    J = {}
    for f in pathlib.Path(a.judge).rglob("batch_out.jsonl"):
        for l in f.read_text(encoding="utf-8").splitlines():
            if l.strip():
                x = json.loads(l)
                J[x["id"]] = x
    unparsed = 0
    for r in A:
        for pol in ("flag", "drop"):
            if r["exact"] is not None:
                r[f"correct_{pol}"] = r["exact"]
            else:
                v = verdict(J.get(f"{r['qid']}@{a.tag}@{pol}", {}).get("raw"))
                unparsed += v is None
                r[f"correct_{pol}"] = 0.0 if v is None else v                      # an unparseable verdict counts as incorrect (stated)
        if not r["parse_ok"]:
            r["correct_flag"] = r["correct_drop"] = 0.0
    sets = sorted({r["set_id"] for r in A})
    sent = lambda r, k: (sum(c[k] for c in r["checks"]) / len(r["checks"])) if r["checks"] else 0.0
    M = {}
    for name, sel in (("headline", lambda r: r["type"] in HEADLINE), ("all", lambda r: True)):
        g = lambda f: boot(A, lambda r: f(r) if sel(r) else None, sets)
        M[name] = dict(
            correctness_flag=g(lambda r: r["correct_flag"]), correctness_drop=g(lambda r: r["correct_drop"]),
            supported_claim_rate=g(lambda r: sent(r, "supported")),
            citation_precision=g(lambda r: (sum(sum(c["relevant"]) for c in r["checks"]) / max(1, sum(len(c["relevant"]) for c in r["checks"]))) if r["checks"] else None),
            hallucination_rate=g(lambda r: sent(r, "hallucinated") if r["checks"] else None),
            lexical_ok=g(lambda r: sent(r, "lexical_ok") if r["checks"] else None),
            uncited_share=g(lambda r: (sum(c["n_cites"] == 0 for c in r["checks"]) / len(r["checks"])) if r["checks"] else None),
            retrieval_completeness=g(lambda r: r["retrieval_completeness"]),
            expl_completeness_flag=g(lambda r: r["expl_completeness_flag"]), expl_completeness_drop=g(lambda r: r["expl_completeness_drop"]))
    per_type = {t: dict(n=sum(r["type"] == t for r in A), correctness=boot(A, lambda r, t=t: r["correct_flag"] if r["type"] == t else None, sets),
                        supported=boot(A, lambda r, t=t: sent(r, "supported") if r["type"] == t and r["checks"] else None, sets))
                for t in sorted({r["type"] for r in A})}
    fp = [r for r in A if r["false_premise"]]
    dc = M["headline"]["correctness_drop"][0] - M["headline"]["correctness_flag"][0]
    dl = M["headline"]["expl_completeness_drop"][0] - M["headline"]["expl_completeness_flag"][0]
    dca = M["all"]["correctness_drop"][0] - M["all"]["correctness_flag"][0]
    dla = M["all"]["expl_completeness_drop"][0] - M["all"]["expl_completeness_flag"][0]
    policy = "drop" if min(dc, dl, dca, dla) >= -0.02 else "flag"
    summary = dict(tag=a.tag, n=len(A), parse_ok=sum(r["parse_ok"] for r in A), unknown_cites=sum(r["unknown_cites"] for r in A), judge_unparsed=unparsed,
                   n_sentences=sum(len(r["checks"]) for r in A), metrics=M, per_type=per_type,
                   false_premise=dict(n=len(fp), regex_ok=sum(bool(r["false_premise_ok"]) for r in fp), judge=[r["correct_flag"] for r in fp]),
                   policy=dict(rule="drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)", deltas=dict(
                       headline_correctness=round(dc, 3), headline_completeness=round(dl, 3), all_correctness=round(dca, 3), all_completeness=round(dla, 3)), chosen=policy),
                   latency=dict(mean_s=round(sum(r["secs"] or 0 for r in A) / len(A), 2), mean_in=round(sum(r["in_tok"] or 0 for r in A) / len(A)),
                                mean_out=round(sum(r["out_tok"] or 0 for r in A) / len(A))))
    (d / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    f = lambda x: "n/a" if x is None else f"{x[0]:.3f} [{x[1][0]:.2f}, {x[1][1]:.2f}] (n={x[2]})"
    L = [f"# Phase 5 DEV results, {a.tag} (final config single_pass_recap_roles_top4; bootstrap over sets)", "",
         f"{summary['n']} answers, {summary['parse_ok']} parsed, {summary['n_sentences']} sentences, {summary['unknown_cites']} unknown citation ids, "
         f"{unparsed} unparseable judge verdicts (counted incorrect).", "", "| metric | headline | all types |", "|---|---|---|"]
    for k in M["headline"]:
        L.append(f"| {k} | {f(M['headline'][k])} | {f(M['all'][k])} |")
    L += ["", "| type | n | correctness (flag) | supported-claim rate |", "|---|---|---|---|"]
    for t, v in per_type.items():
        L.append(f"| {t} | {v['n']} | {f(v['correctness'])} | {f(v['supported'])} |")
    L += ["", f"False premise: {summary['false_premise']}", f"Policy: {summary['policy']}", f"Latency: {summary['latency']}"]
    (d / "table.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
