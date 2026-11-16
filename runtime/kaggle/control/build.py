"""Builds the control-writer kernel: bundles specs code, control plans and writer prompt v3 into one script."""
import base64, io, json, pathlib, tarfile

out = pathlib.Path("runtime/kaggle/control/kernel")
out.mkdir(exist_ok=True)
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz") as t:
    for n in ("arcs.py", "phase1_specs.py", "phase1_status.py", "text_to_tagged.py"):
        t.add(pathlib.Path("synthgen") / n, arcname=f"synthgen/{n}")
    for p in sorted(pathlib.Path("data/synth_work/control_plans").glob("set_*.txt")):
        t.add(p, arcname=f"control_plans/{p.name}")
    t.add("data/synth_work/writer_prompts/v3.md", arcname="v3.md")
src = pathlib.Path("runtime/kaggle/control/template.py").read_text(encoding="utf8").replace("@@BUNDLE@@", base64.b64encode(buf.getvalue()).decode())
(out / "control.py").write_text(src, encoding="utf8", newline="\n")
(out / "kernel-metadata.json").write_text(json.dumps(dict(id="KAGGLE_USER/adl-control", title="adl-control", code_file="control.py", language="python",
    kernel_type="script", is_private=True, enable_gpu=True, enable_internet=True, dataset_sources=[], competition_sources=[], kernel_sources=[])))
print((out / "control.py").stat().st_size)
