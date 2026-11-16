"""Builds the secondary-judge kernel from the per-link judge prompts of the given data dirs (same prompts as eval/panel.py)."""
import base64, gzip, json, pathlib, sys

sys.path.insert(0, "eval")
import panel  # noqa: E402

items = []
for data in sys.argv[1:]:
    for sid, tr, gold, l in panel.iter_links(data):
        items.append(dict(set_id=sid, link_id=l["link_id"], prompt=panel.link_prompt(tr, gold, l)))
blob = base64.b64encode(gzip.compress("\n".join(json.dumps(i) for i in items).encode())).decode()
out = pathlib.Path("runtime/kaggle/judge2/kernel")
out.mkdir(exist_ok=True)
src = pathlib.Path("runtime/kaggle/judge2/template.py").read_text(encoding="utf8").replace("@@BUNDLE@@", blob)
(out / "judge2.py").write_text(src, encoding="utf8", newline="\n")
(out / "kernel-metadata.json").write_text(json.dumps(dict(id="KAGGLE_USER/adl-judge2", title="adl-judge2", code_file="judge2.py", language="python",
    kernel_type="script", is_private=True, enable_gpu=True, enable_internet=True, dataset_sources=[], competition_sources=[], kernel_sources=[])))
print(len(items), "prompts;", (out / "judge2.py").stat().st_size, "bytes")
