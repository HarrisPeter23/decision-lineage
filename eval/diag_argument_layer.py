"""diag_argument_layer.py - diagnostic (post-hoc, descriptive) of how the argumentative layer acts on TEST pool-1 retrieval.
Compares the retrieved item sets of the full system with the no_typing and static_graph ablations per headline question, and counts how often the
role filters, the cap and the version windows change what is retrieved.
  python -I eval/diag_argument_layer.py -> results/phase7/diag_argument_layer.json
"""
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = lambda tag: {json.loads(l)["qid"]: json.loads(l) for l in (ROOT / "results/phase7/retrieval" / f"{tag}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
full, nt, st = R("lineage@test_k1"), R("no_typing@test_k1"), R("static_graph@test_k1")
HEAD = ("why_changed", "evidence_to_reconsider", "full_lineage")
key = lambda r: {(it["meeting_id"], tuple(it["idxs"])) for it in r["retrieval"]["items"]}
out = collections.defaultdict(lambda: collections.Counter())
roles_full = collections.Counter()
versions_n = collections.Counter()
for q, r in full.items():
    t = r.get("type") or r["retrieval"].get("intent")
    intent = r["retrieval"]["intent"]
    grp = intent if intent in HEAD else "other"
    a, b, c = key(r), key(nt[q]), key(st[q])
    o = out[grp]
    o["n"] += 1
    o["same_as_no_typing"] += a == b
    o["same_as_static"] += a == c
    o["at_cap_12"] += len(a) >= 12
    o["fallback"] += bool(r["retrieval"].get("fallback"))
    o["changed_true"] += bool(r["retrieval"].get("changed"))
    o["no_version"] += not r["retrieval"]["versions"]
    o["items_full"] += len(a)
    o["items_static"] += len(c)
    if grp != "other":
        versions_n[len(r["retrieval"]["versions"])] += 1
        roles_full.update(it["role"] or "vector" for it in r["retrieval"]["items"])
res = dict(per_intent={k: dict(v) for k, v in out.items()}, headline_versions_of_anchor=dict(sorted(versions_n.items())), headline_item_roles=dict(roles_full))
(ROOT / "results/phase7/diag_argument_layer.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
