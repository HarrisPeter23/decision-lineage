"""phase5_agent_sample.py - draws the >= 50-sentence agent-check sample (phase5.md section 0b(a)): stratified half NLI-supported / half not, spread over
question types, seed 0, from DEV pool 1. Writes the sheet WITHOUT the NLI verdict (results/phase5/agent_check_sheet.md) and the key separately
(results/phase5/agent_check_key.json), so the agent labels blind.  python eval/phase5_agent_sample.py
"""
import json
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    rng = random.Random(0)
    A = [json.loads(l) for l in (ROOT / "results/phase5/score/k1/answers.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    R = {json.loads(l)["qid"]: json.loads(l) for l in (ROOT / "results/phase5/retrieval_rf1/single_pass_recap_roles_top4@k1.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    pools = {True: [], False: []}
    for a in A:
        items = {(it["meeting_id"], tuple(it["idxs"])): it for it in R[a["qid"]]["retrieval"]["items"]}
        for s, c in zip(a["sentences"], a["checks"]):
            if not s["cites"]:
                continue
            cites = [items[(m, tuple(i))] for m, i in s["cites"] if (m, tuple(i)) in items]
            pools[c["supported"]].append(dict(qid=a["qid"], type=a["type"], text=s["text"], cites=[dict(speaker=x["speaker"], role=x["role"], text=x["text"]) for x in cites],
                                              nli_supported=c["supported"], p=c["p_support"]))
    picked = []
    for v in (True, False):
        by = {}
        for x in pools[v]:
            by.setdefault(x["type"], []).append(x)
        for xs in by.values():
            rng.shuffle(xs)
        types = sorted(by)
        i = 0
        while sum(1 for p in picked if p["nli_supported"] == v) < 26:
            t = types[i % len(types)]
            if by[t]:
                picked.append(by[t].pop())
            i += 1
    rng.shuffle(picked)
    for n, x in enumerate(picked, 1):
        x["sid"] = f"S{n:02d}"
    L = ["# Agent check sheet (blind: no NLI verdicts). Label each: supported by its citations? yes / no", ""]
    for x in picked:
        L.append(f"## {x['sid']} ({x['type']})")
        L.append(f"SENTENCE: {x['text']}")
        for c in x["cites"]:
            L.append(f"- CITED {c['speaker']} ({c['role']}): {c['text']}")
        L.append("")
    (ROOT / "results/phase5/agent_check_sheet.md").write_text("\n".join(L), encoding="utf-8")
    (ROOT / "results/phase5/agent_check_key.json").write_text(json.dumps([dict(sid=x["sid"], qid=x["qid"], type=x["type"], nli_supported=x["nli_supported"], p=x["p"])
                                                                          for x in picked], indent=1), encoding="utf-8")
    print(len(picked), "sentences")


if __name__ == "__main__":
    main()
