"""phase7_stage_loss.py - POST-HOC, descriptive (D-45): where each gold lineage pair of my system's TEST pool-1 headline questions is lost, by stage.
A pair is one (headline question, supporting gold link); 65 questions give 365 pairs over the unique TEST links. Stages, in order:
never extracted / extracted but cut by the top-4 cap / kept but not cited in the final answer (retrieval and generation jointly; the saved logs do
not separate them) / cited. Matching is the frozen rule (same meeting, within one utterance), as in phase7_failure_analysis.py and lineage_f1.
Reads only saved outputs; changes nothing frozen.
  python -I eval/phase7_stage_loss.py   -> results/phase7/stage_loss.json
"""
import json, pathlib, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path[:0] = [str(pathlib.Path(__file__).resolve().parent)]
from phase3_topk import topk
import lineage_f1 as LF
ROOT = pathlib.Path(__file__).resolve().parent.parent
HEAD = ("why_changed", "full_lineage", "evidence_to_reconsider")
A = [json.loads(l) for l in (ROOT / "results/phase7/score/lineage@test_k1/answers.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
ext = {}
for pdir in sorted((ROOT / "data/synth/pools/test").glob("test_k1_*")):
    priv = json.loads((pdir / "private_map.json").read_text(encoding="utf-8"))
    (sid,) = priv["_sets"]
    pred = json.loads((ROOT / "results/phase7/extract/preds" / f"{pdir.name}.json").read_text(encoding="utf-8"))["links"]
    ext[sid] = [(priv[l["meeting_id"]]["meeting_id"], l["utterance_idxs"]) for l in topk(pred, 4)]
    ext[sid + "_all"] = [(priv[l["meeting_id"]]["meeting_id"], l["utterance_idxs"]) for l in pred]
inv = LF.inv_maps("1", "test")


def near(items, l):
    return any(m == l["meeting_id"] and min(abs(x - y) for x in i for y in l["utterance_idxs"]) <= 1 for m, i in items)


st = dict(pairs=0, never_extracted=0, cut_by_cap=0, kept_not_cited=0, cited=0, cited_but_not_kept=0)
uniq, nq = set(), 0
for a in A:
    if a["type"] not in HEAD:
        continue
    nq += 1
    g = json.loads((ROOT / "data/synth/gold" / f"{a['set_id']}.json").read_text(encoding="utf-8"))
    q = next(x for x in g["questions"] if x["qid"] == a["qid"])
    L = {l["link_id"]: l for l in g["chain"] + (g["distractor"]["chain"] if g.get("distractor") else [])}
    back = {v: k for k, v in inv[a["set_id"]].items()}                   # pool meeting id -> gold meeting id
    cites = [(back[m], i) for s in a["sentences"] for m, i in s["cites"] if m in back]
    for lid in q["supporting_links"]:
        l = L.get(lid)
        if not l:
            continue
        st["pairs"] += 1
        uniq.add((a["set_id"], lid))
        kept, cited = near(ext[a["set_id"]], l), near(cites, l)
        if cited and not kept:
            st["cited_but_not_kept"] += 1
        if cited:
            st["cited"] += 1
        elif kept:
            st["kept_not_cited"] += 1
        elif near(ext[a["set_id"] + "_all"], l):
            st["cut_by_cap"] += 1
        else:
            st["never_extracted"] += 1
head = [a for a in A if a["type"] in HEAD]
fp = [a for a in head if a.get("false_premise")]
st.update(headline_questions=nq, unique_links=len(uniq), false_premise_questions=len(fp),
          false_premise_rejected=sum(bool(a.get("false_premise_ok")) for a in fp),
          answers_citing_no_gold_link=sum(a["expl_completeness_flag"] == 0 for a in head))
st["share"] = {k: round(st[k] / st["pairs"], 3) for k in ("never_extracted", "cut_by_cap", "kept_not_cited", "cited")}
(ROOT / "results/phase7/stage_loss.json").write_text(json.dumps(st, indent=1), encoding="utf-8")
print(json.dumps(st, indent=1))
