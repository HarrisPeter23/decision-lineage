"""panel.py - LLM-panel verification of every gold chain link (Phase 1.3). One judge per run; results are resumable and cached.

  python eval/panel.py --data data/synth --judge gemini --out results/panel/gemini_synth.jsonl
Judge families: gemini (JUDGE_PRIMARY, free tier, runs here, throttled) ; the local JUDGE_SECONDARY runs on Kaggle with the same prompt builder
(see runtime/kaggle/judge2). Only synthetic text is sent (Gemini free-tier terms).
"""
import argparse
import json
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "synthgen"))
from llm import LLM, extract_json            # noqa: E402
from prompts import JUDGE_SYSTEM, judge_prompt  # noqa: E402

CONTEXT = 14


def link_prompt(tr, gold, link):
    m = tr["meetings"][link["meeting"] - 1]["utterances"]
    first = min(link["utterance_idxs"])
    ctx = "\n".join(f"[{i}] {u['speaker']}: {u['text']}" for i, u in enumerate(m) if max(0, first - CONTEXT) <= i < first) or "(start of meeting)"
    tgt = "\n".join(f"[{i}] {m[i]['speaker']}: {m[i]['text']}" for i in link["utterance_idxs"])
    role = link["role"] + (" (implicit: the speaker should NOT name the option)" if link.get("implicit") else "")
    p = judge_prompt(link["role"], link["gist"], link["speaker"], ctx, tgt).replace(f"Event role: {link['role']}", f"Event role: {role}", 1)
    return p[:p.index("SPEC_JSON_BEGIN")].rstrip()   # the toolkit appends a mock-only block; real judges must not see it


def iter_links(data):
    for gp in sorted(pathlib.Path(data, "gold").glob("*.json")):
        gold = json.loads(gp.read_text(encoding="utf-8"))
        tr = json.loads(pathlib.Path(data, "transcripts", gp.name).read_text(encoding="utf-8"))
        for l in gold["chain"]:
            yield gold["set_id"], tr, gold, l


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--judge", default="gemini", choices=["gemini", "openai_compatible"])
    ap.add_argument("--model", default="gemini-3.5-flash-lite")
    ap.add_argument("--out", required=True)
    ap.add_argument("--rpm", type=float, default=12.0, help="requests per minute (free tier limit is 15)")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            done.add((r["set_id"], r["link_id"]))
    provider = "gemini_free" if a.judge == "gemini" else "openai_compatible"
    llm = LLM(provider, a.model, temperature=0, max_tokens=300, cache_dir=f"runtime/cache/judge_{a.judge}", log_path=f"runtime/judge_{a.judge}_log.jsonl")
    gap = 60.0 / a.rpm
    n = 0
    t_last = 0.0
    with out.open("a", encoding="utf-8") as f:
        for sid, tr, gold, l in iter_links(a.data):
            if (sid, l["link_id"]) in done:
                continue
            prompt = link_prompt(tr, gold, l)
            wait = gap - (time.time() - t_last)
            if wait > 0:
                time.sleep(wait)
            t_last = time.time()
            try:
                raw = llm.complete(JUDGE_SYSTEM, prompt, kind="judge", temperature=0)
                r = extract_json(raw)
                verdict, reason = str(r.get("verdict", "")).lower(), str(r.get("reason", ""))[:300]
                if verdict not in ("yes", "partial", "no"):
                    verdict, reason = "invalid", raw[:200]
            except Exception as e:
                verdict, reason = "error", f"{type(e).__name__}: {str(e)[:160]}"
            f.write(json.dumps(dict(set_id=sid, link_id=l["link_id"], role=l["role"], implicit=l.get("implicit", False),
                                    judge=a.judge, model=a.model, verdict=verdict, reason=reason)) + "\n")
            f.flush()
            n += 1
            if n % 25 == 0:
                print(time.strftime("%H:%M:%S"), n, "judged", flush=True)
    print("done", n, "new verdicts")


if __name__ == "__main__":
    main()
