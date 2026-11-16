"""Builds a Phase 3 DEV extraction kernel.
  python runtime/kaggle/phase3/build.py <kernel-name> --server vllm|ollama --model <name> --configs single_pass,mp_p123,mp_p123_verify [--workers 8]
Bundle = config JSON + a tar.gz of synthgen/*.py and the DEV sets' transcripts and gold (DEV only; TEST is never bundled)."""
import argparse, base64, io, json, pathlib, tarfile

ap = argparse.ArgumentParser()
ap.add_argument("name")
ap.add_argument("--server", required=True, choices=["vllm", "ollama"])
ap.add_argument("--model", required=True)
ap.add_argument("--configs", required=True)
ap.add_argument("--workers", type=int, default=8)
ap.add_argument("--max-num-seqs", type=int, default=16)
ap.add_argument("--chunk-budget", type=int, default=0)
ap.add_argument("--phase7", action="store_true", help="after FREEZE only: allow test_/ami_ corpora from runtime/kaggle/phase7 (no gold is ever bundled for them)")
ap.add_argument("--sets", help="comma list: a DEV subset (P3-F tune half)")
ap.add_argument("--base-preds", help="directory of the config's own pass-1 outputs <set>.json (P3-F); bundled as data/base_preds")
ap.add_argument("--data-dir", help="Phase 5: a directory with transcripts/<corpus>.json (pooled DEV corpora, no gold) instead of the DEV sets")
a = ap.parse_args()
split = json.loads(pathlib.Path("data/synth/split.json").read_text(encoding="utf-8"))
dev = split["dev"]
base = pathlib.Path("data/synth")
if a.sets:
    dev = [x for x in a.sets.split(",") if x in dev]
if a.data_dir:
    base = pathlib.Path(a.data_dir)
    dev = sorted(p.stem for p in (base / "transcripts").glob("*.json"))
    assert all(x.startswith("dev_") for x in dev) or (a.phase7 and all(x.startswith(("test_", "ami_")) for x in dev)),         "only DEV pooled corpora (or, after FREEZE with --phase7, TEST / AMI corpora built from the shared pools) may be bundled"
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz") as t:
    for p in pathlib.Path("synthgen").glob("*.py"):
        t.add(p, arcname=f"synthgen/{p.name}")
    t.add("argdecisionlineage/chunking.py", arcname="synthgen/chunking.py")
    for s in dev:
        for sub in ("transcripts", "gold"):
            if (base / sub / f"{s}.json").exists():
                t.add(base / sub / f"{s}.json", arcname=f"data/{sub}/{s}.json")
        if a.base_preds:
            t.add(pathlib.Path(a.base_preds) / f"{s}.json", arcname=f"data/base_preds/{s}.json")
cfg = json.dumps(dict(server=a.server, model=a.model, configs=a.configs.split(","), workers=a.workers, dev_sets=dev, max_num_seqs=a.max_num_seqs, chunk_budget=a.chunk_budget)).encode()
raw = len(cfg).to_bytes(8, "big") + cfg + buf.getvalue()
out = pathlib.Path("runtime/kaggle/phase3/kernels") / a.name
out.mkdir(parents=True, exist_ok=True)
src = pathlib.Path("runtime/kaggle/phase3/template.py").read_text(encoding="utf8").replace("@@BUNDLE@@", base64.b64encode(raw).decode())
(out / "phase3.py").write_text(src, encoding="utf8", newline="\n")
(out / "kernel-metadata.json").write_text(json.dumps(dict(id="KAGGLE_USER/" + a.name, title=a.name, code_file="phase3.py", language="python", kernel_type="script",
    is_private=True, enable_gpu=True, enable_internet=True, dataset_sources=[], competition_sources=[], kernel_sources=[])))
print(a.name, a.server, a.model, "dev sets", len(dev), "bytes", (out / "phase3.py").stat().st_size, "->", out)
