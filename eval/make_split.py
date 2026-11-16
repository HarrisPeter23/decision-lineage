"""make_split.py - freeze the DEV/TEST split of the synthetic benchmark (Phase 1.5). Run ONCE; later phases must not change the result.

Rule (written before looking at any system output):
  - DEV is about one third of the sets and contains the 6 toolkit pilot sets and the 4 writer-prompt tuning sets (01013-01016), because
    those were read and used during prompt tuning; the remaining DEV slots are filled per arc from the other Claude-written sets.
  - ALL control-writer sets (06x) go to TEST, because H4 compares them with Claude-written sets and H4 is a TEST-only analysis.
  - Arc quota in DEV (of the sets in that arc): simple_reversal 3, external_trigger 3, no_reversal 2, partial_override 2, re_reversal 2, deferred 2.
  - Remaining DEV slots are filled by a seeded draw (seed 20261102) that prefers business domains not yet in DEV.
split.json records the lists, the rule, and the SHA-256 of the sorted file list per split and overall.
"""
import hashlib
import json
import pathlib
import random

DATA = pathlib.Path("data/synth")
DEV_QUOTA = dict(simple_reversal=3, external_trigger=3, no_reversal=2, partial_override=2, re_reversal=2, deferred=2)
PILOT = {f"set_{s:05d}" for s in (1000, 1002, 1003, 1004, 1006, 1012)}
TUNING = {"set_01013", "set_01014", "set_01015", "set_01016"}


def main():
    prov = json.loads((DATA / "provenance.json").read_text(encoding="utf-8"))
    sets = sorted(prov)
    control = {s for s in sets if int(s.split("_")[1]) >= 1060}
    dev = set(PILOT | TUNING)
    rng = random.Random(20261102)
    for arc, q in DEV_QUOTA.items():
        have = [s for s in dev if prov[s]["arc_type"] == arc]
        pool = [s for s in sets if prov[s]["arc_type"] == arc and s not in dev and s not in control]
        rng.shuffle(pool)
        while len(have) < q and pool:
            seen = {prov[s]["domain"] for s in dev}
            pool.sort(key=lambda s: prov[s]["domain"] in seen)   # stable: unseen domains first, ties keep shuffled order
            pick = pool.pop(0)
            dev.add(pick)
            have.append(pick)
    test = sorted(set(sets) - dev)
    dev = sorted(dev)
    h = lambda L: hashlib.sha256("\n".join(L).encode()).hexdigest()
    out = dict(rule=__doc__.split("Rule", 1)[1].split("split.json")[0].strip(), dev=dev, test=test, control=sorted(control),
               sha256=dict(dev=h(dev), test=h(test), all=h(sorted(sets))), counts=dict(dev=len(dev), test=len(test)))
    (DATA / "split.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for name, L in (("DEV", dev), ("TEST", test)):
        arcs = {}
        for s in L:
            arcs[prov[s]["arc_type"]] = arcs.get(prov[s]["arc_type"], 0) + 1
        print(name, len(L), arcs, "writers", {w[:12]: sum(prov[s]["writer"].startswith(w[:12]) for s in L) for w in {prov[s]["writer"] for s in L}})
        print("   domains", len({prov[s]["domain"] for s in L}))
    print("sha256", out["sha256"])


if __name__ == "__main__":
    main()
