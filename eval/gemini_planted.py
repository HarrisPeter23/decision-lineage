"""gemini_planted.py - judge qualification of JUDGE_PRIMARY (gemini-3.5-flash-lite) on the DEV planted-error sets (FREEZE section 17), 2026-11-08.
Sentences: the 120 items of results/phase5/planted/sentences_k1.jsonl (60 corrupted in 6 ways + 60 real), with the SAME prompt as the DEV faithfulness
calibration (eval/phase5_gemini_faith.py); flagged = verdict "no". Answers: the 69 items of results/phase5/planted/answers_judge_items.jsonl (26 corrupted
in 4 ways + 43 real), with the SAME rubric prompt as granite; flagged = any verdict other than "correct". Single item, free tier, 450/day guard.
  python eval/gemini_planted.py run      (resumable)
  python eval/gemini_planted.py report   -> results/phase5/planted/gemini_qualification.json
"""
import json
import math
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "eval"), str(ROOT / "synthgen")]
import gemini_batch as GB                                  # noqa: E402
from phase5_gemini_faith import PROMPT as SENT_PROMPT      # noqa: E402
from phase5_score import JUDGE_SYSTEM                      # noqa: E402

LOG = "runtime/gemini_planted_log.jsonl"
if LOG not in GB.LOGS:
    GB.LOGS.append(LOG)
D = ROOT / "results/phase5/planted"
OUT = D / "gemini_planted.jsonl"


def items():
    S = [json.loads(l) for l in (D / "sentences_k1.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    for n, x in enumerate(S):
        c = "\n".join(f"- {i['speaker']} ({i.get('role') or 'excerpt'}): {i.get('source_text', i['text'])}" for i in x["cites"])
        yield dict(id=f"S{n:03d}", task="sentence", kind=x["kind"], system=GB.SYSTEM, prompt=SENT_PROMPT.format(s=x["text"], c=c))
    J = {json.loads(l)["id"]: json.loads(l) for l in (D / "answers_judge_items.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    for m in (json.loads(l) for l in (D / "answers_meta.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()):
        yield dict(id=m["id"], task="answer", kind=m["kind"], system=JUDGE_SYSTEM, prompt=J[m["id"]]["prompt"])


def run():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    from llm import LLM, DailyQuotaExceeded
    done = {json.loads(l)["id"] for l in OUT.read_text(encoding="utf-8").splitlines() if l.strip()} if OUT.exists() else set()
    llm = LLM("gemini_free", GB.MODEL, temperature=0, cache_dir="runtime/cache/gemini_planted", log_path=LOG)
    for it in items():
        if it["id"] in done:
            continue
        if GB.used_today() >= GB.BUDGET:
            print("daily budget reached; resume after the reset")
            break
        try:
            raw = llm.complete(it["system"], it["prompt"], kind="judge", temperature=0, tag=it["id"])
        except DailyQuotaExceeded:
            print("daily quota error; stopping")
            break
        with OUT.open("a", encoding="utf-8") as f:
            f.write(json.dumps(dict(id=it["id"], task=it["task"], kind=it["kind"], raw=raw[:400])) + "\n")
    print("done", sum(1 for _ in OUT.open(encoding="utf-8")))


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [k, n, round(p, 3), [round(max(0, c - h), 3), round(min(1, c + h), 3)]]


def report():
    R = [json.loads(l) for l in OUT.read_text(encoding="utf-8").splitlines() if l.strip()]
    res = {}
    for task in ("sentence", "answer"):
        rs = [r for r in R if r["task"] == task]
        if task == "sentence":
            flag = lambda r: (lambda m: (m.group(1).lower() == "no") if m else None)(re.search(r'"verdict"\s*:\s*"(yes|no)"', r["raw"], re.I))
        else:
            flag = lambda r: (lambda m: (m.group(1).lower() != "correct") if m else None)(re.search(r'"verdict"\s*:\s*"(correct|partial|incorrect)"', r["raw"], re.I))
        real = [flag(r) for r in rs if r["kind"] == "real"]
        fa = wilson(sum(bool(x) for x in real), len(real))
        out = dict(real_flagged=fa, unparsed=sum(flag(r) is None for r in rs), types={})
        for k in sorted({r["kind"] for r in rs} - {"real"}):
            xs = [flag(r) for r in rs if r["kind"] == k]
            caught = wilson(sum(bool(x) for x in xs), len(xs))
            out["types"][k] = dict(caught=caught, qualifies=bool(caught and fa and caught[2] >= 0.80 and fa[2] <= 0.10))
        res[task] = out
    (D / "gemini_qualification.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    dict(run=run, report=report)[sys.argv[1]]()
