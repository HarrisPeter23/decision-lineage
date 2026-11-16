"""Builds a GPU NLI kernel: scores (premise, hypothesis) pairs with NLI_MODEL (cross-encoder/nli-deberta-v3-small, revision fa2804872c3b), the same model and
revision as the CPU checker (argdecisionlineage/faithfulness.py), on one T4, and returns {p, h, e} with e = P(entailment).
  python runtime/kaggle/nli/build.py <kernel-name> <pairs.jsonl> [<pairs.jsonl> ...]
Pairs are synthetic DEV text only."""
import base64, gzip, json, pathlib, sys

name, files = sys.argv[1], sys.argv[2:]
pairs, seen = [], set()
for f in files:
    for l in pathlib.Path(f).read_text(encoding="utf-8").splitlines():
        if l.strip():
            d = json.loads(l)
            k = (d["p"], d["h"])
            if k not in seen:
                seen.add(k)
                pairs.append(d)
blob = base64.b64encode(gzip.compress(json.dumps(pairs).encode(), 9)).decode()
src = '''# GPU NLI scoring (Phase 6): same model and revision as the CPU checker. Self-check first (the failure seen on 2026-11-04 was a missing tokenizer).
import base64, gzip, json, pathlib, subprocess, time
subprocess.run("pip install -q sentence-transformers sentencepiece", shell=True)
from sentence_transformers import CrossEncoder
PAIRS = json.loads(gzip.decompress(base64.b64decode("@@B@@")).decode())
m = CrossEncoder("cross-encoder/nli-deberta-v3-small", revision="fa2804872c3b", device="cuda")
lab = {v.lower(): k for k, v in m.model.config.id2label.items()}
ent = lab["entailment"]
chk = m.predict([("The van costs 4,100 a month.", "The van costs 4,100 a month."), ("The van costs 4,100 a month.", "The van costs 9,000 a month.")], apply_softmax=True)
assert chk[0][ent] > 0.9 and chk[1][ent] < 0.1, chk
t0 = time.time()
probs = m.predict([(d["p"], d["h"]) for d in PAIRS], apply_softmax=True, batch_size=64, show_progress_bar=False)
pathlib.Path("/kaggle/working/nli_e.json").write_text(json.dumps([round(float(pr[ent]), 6) for pr in probs]))   # bundle order; the pairs stay local
print("DONE", len(PAIRS), "pairs in", round(time.time() - t0), "s")
'''.replace("@@B@@", blob)
pathlib.Path("results/phase6/nli").mkdir(parents=True, exist_ok=True)
pathlib.Path(f"results/phase6/nli/ordered_{name}.jsonl").write_text("\n".join(json.dumps(d) for d in pairs) + "\n", encoding="utf-8")
out = pathlib.Path("runtime/kaggle/nli/kernels") / name
out.mkdir(parents=True, exist_ok=True)
(out / "nli.py").write_text(src, encoding="utf8", newline="\n")
(out / "kernel-metadata.json").write_text(json.dumps(dict(id="KAGGLE_USER/" + name, title=name, code_file="nli.py", language="python", kernel_type="script",
    is_private=True, enable_gpu=True, enable_internet=True, dataset_sources=[], competition_sources=[], kernel_sources=[])))
print(name, len(pairs), "pairs;", round((out / "nli.py").stat().st_size / 1e6, 1), "MB ->", out)
