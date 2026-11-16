"""prompts.py - all prompt templates in one place so they can be versioned and
reported in the paper. Each user prompt embeds a SPEC_JSON block (also used by
the offline mock)."""
import json
from arcs import ROLE_DEFS, SLOT_DESC, option_keys, option_key, slot_name

PLANNER_SYSTEM = (
    "You design synthetic corporate-meeting scenarios (internal meetings of teams inside a company) for a research benchmark. "
    "Output ONLY valid JSON, no commentary, no code fences."
)

MEETING_SYSTEM = (
    "You write realistic, messy transcripts of internal corporate meetings (colleagues in a company) as spoken conversation. "
    "Output ONLY valid JSON, no commentary, no code fences."
)


def _block(payload):
    return "SPEC_JSON_BEGIN\n" + json.dumps(payload) + "\nSPEC_JSON_END"


def planner_prompt(spec):
    keys = option_keys(spec)
    beats = [dict(id=b["id"], role=b["role"], meeting=b["meeting"], option=option_key(spec, b),
                  version=b["version"]) for b in spec["beats"]]
    payload = dict(domain=spec["domain"], option_keys=keys, beats=beats,
                   distractor=spec["distractor"])
    text = f"""Scenario setting: an internal meeting series of a {spec['domain']} inside a company (corporate setting: budgets, vendors, customers, deadlines, approvals). Decision area (a hint, not a requirement): {spec['decision_hint']}.
Arc: {spec['arc_description']}
Option keys: {', '.join(keys)}   (A = the first option; B = a competing option; "A+M" = A plus a specific modification M)

Fill in concrete content for this arc. Return JSON:
{{
  "topic": "short noun phrase naming the decision (e.g. 'the datastore for the order-tracking service')",
  "options": {{ {', '.join(f'"{k}": "short description"' for k in keys)} }},
  "beats": {{ "<beat id>": "ONE concrete sentence stating what is said or argued at this beat" }},
  "distractor": null or {{"topic": "...", "option": "...", "beats": {{"<id>": "..."}}}}
}}

Beats to fill (role definitions below):
{json.dumps(beats, indent=1)}

Role definitions:
{json.dumps({r: ROLE_DEFS[r] for r in sorted({b['role'] for b in spec['beats']})}, indent=1)}

Rules:
- Be specific: real-sounding numbers, constraints, named tools or vendors (fictional names are fine). Avoid the single most obvious example for this domain.
- Evidence must be concrete and checkable (a measurement, a quote, a budget figure), never vague.
- Reasons for the later option must plausibly follow from the evidence and challenge.
- For "reconsideration" beats the gist is the lead agreeing to reopen the question and why.
- For "A+M", state exactly what the modification M is, in the option description.
- If a distractor is required, it must be an unrelated, smaller decision in the same team (settled in one meeting, never revisited).
- Gists must not contain meta words like "reversal", "beat", or "role".

{_block(payload)}"""
    return text


def _recap(spec, plan, m):
    if m == 1:
        return "This is the first meeting of the series. The team has no prior history on this topic."
    lines = []
    for b in spec["beats"]:
        if b["meeting"] < m:
            lines.append(f"- (meeting {b['meeting']}) {slot_name(spec, b['slot'])}: {plan['beats'][b['id']]}")
    if spec.get("distractor"):
        for b in spec["distractor"]["beats"]:
            if b["meeting"] < m:
                lines.append(f"- (meeting {b['meeting']}) {slot_name(spec, b['slot'])}: {plan['distractor']['beats'][b['id']]}")
    return "What the team remembers from earlier meetings:\n" + "\n".join(lines)


