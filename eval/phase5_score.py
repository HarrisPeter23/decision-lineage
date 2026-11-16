"""phase5_score.py - scores Layer 5 on DEV with the metrics pre-declared in reports/phase5.md section 0b.

  stage 1: python eval/phase5_score.py --tag k1 --stage parse           # parse generations, exact-match correctness, NLI faithfulness, judge items
           -> results/phase5/score/<tag>/{answers.jsonl, judge_items_flag.jsonl, judge_items_drop.jsonl}
  stage 2: python eval/phase5_score.py --tag k1 --stage final --judge <dir with batch_out.jsonl of the granite judge kernel>
           -> results/phase5/score/<tag>/summary.json, table.md
Inputs: results/phase5/retrieval_rf1/single_pass_recap_roles_top4@<tag>.jsonl and results/phase5/gen/<tag>/out/batch_out.jsonl. DEV only.
"""
import argparse
import json
import pathlib
import random
import re
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "eval"), str(ROOT / "synthgen")]
from argdecisionlineage import explain                                  # noqa: E402
from argdecisionlineage.faithfulness import NLIChecker, check_answer    # noqa: E402
from argdecisionlineage.graph import tokens                             # noqa: E402
from argdecisionlineage.linking import Embedder                         # noqa: E402
from phase5_retrieval import HEADLINE, completeness                     # noqa: E402
from score import gold_links                                            # noqa: E402

EXACT_OPTION = ("as_of", "lookup_final")
EXACT_WHO = ("who_proposed",)
NO_DECISION = re.compile(r"no decision|not (yet )?(been )?(made|decided)|undecided|had not decided|hadn't decided", re.I)
NO_CHANGE = re.compile(r"did not change|didn't change|was not changed|wasn't changed|no change|never changed|stayed|remained|kept|reaffirm", re.I)
EMB = Embedder()

JUDGE_SYSTEM = "You grade answers to questions about meeting decisions against a reference. Output ONLY valid JSON."


def judge_prompt(q, ans, sents):
    expl = " ".join(s["text"] for s in sents) or "(no explanation)"
    return f"""Grade the SYSTEM ANSWER against the REFERENCE. Judge only whether the system states the same facts as the reference (options, people, meetings,
reasons, evidence, whether the decision changed). Extra correct detail is fine. Missing key facts make it partial; a wrong or contradicting fact makes it incorrect.

QUESTION: {q['question']}
REFERENCE ANSWER: {q['answer_text']}
REFERENCE FACTS: {json.dumps(q['answer_facts'])[:1500]}

SYSTEM ANSWER: {ans}
SYSTEM EXPLANATION: {expl}

Return JSON: {{"verdict": "correct" | "partial" | "incorrect", "reason": "<one sentence>"}}"""


def map_option(text, g):
    keys = list(g["options"])
    if len(keys) > 1:
        toks = {k: set(tokens(g["options"][k])) for k in keys}
        t = set(tokens(text))
        sc = {k: len((toks[k] - set().union(*(toks[j] for j in keys if j != k))) & t) for k in keys}
        top = max(sc.values())
        if top > 0 and list(sc.values()).count(top) == 1:
            return max(sc, key=sc.get)
    vecs = EMB([g["options"][k] for k in keys])
    (v,) = EMB([text])
    return keys[int(np.argmax(vecs @ v))]


def gold_key(g, k):
    for v in g["versions"]:
        if v["valid_from"] <= k and (v["valid_to"] is None or k < v["valid_to"]):
            return v["option"]
    return None


def first_cast(text, cast):
    hits = [(m.start(), c) for c in cast for m in [re.search(rf"\b{re.escape(c)}\b", text)] if m]
    return min(hits)[1] if hits else None


