"""phase5_gemini_faith.py - JUDGE_PRIMARY (gemini-3.5-flash-lite, free tier) on a pre-drawn stratified sample of DEV pool-1 sentences (phase5.md 0b(b)):
all 52 agent-checked sentences + 148 more (seed 1, stratified by NLI verdict and question type). Single item per request (batching not validated for this
task). Daily budget guard of eval/gemini_batch.py (this log is counted). Synthetic text only (free-tier terms).
  python eval/phase5_gemini_faith.py draw     -> results/phase5/gemini_faith_sample.json
  python eval/phase5_gemini_faith.py run      -> results/phase5/gemini_faith.jsonl
  python eval/phase5_gemini_faith.py report   -> agreement with NLI and with the agent labels
"""
import json
import pathlib
import random
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "eval"), str(ROOT / "synthgen")]
import gemini_batch as GB                         # noqa: E402

LOG = "runtime/phase5_gemini_faith_log.jsonl"
if LOG not in GB.LOGS:
    GB.LOGS.append(LOG)
OUT = ROOT / "results/phase5"
PROMPT = """Decide whether the SENTENCE is fully supported by the CITED STATEMENTS from a meeting. "yes" = every claim in the sentence is stated in or
directly implied by the cited statements (who said or did what, numbers, options, outcomes, whether something changed). "no" = any claim is missing,
wrong, or only guessed. Ignore meeting numbers and dates.

SENTENCE: {s}

CITED STATEMENTS:
{c}

Return JSON: {{"verdict": "yes" | "no", "reason": "<one sentence>"}}"""


def draw():
    rng = random.Random(1)
    A = [json.loads(l) for l in (OUT / "score/k1/answers.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    R = {json.loads(l)["qid"]: json.loads(l) for l in (ROOT / "results/phase5/retrieval_rf1/single_pass_recap_roles_top4@k1.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    sheet = (OUT / "agent_check_sheet.md").read_text(encoding="utf-8")
    agent_texts = set(re.findall(r"^SENTENCE: (.*)$", sheet, re.M))
    rows = []
    for a in A:
        items = {(it["meeting_id"], tuple(it["idxs"])): it for it in R[a["qid"]]["retrieval"]["items"]}
        for s, c in zip(a["sentences"], a["checks"]):
            cites = [items[(m, tuple(i))] for m, i in s["cites"] if (m, tuple(i)) in items]
            if cites:
                rows.append(dict(qid=a["qid"], type=a["type"], text=s["text"], cites=[dict(speaker=x["speaker"], role=x["role"], text=x["text"]) for x in cites],
                                 nli_supported=c["supported"], agent=s["text"] in agent_texts))
    picked = [r for r in rows if r["agent"]]
    rest = [r for r in rows if not r["agent"]]
    rng.shuffle(rest)
    need = {True: 74, False: 74}
    for r in rest:
        if need[r["nli_supported"]] > 0:
            picked.append(r)
            need[r["nli_supported"]] -= 1
    for n, r in enumerate(picked):
        r["gid"] = f"G{n:03d}"
    (OUT / "gemini_faith_sample.json").write_text(json.dumps(picked, indent=1), encoding="utf-8")
    print(len(picked), "drawn;", sum(r["agent"] for r in picked), "agent-checked")


def run():
    from dotenv import load_dotenv                 # GEMINI_API_KEY from .env; never printed or logged
    load_dotenv(ROOT / ".env")
    from llm import LLM, DailyQuotaExceeded
    S = json.loads((OUT / "gemini_faith_sample.json").read_text(encoding="utf-8"))
    done = set()
    f = OUT / "gemini_faith.jsonl"
    if f.exists():
        done = {json.loads(l)["gid"] for l in f.read_text(encoding="utf-8").splitlines() if l.strip()}
    llm = LLM("gemini_free", GB.MODEL, temperature=0, cache_dir="runtime/cache/phase5_gemini_faith", log_path=LOG)
    for r in S:
        if r["gid"] in done:
            continue
        if GB.used_today() >= GB.BUDGET:
            print("daily budget reached; resume after the reset")
            break
        c = "\n".join(f"- {x['speaker']} ({x['role'] or 'excerpt'}): {x['text']}" for x in r["cites"])
        try:
            raw = llm.complete(GB.SYSTEM, PROMPT.format(s=r["text"], c=c), kind="judge", temperature=0, tag=r["gid"])
        except DailyQuotaExceeded:
            print("daily quota error; stopping")
            break
        m = re.search(r'"verdict"\s*:\s*"(yes|no)"', raw, re.I)
        with f.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(gid=r["gid"], verdict=m.group(1).lower() if m else None, raw=raw[:400])) + "\n")
    print("done", sum(1 for _ in f.open(encoding="utf-8")) if f.exists() else 0)


def report():
    S = {r["gid"]: r for r in json.loads((OUT / "gemini_faith_sample.json").read_text(encoding="utf-8"))}
    V = {json.loads(l)["gid"]: json.loads(l)["verdict"] for l in (OUT / "gemini_faith.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    lab = json.loads((OUT / "agent_check.json").read_text(encoding="utf-8"))["labels"]
    sheet = (OUT / "agent_check_sheet.md").read_text(encoding="utf-8")
    sid = {t: s for s, t in re.findall(r"^## (S\d+) .*\nSENTENCE: (.*)$", sheet, re.M)}

    def agree(pairs):
        n = len(pairs)
        if not n:
            return None
        po = sum(a == b for a, b in pairs) / n
        pa, pb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
        pe = pa * pb + (1 - pa) * (1 - pb)
        return dict(n=n, agreement=round(po, 3), kappa=round((po - pe) / (1 - pe), 3) if pe < 1 else None)
    g_nli = [(V[g] == "yes", S[g]["nli_supported"]) for g in V if V[g]]
    g_ag = [(V[g] == "yes", lab[sid[S[g]["text"]]] == "yes") for g in V if V[g] and S[g]["agent"] and S[g]["text"] in sid]
    n_ag = [(S[g]["nli_supported"], lab[sid[S[g]["text"]]] == "yes") for g in V if S[g]["agent"] and S[g]["text"] in sid]
    res = dict(gemini_vs_nli=agree(g_nli), gemini_vs_agent=agree(g_ag), nli_vs_agent_on_same=agree(n_ag), unparsed=sum(v is None for v in V.values()),
               gemini_yes_rate=round(sum(v == "yes" for v in V.values()) / max(1, len(V)), 3), n=len(V))
    (OUT / "gemini_faith_report.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


if __name__ == "__main__":
    dict(draw=draw, run=run, report=report)[sys.argv[1]]()
