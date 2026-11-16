"""extract_baseline.py - single-pass chain extraction baseline (one call per meeting).

  python extract_baseline.py --data data/pilot --out preds/rules --provider rules
  python extract_baseline.py --data data/pilot --out preds/single_pass --provider anthropic --model MODEL
  python score.py --pred preds/single_pass --data data/pilot --bootstrap 1000

--provider rules is a crude keyword baseline: a LOWER BOUND that any LLM method should beat.
The LLM branch reads each meeting on its own (no cross-meeting context) in one pass; it is the
reference point for the multi-pass ablation (flag decisions -> resolve references -> type roles).
The anthropic/openai branches are untested against live APIs (no network where this was written).
"""
import argparse
import json
import pathlib
import re

from arcs import ROLE_DEFS
from llm import LLM, extract_json
from prompts import EXTRACT_SYSTEM, extract_prompt

ROLES = list(ROLE_DEFS)

# priority order: first matching rule wins for an utterance
RULES = [
    ("reconsideration", r"\b(reopen|look at (this|it) again|second look|take another look|revisit)\b"),
    ("resolution", r"\b(let'?s (just )?(go with|do that|switch|keep)|we'?re (switching|keeping|booking|going with)|"
                   r"i'?m (going to )?decid|decision:|we sign|we switch|we go with|moves to|go ahead with)\b"),
    ("proposal", r"\b(i (think|would say|'d say) we (should |just )?(go|use|do|charge|get|move|switch|put|hold)|"
                 r"can i propose|i propose|my ask|let'?s put|i think we (go|do|get))\b"),
    ("challenge", r"\b(this is (a|the) (real )?problem|i'?m (a bit )?worried|was worried|balk|objection|"
                  r"i don'?t think (it'?s|this)|that'?s a problem)\b"),
    ("evidence", r"(\b\d+(\.\d+)? ?(percent|%)|\bsoak test|\bload test|\bquote|\bpilot\b.*\d|\d+ (dollars|weeks|days))"),
    ("rationale", r"\bbecause\b"),
]


def rule_extract(meeting, mid):
    links = []
    for u in meeting["utterances"]:
        t = u["text"].lower()
        for role, pat in RULES:
            if re.search(pat, t):
                links.append(dict(meeting_id=mid, role=role, utterance_idxs=[u["idx"]],
                                  speaker=u["speaker"], confidence=0.3))
                break
    return links


FAILURES = []


def llm_extract(meeting, mid, llm, tag):
    n = len(meeting["utterances"])
    try:
        out = extract_json(llm.complete(EXTRACT_SYSTEM, extract_prompt(meeting), kind="extract",
                                        temperature=0, tag=tag))
        raw = out["links"] if isinstance(out, dict) else out
    except Exception as e:
        print(f"   {tag}: extraction failed ({type(e).__name__}: {e}); recording no links")
        FAILURES.append(tag)
        return []
    links = []
    for l in raw:
        try:
            role = str(l["role"]).strip().lower()
            idxs = [int(i) for i in l["utterance_idxs"] if 0 <= int(i) < n]
            if role in ROLES and idxs:
                links.append(dict(meeting_id=mid, role=role, utterance_idxs=idxs,
                                  speaker=l.get("speaker"), confidence=float(l.get("confidence", 0.5))))
        except Exception:
            continue
    return links


def run_dir(data, out, llm):
    """llm=None -> rule baseline. Returns (n_meetings, n_failed_meetings)."""
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    FAILURES.clear()
    total = 0
    for p in sorted((pathlib.Path(data) / "transcripts").glob("*.json")):
        tr = json.loads(p.read_text())
        links = []
        for m in tr["meetings"]:
            total += 1
            if llm is None:
                links += rule_extract(m, m["meeting_id"])
            else:
                import chunk_support
                ls, _, _w = chunk_support.run(m, m["meeting_id"], f"{tr['set_id']}-{m['meeting_id']}-extract", lambda w, mid, t: llm_extract(w, mid, llm, t))
                links += ls
        (out / f"{tr['set_id']}.json").write_text(json.dumps(
            dict(set_id=tr["set_id"], method="single_pass" if llm else "rules", links=links), indent=1))
        print(f"{tr['set_id']}: {len(links)} links")
    return total, len(FAILURES)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--provider", default="anthropic", help="anthropic | openai | rules")
    ap.add_argument("--model")
    a = ap.parse_args()
    llm = None if a.provider == "rules" else LLM(a.provider, a.model, temperature=0)
    total, failed = run_dir(a.data, a.out, llm)
    if failed:
        print(f"\n{failed} of {total} meeting extractions FAILED - scores would be misleading.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
