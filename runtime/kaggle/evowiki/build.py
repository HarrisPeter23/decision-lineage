"""Builds the evowiki_style Build kernel for DEV pooled corpora.
  python runtime/kaggle/evowiki/build.py <kernel-name> --pools dev_k1_*,dev_k10_*   (comma list; * allowed)
Bundles the code (baselines/evowiki_style, synthgen/llm.py, argdecisionlineage/chunking.py) and the corpora as parsed from the pools' plain-text meetings
(opaque ids, dates, utterances). DEV only. No gold, no set ids, no private map."""
import argparse, base64, fnmatch, io, json, pathlib, sys, tarfile

sys.path.insert(0, ".")
from argdecisionlineage.retrieve import load_corpus   # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("name")
ap.add_argument("--pools", required=True)
ap.add_argument("--workers", type=int, default=4)
ap.add_argument("--phase7", action="store_true", help="after FREEZE only: also TEST pools (data/synth/pools/test) and the shared AMI pools (data/ami/pools)")
a = ap.parse_args()
ROOTS = [pathlib.Path("data/synth/pools/dev")] + ([pathlib.Path("data/synth/pools/test"), pathlib.Path("data/ami/pools")] if a.phase7 else [])
found = sorted({(P, p.name) for P in ROOTS for pat in a.pools.split(",") for p in P.iterdir() if p.is_dir() and fnmatch.fnmatch(p.name, pat)})
names = [n for _, n in found]
assert names and all(n.startswith("dev_") or (a.phase7 and n.startswith(("test_", "ami_"))) for n in names)
corpora = {}
for P, n in found:
    ids = json.loads((P / n / "corpus.json").read_text(encoding="utf-8"))["meetings"]
    corpora[n] = load_corpus([(P / n / "meetings" / f"{m}.txt").read_text(encoding="utf-8") for m in ids])
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz") as t:
    for f in ["baselines/__init__.py", "baselines/evowiki_style/__init__.py", "baselines/evowiki_style/evowiki.py", "synthgen/llm.py"]:
        t.add(f, arcname=f)
    t.add("argdecisionlineage/chunking.py", arcname="synthgen/chunking.py")
    data = json.dumps(corpora).encode()
    ti = tarfile.TarInfo("corpora.json")
    ti.size = len(data)
    t.addfile(ti, io.BytesIO(data))
cfg = json.dumps(dict(model="qwen3:14b", ctx=16384, max_tokens=3000, workers=a.workers)).encode()
raw = len(cfg).to_bytes(8, "big") + cfg + buf.getvalue()
out = pathlib.Path("runtime/kaggle/evowiki/kernels") / a.name
out.mkdir(parents=True, exist_ok=True)
(out / "evowiki_build.py").write_text(pathlib.Path("runtime/kaggle/evowiki/template.py").read_text(encoding="utf8").replace("@@BUNDLE@@", base64.b64encode(raw).decode()),
                                      encoding="utf8", newline="\n")
(out / "kernel-metadata.json").write_text(json.dumps(dict(id="KAGGLE_USER/" + a.name, title=a.name, code_file="evowiki_build.py", language="python", kernel_type="script",
    is_private=True, enable_gpu=True, enable_internet=True, dataset_sources=[], competition_sources=[], kernel_sources=[])))
print(a.name, len(corpora), "corpora,", sum(len(c["meetings"]) for c in corpora.values()), "meetings ->", out)
