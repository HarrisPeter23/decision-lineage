"""selftest_score.py - verify score.py by corrupting perfect (oracle) predictions in known ways.
Run: python selftest_score.py [data_dir]   (default data/pilot)"""
import copy
import json
import pathlib
import random
import sys

from score import ROLES, aggregate, gold_links, score_set

DATA = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "data/pilot")
golds = [json.loads(p.read_text()) for p in sorted((DATA / "gold").glob("*.json"))]


def oracle(g):
    return [dict(meeting_id=l["meeting_id"], role=l["role"], utterance_idxs=list(l["utterance_idxs"]),
                 speaker=l["speaker"], confidence=1.0) for l in gold_links(g)]


def run(mutate, tol=0):
    rs = []
    for g in golds:
        preds = oracle(g)
        preds = mutate(preds, g)
        rs.append(score_set(preds, g, tol))
    return aggregate(rs)


results = []


def check(name, cond, detail=""):
    results.append(cond)
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"   {detail}"))


# 1. perfect predictions
a = run(lambda p, g: p)
check("oracle: role-typed P=R=F1=1", all(abs(a["role_typed"][k] - 1) < 1e-9 for k in ("p", "r", "f1")), a["role_typed"])
check("oracle: speaker acc 1, chain completeness 1, chain-exact 1",
      a["speaker_accuracy_given_localized"] == 1 and a["chain_completeness"] == 1 and a["chain_exact_rate"] == 1)
check("oracle: implicit recall 1", a["implicit_resolution_recall"] == 1)

# 2. drop links deterministically: precision stays 1, recall = kept share
rng = random.Random(0)
def drop_half(p, g):
    return [x for i, x in enumerate(p) if i % 2 == 0]
a = run(drop_half)
kept = sum((len(gold_links(g)) + 1) // 2 for g in golds)
total = sum(len(gold_links(g)) for g in golds)
check("drop half: precision 1", abs(a["role_typed"]["p"] - 1) < 1e-9, a["role_typed"])
check("drop half: recall = kept/total", abs(a["role_typed"]["r"] - kept / total) < 1e-9,
      (a["role_typed"]["r"], kept / total))

# 3. spurious predictions: recall unchanged, precision falls
def add_spurious(p, g):
    extra = [dict(meeting_id="m1", role="proposal", utterance_idxs=[i], speaker="X") for i in range(500, 505)]
    return p + extra
a = run(add_spurious)
check("spurious: recall still 1", abs(a["role_typed"]["r"] - 1) < 1e-9)
check("spurious: precision < 1", a["role_typed"]["p"] < 1)

# 4. role swap on evidence only: localization perfect, evidence role recall 0
def swap_evidence(p, g):
    return [dict(x, role="challenge") if x["role"] == "evidence" else x for x in p]
a = run(swap_evidence)
check("role swap: localization recall 1", abs(a["localization"]["r"] - 1) < 1e-9, a["localization"])
check("role swap: evidence recall 0", a["per_role"]["evidence"]["r"] == 0, a["per_role"]["evidence"])
check("role swap: confusion records evidence->challenge",
      any(k == "evidence->challenge" for k in a["confusion"]))
check("role swap: role accuracy < 1", a["role_accuracy_given_localized"] < 1)

# 5. index shift by one: tol 0 misses, tol 1 recovers
def shift(p, g):
    return [dict(x, utterance_idxs=[i + 1 for i in x["utterance_idxs"]]) for x in p]
a0, a1 = run(shift, 0), run(shift, 1)
check("shift +1, tol 0: localization recall < 0.2", a0["localization"]["r"] < 0.2, a0["localization"])
check("shift +1, tol 1: localization recall 1", abs(a1["localization"]["r"] - 1) < 1e-9, a1["localization"])

# 6. wrong speakers: localization fine, speaker accuracy 0
def wrong_speaker(p, g):
    return [dict(x, speaker="Nobody") for x in p]
a = run(wrong_speaker)
check("wrong speaker: speaker acc 0, role-typed F1 still 1",
      a["speaker_accuracy_given_localized"] == 0 and abs(a["role_typed"]["f1"] - 1) < 1e-9)

# 7. drop only implicit resolutions: implicit recall 0, everything else intact
def drop_implicit(p, g):
    imp = {(l["meeting_id"], tuple(l["utterance_idxs"])) for l in gold_links(g) if l.get("implicit")}
    return [x for x in p if (x["meeting_id"], tuple(x["utterance_idxs"])) not in imp]
a = run(drop_implicit)
check("drop implicit: implicit recall 0", a["implicit_resolution_recall"] == 0, a["implicit_resolution_recall"])
check("drop implicit: precision 1", abs(a["role_typed"]["p"] - 1) < 1e-9)

# 8. chain-exact: remove one main-chain link from one set only
def drop_one(p, g):
    return p[1:] if g["set_id"] == golds[0]["set_id"] else p
a = run(drop_one)
check("drop one link in one set: chain-exact = (n-1)/n",
      abs(a["chain_exact_rate"] - (len(golds) - 1) / len(golds)) < 1e-9, a["chain_exact_rate"])

# 9. one-to-one matching: duplicate predictions must not both count as true positives
def duplicate(p, g):
    return p + copy.deepcopy(p)
a = run(duplicate)
check("duplicates: recall 1 but precision 0.5", abs(a["role_typed"]["r"] - 1) < 1e-9
      and abs(a["role_typed"]["p"] - 0.5) < 1e-9, a["role_typed"])

print(f"\n{sum(results)}/{len(results)} scorer checks passed")
sys.exit(0 if all(results) else 1)
