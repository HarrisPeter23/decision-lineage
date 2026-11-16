"""extract_args.py - P3-F config `recap_args_div4`, pass 2: argument completion on top of `single_pass_recap_roles` (reports/phase3_configs.md P3-F).

For each meeting: given the transcript and the decisions/options the SYSTEM ITSELF extracted from this meeting in pass 1 (single_pass_recap_roles output,
read from <data>/base_preds/<set>.json; never gold), find the utterances that give a REASON for or against an option (rationale) or OBJECT to a decided
option (challenge). New links are merged with pass 1 with the chunking merge rule (same role and a shared utterance, or adjacent with the same speaker).
The role-balanced cap (eval/phase3_topk.div_topk, K=4) is applied afterwards, outside this module. Examples are invented (an orchard cooperative; names
outside the benchmark's cast pool). Prompt version args_v1.
"""
import json
import pathlib

import chunk_support
from llm import extract_json

PROMPT_VERSION = "args_v1"
SYSTEM = "You analyze workplace meeting transcripts and label how decisions are argued. Output ONLY valid JSON, no commentary, no code fences."
GUIDE = """Two roles only:
- rationale: a REASON for or against an option, argued from judgement, values or consequences. It explains WHY an option is good or bad.
- challenge: an OBJECTION to an option that has already been decided or is clearly winning; the speaker argues it is wrong or risky.
Not a rationale: new data, figures, test results or outside facts on their own (that is evidence); proposing an option; agreeing to an option.

Contrastive examples (an invented orchard cooperative choosing a cold-store supplier; NOT from the transcript below):
- "Frostline is closer, so the pickers lose less time on the road." -> rationale (a reason for Frostline).
- "Frostline's quote is 8,300 a season." -> NOT a rationale (a figure on its own: evidence).
- "That price only works if the apples don't sit there past October, and they always do." -> rationale (a reason against, argued from consequences).
- Odile, after Frostline was chosen: "I still think Frostline is the wrong call, their doors failed twice last winter." -> challenge.
- Bram: "Let's go with Frostline." -> NOT a rationale (a proposal or a resolution).
- Esko: "Because the co-op can't carry a second contract next year." -> rationale (a reason, even if it is short and starts with 'because')."""


V2_RULE = """
Be selective: for each decision return at most ONE reason for and ONE reason against an option (the clearest, explicit ones), plus any objection to a decided
option. Skip restatements of a reason already given, passing remarks and jokes."""


def prompt(meeting, decisions, version="v1"):
    lines = "\n".join(f"[{u['idx']}] {u['speaker']}: {u['text']}" for u in meeting["utterances"])
    dec = "\n".join(f"- {d}" for d in decisions) or "- (none found yet; consider any decision discussed)"
    return f"""Below is one meeting transcript. Each line is [index] speaker: text.

{GUIDE}
{V2_RULE if version == "v2" else ""}
Decisions discussed in this meeting (from an earlier analysis; it may contain mistakes):
{dec}

Find every rationale and every challenge about these decisions in THIS meeting. An event is 1-3 consecutive utterances by the same speaker; give all their
indexes, the most important first. speaker = the speaker of the first utterance. confidence is between 0 and 1. decision = which decision above it is about.

Return JSON: {{"links": [{{"role": "rationale|challenge", "utterance_idxs": [int, ...], "speaker": "Name", "confidence": 0.0, "decision": "..."}}]}}

TRANSCRIPT:
{lines}"""


FAILURES = []


def _same(a, b):
    if a["role"] != b["role"] or a["meeting_id"] != b["meeting_id"]:
        return False
    A, B = set(a["utterance_idxs"]), set(b["utterance_idxs"])
    return bool(A & B) or (a.get("speaker") == b.get("speaker") and min(abs(x - y) for x in A for y in B) <= 1)


def _call(window, mid, llm, tag, decisions, version="v1"):
    n = len(window["utterances"])
    try:
        out = extract_json(llm.complete(SYSTEM, prompt(window, decisions, version), kind="extract_args", temperature=0, tag=tag))
        raw = out["links"] if isinstance(out, dict) else out
    except Exception as e:
        print(f"   {tag}: argument pass failed ({type(e).__name__}: {e}); pass-1 links kept unchanged")
        FAILURES.append(tag)
        return []
    links = []
    for l in raw:
        try:
            role = str(l["role"]).strip().lower()
            idxs = [int(i) for i in l["utterance_idxs"] if 0 <= int(i) < n]
            if role in ("rationale", "challenge") and idxs:
                links.append(dict(meeting_id=mid, role=role, utterance_idxs=idxs, speaker=l.get("speaker"), confidence=float(l.get("confidence", 0.5)),
                                  decision=str(l.get("decision") or "")[:120], option="", source="args"))
        except Exception:
            continue
    return links


def run_dir(data, out, llm, version="v1"):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    FAILURES.clear()
    total = added = 0
    for p in sorted((pathlib.Path(data) / "transcripts").glob("*.json")):
        tr = json.loads(p.read_text(encoding="utf-8"))
        base = json.loads((pathlib.Path(data) / "base_preds" / p.name).read_text(encoding="utf-8"))["links"]
        links = list(base)
        for m in tr["meetings"]:
            total += 1
            mine = [l for l in base if l["meeting_id"] == m["meeting_id"]]
            decisions = list(dict.fromkeys(f"{l.get('decision') or '?'}" + (f" (option: {l['option']})" if l.get("option") else "") for l in mine))[:10]
            tag = f"{tr['set_id']}-{m['meeting_id']}-args"
            new, _, _w = chunk_support.run(m, m["meeting_id"], tag, lambda w, mid, t: _call(w, mid, llm, t, decisions, version))
            for l in new:
                if not any(_same(l, x) for x in links):
                    links.append(l)
                    added += 1
        (out / p.name).write_text(json.dumps(dict(set_id=tr["set_id"], method="single_pass_recap_args", prompt_version=f"args_{version}", links=links), indent=1),
                                  encoding="utf-8")
        print(f"{tr['set_id']}: {len(links)} links ({len(links) - len(base)} added)")
    return total, len(FAILURES)
