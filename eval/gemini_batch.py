"""gemini_batch.py - batched Gemini judging within the free-tier daily limit (user rules of 2026-11-03).

Rules this module enforces:
  * Gemini is used ONLY on pre-drawn calibration samples; local NLI and JUDGE_SECONDARY do the bulk.
  * 5-10 independent items per request, answered as a JSON array; the batched procedure is validated against single-item verdicts before use.
  * A daily budget: at most BUDGET requests per Pacific-time day (the free tier resets at midnight Pacific; limit measured: 500/day for
    gemini-3.5-flash-lite). Requests are counted from the timestamped call logs; a daily-quota 429 stops the run at once.
  * One judge model per task, fixed in advance and recorded in reports/judge_registry.md. Never switched mid-task.

  python eval/gemini_batch.py validate      # 50 pre-drawn planted-negative items, batches of 10 (5 requests), compared with their single-item verdicts
  python eval/gemini_batch.py budget        # requests used today (Pacific day) and remaining
"""
import collections
import datetime
import json
import pathlib
import random
import re
import sys
import time

sys.path.insert(0, "eval")
sys.path.insert(0, "synthgen")
from llm import LLM, DailyQuotaExceeded, extract_json      # noqa: E402

MODEL = "gemini-3.5-flash-lite"
BUDGET = 450                                     # of the 500/day limit; the rest is a safety margin
LOGS = ["runtime/judge_gemini_log.jsonl", "runtime/role_blind_gemini_log.jsonl", "runtime/gemini_batch_log.jsonl", "runtime/gemini_log.jsonl",
        "runtime/phase5_gemini_faith_log.jsonl", "runtime/gemini_planted_log.jsonl",
        "runtime/gemini_pairwise_log.jsonl", "runtime/phase7_gemini_calib_log.jsonl"]   # Phase 7 logs (D-38: budget accounting only)
SYSTEM = "You are a strict annotation checker. Output ONLY valid JSON."


def pacific_day_start(now=None):
    now = now or time.time()
    pt = datetime.timezone(datetime.timedelta(hours=-8))           # PST; the quota reset observed on 2026-11-03 matched midnight PST
    d = datetime.datetime.fromtimestamp(now, pt).replace(hour=0, minute=0, second=0, microsecond=0)
    return d.timestamp()


def used_today():
    t0, n = pacific_day_start(), 0
    for p in LOGS:
        f = pathlib.Path(p)
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("provider") == "gemini_free" and r.get("ts", 0) >= t0:
                    n += 1
    return n


def strip_answer_format(prompt):
    # drop the single-item answer instruction; the batch header gives the array format instead
    return re.split(r"\nAnswer JSON:", prompt)[0].rstrip()


def batch_prompt(items, field="verdict", choices='"yes" | "partial" | "no"', rubric='"yes" = right speaker, right role, content matches. "partial" = content or role only partly matches. "no" otherwise.'):
    head = (f"Below are {len(items)} INDEPENDENT items. Judge each one on its own, as if it were the only item; do not compare items or let one "
            f"influence another.\n\n")
    body = "\n\n".join(f"=== ITEM {it['id']} ===\n{strip_answer_format(it['prompt'])}" for it in items)
    tail = (f"\n\nAnswer with ONE JSON array, one object per item, in the same order:\n"
            f'[{{"id": "<item id>", "{field}": {choices}, "reason": "one sentence"}}, ...]\n{rubric}')
    return head + body + tail


def run_batches(items, size=10, field="verdict", allowed=("yes", "partial", "no"), cache="runtime/cache/gemini_batch", tag="", **kw):
    llm = LLM("gemini_free", MODEL, temperature=0, max_tokens=2500, cache_dir=cache, log_path="runtime/gemini_batch_log.jsonl")
    out = {}
    for i in range(0, len(items), size):
        chunk = items[i:i + size]
        if used_today() >= BUDGET:
            raise SystemExit(f"daily budget of {BUDGET} Gemini requests reached; resume after the Pacific midnight reset")
        try:
            raw = llm.complete(SYSTEM, batch_prompt(chunk, field=field, **kw), kind="judge_batch", temperature=0, tag=tag)
        except DailyQuotaExceeded as e:
            raise SystemExit(str(e))
        try:
            arr = extract_json(raw)
            arr = arr if isinstance(arr, list) else arr.get("items", [])
        except Exception:
            arr = []
        got = {str(a.get("id")): str(a.get(field, "")).lower().strip() for a in arr if isinstance(a, dict)}
        for it in chunk:
            v = got.get(it["id"], "missing")
            out[it["id"]] = v if v in allowed or v == "missing" else "invalid"
        time.sleep(5)
    return out


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    pe = sum(ca[c] * cb[c] for c in set(ca) | set(cb)) / (n * n)
    return round(po, 3), (None if pe == 1 else round((po - pe) / (1 - pe), 3))


def validate():
    key = json.loads(pathlib.Path("results/judge_sensitivity/key.json").read_text(encoding="utf-8"))
    items = {json.loads(l)["item"]: json.loads(l) for l in pathlib.Path("results/judge_sensitivity/items.jsonl").read_text(encoding="utf-8").splitlines()}
    single = {r["item"]: r["verdict"] for r in map(json.loads, pathlib.Path("results/judge_sensitivity/gemini.jsonl").read_text(encoding="utf-8").splitlines())}
    rng = random.Random(20261104)
    want = dict(real=20, wrong_role=8, wrong_speaker=8, shifted_utt=7, unsupportive=7)
    pick = []
    for kind, k in want.items():
        ids = sorted(i for i in key if key[i]["kind"] == kind)
        rng.shuffle(ids)
        pick += ids[:k]
    rng.shuffle(pick)
    pathlib.Path("results/gemini_batch").mkdir(parents=True, exist_ok=True)
    pathlib.Path("results/gemini_batch/validation_sample.json").write_text(json.dumps(pick, indent=1), encoding="utf-8")
    batched = run_batches([dict(id=i, prompt=items[i]["prompt"]) for i in pick], size=10, tag="validate")
    pairs = [(single[i], batched[i]) for i in pick]
    flag = lambda v: "flag" if v in ("partial", "no") else v
    agree, kap = kappa(pairs)
    fagree, fkap = kappa([(flag(a), flag(b)) for a, b in pairs])
    res = dict(n=len(pick), exact_agreement=agree, kappa=kap, flagged_agreement=fagree, flagged_kappa=fkap,
               missing=sum(b == "missing" for _, b in pairs), invalid=sum(b == "invalid" for _, b in pairs),
               disagreements=[dict(item=i, kind=key[i]["kind"], single=single[i], batched=batched[i]) for i in pick if single[i] != batched[i]])
    pathlib.Path("results/gemini_batch/validation.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "disagreements"}), "\ndisagreements:", res["disagreements"])


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "validate":
        validate()
    elif cmd == "budget":
        u = used_today()
        print(f"Gemini requests today (Pacific day): {u}; budget {BUDGET}; remaining {max(0, BUDGET - u)}")
