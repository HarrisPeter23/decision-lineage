"""selftest.py - sanity-check the checker. Generates mock sets, corrupts them in known
ways, and asserts validate_set() flags each corruption. Run: python selftest.py"""
import copy
import json
import pathlib
import subprocess
import sys

from validate import list_sets, load_set, validate_set

OUT = "data/_selftest"
subprocess.run([sys.executable, "generate.py", "--mock", "--n", "12", "--seed", "5000", "--out", OUT],
               check=True, capture_output=True)


def errs(tr, g):
    return [m for lv, m in validate_set(tr, g) if lv == "ERROR"]


def find(arc):
    for sid in list_sets(OUT):
        tr, g = load_set(OUT, sid)
        if g["meta"]["arc_type"] == arc:
            return tr, g
    raise SystemExit(f"no {arc} set generated")


tr, g = find("simple_reversal")
assert errs(tr, g) == [], "clean set should have no errors"

checks = []

def case(name, mutate, expect):
    t, gg = copy.deepcopy(tr), copy.deepcopy(g)
    mutate(t, gg)
    got = errs(t, gg)
    ok = any(expect in e for e in got)
    checks.append(ok)
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  (got {got[:3]})"))


def wrong_speaker(t, gg):
    l = gg["chain"][0]
    l["speaker"] = [c for c in t["cast"] if c != l["speaker"]][0]

def bad_index(t, gg):
    gg["chain"][0]["utterance_idxs"] = [9999]

def leak(t, gg):
    t["meetings"][0]["utterances"][0]["text"] += " (see B3)"

def unknown_speaker(t, gg):
    t["meetings"][1]["utterances"][0]["speaker"] = "Nobody"

def res_before_proposal(t, gg):
    p = [l for l in gg["chain"] if l["role"] == "proposal"][0]
    r = [l for l in gg["chain"] if l["role"] == "resolution"][0]
    p["meeting"], p["meeting_id"], p["utterance_idxs"] = 3, "m3", [40]
    r["meeting"], r["meeting_id"], r["utterance_idxs"] = 1, "m1", [1]

def evidence_too_early(t, gg):
    ev = [l for l in gg["chain"] if l["role"] == "evidence"][0]
    ev["meeting"], ev["meeting_id"], ev["utterance_idxs"] = 1, "m1", [0]

def short_meeting(t, gg):
    t["meetings"][0]["utterances"] = t["meetings"][0]["utterances"][:10]

def dangling_question(t, gg):
    gg["questions"][0]["supporting_links"].append("ZZ9")

case("wrong speaker on a link", wrong_speaker, "expected")
case("utterance index out of range", bad_index, "out of range")
case("event id leaked into transcript", leak, "leaked")
case("speaker not in cast", unknown_speaker, "unknown speaker")
case("resolution before proposal", res_before_proposal, "before the first proposal")
case("evidence before the decision it challenges", evidence_too_early, "occurs before the resolution")
case("meeting too short", short_meeting, "only")
case("question cites missing link", dangling_question, "not in chain")

print(f"\n{sum(checks)}/{len(checks)} corruption checks caught")
sys.exit(0 if all(checks) else 1)
