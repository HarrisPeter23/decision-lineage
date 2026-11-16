"""phase7_calib_report.py - agreement report for the TEST Gemini calibration (FREEZE sections 15 and 20). Post-freeze tooling (deviation D-42):
it only reads cached outputs and computes agreement; no model is called and no frozen behaviour changes.

Inputs (all existing):
  results/phase7/gemini_sample.json         the pre-drawn sample (seed 0)
  results/phase7/gemini_calib.jsonl         Gemini raw outputs, single item (eval/phase7_gemini_calib.py)
  results/phase7/score/<tag>/answers.jsonl  NLI checks per sentence (frozen faithfulness checker) and exact-match correctness
  results/phase7/judge/out/batch_out.jsonl  granite rubric verdicts (id "<qid>@<tag>@flag", the frozen flag policy)
Verdicts are parsed with the same regexes as the DEV calibration (phase5_gemini_faith) and phase5_final.verdict.

Reported:
  sentences: Gemini yes/no vs NLI supported (agreement, Cohen's kappa), overall and per system; checker flag precision / recall against
             Gemini "no" (the checker flags exactly the NLI-unsupported sentences under the flag policy). LLM-judged; Gemini is not
             qualified for sentences (FREEZE section 17), so these are bounds.
  answers:   rubric types: Gemini vs granite, 3-class (correct / partial / incorrect) and binary (correct vs not);
             exact-match types: Gemini "correct" vs exact match = 1.
Unparseable verdicts are counted and excluded from agreement.
  python eval/phase7_calib_report.py check   -> counts only (ids matched, unparsed), no agreement printed
  python eval/phase7_calib_report.py report  -> results/phase7/gemini_calib_report.json (+ .md)
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "eval")]
from gemini_batch import kappa                  # noqa: E402  (frozen helper: observed agreement, Cohen's kappa)
from phase5_final import verdict as rubric      # noqa: E402  (frozen rubric parser: 1.0 / 0.5 / 0.0 or None)

P7 = ROOT / "results/phase7"
LABEL = {1.0: "correct", 0.5: "partial", 0.0: "incorrect"}


def jl(p):
    return [json.loads(l) for l in pathlib.Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def sent_verdict(raw):
    m = re.search(r'"verdict"\s*:\s*"(yes|no)"', raw or "", re.I)
    return None if not m else m.group(1).lower()


def ans_verdict(raw):
    v = rubric(raw)
    return None if v is None else LABEL[v]


def load():
    S = json.loads((P7 / "gemini_sample.json").read_text(encoding="utf-8"))
    G = {r["id"]: r["raw"] for r in jl(P7 / "gemini_calib.jsonl")}
    J = {r["id"]: r.get("raw") for r in jl(P7 / "judge/out/batch_out.jsonl")}
    sents, answers = [], []
    for tag, d in S["systems"].items():
        A = {r["qid"]: r for r in jl(P7 / "score" / tag / "answers.jsonl")}
        for x in d["sentences"]:
            gid = f"S|{tag}|{x['qid']}|{x['sent_index']}"
            ck = A[x["qid"]]["checks"][x["sent_index"]]
            assert ck["text"] == x["text"], gid
            sents.append(dict(id=gid, tag=tag, done=gid in G, gemini=sent_verdict(G.get(gid)), nli=bool(ck["supported"])))
        for x in d["answers"]:
            gid = f"A|{tag}|{x['qid']}"
            a = A[x["qid"]]
            row = dict(id=gid, tag=tag, exact_type=x["exact_type"], done=gid in G, gemini=ans_verdict(G.get(gid)))
            if x["exact_type"]:
                row["ref"] = "correct" if a.get("exact") == 1.0 else "not"
            else:
                jid = f"{x['qid']}@{tag}@flag"
                row["ref"] = ans_verdict(J.get(jid)) if a["parse_ok"] else "incorrect"     # unparsed answers were scored incorrect, as frozen
                row["ref_missing"] = a["parse_ok"] and jid not in J
            answers.append(row)
    return sents, answers


def agree(pairs):
    if not pairs:
        return None
    o, k = kappa(pairs)
    return dict(n=len(pairs), agreement=o, kappa=k)


def sentence_stats(rows):
    r = [x for x in rows if x["gemini"] is not None]
    flagged = [x for x in r if not x["nli"]]                 # the checker flags NLI-unsupported sentences
    g_no = [x for x in r if x["gemini"] == "no"]
    tp = sum(1 for x in flagged if x["gemini"] == "no")
    return dict(n=len(r), gemini_yes_rate=round(sum(x["gemini"] == "yes" for x in r) / max(1, len(r)), 3),
                nli_supported_rate=round(sum(x["nli"] for x in r) / max(1, len(r)), 3),
                gemini_vs_nli=agree([(x["gemini"] == "yes", x["nli"]) for x in r]),
                checker_vs_gemini=dict(flagged=len(flagged), gemini_no=len(g_no), both=tp,
                                       flag_precision=round(tp / len(flagged), 3) if flagged else None,
                                       flag_recall=round(tp / len(g_no), 3) if g_no else None))


def answer_stats(rows):
    rub = [x for x in rows if not x["exact_type"] and x["gemini"] is not None and x["ref"] is not None]
    ex = [x for x in rows if x["exact_type"] and x["gemini"] is not None]
    return dict(rubric=dict(three_class=agree([(x["gemini"], x["ref"]) for x in rub]),
                            binary=agree([(x["gemini"] == "correct", x["ref"] == "correct") for x in rub]),
                            gemini_correct_rate=round(sum(x["gemini"] == "correct" for x in rub) / max(1, len(rub)), 3),
                            granite_correct_rate=round(sum(x["ref"] == "correct" for x in rub) / max(1, len(rub)), 3)),
                exact=dict(binary=agree([(x["gemini"] == "correct", x["ref"] == "correct") for x in ex]),
                           gemini_correct_rate=round(sum(x["gemini"] == "correct" for x in ex) / max(1, len(ex)), 3),
                           exact_match_rate=round(sum(x["ref"] == "correct" for x in ex) / max(1, len(ex)), 3)))


def check():
    s, a = load()
    print(f"sentences: {len(s)} sampled, {sum(x['done'] for x in s)} judged, {sum(x['done'] and x['gemini'] is None for x in s)} unparsed")
    print(f"answers:   {len(a)} sampled, {sum(x['done'] for x in a)} judged, {sum(x['done'] and x['gemini'] is None for x in a)} unparsed; "
          f"granite verdict missing for {sum(x.get('ref_missing', False) for x in a)}, unparseable for {sum((not x['exact_type']) and x['ref'] is None for x in a)}")


def report():
    s, a = load()
    todo = sum(not x["done"] for x in s + a)
    if todo:
        sys.exit(f"{todo} items not judged yet; run eval/phase7_gemini_calib.py run first")
    tags = sorted({x["tag"] for x in s})
    out = dict(label="LLM-judged (gemini-3.5-flash-lite); not human evaluation; Gemini is not qualified for sentences (FREEZE 17), so bounds",
               unparsed=dict(sentences=sum(x["gemini"] is None for x in s), answers=sum(x["gemini"] is None for x in a)),
               sentences=dict(all=sentence_stats(s), **{t: sentence_stats([x for x in s if x["tag"] == t]) for t in tags}),
               answers=dict(all=answer_stats(a), **{t: answer_stats([x for x in a if x["tag"] == t]) for t in tags}))
    (P7 / "gemini_calib_report.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    L = ["# Gemini calibration on TEST (FREEZE sections 15, 20). LLM-judged; bounds, not human evaluation", "",
         f"Unparsed Gemini verdicts: {out['unparsed']['sentences']} sentences, {out['unparsed']['answers']} answers (excluded).", "",
         "| system | sentences n | Gemini yes | NLI supported | agreement | kappa | flag precision | flag recall |", "|---|---|---|---|---|---|---|---|"]
    for t in ["all"] + tags:
        v = out["sentences"][t]
        g, c = v["gemini_vs_nli"] or {}, v["checker_vs_gemini"]
        L.append(f"| {t} | {v['n']} | {v['gemini_yes_rate']} | {v['nli_supported_rate']} | {g.get('agreement')} | {g.get('kappa')} | {c['flag_precision']} | {c['flag_recall']} |")
    L += ["", "| system | rubric n | 3-class agr. | 3-class kappa | binary agr. | binary kappa | exact n | exact agr. | exact kappa |", "|---|---|---|---|---|---|---|---|---|"]
    for t in ["all"] + tags:
        v = out["answers"][t]
        r3, rb, ex = v["rubric"]["three_class"] or {}, v["rubric"]["binary"] or {}, v["exact"]["binary"] or {}
        L.append(f"| {t} | {r3.get('n')} | {r3.get('agreement')} | {r3.get('kappa')} | {rb.get('agreement')} | {rb.get('kappa')} | {ex.get('n')} | {ex.get('agreement')} | {ex.get('kappa')} |")
    (P7 / "gemini_calib_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    dict(check=check, report=report)[sys.argv[1]]()
