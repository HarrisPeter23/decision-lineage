"""phase6_nli_merge.py - merges the GPU NLI outputs (adl-p6-nli-a: ordered pairs [0, 124365); adl-p6-nli-5: [124365, end)) into one cache
results/phase6/nli/cache_gpu.jsonl, and checks GPU vs CPU agreement on the Phase 5 lineage pairs (whose CPU scores are cached in the Phase 5 answers' NLI
run). Agreement = same verdict at the 0.5 threshold; also the max absolute difference."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
P = [json.loads(l) for l in (ROOT / "results/phase6/nli/ordered_adl-p6-nli.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
E = json.loads((ROOT / "results/phase6/nli/out/adl-p6-nli-a/nli_e.json").read_text()) + json.loads((ROOT / "results/phase6/nli/out/adl-p6-nli-5/nli_e.json").read_text())
assert len(E) == len(P), (len(E), len(P))
(ROOT / "results/phase6/nli/cache_gpu.jsonl").write_text("\n".join(json.dumps(dict(p=d["p"], h=d["h"], e=e)) for d, e in zip(P, E)) + "\n", encoding="utf-8")
gpu = {(d["p"], d["h"]): e for d, e in zip(P, E)}
lin = [json.loads(l) for l in (ROOT / "results/phase6/nli/pairs_lineage_k1.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
from argdecisionlineage.faithfulness import NLIChecker   # noqa: E402
import random                                            # noqa: E402
sample = random.Random(0).sample(lin, 400)
cpu = NLIChecker().probs([(d["p"], d["h"]) for d in sample])
agree = sum((c >= 0.5) == (gpu[(d["p"], d["h"])] >= 0.5) for d, c in zip(sample, cpu))
diff = max(abs(c - gpu[(d["p"], d["h"])]) for d, c in zip(sample, cpu))
res = dict(pairs=len(P), cpu_gpu_sample=len(sample), verdict_agreement=round(agree / len(sample), 4), max_abs_diff=round(diff, 4))
(ROOT / "results/phase6/nli/cpu_gpu_check.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(res)
