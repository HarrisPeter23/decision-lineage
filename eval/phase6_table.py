"""phase6_table.py - DEV comparison of my system and the three baselines, from the per-run summaries written by eval/phase5_final.py (no new computation).
  python eval/phase6_table.py -> results/phase6/comparison.md
Point estimates with 95% CIs from the bootstrap over DEV sets; CIs are per system (unpaired), so overlap is not a test. Pre-registered paired tests are TEST-only.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SYS = [("lineage (mine)", "k{}"), ("vector_rag", "vector_rag_k{}"), ("evowiki_style", "evowiki_style_k{}"), ("graphiti", "graphiti_k{}")]
METRICS = [("correctness_flag", "answer correctness (LLM-judged where not exact)"), ("supported_claim_rate", "supported-claim rate (NLI)"),
           ("citation_precision", "citation precision (NLI)"), ("hallucination_rate", "hallucination rate (NLI, lower is better)"),
           ("retrieval_completeness", "lineage completeness, retrieved"), ("expl_completeness_flag", "lineage completeness, cited")]


def f(x):
    return "n/a" if not x else f"{x[0]:.3f} [{x[1][0]:.2f}, {x[1][1]:.2f}]"


def main():
    L = ["# Phase 6 DEV comparison (14 sets, 141 questions; 95% CI by bootstrap over sets; unpaired, so overlap is not a test)", ""]
    for size in (1, 10):
        S = {}
        for name, pat in SYS:
            p = ROOT / f"results/phase5/score/{pat.format(size)}/summary.json"
            S[name] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        for scope in ("headline", "all"):
            L += [f"## pool size {size}, {scope} questions", "", "| metric | " + " | ".join(n for n, _ in SYS) + " |", "|---|" + "---|" * len(SYS)]
            for key, label in METRICS:
                L.append(f"| {label} | " + " | ".join(f(S[n]["metrics"][scope].get(key)) if S[n] else "pending" for n, _ in SYS) + " |")
            L.append("")
        L.append("| per type (correctness, pool %d) | " % size + " | ".join(n for n, _ in SYS) + " |")
        L.append("|---|" + "---|" * len(SYS))
        types = sorted(next(s for s in S.values() if s)["per_type"])
        for t in types:
            L.append(f"| {t} | " + " | ".join(f"{S[n]['per_type'][t]['correctness'][0]:.2f}" if S[n] else "pending" for n, _ in SYS) + " |")
        L.append("| false premise (regex, n=2) | " + " | ".join(f"{S[n]['false_premise']['regex_ok']}/2" if S[n] else "pending" for n, _ in SYS) + " |")
        L.append("| parse failures | " + " | ".join(f"{S[n]['n'] - S[n]['parse_ok']}" if S[n] else "pending" for n, _ in SYS) + " |")
        L.append("")
    (ROOT / "results/phase6/comparison.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
