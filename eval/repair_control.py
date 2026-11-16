"""repair_control.py - disclosed plumbing repair for control-writer output (deviation D-09), then the standard QC.

The control model often writes an event tag in the middle of a line ('Marco: ok @B2 so then...') or writes a bare event id ('B4', '(B5)') in the words.
Repair: (1) collect the event ids written as '@B2' anywhere in the line, remove them from the words, and put them at the END of the same line;
(2) delete bare event ids that are not tags. Nothing else is touched: no wording, no speaker, no line order, no length. Lines are never moved or added.
The standard QC (phase1_status.qc) is then applied; a meeting that still fails is NOT used.

  python eval/repair_control.py results/control_v3c/control results/control_v3c2/control --out data/synth_work/control_meetings
"""
import json
import pathlib
import re
import shutil
import sys

sys.path.insert(0, "synthgen")
import phase1_specs as ps                       # noqa: E402
import phase1_status as st                      # noqa: E402
from arcs import sample_spec                    # noqa: E402
from text_to_tagged import parse                # noqa: E402

TAG_ANY = re.compile(r"\s*@([BD]\d{1,2}(?:,[BD]\d{1,2})*)")
BARE = re.compile(r"\s*[\(\[]?(?<!@)\b[BD]\d{1,2}\b[\)\]]?")


def repair_line(line):
    sp, sep, rest = line.partition(": ")
    if not sep:
        return line
    ids = []
    for m in TAG_ANY.finditer(rest):
        ids += m.group(1).split(",")
    body = TAG_ANY.sub("", rest)
    body = BARE.sub("", body).strip()
    ids = list(dict.fromkeys(ids))
    return f"{sp}: {body}" + (" @" + ",".join(ids) if ids else "")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = pathlib.Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else pathlib.Path("data/synth_work/control_meetings")
    srcs = [pathlib.Path(a) for a in args if a != str(out)]
    ps.W = pathlib.Path("data/synth_work")
    plans = {p.stem: parse(p) for p in (ps.W / "control_plans").glob("set_*.txt")}
    shutil.rmtree(out, ignore_errors=True)
    report = {}
    for sid, plan in sorted(plans.items()):
        spec = sample_spec(int(sid.split("_")[1]), plan["arc_type"], sid)
        for m in range(1, spec["n_meetings"] + 1):
            best = None
            for src in srcs:                      # later sources are newer procedure versions; the lowest problem count wins, ties go to the later one
                f = src / sid / f"m{m}.txt"
                if not f.exists():
                    continue
                raw = [l for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
                fixed = [repair_line(l) for l in raw]
                probs = st.qc(sid, m, spec, "\n".join(fixed))
                if best is None or len(probs) <= best[0]:
                    best = (len(probs), fixed, probs, str(src))
            if best is None:
                report[f"{sid}/m{m}"] = dict(status="missing")
                continue
            ok = not best[2]
            report[f"{sid}/m{m}"] = dict(status="pass" if ok else "fail", problems=best[2][:3], source=best[3], utterances=len(best[1]))
            if ok:
                (out / sid).mkdir(parents=True, exist_ok=True)
                (out / sid / f"m{m}.txt").write_text("\n".join(best[1]) + "\n", encoding="utf-8", newline="\n")
    sets = {}
    for k, v in report.items():
        sets.setdefault(k.split("/")[0], []).append(v["status"])
    for k, v in sorted(report.items()):
        print(k, v["status"], v.get("utterances", ""), v.get("problems", ""))
    complete = [s for s, v in sets.items() if all(x == "pass" for x in v) and len(v) == sample_spec(int(s.split("_")[1]), plans[s]["arc_type"], s)["n_meetings"]]
    print("complete control sets after repair:", complete)
    (out.parent / "control_repair_report.json").write_text(json.dumps(dict(report=report, complete_sets=complete), indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
