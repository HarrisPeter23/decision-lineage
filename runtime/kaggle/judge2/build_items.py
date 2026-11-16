"""Builds the granite kernel from prepared prompt files (jsonl with item, set_id, link_id, prompt, optional mode).
  python runtime/kaggle/judge2/build_items.py results/judge_sensitivity/items.jsonl results/role_blind/items.jsonl
Same template as the panel job; prompts are synthetic text only."""
import base64, gzip, json, pathlib, sys

items = []
for f in sys.argv[1:]:
    items += [json.loads(l) for l in pathlib.Path(f).read_text(encoding="utf-8").splitlines() if l.strip()]
assert len({i["item"] for i in items}) == len(items), "item ids must be unique"
blob = base64.b64encode(gzip.compress("\n".join(json.dumps(i) for i in items).encode())).decode()
out = pathlib.Path("runtime/kaggle/judge2/kernel")
out.mkdir(exist_ok=True)
src = pathlib.Path("runtime/kaggle/judge2/template.py").read_text(encoding="utf8").replace("@@BUNDLE@@", blob)
(out / "judge2.py").write_text(src, encoding="utf8", newline="\n")
(out / "kernel-metadata.json").write_text(json.dumps(dict(id="KAGGLE_USER/adl-judge2", title="adl-judge2", code_file="judge2.py", language="python",
    kernel_type="script", is_private=True, enable_gpu=True, enable_internet=True, dataset_sources=[], competition_sources=[], kernel_sources=[])))
print(len(items), "prompts;", (out / "judge2.py").stat().st_size, "bytes")
