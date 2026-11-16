"""Builds supplementary section S7 from the Fig. 1 case: the real answer, a constructed wrong-reason answer with the same citations, both scored
with the frozen eval/lineage_f1.score_question."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent   # usage: python paper/make_supp_example.py  (prints section S7 of SUPPLEMENTARY.md)
sys.path[:0] = [str(ROOT / "eval"), str(ROOT / "synthgen"), str(ROOT)]
import os; os.chdir(ROOT)
import lineage_f1 as LF

SET, QID = "set_01037", "set_01037-q06"
g = json.loads((ROOT / f"data/synth/gold/{SET}.json").read_text(encoding="utf-8"))
q = next(x for x in g["questions"] if x["qid"] == QID)
a = next(json.loads(l) for l in (ROOT / "results/phase7/score/lineage@test_k1/answers.jsonl").read_text(encoding="utf-8").splitlines()
         if l.strip() and json.loads(l)["qid"] == QID)
inv = LF.inv_maps("1", "test")[SET]; back = {v: k for k, v in inv.items()}
chain = [dict(l, meeting_id=inv[l["meeting_id"]]) for l in g["chain"]]
lin = [l for l in chain if l["link_id"] in q["supporting_links"]]

WRONG_ANSWER = "The original decision was changed because Parcelwise turned out to cost more than the regional couriers."
WRONG = ["In meeting 2, Arjun reported that Parcelwise's price per parcel was higher than the team had expected.",
         "Aisha kept Parcelwise for now because the cost figures were not yet complete.",
         "In meeting 3, Aisha reopened the decision because of the higher cost.",
         "Arjun stated that the earlier saving had been overstated and that Parcelwise was the more expensive option.",
         "Aisha moved the south-east parcels to Eastline and Southgate to reduce shipping costs.",
         "The original decision rested on a price estimate that turned out to be too low.",
         "The change followed a review of the carriers' prices.",
         "The decision was changed to cut costs."]
assert len(WRONG) == len(a["sentences"])
cited = [(m, i) for s in a["sentences"] for m, i in s["cites"]]
wrong = {"answer": WRONG_ANSWER, "sentences": [dict(text=t, cites=s["cites"]) for t, s in zip(WRONG, a["sentences"])]}
cited_w = [(m, i) for s in wrong["sentences"] for m, i in s["cites"]]
s1, s2 = LF.score_question(cited, lin, 6), LF.score_question(cited_w, lin, 6)
assert s1 == s2


def ref(m, ix):
    return f"[M{back[m][1:]}:{ix[0]}{'-' + str(ix[-1]) if len(ix) > 1 else ''}]"


def block(ans, sents):
    out = [f"**Answer.** {ans}", ""]
    out += [f"{k}. {s['text']} {' '.join(dict.fromkeys(ref(m, tuple(ix)) for m, ix in s['cites']))}" for k, s in enumerate(sents, 1)]
    return out


def sc(s):
    return f"{s['n_cited']} items cited; precision {s['p']:.2f}, recall {s['r']:.2f}, cited-lineage F1 {s['f1']:.2f}"


L = ["## S7. Worked example: what cited-lineage F1 does and does not measure",
     "Referenced in Section IV (\"Illustration of metric scope\"). Case: the Fig. 1 question (TEST `set_01037-q06`, why_changed): "
     f"\"{q['question']}\" Gold lineage: {', '.join(l['link_id'] for l in lin)}. "
     "Built by `paper/make_supp_example.py` from the gold file and our scored answer; both versions are scored with the frozen `eval/lineage_f1.score_question`.",
     "", "**Reference answer (gold).** " + q["answer_text"], "",
     "### (a) Our pipeline's actual answer (TEST output, unedited)", ""] + block(a["answer"], a["sentences"]) + [
     "", f"Score: {sc(s1)}.", "",
     "### (b) CONSTRUCTED FOR ILLUSTRATION: wrong reason, same citations",
     "Not a system output. Each sentence keeps the citations of the matching sentence in (a), but the stated reason for the change is cost, "
     "not late deliveries, which contradicts the gold lineage.", ""] + block(WRONG_ANSWER, wrong["sentences"]) + [
     "", f"Score: {sc(s2)}, identical to (a).", "",
     "### What this shows",
     "Cited-lineage F1 depends only on which lines are cited, so (a) and (b) score the same although (b) explains the change wrongly. "
     "The metric measures evidence localization; it does not check what the explanation says about the cited lines. "
     "(b) was not run through the correctness judge or the NLI checker; whether they would catch it is not claimed here.", ""]
print("\n".join(L))
