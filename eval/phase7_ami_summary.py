"""phase7_ami_summary.py - AMI case study (qualitative, descriptive; D-37/D-46): per-system means over the 5 AMI series for the systems with AMI
outputs (ours, vector_rag, evowiki_style; Graphiti on AMI was cut, D-37). Same metric code as TEST: cited-lineage F1 / precision / recall
(eval/lineage_f1.score_question, frozen tol-1 match), NLI-accepted claim rate and answer correctness (exact match, else the granite rubric under the
frozen *flag* policy; unparsed = 0). No tests: five series are too few. Reads only saved outputs.
  python -I eval/phase7_ami_summary.py   -> results/phase7/ami_summary.json, results/phase7/ami_summary.md
"""
import json, pathlib, re, sys
sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "eval"), str(ROOT / "synthgen"), str(ROOT)]
import lineage_f1 as LF                                                # noqa: E402

SYSTEMS = {"ours": "lineage@ami", "vector_rag": "vector_rag@ami", "evowiki_style": "evowiki_style@ami"}
VERD = {"correct": 1.0, "partial": 0.5, "incorrect": 0.0}
K = 6
J = {}
for l in (ROOT / "results/phase7/judge_ami/out/batch_out.jsonl").read_text(encoding="utf-8").splitlines():
    if l.strip():
        x = json.loads(l)
        m = re.search(r'"verdict"\s*:\s*"(correct|partial|incorrect)"', x.get("raw") or "", re.I)
        J[x["id"]] = VERD[m.group(1).lower()] if m else 0.0
INV = {}
for pdir in sorted((ROOT / "data/ami/pools").glob("ami_*")):
    for oid, v in json.loads((pdir / "private_map.json").read_text(encoding="utf-8")).items():
        if oid != "_sets":
            INV.setdefault(v["set_id"], {})[v["meeting_id"]] = oid
GOLD = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "data/ami/gold").glob("ami_*.json"))}

out = {}
for name, tag in SYSTEMS.items():
    A = {json.loads(l)["qid"]: json.loads(l) for l in (ROOT / "results/phase7/score" / tag / "answers.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    head, allq = [], []
    for sid, g in GOLD.items():
        gl = {l["link_id"]: dict(l, meeting_id=INV[sid][l["meeting_id"]]) for l in LF.gold_links(g)}
        for q in g["questions"]:
            a = A[q["qid"]]
            ch = a["checks"] if a["parse_ok"] else []
            corr = 0.0 if not a["parse_ok"] else (a["exact"] if a["exact"] is not None else J.get(f"{q['qid']}@{tag}@flag", 0.0))
            allq.append(dict(set_id=sid, correct=corr))
            if q["type"] in LF.HEADLINE and q["supporting_links"]:
                cited = [(m, i) for s in a["sentences"] for m, i in s["cites"]] if a["parse_ok"] else []
                r = LF.score_question(cited, [gl[i] for i in q["supporting_links"] if i in gl], K)
                r.update(set_id=sid, correct=corr, nli=(sum(c["supported"] for c in ch) / len(ch)) if ch else 0.0)
                head.append(r)
    mean = lambda rows, k: round(sum(LF.set_means(rows, k).values()) / len(LF.set_means(rows, k)), 3)   # noqa: E731
    out[name] = dict(n_headline=len(head), n_all=len(allq), parse_ok=sum(a["parse_ok"] for a in A.values()),
                     f1=mean(head, "f1"), p=mean(head, "p"), r=mean(head, "r"), nli_accepted=mean(head, "nli"),
                     correct_headline=mean(head, "correct"), correct_all=mean(allq, "correct"))
(ROOT / "results/phase7/ami_summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
L = ["# AMI case study (5 series; means over series; descriptive, no tests)", "",
     "| system | headline n | cited-lineage F1 | P | R | NLI-accepted | correctness (headline) | correctness (all 50) |", "|---|---|---|---|---|---|---|---|"]
L += [f"| {k} | {v['n_headline']} | {v['f1']:.3f} | {v['p']:.3f} | {v['r']:.3f} | {v['nli_accepted']:.3f} | {v['correct_headline']:.3f} | {v['correct_all']:.3f} |" for k, v in out.items()]
(ROOT / "results/phase7/ami_summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