def meeting_prompt(spec, plan, m):
    noise = spec["noise"][m - 1]
    beats = [b for b in spec["beats"] if b["meeting"] == m]
    dbeats = spec["distractor"]["beats"] if spec.get("distractor") else []
    dbeats = [b for b in dbeats if b["meeting"] == m]
    items, payload_beats = [], []
    for b in beats + dbeats:
        is_d = b["id"].startswith("D")
        gist = plan["distractor"]["beats"][b["id"]] if is_d else plan["beats"][b["id"]]
        key = option_key(spec, b)
        opt_text = plan["distractor"]["option"] if is_d else (plan["options"].get(key, "") if key else "")
        who = slot_name(spec, b["slot"])
        note = ""
        if b["role"] == "resolution" and b["implicit"]:
            note = (" IMPLICIT: the speaker must NOT name the option. Use a bare agreement that refers back to "
                    "something said just before (e.g. 'yeah, let's go with that', 'fine, do it').")
        elif b["role"] == "resolution":
            note = " EXPLICIT: the speaker states the chosen option clearly."
        items.append(f"- [{b['id']}] ({b['role']}) spoken by {who}: {gist}{note}")
        payload_beats.append(dict(id=b["id"], role=b["role"], speaker=who, gist=gist,
                                  implicit=b["implicit"], option_text=opt_text))
    if not items:
        items = ["- (no required events; the team simply continues, discussing implementation of the current "
                 "position and unrelated agenda items)"]
    cast = "\n".join(f"- {c['name']} - {SLOT_DESC[c['slot']]}; style: {c['style']}" for c in spec["cast"])
    standing = ""
    if m > 1:
        standing = "\nUnless this meeting changes it, the team's standing position is whatever the last decision was."
    payload = dict(m=m, names=[c["name"] for c in spec["cast"]], beats=payload_beats,
                   target=noise["target_utterances"])
    return f"""Write the transcript of meeting {m} of {spec['n_meetings']} for the same {spec['domain']} (date {spec['dates'][m-1]}).

PARTICIPANTS (use exactly these names as speakers):
{cast}

{_recap(spec, plan, m)}{standing}

REQUIRED EVENTS - realize each in natural speech, in this relative order (other talk may appear between them):
{chr(10).join(items)}

STYLE AND NOISE (this meeting):
- Real spoken language: fillers (um, uh, like, you know), false starts, self-corrections, trailing off with "-", people cutting each other off ("-" at the end of an utterance, next speaker jumps in).
- Interruptions: {noise['interruptions']}. False starts: {noise['false_starts']}.
- About {noise['filler_talk_pct']}% of utterances are unrelated agenda items, small talk, scheduling, or status updates{' including one tangent that wanders off-topic' if noise['digression'] else ''}.
- {'Use pronouns and vague references ("that", "it", "the thing we talked about") instead of repeating names of options wherever natural.' if noise['pronoun_heavy'] else 'Refer to things by name most of the time.'}
- Target length: about {noise['target_utterances']} utterances (short turns are fine).
- Other participants react naturally (questions, backchannels, partial agreement). Nobody should sound like they are reading a summary.

HARD RULES:
1. Each required event is spoken by the named person. An event may take 1-3 consecutive utterances by that person; list all their indexes, key utterance first.
2. Do not label events in the text. Never use the words "beat", "role", "reversal", "supersede", "lineage".
3. Keep numbers and facts consistent with the event text. Do not invent other decisions on this topic.
4. Indexes are 0-based positions in your "utterances" list.

Return JSON:
{{"utterances": [{{"speaker": "Name", "text": "..."}}, ...],
  "realized": {{"<event id>": [utterance indexes]}} }}

{_block(payload)}"""


PARAPHRASE_SYSTEM = "You rewrite questions. Output ONLY a JSON list of strings, same length and order as the input."


def paraphrase_prompt(questions):
    return ("Rewrite each question as a natural question a colleague might ask, varying wording and structure. "
            "Keep the exact meaning and every name, topic and meeting number; add no new information. "
            "Do not hint at the answer.\n\n" + _block(dict(questions=questions)))


JUDGE_SYSTEM = "You are a strict annotation checker. Output ONLY valid JSON."


def judge_prompt(role, gist, speaker, context_lines, utterance_lines):
    return f"""Decide whether the TARGET utterances realize the intended event.

Event role: {role} - {ROLE_DEFS[role]}
Intended content: {gist}
Expected speaker: {speaker}

CONTEXT (preceding lines):
{context_lines}

TARGET utterances:
{utterance_lines}

Answer JSON: {{"verdict": "yes" | "partial" | "no", "reason": "one sentence"}}
"yes" = right speaker, right role, content matches. "partial" = content or role only partly matches. "no" otherwise.
{_block(dict(kind='judge'))}"""


# ------------------------------------------------------------------ extraction baseline
EXTRACT_SYSTEM = (
    "You analyze workplace meeting transcripts and label how decisions are discussed. "
    "Output ONLY valid JSON, no commentary, no code fences."
)


