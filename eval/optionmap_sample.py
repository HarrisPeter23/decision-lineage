"""optionmap_sample.py - pre-declared validation of the evaluation-side option mapper (eval/option_map.py).
Rule, fixed BEFORE the labels or the mapper outputs on this sample are seen: draw 40 exact-type (lookup_final / as_of) answers that name an option, at random
(seed 0) from DEV pool 1 of all three systems so far (lineage, vector_rag, evowiki_style). The agent labels which gold option each answer states, blind to
the mapper outputs. The mapper version (v1 or v3) with the higher accuracy on those 40 is used for every system and every reported number; a tie keeps v1.
  python eval/optionmap_sample.py draw     -> results/phase6/optionmap_sheet.md, optionmap_key.json
  python eval/optionmap_sample.py score    (needs results/phase6/optionmap_labels.json)
"""
import json
import pathlib
import random
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "eval")]
NO = re.compile(r"no decision|not (yet )?(been )?(made|decided)|undecided|had not decided|hadn't decided", re.I)
TAGS = ("k1", "vector_rag_k1", "evowiki_style_k1")


def draw():
    pool = []
    for t in TAGS:
        for l in (ROOT / f"results/phase5/score/{t}/answers.jsonl").read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            a = json.loads(l)
            if a["type"] in ("lookup_final", "as_of") and a["answer"] and not NO.search(a["answer"]):
                pool.append((t, a["qid"], a["set_id"], a["answer"]))
    random.Random(0).shuffle(pool)
    S = pool[:40]
    L = ["# Option-mapping check sheet (agent, blind to mapper outputs): which gold option does the ANSWER state? key, or 'unclear'", ""]
    for n, (t, qid, sid, ans) in enumerate(S, 1):
        g = json.loads((ROOT / "data/synth/gold" / f"{sid}.json").read_text(encoding="utf-8"))
        q = next(x for x in g["questions"] if x["qid"] == qid)
        L += [f"## M{n:02d}", "Q: " + q["question"]] + [f"  [{k}] {v}" for k, v in g["options"].items()] + ["ANSWER: " + ans, ""]
    (ROOT / "results/phase6/optionmap_sheet.md").write_text("\n".join(L), encoding="utf-8")
    (ROOT / "results/phase6/optionmap_key.json").write_text(json.dumps([dict(mid=f"M{n:02d}", tag=t, qid=qid, set_id=sid, answer=ans)
                                                                         for n, (t, qid, sid, ans) in enumerate(S, 1)], indent=1), encoding="utf-8")
    print(len(pool), "candidates;", len(S), "drawn")


def score():
    from option_map import map_option
    K = json.loads((ROOT / "results/phase6/optionmap_key.json").read_text(encoding="utf-8"))
    lab = json.loads((ROOT / "results/phase6/optionmap_labels.json").read_text(encoding="utf-8"))["labels"]
    res = {}
    for ver in (1, 3):
        ok = 0
        wrong = []
        for k in K:
            g = json.loads((ROOT / "data/synth/gold" / f"{k['set_id']}.json").read_text(encoding="utf-8"))
            q = next(x for x in g["questions"] if x["qid"] == k["qid"])
            got = map_option(k["answer"], g, q["question"], ver)
            ok += got == lab[k["mid"]]
            if got != lab[k["mid"]]:
                wrong.append((k["mid"], got, lab[k["mid"]]))
        res[f"v{ver}"] = dict(accuracy=f"{ok}/{len(K)}", wrong=wrong)
    a1, a3 = (int(res[v]["accuracy"].split("/")[0]) for v in ("v1", "v3"))
    res["selected"] = "v3" if a3 > a1 else "v1"
    (ROOT / "results/phase6/optionmap_validation.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    dict(draw=draw, score=score)[sys.argv[1]]()
