"""diag_versions.py - diagnostic (post-hoc, descriptive): does the anchored decision's version history on TEST pool 1 match the gold one?
For each headline question: gold number of versions (data/synth/gold <set>.json 'versions') vs the system's versions of the anchored decision, and
whether the anchored decision is the gold decision (its retrieved items overlap the gold main-chain links, tol 1).
  python -I eval/diag_versions.py
"""
import collections
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
HEAD = ("why_changed", "evidence_to_reconsider", "full_lineage")
R = {json.loads(l)["qid"]: json.loads(l) for l in (ROOT / "results/phase7/retrieval/lineage@test_k1.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
inv = {}
for pdir in (ROOT / "data/synth/pools/test").glob("test_k1_*"):
    priv = json.loads((pdir / "private_map.json").read_text(encoding="utf-8"))
    for oid, v in priv.items():
        if oid != "_sets":
            inv[(v["set_id"], v["meeting_id"])] = oid
C = collections.Counter()
rows = []
for q, r in R.items():
    if r["retrieval"]["intent"] not in HEAD:
        continue
    g = json.loads((ROOT / "data/synth/gold" / f"{r['set_id']}.json").read_text(encoding="utf-8"))
    gq = next(x for x in g["questions"] if x["qid"] == q)
    gv = len(g["versions"])
    sv = len(r["retrieval"]["versions"])
    main = [(inv[(r["set_id"], l["meeting_id"])], l["utterance_idxs"]) for l in g["chain"]]
    items = [(it["meeting_id"], it["idxs"]) for it in r["retrieval"]["items"]]
    hit = any(m == gm and min(abs(a - b) for a in i for b in gi) <= 1 for m, i in items for gm, gi in main)
    fp = bool(gq["answer_facts"].get("false_premise"))
    C["n"] += 1
    C["anchor_on_gold_decision"] += hit
    C["gold_changed"] += gv >= 2
    C["sys_changed"] += sv >= 2
    C["changed_agree"] += (gv >= 2) == (sv >= 2)
    C["version_count_exact"] += gv == sv
    rows.append((q, gq["type"], fp, gv, sv, hit))
print(dict(C))
print("gold vs system version counts (headline):", collections.Counter((gv, sv) for _, _, _, gv, sv, _ in rows).most_common())
