"""phase1_import.py - assemble every planned set, import it into data/synth with writer provenance, copy the 6 pilot sets, validate.

Provenance (rule 6) is written to data/synth/provenance.json and merged into each gold file's meta:
  writer, writer_prompt_version(s), seed, verification (none until the panel runs).
"""
import json
import pathlib
import shutil
import subprocess
import sys

from phase1_specs import W, assemble_set
from phase1_status import qc
from arcs import sample_spec
from text_to_tagged import parse

OUT = pathlib.Path("../data/synth")
OPUS = {"set_01013", "set_01014", "set_01015", "set_01016"}          # tuning sets, prompt v1
V2 = {"set_01017", "set_01018", "set_01019"}                         # meetings 1-2 prompt v2, later meetings v3
PILOT_SEEDS = [1000, 1002, 1003, 1004, 1006, 1012]


def main():
    inboxes = {"claude-opus-5.5": W / "inbox_opus", "claude-sonnet-5.5": W / "inbox_sonnet"}
    for d in inboxes.values():
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
    prov = {}
    bad = 0
    for p in sorted((W / "plans").glob("set_*.txt")):
        sid = p.stem
        plan = parse(p)
        spec = sample_spec(int(sid.split("_")[1]), plan["arc_type"], sid)
        for m in range(1, spec["n_meetings"] + 1):
            f = W / "meetings" / sid / f"m{m}.txt"
            if not f.exists():
                print("MISSING", sid, m); bad += 1; continue
            for x in qc(sid, m, spec, f.read_text(encoding="utf-8")):
                print("QC", sid, f"m{m}", x); bad += 1
        assemble_set(sid)
        writer = "claude-opus-5.5" if sid in OPUS else "claude-sonnet-5.5"
        shutil.copy(W / "inbox" / f"{sid}.txt", inboxes[writer] / f"{sid}.txt")
        pv = "v1" if sid in OPUS else ("v2 (m1-2) + v3 (rest)" if sid in V2 else "v3")
        prov[sid] = dict(writer=writer, prompt_version=pv, seed=spec["seed"], arc_type=plan["arc_type"], domain=spec["domain"],
                         meetings=spec["n_meetings"], verification="none")
    rep = json.loads((W / "control_repair_report.json").read_text(encoding="utf-8"))
    rejected = json.loads((W / "control_rejected.json").read_text(encoding="utf-8")) if (W / "control_rejected.json").exists() else {}
    rep["complete_sets"] = [x for x in rep["complete_sets"] if x not in rejected]
    inbox_ctrl = W / "inbox_control"
    shutil.rmtree(inbox_ctrl, ignore_errors=True)
    inbox_ctrl.mkdir(parents=True)
    for sid in rep["complete_sets"]:
        head = (W / "control_plans" / f"{sid}.txt").read_text(encoding="utf-8").rstrip()
        parts = [head]
        srcs = []
        for i, f in enumerate(sorted((W / "control_meetings" / sid).glob("m*.txt")), 1):
            parts += [f"== m{i}", f.read_text(encoding="utf-8").strip()]
            srcs.append(rep["report"][f"{sid}/m{i}"]["source"].split("control")[0].rstrip("/\\").split("/")[-1].split("\\")[-1])
        (inbox_ctrl / f"{sid}.txt").write_text(chr(10).join(parts) + chr(10), encoding="utf-8", newline=chr(10))
        plan = parse(W / "control_plans" / f"{sid}.txt")
        spec = sample_spec(int(sid.split("_")[1]), plan["arc_type"], sid)
        prov[sid] = dict(writer="mistral-nemo:12b (dialogue only; plan by claude-sonnet-5.5)", prompt_version="v3c/v3c2 chunked + repair D-09", seed=spec["seed"],
                         arc_type=plan["arc_type"], domain=spec["domain"], meetings=spec["n_meetings"], verification="none", meeting_sources=srcs,
                         note="control writer set (H4); exploratory N=2")
        inboxes["mistral-nemo:12b"] = inbox_ctrl
    if bad:
        sys.exit(f"{bad} problems; fix before importing")
    for sub in ('gold', 'transcripts', 'rejected', 'transcripts_txt'):   # keep verification.json, split.json etc. in OUT
        shutil.rmtree(OUT / sub, ignore_errors=True)
    for writer, d in inboxes.items():
        r = subprocess.run([sys.executable, "import_tagged.py", str(d), "--out", str(OUT), "--source", writer],
                           capture_output=True, text=True)
        print(r.stdout[-600:], r.stderr[-300:])
        if (r.returncode or "need fixing" in r.stdout and " 0 need fixing" not in r.stdout) and writer != "mistral-nemo:12b":
            sys.exit("import failed")
    for sid in [k for k, v in prov.items() if str(v["writer"]).startswith("mistral-nemo")]:
        if not (OUT / "gold" / f"{sid}.json").exists():       # a control set that fails the validator is dropped, never edited
            print("control set rejected by the validator and dropped:", sid)
            prov.pop(sid)
    # pilot sets (toolkit-written, DEV only)
    pil = pathlib.Path("data/pilot")
    for seed in PILOT_SEEDS:
        sid = f"set_{seed:05d}"
        for sub in ("transcripts", "gold"):
            shutil.copy(pil / sub / f"{sid}.json", OUT / sub / f"{sid}.json")
        shutil.copytree(pil / "transcripts_txt" / sid, OUT / "transcripts_txt" / sid, dirs_exist_ok=True)
        g = json.loads((pil / "gold" / f"{sid}.json").read_text(encoding="utf-8"))
        prov[sid] = dict(writer="claude (earlier session, model not recorded)", prompt_version="PROMPT_base", seed=seed,
                         arc_type=g["meta"].get("arc_type"), domain=g["meta"].get("domain"), meetings=len(g.get("meetings", [])) or None,
                         verification="none", note="pilot set, short meetings (25-38 utterances)")
    (OUT / "provenance.json").write_text(json.dumps(prov, indent=1), encoding="utf-8")
    print("sets in data/synth:", len(list((OUT / "gold").glob("*.json"))))


if __name__ == "__main__":
    main()