def stage_parse(a):
    split = json.loads((ROOT / "data/synth/split.json").read_text(encoding="utf-8"))
    # --scope (Phase 7 plumbing, FREEZE): which sets, gold and pool maps; the metric code below is unchanged
    SC = dict(dev=("dev", "data/synth/gold", "data/synth/pools/dev", "dev_k"), test_k1=("test", "data/synth/gold", "data/synth/pools/test", "test_k"),
              test_k10=("test", "data/synth/gold", "data/synth/pools/test", "test_k"), ami=("ami", "data/ami/gold", "data/ami/pools", "ami_"))[a.scope]
    dev = set(split[SC[0]]) if SC[0] != "ami" else {p.stem for p in (ROOT / "data/ami/gold").glob("*.json")}
    rpath = a.retrieval or f"results/phase5/retrieval_rf1/single_pass_recap_roles_top4@{a.tag}.jsonl"
    rows = [json.loads(l) for l in (ROOT / rpath).read_text(encoding="utf-8").splitlines() if l.strip()]
    gen = {}
    for f in (ROOT / (a.gen_dir or f"results/phase5/gen/{a.tag}/out")).rglob("batch_out.jsonl"):
        for l in f.read_text(encoding="utf-8").splitlines():
            if l.strip():
                d = json.loads(l)
                gen[d["id"]] = d
    G = {}
    if a.collect_pairs:                       # pass 1 for the GPU NLI kernel: record every (premise, hypothesis) pair, score nothing
        seen = {}
        nli = NLIChecker(nli=lambda pairs: [seen.setdefault(p, 0.0) for p in pairs])
    elif a.nli_cache:                         # pass 2: scores computed by the same NLI model on GPU (kernel adl-*-nli), looked up by pair
        cache = {}
        for f in a.nli_cache.split(","):
            for l in pathlib.Path(f).read_text(encoding="utf-8").splitlines():
                if l.strip():
                    d = json.loads(l)
                    cache[(d["p"], d["h"])] = d["e"]
        nli = NLIChecker(nli=lambda pairs: [cache[p] for p in pairs])
    else:
        nli = NLIChecker()
    size = a.size or a.tag.split("k")[-1]
    index = json.loads((ROOT / SC[2] / "index.json").read_text(encoding="utf-8"))
    INV = {}
    for pname, info in index.items():
        if pname.startswith(SC[3] if SC[0] == "ami" else f"{SC[3]}{size}_"):
            priv = json.loads((ROOT / SC[2] / pname / "private_map.json").read_text(encoding="utf-8"))
            for oid, v in priv.items():
                if oid != "_sets":
                    INV.setdefault(v["set_id"], {})[v["meeting_id"]] = oid
    out_dir = ROOT / (a.score_root or "results/phase5/score") / a.tag
    out_dir.mkdir(parents=True, exist_ok=True)
    answers, jf, jd = [], [], []
    for r in rows:
        s = r["set_id"]
        assert s in dev
        if s not in G:
            G[s] = json.loads((ROOT / SC[1] / f"{s}.json").read_text(encoding="utf-8"))
        g = G[s]
        q = next(x for x in g["questions"] if x["qid"] == r["qid"])
        sub = r["retrieval"]
        _, _, idmap = explain.prompt(q["question"], sub)
        rec = gen.get(f"{r['qid']}@{a.tag}")
        assert rec is not None, f"no generation for {r['qid']}"
        p = explain.parse(rec.get("raw", ""), idmap)
        ordn = explain._ordinals(sub)
        checks = check_answer(p["sentences"], list(idmap.values()), nli, ordn)
        # correctness, exact types
        exact = None
        if q["type"] in EXACT_WHO:
            exact = float(first_cast(p["answer"], [c["name"] if isinstance(c, dict) else c for c in g["cast"]]) == q["answer_facts"]["speaker"])
        elif q["type"] in EXACT_OPTION:
            k = q["answer_facts"].get("as_of") or g["meta"]["n_meetings"]
            want = gold_key(g, k)
            got = None if (NO_DECISION.search(p["answer"]) or not p["answer"]) else map_option(p["answer"], g)
            exact = float(got == want) if p["parse_ok"] else 0.0
        fp = bool(q["answer_facts"].get("false_premise"))
        # explanation-level completeness: cited items, under flag (all) and drop (supported only)
        inv = INV[s]
        gl = {l["link_id"]: dict(l, meeting_id=inv[l["meeting_id"]]) for l in gold_links(g)}
        sup = [gl[i] for i in q["supporting_links"] if i in gl]
        cited = [c for x in p["sentences"] for c in x["cites"]]
        cited_drop = [c for x, ck in zip(p["sentences"], checks) if ck["supported"] for c in x["cites"]]
        answers.append(dict(qid=r["qid"], set_id=s, type=q["type"], false_premise=fp, parse_ok=p["parse_ok"], unknown_cites=p["unknown_cites"], answer=p["answer"],
                            sentences=[dict(text=x["text"], cites=[(c["meeting_id"], c["idxs"]) for c in x["cites"]]) for x in p["sentences"]], checks=checks,
                            exact=exact, false_premise_ok=(bool(NO_CHANGE.search(p["answer"])) if fp else None),
                            secs=rec.get("secs"), in_tok=rec.get("in_tok"), out_tok=rec.get("out_tok"), retrieval_completeness=r["completeness"],
                            expl_completeness_flag=completeness(cited, sup), expl_completeness_drop=completeness(cited_drop, sup)))
        if exact is None:
            keep = [x for x, c in zip(p["sentences"], checks) if c["supported"]]
            jf.append(dict(id=f"{r['qid']}@{a.tag}@flag", prompt=judge_prompt(q, p["answer"], p["sentences"])))
            jd.append(dict(id=f"{r['qid']}@{a.tag}@drop", prompt=judge_prompt(q, p["answer"], keep)))
    if a.collect_pairs:
        pairs = list(nli.cache)
        pathlib.Path(a.collect_pairs).write_text("\n".join(json.dumps(dict(p=p, h=h)) for p, h in pairs) + "\n", encoding="utf-8")
        print(len(pairs), "unique NLI pairs ->", a.collect_pairs)
        return
    (out_dir / "answers.jsonl").write_text("\n".join(json.dumps(x) for x in answers) + "\n", encoding="utf-8")
    (out_dir / "judge_items.jsonl").write_text("\n".join(json.dumps(x) for x in jf + jd) + "\n", encoding="utf-8")
    (out_dir / "judge_config.json").write_text(json.dumps(dict(model="granite4.2:8b", ctx=8192, think=False, num_predict=200, temperature=0, seed=7, system=JUDGE_SYSTEM), indent=1),
                                               encoding="utf-8")
    print(len(answers), "answers;", len(jf) + len(jd), "judge items; parse ok", sum(x["parse_ok"] for x in answers))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--stage", required=True, choices=["parse", "final"])
    ap.add_argument("--judge")
    ap.add_argument("--retrieval")
    ap.add_argument("--size", help="pool size (default: the number after the last 'k' in --tag)")
    ap.add_argument("--scope", default="dev", choices=["dev", "test_k1", "test_k10", "ami"])
    ap.add_argument("--gen-dir", help="directory holding the generation batch_out.jsonl files (Phase 7)")
    ap.add_argument("--score-root", help="output root (Phase 7: results/phase7/score)")
    ap.add_argument("--collect-pairs", help="write the unique NLI pairs to this jsonl and stop")
    ap.add_argument("--nli-cache", help="comma list of jsonl files {p, h, e} with GPU-computed entailment probabilities")
    a = ap.parse_args()
    if a.stage == "parse":
        stage_parse(a)
    else:
        import phase5_final
        phase5_final.main(a)
