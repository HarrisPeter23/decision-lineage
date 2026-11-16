"""GPU NLI kernel with an indexed bundle (unique premises + unique hypotheses + index pairs), so ~125k pairs fit under Kaggle's ~1 MB script limit.
Same model, revision and self-check as runtime/kaggle/nli/build.py.
  python runtime/kaggle/nli/build_indexed.py <kernel-name> <ordered.jsonl> <start> <end>    (pairs [start, end) of the ordered file)
Output on Kaggle: nli_e.json = entailment probabilities in the same order as the selected pairs."""
import base64, gzip, json, pathlib, sys

name, ordered, start, end = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
P = [json.loads(l) for l in pathlib.Path(ordered).read_text(encoding="utf-8").splitlines() if l.strip()][start:end]
prem, hyp = {}, {}
idx = [(prem.setdefault(d["p"], len(prem)), hyp.setdefault(d["h"], len(hyp))) for d in P]
blob = base64.b64encode(gzip.compress(json.dumps(dict(P=list(prem), H=list(hyp), I=idx)).encode(), 9)).decode()
src = '''# GPU NLI scoring (Phase 6), indexed bundle. Same model and revision as the CPU checker; self-check first.
import base64, gzip, json, pathlib, subprocess, time
subprocess.run("pip install -q sentence-transformers sentencepiece", shell=True)
from sentence_transformers import CrossEncoder
B = json.loads(gzip.decompress(base64.b64decode("@@B@@")).decode())
m = CrossEncoder("cross-encoder/nli-deberta-v3-small", revision="fa2804872c3b", device="cuda")
lab = {v.lower(): k for k, v in m.model.config.id2label.items()}
ent = lab["entailment"]
chk = m.predict([("The van costs 4,100 a month.", "The van costs 4,100 a month."), ("The van costs 4,100 a month.", "The van costs 9,000 a month.")], apply_softmax=True)
assert chk[0][ent] > 0.9 and chk[1][ent] < 0.1, chk
t0 = time.time()
probs = m.predict([(B["P"][i], B["H"][j]) for i, j in B["I"]], apply_softmax=True, batch_size=64, show_progress_bar=False)
pathlib.Path("/kaggle/working/nli_e.json").write_text(json.dumps([round(float(p[ent]), 6) for p in probs]))
print("DONE", len(B["I"]), "pairs in", round(time.time() - t0), "s")
'''.replace("@@B@@", blob)
out = pathlib.Path("runtime/kaggle/nli/kernels") / name
out.mkdir(parents=True, exist_ok=True)
(out / "nli.py").write_text(src, encoding="utf8", newline="\n")
(out / "kernel-metadata.json").write_text(json.dumps(dict(id="KAGGLE_USER/" + name, title=name, code_file="nli.py", language="python", kernel_type="script",
    is_private=True, enable_gpu=True, enable_internet=True, dataset_sources=[], competition_sources=[], kernel_sources=[])))
print(name, len(P), "pairs;", round((out / "nli.py").stat().st_size / 1e6, 2), "MB ->", out)
