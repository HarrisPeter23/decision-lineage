"""phase1_status.py - show which meetings exist for each planned set, QC each new file, and build specs that are ready.

  python phase1_status.py            # table + builds the next spec for every set whose previous meeting exists
Prints a READY line for every meeting that a writer can start now (spec built, meeting file missing).
QC per meeting: utterance count (60-120), tag order and set, cast names, banned words, brand-name scan.
"""
import pathlib
import re
import subprocess
import sys

from arcs import sample_spec
from phase1_specs import W, build
from text_to_tagged import parse

BRANDS = re.compile(r"\b(?i:stripe|marriott|amex|gmail|mailinator|google|amazon|zoom|salesforce|hubspot|aws|azure|jira|excel|outlook|"
                    r"mastercard|paypal|linkedin|github|notion|asana|trello|docusign|netflix|apple|microsoft|oracle|whatsapp|"
                    r"uber|walmart|ikea|starbucks|fedex|dhl|tesla|toyota|youtube|facebook|instagram|twitter|zendesk|shopify)\b"
                    r"|\b(?:Slack|Visa|UPS|Ford)\b")
BANNED = re.compile(r"\b(?i:beat|reversal|supersede|lineage)\b|\bB\d+\b|\bD\d\b")
TAGRE = re.compile(r"\s@([A-Z]\d+(?:,[A-Z]\d+)*)\s*$")


def qc(sid, m, spec, text):
    probs = []
    lines = [l for l in text.splitlines() if l.strip()]
    names = {c["name"] for c in spec["cast"]}
    if not 60 <= len(lines) <= 120:
        probs.append(f"{len(lines)} utterances")
    spoke = set()
    tags = []
    for i, l in enumerate(lines):
        sp, sep, rest = l.partition(": ")
        if not sep or sp not in names:
            probs.append(f"line {i + 1}: bad speaker {sp[:20]!r}")
            continue
        spoke.add(sp)
        mt = TAGRE.search(" " + rest)
        if mt:
            tags += mt.group(1).split(",")
            rest = TAGRE.sub("", " " + rest)
        if BANNED.search(rest):
            probs.append(f"line {i + 1}: banned word {BANNED.search(rest).group(0)!r}")
        if BRANDS.search(rest):
            probs.append(f"line {i + 1}: real brand {BRANDS.search(rest).group(0)!r}")
    if names - spoke:
        probs.append(f"silent: {sorted(names - spoke)}")
    allb = spec["beats"] + (spec["distractor"]["beats"] if spec["distractor"] else [])
    want = [b["id"] for b in allb if b["meeting"] == m]
    seen = [t for t in dict.fromkeys(tags)]
    if sorted(seen) != sorted(want):
        probs.append(f"tags {seen} != expected {want}")
    return probs


def main():
    ready = []
    for p in sorted((W / "plans").glob("set_*.txt")):
        sid = p.stem
        plan = parse(p)
        spec = sample_spec(int(sid.split("_")[1]), plan["arc_type"], sid)
        n = spec["n_meetings"]
        row = []
        for m in range(1, n + 1):
            f = W / "meetings" / sid / f"m{m}.txt"
            if f.exists():
                pr = qc(sid, m, spec, f.read_text(encoding="utf-8"))
                row.append(f"m{m}:" + ("ok" if not pr else "PROBLEM"))
                for x in pr:
                    print(f"  {sid} m{m}: {x}")
            else:
                row.append(f"m{m}:-")
        have = [(W / "meetings" / sid / f"m{m}.txt").exists() for m in range(1, n + 1)]
        nxt = next((m for m, h in enumerate(have, 1) if not h), None)
        status = "complete" if nxt is None else f"next m{nxt}"
        if nxt is not None and (nxt == 1 or have[nxt - 2]):
            (W / "meetings" / sid).mkdir(parents=True, exist_ok=True)
            if not (W / "specs" / sid / f"m{nxt}.md").exists():
                build(sid, nxt)
            ready.append((sid, nxt))
        print(f"{sid} {plan['arc_type']:<17} {' '.join(row)}  [{status}]")
    print("READY:", " ".join(f"{s}/m{m}" for s, m in ready))


if __name__ == "__main__":
    main()
