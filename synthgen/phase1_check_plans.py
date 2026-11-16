"""phase1_check_plans.py - every beat gist must name the speaker the arc assigns to that beat's slot (gold consistency).

  python phase1_check_plans.py          # report mismatches
  python phase1_check_plans.py --fix    # replace a wrong leading speaker name in the gist with the right one (logged)
"""
import re
import sys

from arcs import sample_spec, slot_name
from phase1_specs import W
from text_to_tagged import parse

FIX = "--fix" in sys.argv
LOG = W.parent.parent / "reports" / "label_issues.md"
total = 0
for p in sorted((W / "plans").glob("set_*.txt")):
    sid = p.stem
    plan = parse(p)
    spec = sample_spec(int(sid.split("_")[1]), plan["arc_type"], sid)
    names = [c["name"] for c in spec["cast"]]
    gists = dict(plan["beats"], **((plan["distractor"] or {}).get("beats") or {}))
    allb = spec["beats"] + (spec["distractor"]["beats"] if spec["distractor"] else [])
    text = p.read_text(encoding="utf-8")
    for b in allb:
        want = slot_name(spec, b["slot"])
        g = gists[b["id"]]
        found = [n for n in names if re.search(rf"\b{n}\b", g)]
        first = min(found, key=lambda n: re.search(rf"\b{n}\b", g).start()) if found else None
        if first != want:
            total += 1
            print(f"{sid} {b['id']} ({b['role']}): slot speaker {want}, gist leads with {first}: {g[:90]}")
            if FIX and first:
                new = re.sub(rf"\b{first}\b", want, g, count=1)
                text = text.replace(g, new)
                with LOG.open("a", encoding="utf-8") as f:
                    f.write(f"- {sid} {b['id']}: gist named {first}, but the arc assigns this beat to {want}; gist corrected. before: `{g}` after: `{new}`\n")
    if FIX:
        p.write_text(text, encoding="utf-8", newline="\n")
print("mismatches:", total)
