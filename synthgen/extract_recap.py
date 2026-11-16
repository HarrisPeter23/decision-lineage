"""extract_recap.py - Phase 3 extra DEV config `single_pass_recap_roles` (deviation D-17; requested at the CHECKPOINT 3 review).

single_pass plus two changes, nothing else:
  1. cross-meeting recap: before meeting k, the prompt lists the decisions the SYSTEM ITSELF extracted from meetings 1..k-1 of the same corpus (its own
     links, their role, speaker, meeting and the words of the cited utterance from the transcript). Gold is never read. Meetings are processed in order.
  2. explicit role definitions with contrastive examples for the confusable pairs: challenge vs rationale, reconsideration vs proposal / challenge,
     rationale vs evidence. The examples are invented for this prompt (a facilities team choosing a cleaning contractor); they are not taken from
     any benchmark set, DEV or TEST.
Each link also carries `decision` (a short name for what is being decided) and `option` (the option it concerns), which the recap and the per-decision cap
(eval/phase3_caps.py) use. Same chunking rule (chunk_support) and output format as single_pass; extra fields are ignored by score.py.
"""
import json
import pathlib

import chunk_support
from llm import extract_json

ROLES = ["proposal", "rationale", "evidence", "challenge", "reconsideration", "resolution"]
PROMPT_VERSION = "recap_roles_v1"

SYSTEM = ("You analyze workplace meeting transcripts and label how decisions are discussed. "
          "Output ONLY valid JSON, no commentary, no code fences.")

ROLE_GUIDE = """Roles (exactly one per event):
- proposal: someone puts forward an option for a decision ("I'd go with X", "what about we do X instead").
- rationale: a REASON for or against an option, argued from judgement, values or consequences ("X is simpler to run", "that would annoy the night shift").
- evidence: NEW INFORMATION that bears on the decision: a number, a test or pilot result, a quote, a deadline, a rule, an outside event ("the trial cost 14% more", "legal says we can't before March").
- challenge: an OBJECTION to the option currently decided or currently winning; the speaker argues it is wrong or risky ("I don't think we should keep X, it keeps failing").
- reconsideration: the group, usually the lead, AGREES TO REOPEN a decision that was already made ("fine, let's put X back on the table next week", "we should look at that decision again").
- resolution: the group settles on an option: a decision is made, changed, or kept. Can be implicit: "yeah, go ahead", or an instruction that presupposes it ("Sam, send them the contract").

Contrastive examples (an invented facilities team choosing a cleaning contractor; NOT from the transcript below):
- "Brightway is cheaper and they already know the building." -> rationale (a reason), NOT evidence.
- "Brightway's quote came in at 4,200 a month, the other one 5,100." -> evidence (new figures), NOT rationale.
- "Their last audit failed two of six floors." -> evidence (a reported result), even though it argues against them.
- "I'm not comfortable staying with Brightway after those audits." said AFTER Brightway was chosen -> challenge (objects to the decided option).
- "Brightway would be cheaper." said BEFORE anything is decided -> rationale, NOT challenge.
- "Okay, let's revisit the cleaning contract at the next review." by the lead -> reconsideration (agrees to reopen).
- "We could switch to Clearline." -> proposal, NOT reconsideration, unless the group also agrees to reopen the decision.
- "I just think we picked wrong." with no agreement to reopen -> challenge, NOT reconsideration.
- "Right, Clearline then. Priya, tell Brightway." -> resolution (decision changed), and the instruction confirms it."""


def recap_text(prior):
    """prior: list of (meeting_number, link_dict_with_text). Grouped by the system's own decision names, in time order."""
    if not prior:
        return "This is the first meeting of the series."
    by, order = {}, []
    for k, l in prior:
        d = (l.get("decision") or "unnamed decision").strip()[:80]
        if d not in by:
            by[d] = []
            order.append(d)
        by[d].append((k, l))
    lines = ["Earlier meetings in this series (from your own earlier analysis; it may contain mistakes):"]
    for d in order[-12:]:
        lines.append(f"* {d}")
        evs = by[d]
        keep = [e for e in evs if e[1]["role"] in ("proposal", "resolution", "reconsideration", "challenge")] or evs
        for k, l in keep[-6:]:
            opt = f" [option: {l['option'][:80]}]" if l.get("option") else ""
            lines.append(f"  - meeting {k}, {l['role']} by {l.get('speaker')}{opt}: \"{l.get('text', '')[:160]}\"")
    return "\n".join(lines)


def prompt(meeting, recap):
    lines = "\n".join(f"[{u['idx']}] {u['speaker']}: {u['text']}" for u in meeting["utterances"])
    return f"""Below is one meeting transcript from a series of meetings of the same team. Each line is [index] speaker: text.

{ROLE_GUIDE}

{recap}

Label every decision-related event in THIS meeting. Rules:
- Label events for ANY decision that is discussed, not only one. Use the earlier meetings to tell a challenge to an existing decision, a reopening, or a
  reaffirmation from a fresh proposal; reuse the same decision name for a decision that was discussed before.
- An event is 1-3 consecutive utterances by the same speaker; give all their indexes, the most important first.
- Do not label small talk, status updates, or scheduling unless a decision is actually made.
- speaker = the speaker of the first (key) utterance. confidence is between 0 and 1.
- decision = a short name for what is being decided (4-8 words); option = the option this event concerns, or "" if none.

Return JSON: {{"links": [{{"role": "...", "utterance_idxs": [int, ...], "speaker": "Name", "confidence": 0.0, "decision": "...", "option": "..."}}]}}

TRANSCRIPT:
{lines}"""


FAILURES = []


def _extract(window, mid, llm, tag, recap):
    n = len(window["utterances"])
    try:
        out = extract_json(llm.complete(SYSTEM, prompt(window, recap), kind="extract_recap", temperature=0, tag=tag))
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
                links.append(dict(meeting_id=mid, role=role, utterance_idxs=idxs, speaker=l.get("speaker"), confidence=float(l.get("confidence", 0.5)),
                                  decision=str(l.get("decision") or "")[:120], option=str(l.get("option") or "")[:160]))
        except Exception:
            continue
    return links


def run_dir(data, out, llm):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    total = 0
    FAILURES.clear()
    for p in sorted((pathlib.Path(data) / "transcripts").glob("*.json")):
        tr = json.loads(p.read_text(encoding="utf-8"))
        links, prior = [], []
        for k, m in enumerate(tr["meetings"], 1):
            total += 1
            recap = recap_text(prior)
            tag = f"{tr['set_id']}-{m['meeting_id']}-recap"
            ls, _, _w = chunk_support.run(m, m["meeting_id"], tag, lambda w, mid, t: _extract(w, mid, llm, t, recap))
            text = {u["idx"]: u["text"] for u in m["utterances"]}
            for l in ls:
                prior.append((k, dict(l, text=" ".join(text.get(i, "") for i in l["utterance_idxs"]))))
            links += ls
        (out / f"{tr['set_id']}.json").write_text(json.dumps(dict(set_id=tr["set_id"], method="single_pass_recap_roles", prompt_version=PROMPT_VERSION, links=links), indent=1),
                                                  encoding="utf-8")
        print(f"{tr['set_id']}: {len(links)} links")
    return total, len(FAILURES)
