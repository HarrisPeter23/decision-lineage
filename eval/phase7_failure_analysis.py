"""phase7_failure_analysis.py - failure analysis of my system on TEST pool 1 (headline questions): where each gold lineage link is lost (kept after
the top-4 cap / cut by the cap / never extracted), false-premise outcomes, NLI-unsupported sentences, zero-completeness answers; prints examples.
  python -I eval/phase7_failure_analysis.py"""
import json, pathlib, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path[:0] = [str(pathlib.Path(__file__).resolve().parent)]
from phase3_topk import topk
ROOT = pathlib.Path(__file__).resolve().parent.parent
A = [json.loads(l) for l in (ROOT / "results/phase7/score/lineage@test_k1/answers.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
P = ROOT / "data/synth/pools/test"
ext, inv = {}, {}
for pdir in sorted(P.glob("test_k1_*")):
    priv = json.loads((pdir / "private_map.json").read_text(encoding="utf-8"))
    (sid,) = priv["_sets"]
    pred = json.loads((ROOT / "results/phase7/extract/preds" / f"{pdir.name}.json").read_text(encoding="utf-8"))["links"]
    ext[sid] = [(priv[l["meeting_id"]]["meeting_id"], l["utterance_idxs"], l["role"]) for l in topk(pred, 4)]
    ext[sid + "_all"] = [(priv[l["meeting_id"]]["meeting_id"], l["utterance_idxs"], l["role"]) for l in pred]
n_shown = 0
stats = dict(gold=0, kept=0, cut_by_cap=0, never=0)
for a in A:
    if a["type"] not in ("why_changed", "full_lineage", "evidence_to_reconsider"):
        continue
    g = json.loads((ROOT / "data/synth/gold" / f"{a['set_id']}.json").read_text(encoding="utf-8"))
    q = next(x for x in g["questions"] if x["qid"] == a["qid"])
    L = {l["link_id"]: l for l in g["chain"] + (g["distractor"]["chain"] if g.get("distractor") else [])}
    near = lambda pool, l: any(m == l["meeting_id"] and min(abs(x - y) for x in i for y in l["utterance_idxs"]) <= 1 for m, i, r in pool)
    for lid in q["supporting_links"]:
        l = L.get(lid)
        if not l:
            continue
        stats["gold"] += 1
        if near(ext[a["set_id"]], l):
            stats["kept"] += 1
        elif near(ext[a["set_id"] + "_all"], l):
            stats["cut_by_cap"] += 1
        else:
            stats["never"] += 1
    if a["expl_completeness_flag"] == 0 and n_shown < 2:
        miss = [L[i] for i in q["supporting_links"] if i in L and not near(ext[a["set_id"]], L[i])]
        if miss:
            n_shown += 1
            print("ZERO", a["qid"], q["type"], "| Q:", q["question"])
            for l in miss[:3]:
                print("   missed", l["role"], l["meeting_id"], l["utterance_idxs"], l["speaker"], "|", l["gist"][:160], "| cut_by_cap" if near(ext[a["set_id"] + "_all"], l) else "| never extracted")
            print("   SYS:", a["answer"][:220])
print("headline gold lineage links:", stats)
