"""leakcheck.py - anti-foreshadowing audit (Phase 1). For every meeting spec that a writer sees, verify it contains nothing from later meetings.

A spec for meeting k must NOT contain: the gist or the key words of any event scheduled in a meeting > k, the text of an option that is first
introduced after meeting k, the date of any later meeting, the arc name, or the words 'reversal'/'supersede'. It MAY contain earlier meetings'
transcripts (tags stripped) and this meeting's own events.

  python eval/leakcheck.py claude    # the specs actually given to the Claude writers (data/synth_work/specs)
  python eval/leakcheck.py control   # specs rebuilt from the control plans with placeholder earlier transcripts (same code the Kaggle job runs)
"""
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, "synthgen")
import phase1_specs as ps                       # noqa: E402
from arcs import sample_spec                    # noqa: E402
from text_to_tagged import parse                # noqa: E402

ARCS = ("simple_reversal", "re_reversal", "partial_override", "no_reversal", "deferred", "external_trigger")


def audit(sid, plan, spec, specs_dir):
    probs = []
    allb = spec["beats"] + (spec["distractor"]["beats"] if spec["distractor"] else [])
    gists = dict(plan["beats"], **((plan["distractor"] or {}).get("beats") or {}))
    first_meeting = {}
    for b in spec["beats"]:
        key = ps.option_for(spec, b)
        if key and key not in first_meeting:
            first_meeting[key] = b["meeting"]
    for k in range(1, spec["n_meetings"] + 1):
        f = specs_dir / sid / f"m{k}.md"
        if not f.exists():
            probs.append(f"m{k}: spec file missing")
            continue
        text = f.read_text(encoding="utf-8")
        # the transcripts of earlier meetings are allowed to talk about anything that happened; check only the header part
        header = text.split("## Transcripts of the earlier meetings")[0]
        for b in allb:
            if b["meeting"] > k:
                g = gists[b["id"]]
                if g[:45] in header:
                    probs.append(f"m{k}: gist of {b['id']} (meeting {b['meeting']}) is in the spec")
        for key, mt in first_meeting.items():
            if mt > k and plan["options"].get(key) and plan["options"][key] in header:
                probs.append(f"m{k}: text of option {key} (first used in meeting {mt}) is in the spec")
        for later in range(k + 1, spec["n_meetings"] + 1):
            if spec["dates"][later - 1] in text:
                probs.append(f"m{k}: date of meeting {later} is in the spec")
        for w in ARCS + ("reversal", "supersede", "arc_type"):
            if w in text:
                probs.append(f"m{k}: forbidden word {w!r}")
    return probs


def main():
    which = sys.argv[1]
    total = bad = 0
    if which == "claude":
        ps.W = pathlib.Path("data/synth_work")
        plans, specs_dir = ps.W / "plans", ps.W / "specs"
        ids = sorted(p.stem for p in plans.glob("set_*.txt"))
    else:
        tmp = pathlib.Path(tempfile.mkdtemp())
        ps.W = tmp
        (tmp / "plans").mkdir()
        for p in pathlib.Path("data/synth_work/control_plans").glob("set_*.txt"):
            shutil.copy(p, tmp / "plans" / p.name)
        plans, specs_dir = tmp / "plans", tmp / "specs"
        ids = sorted(p.stem for p in plans.glob("set_*.txt"))
        for sid in ids:
            plan = parse(plans / f"{sid}.txt")
            spec = sample_spec(int(sid.split("_")[1]), plan["arc_type"], sid)
            (tmp / "meetings" / sid).mkdir(parents=True)
            for k in range(1, spec["n_meetings"] + 1):
                ps.build(sid, k)
                (tmp / "meetings" / sid / f"m{k}.txt").write_text("Placeholder: earlier meeting text.\n", encoding="utf-8")
    for sid in ids:
        plan = parse(plans / f"{sid}.txt")
        spec = sample_spec(int(sid.split("_")[1]), plan["arc_type"], sid)
        p = audit(sid, plan, spec, specs_dir)
        total += spec["n_meetings"]
        bad += len(p)
        for x in p:
            print(" ", sid, x)
    print(f"{which}: {len(ids)} sets, {total} meeting specs audited, {bad} leaks found")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
