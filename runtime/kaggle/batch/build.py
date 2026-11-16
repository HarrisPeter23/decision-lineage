"""Builds a generic batch kernel.
  python runtime/kaggle/batch/build.py <kernel-name> <config.json> <items.jsonl>
config.json: {"model": "qwen3:14b", "ctx": 8192, "system": "...", "think": false, "num_predict": 300, "temperature": 0}
items.jsonl: one {"id": ..., "prompt": ...} per line (ids unique).  Output kernel dir: runtime/kaggle/batch/kernels/<kernel-name>/
"""
import base64, gzip, json, pathlib, sys

name, cfg_path, items_path = sys.argv[1:4]
cfg = json.loads(pathlib.Path(cfg_path).read_text(encoding="utf-8"))
items = [json.loads(l) for l in pathlib.Path(items_path).read_text(encoding="utf-8").splitlines() if l.strip()]
assert len({i["id"] for i in items}) == len(items), "ids must be unique"
blob = base64.b64encode(gzip.compress(json.dumps(dict(config=cfg, items=items)).encode())).decode()
out = pathlib.Path("runtime/kaggle/batch/kernels") / name
out.mkdir(parents=True, exist_ok=True)
src = pathlib.Path("runtime/kaggle/batch/template.py").read_text(encoding="utf8").replace("@@BUNDLE@@", blob)
(out / "batch.py").write_text(src, encoding="utf8", newline="\n")
(out / "kernel-metadata.json").write_text(json.dumps(dict(id="KAGGLE_USER/" + name, title=name, code_file="batch.py", language="python", kernel_type="script",
    is_private=True, enable_gpu=True, enable_internet=True, dataset_sources=[], competition_sources=[], kernel_sources=[])))
print(name, len(items), "items;", (out / "batch.py").stat().st_size, "bytes ->", out)
