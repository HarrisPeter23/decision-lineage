"""phase7_gemini_calib.py - Gemini calibration on TEST (FREEZE section 20), on the sample drawn BEFORE any Gemini call by eval/phase7_gemini_sample.py
(results/phase7/gemini_sample.json, seed 0). The prompts are the frozen DEV ones, imported, not copied:
  sentences: eval/phase5_gemini_faith.PROMPT with system gemini_batch.SYSTEM (cited items shown as "speaker (role): text", as on DEV);
  answers:   eval/phase5_score.judge_prompt (flag policy: all sentences) with system phase5_score.JUDGE_SYSTEM, the same rubric prompt as granite.
Single item per request, gemini-3.5-flash-lite, free tier, the 450/day guard of eval/gemini_batch.py. Every Gemini log of the project is counted,
including the pairwise log. Resumable. The run prints counts only, never verdicts (the user's rule: no Gemini score before CHECKPOINT 8).
  HF_HUB_OFFLINE=1 python eval/phase7_gemini_calib.py items   -> results/phase7/gemini_calib_items.jsonl
  HF_HUB_OFFLINE=1 python eval/phase7_gemini_calib.py run     -> results/phase7/gemini_calib.jsonl
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "eval"), str(ROOT / "synthgen")]
import gemini_batch as GB                                  # noqa: E402

LOG = "runtime/phase7_gemini_calib_log.jsonl"
for lg in (LOG, "runtime/gemini_pairwise_log.jsonl"):
    if lg not in GB.LOGS:
        GB.LOGS.append(lg)
OUT = ROOT / "results/phase7"
ITEMS = OUT / "gemini_calib_items.jsonl"
RES = OUT / "gemini_calib.jsonl"


def items():
    from phase5_gemini_faith import PROMPT as SENT_PROMPT
    from phase5_score import JUDGE_SYSTEM, judge_prompt
    S = json.loads((OUT / "gemini_sample.json").read_text(encoding="utf-8"))
    G = {}
    out = []
    for tag, d in S["systems"].items():
        R = {json.loads(l)["qid"]: json.loads(l) for l in (OUT / "retrieval" / f"{tag}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
        A = {json.loads(l)["qid"]: json.loads(l) for l in (OUT / "score" / tag / "answers.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
        for x in d["sentences"]:
            its = {(it["meeting_id"], tuple(it["idxs"])): it for it in R[x["qid"]]["retrieval"]["items"]}
            cites = [its[(m, tuple(i))] for m, i in x["cites"] if (m, tuple(i)) in its]
            c = "\n".join(f"- {it.get('speaker')} ({it.get('role') or 'excerpt'}): {it.get('text')}" for it in cites)
            out.append(dict(id=f"S|{tag}|{x['qid']}|{x['sent_index']}", task="sentence", tag=tag, qid=x["qid"], sent_index=x["sent_index"],
                            n_cites_found=len(cites), system=GB.SYSTEM, prompt=SENT_PROMPT.format(s=x["text"], c=c)))
        for x in d["answers"]:
            s = x["set_id"]
            if s not in G:
                G[s] = {q["qid"]: q for q in json.loads((ROOT / "data/synth/gold" / f"{s}.json").read_text(encoding="utf-8"))["questions"]}
            a = A[x["qid"]]
            out.append(dict(id=f"A|{tag}|{x['qid']}", task="answer", tag=tag, qid=x["qid"], exact_type=x["exact_type"], system=JUDGE_SYSTEM,
                            prompt=judge_prompt(G[s][x["qid"]], a["answer"] if a["parse_ok"] else "", a["sentences"] if a["parse_ok"] else [])))
    ITEMS.write_text("\n".join(json.dumps(i) for i in out) + "\n", encoding="utf-8")
    print(len(out), "items:", sum(i["task"] == "sentence" for i in out), "sentences,", sum(i["task"] == "answer" for i in out), "answers;",
          "sentences with a cited item not found:", sum(i["task"] == "sentence" and i["n_cites_found"] == 0 for i in out))


def free_mb():
    """Available physical memory in MB (Windows GlobalMemoryStatusEx; None elsewhere). The user's rule: pause below 1.5 GB free."""
    try:
        import ctypes

        class MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MS()
        m.dwLength = ctypes.sizeof(MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return m.ullAvailPhys // 2**20
    except Exception:
        return None


MIN_FREE_MB = 1536


def run():
    from dotenv import load_dotenv                         # GEMINI_API_KEY from .env; never printed or logged
    load_dotenv(ROOT / ".env")
    from llm import LLM, DailyQuotaExceeded
    its = [json.loads(l) for l in ITEMS.read_text(encoding="utf-8").splitlines() if l.strip()]
    done = {json.loads(l)["id"] for l in RES.read_text(encoding="utf-8").splitlines() if l.strip()} if RES.exists() else set()
    llm = LLM("gemini_free", GB.MODEL, temperature=0, cache_dir="runtime/cache/phase7_gemini_calib", log_path=LOG)
    n = 0
    for it in its:
        if it["id"] in done:
            continue
        if GB.used_today() >= GB.BUDGET:
            print("daily budget reached; resume after the reset")
            break
        fm = free_mb()
        if fm is not None and fm < MIN_FREE_MB:
            print(f"PAUSED: low memory ({fm} MB free < {MIN_FREE_MB} MB); resume when memory is free")
            break
        try:
            raw = llm.complete(it["system"], it["prompt"], kind="judge", temperature=0, tag=it["id"])
        except DailyQuotaExceeded:
            print("daily quota error; stopping")
            break
        with RES.open("a", encoding="utf-8") as f:
            f.write(json.dumps(dict(id=it["id"], raw=raw[:600])) + "\n")
        n += 1
    print("calibration judgements:", len(done) + n, "of", len(its), "| used today:", GB.used_today(), "of", GB.BUDGET)


if __name__ == "__main__":
    dict(items=items, run=run)[sys.argv[1]]()