def extract_prompt(meeting):
    lines = "\n".join(f"[{u['idx']}] {u['speaker']}: {u['text']}" for u in meeting["utterances"])
    roles = "\n".join(f"- {r}: {d}" for r, d in ROLE_DEFS.items())
    return f"""Below is one meeting transcript. Each line is [index] speaker: text.

Label every decision-related event with one of these roles:
{roles}

Rules:
- A decision can be implicit: a bare agreement such as "yeah, let's do that" that points back to a proposal is a resolution.
- Label events for ANY decision that is discussed, not only the main one.
- An event is 1-3 consecutive utterances by the same speaker; give all their indexes, the most important first.
- Use only the roles above. Do not label small talk, status updates, or scheduling unless a decision is actually made.
- speaker = the speaker of the first (key) utterance. confidence is between 0 and 1.

Return JSON: {{"links": [{{"role": "...", "utterance_idxs": [int, ...], "speaker": "Name", "confidence": 0.0}}]}}

TRANSCRIPT:
{lines}"""


# ------------------------------------------------------------------ multi-pass extraction
MP_SYSTEM = (
    "You analyze workplace meeting transcripts and label how decisions are discussed. "
    "Output ONLY valid JSON, no commentary, no code fences."
)


def _numbered(meeting):
    return "\n".join(f"[{u['idx']}] {u['speaker']}: {u['text']}" for u in meeting["utterances"])


def mp_flag_prompt(meeting):
    return f"""Below is one meeting transcript. Each line is [index] speaker: text.

List the index of every utterance that does one of these:
- PROPOSES an option or course of action for a decision,
- DECIDES or agrees to a decision (including implicit agreement, and actions or instructions that presuppose a decision was made),
- REOPENS or says a decision needs another look.
Do NOT flag utterances that only give reasons, data, or objections, and ignore small talk and scheduling unless a decision is made.

Return JSON: {{"flagged": [int, ...]}}

TRANSCRIPT:
{_numbered(meeting)}"""


def mp_resolve_prompt(meeting, flagged, context=6):
    by_idx = {u["idx"]: u for u in meeting["utterances"]}
    blocks = []
    for i in flagged:
        lo = max(0, i - context)
        ctx = "\n".join(f"[{u['idx']}] {u['speaker']}: {u['text']}" for u in meeting["utterances"][lo:i])
        u = by_idx[i]
        blocks.append(f"--- item\nPRECEDING LINES:\n{ctx or '(start of meeting)'}\nFLAGGED [{i}] {u['speaker']}: {u['text']}")
    return f"""For each flagged utterance below, use the preceding lines to rewrite it as a self-contained statement:
replace pronouns and vague references ("that", "it", "the thing") with what they refer to, and spell out implicit agreement.
Also say what decision or option it concerns, and classify it as proposal, resolution, reconsideration, or other.

Return JSON: {{"resolved": [{{"idx": int, "resolved_text": "...", "refers_to": "...", "speech_act": "proposal|resolution|reconsideration|other"}}]}}

{chr(10).join(blocks)}"""


def mp_type_prompt(meeting, hints=""):
    roles = "\n".join(f"- {r}: {d}" for r, d in ROLE_DEFS.items())
    hint_block = (f"\nHINTS from an earlier analysis (may contain mistakes; use your own judgement):\n{hints}\n"
                  if hints else "")
    return f"""Below is one meeting transcript. Each line is [index] speaker: text.

Label every decision-related event with one of these roles:
{roles}

Rules:
- A decision can be implicit: a bare agreement, or an instruction that presupposes the decision, is a resolution.
- Label events for ANY decision that is discussed, not only the main one.
- An event is 1-3 consecutive utterances by the same speaker; give all their indexes, the most important first.
- Do not label small talk, status updates, or scheduling unless a decision is actually made.
- speaker = the speaker of the first (key) utterance. quote = up to 12 words copied EXACTLY from that key utterance.
{hint_block}
Return JSON: {{"links": [{{"role": "...", "utterance_idxs": [int, ...], "speaker": "Name", "quote": "...", "confidence": 0.0}}]}}

TRANSCRIPT:
{_numbered(meeting)}"""
