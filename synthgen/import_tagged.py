"""import_tagged.py - convert hand/LLM-authored "tagged" sets into transcript + gold files.

The author (e.g. another Claude chat) supplies only CONTENT: topic, options, one gist per
event, and utterances with event tags. This script supplies STRUCTURE (roles, versions,
cast, dates, questions, gold answers) from arcs.sample_spec(seed, arc_type), so the gold
chain cannot disagree with the arc definition and utterance indexes are computed, not typed.

Input: one file per set in the inbox, either plain text (preferred, see text_to_tagged.py)
or JSON (below), e.g. inbox/set_01000.txt or inbox/set_01000.json:
{
  "set_id": "set_01000", "seed": 1000, "arc_type": "deferred",
  "topic": "...", "options": {"A": "...", "B": "..."},
  "beats": {"B1": "one concrete sentence", ...},
  "distractor": null | {"topic": "...", "option": "...", "beats": {"D1": "...", "D2": "...", "D3": "..."}},
  "meetings": [ {"utterances": [ {"speaker": "Name", "text": "...", "tags": ["B1"]}, ... ]}, ... ]
}
Usage: python import_tagged.py inbox/ --out data/synth     (then: python validate.py data/synth --stats)
"""
import argparse
import json
import pathlib

from arcs import option_keys, sample_spec
from assemble import assemble
from text_to_tagged import parse as parse_text
from validate import validate_set


def convert(d, source="claude-chat"):
    """Return (transcript, gold, problems). problems is a list of strings (fatal if non-empty)."""
    probs = []
    spec = sample_spec(d["seed"], d["arc_type"], d["set_id"])
    names = {c["name"] for c in spec["cast"]}

    need = [b["id"] for b in spec["beats"]]
    dneed = [b["id"] for b in spec["distractor"]["beats"]] if spec["distractor"] else []
    plan = dict(topic=d.get("topic"), options=d.get("options", {}), beats=d.get("beats", {}),
                distractor=d.get("distractor"))
    if not plan["topic"]:
        probs.append("missing topic")
    for k in option_keys(spec):
        if not plan["options"].get(k):
            probs.append(f"missing option {k!r}")
    for b in need:
        if not plan["beats"].get(b):
            probs.append(f"missing gist for {b}")
    if dneed:
        dd = plan["distractor"] or {}
        if not dd.get("topic") or not dd.get("option"):
            probs.append("distractor required for this set but missing topic/option")
        for b in dneed:
            if not (dd.get("beats") or {}).get(b):
                probs.append(f"missing distractor gist for {b}")
    elif plan["distractor"]:
        probs.append("distractor supplied but this set has none; set it to null")
        plan["distractor"] = None

    ms = d.get("meetings", [])
    if len(ms) != spec["n_meetings"]:
        probs.append(f"expected {spec['n_meetings']} meetings, got {len(ms)}")
        return None, None, probs

    allowed = set(need) | set(dneed)
    meetings, seen = [], {}
    for mi, m in enumerate(ms, 1):
        utts, realized = [], {}
        for j, u in enumerate(m["utterances"]):
            if u.get("speaker") not in names:
                probs.append(f"m{mi}[{j}]: speaker {u.get('speaker')!r} not in cast {sorted(names)}")
            utts.append(dict(speaker=u.get("speaker"), text=u.get("text", "")))
            for t in u.get("tags", []) or []:
                if t not in allowed:
                    probs.append(f"m{mi}[{j}]: unknown tag {t!r}")
                    continue
                want = next(b["meeting"] for b in spec["beats"] + (spec["distractor"]["beats"] if spec["distractor"] else [])
                            if b["id"] == t)
                if want != mi:
                    probs.append(f"m{mi}[{j}]: tag {t} belongs in meeting {want}")
                realized.setdefault(t, []).append(j)
                seen[t] = seen.get(t, 0) + 1
        meetings.append(dict(utterances=utts, realized=realized))
    for t in sorted(allowed - set(seen)):
        probs.append(f"tag {t} never used")
    if probs:
        return None, None, probs

    # implicit flags are part of the assignment (from sample_spec); nothing to do here
    tr, gold = assemble(spec, plan, meetings, models=dict(generator=source))
    return tr, gold, []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inbox")
    ap.add_argument("--out", default="data/synth")
    ap.add_argument("--source", default="claude-chat")
    ap.add_argument("--allow-errors", action="store_true", help="write sets even if validation errors remain")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    for sub in ("transcripts", "gold", "rejected"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    ok = bad = 0
    files = sorted(pathlib.Path(a.inbox).glob("*.txt")) + sorted(pathlib.Path(a.inbox).glob("*.json"))
    for p in files:
        try:
            d = parse_text(p) if p.suffix == ".txt" else json.loads(p.read_text())
        except Exception as e:
            print(f"{p.name}: could not read ({type(e).__name__}: {e})")
            bad += 1
            continue
        tr, gold, probs = convert(d, a.source)
        if probs:
            print(f"{p.name}: {len(probs)} problem(s)")
            for m in probs[:15]:
                print("   -", m)
            bad += 1
            continue
        errs = [m for lv, m in validate_set(tr, gold) if lv == "ERROR"]
        if errs and not a.allow_errors:
            print(f"{p.name}: {len(errs)} validation error(s)")
            for m in errs[:15]:
                print("   -", m)
            (out / "rejected" / p.name).write_text(json.dumps(dict(transcript=tr, gold=gold, errors=errs), indent=1))
            bad += 1
            continue
        sid = d["set_id"]
        (out / "transcripts" / f"{sid}.json").write_text(json.dumps(tr, indent=1))
        (out / "gold" / f"{sid}.json").write_text(json.dumps(gold, indent=1))
        ok += 1
        print(f"{p.name}: ok")
    print(f"\n{ok} imported, {bad} need fixing")


if __name__ == "__main__":
    main()
