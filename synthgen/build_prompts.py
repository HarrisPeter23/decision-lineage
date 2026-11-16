"""build_prompts.py - generates prompts_out/PROMPT_base.md, batch_01..NN.md (base prompt +
5 set assignments each) and assignments_all.md, straight from arcs.py so tables never drift.
Usage: python build_prompts.py [--n 60] [--seed 1000] [--per-batch 5]"""
import argparse
import pathlib

from arcs import ARCS, SLOT_DESC, ROLE_DEFS, sample_spec, slot_name
from generate import arc_schedule

ARC_NOTES = {
    "simple_reversal": "Meeting 1 settles on A. Meeting 2 brings evidence and a challenge but ends WITHOUT changing anything (the lead postpones). Meeting 3 reopens it and switches to B.",
    "re_reversal": "A in m1. In m2 evidence and a challenge lead to B in the same meeting. In m3 new evidence and a challenge against B appear and the meeting ends UNRESOLVED ('let's revisit next time'). In m4 the lead reopens it and the team goes back to A for new reasons.",
    "partial_override": "A is decided in m1. m2 raises evidence and a challenge, ends unresolved. m3: the team keeps A but adds a specific modification M; the final decision is 'A+M'. Describe M precisely in options['A+M'].",
    "no_reversal": "CONTROL. A is decided in m1. m2: evidence and a challenge that are genuinely serious, ending unresolved. m3: the lead reopens it, the proposer answers the concerns with specific reasons, and the team reaffirms A. Nobody changes the decision and nobody announces 'we are not changing anything'; it simply stays.",
    "deferred": "m1: A is proposed with a reason but NOBODY decides; the meeting ends with the question open. m2: new information arrives, and a competing option B is proposed with a reason; still nobody decides. m3: the lead picks B. No decision may be stated or implied before m3.",
    "external_trigger": "A is decided in m1. In m2 the LEAD brings an outside constraint (budget cut, vendor change, regulation, moved deadline), reopens the question, a supporter gives the reason for B, and the lead decides B in the same meeting. No one is being 'challenged'. m3 has NO tagged events: the team just discusses implementation of B (B is now the standing decision) and unrelated agenda items.",
}


def arc_tables():
    out = []
    for name, arc in ARCS.items():
        vers = {v["version"]: v["option"] for v in arc["versions"]}
        out.append(f"### {name}  ({arc['n_meetings']} meetings)\n{ARC_NOTES[name]}\n")
        out.append("| tag | role | meeting | speaker slot | option concerned |\n|---|---|---|---|---|")
        for b in arc["beats"]:
            out.append(f"| {b['id']} | {b['role']} | m{b['meeting']} | {b['slot']} | {b['option'] or vers.get(b['version'])} |")
        out.append("")
    return "\n".join(out)


BASE = """# TASK: write synthetic corporate meeting transcripts for a research benchmark

You are helping build a benchmark that tests whether AI systems can explain how a team's decision
evolved across several meetings (who proposed what, what reasons and evidence were given, who
challenged it, why the team changed its mind or kept its decision). I will give you ASSIGNMENTS.
For each one you write the content of a short series of meetings. You do NOT decide the structure:
the assignment fixes the arc, the cast, the dates, who speaks which event, and the noise level.
You write the topic, the options, one sentence per event, and the dialogue.

## Setting: corporate meetings only
Every meeting is an INTERNAL BUSINESS MEETING of colleagues in one team of a company (the assignment names the team,
e.g. finance, IT and security, sales operations, product, procurement-style supply chain, HR, marketing). No charities,
hospitals, schools or universities, hobby groups, or families. Decisions have business stakes: budgets and approvals,
vendors and contracts, customers and revenue, headcount, deadlines and quarterly goals, compliance, tooling. Use natural
corporate meeting texture: status updates, action items, "let's take that offline", sign-off from finance or legal,
calendar and planning chatter. Keep it conversational, not a slide-deck voice.

## Output rules (strict)
- ONE set per message. Output exactly one plain-text block (a single ```text code block) and nothing else: no commentary before or after. If you can write files, save it as inbox/<set_id>.txt instead and reply only "saved <set_id>".
- Start the next set only when I say "next" (or, if I told you to do the whole batch, continue with the next assignment in a new message).

## File format (plain text, one utterance per line; no JSON, no markdown)
```text
set_id: <from assignment>
seed: <from assignment>
arc_type: <from assignment>
topic: short noun phrase naming the decision, e.g. the venue for the autumn fundraiser
option A: short description
option B: short description
beat B1: ONE concrete sentence stating what is said or argued at this event
beat B2: ...
== m1
Name: spoken words
Name: spoken words that realize event B1 @B1
== m2
Name: spoken words
```
- Header lines first (set_id, seed, arc_type, topic, option lines, beat lines), then one `== mN` line per meeting, in order, with exactly the number of meetings of the arc.
- One `option` line for every option key the arc uses (A, B, and/or A+M; see the tables). One `beat` line (a gist) for every tag of the arc.
- If the assignment says Distractor YES, also add the lines `distractor topic: ...`, `distractor option: the option chosen` and `beat D1: ...`, `beat D2: ...`, `beat D3: ...` in the header. If NO, add no distractor lines.
- Each utterance is ONE line: `Name: spoken words`. No blank lines inside a meeting, no line breaks inside an utterance. Tags go at the very end of the line after a space: ` @B4`, or ` @B4,B5` for two events on one line.
- Plain text only: no bold, no bullet points, no stage directions, no brackets, no narration.

## Arc tables (fixed; do not change)
Tags mark the KEY utterance(s) that realize an event. The named speaker slot is mapped to a real name
in each assignment. Roles: """ + "; ".join(f"{r} = {d}" for r, d in ROLE_DEFS.items()) + """.
Option keys: A = the first option; B = a competing option; "A+M" = option A plus a modification M.
Slots: """ + "; ".join(f"{s} = {d}" for s, d in SLOT_DESC.items()) + """.

""" + arc_tables() + """
Distractor (only if the assignment says YES), always in meeting 2: D1 proposal and D2 rationale by the
supporter, D3 resolution by the manager. It is a small, unrelated decision in the same team that is
settled in that meeting and never revisited.

## How to tag
- Put tags only on the 1-3 consecutive utterances by the named speaker that realize the event; the
  most important utterance first. Reactions by other people get no tags.
- Every tag must appear, in its assigned meeting, in the order of the table (a later tag never comes
  before an earlier one within a meeting).
- A decision event happens at the tagged utterance, never earlier. Between events the current
  decision simply stays in force; do not state or imply any decision that is not scheduled.

## Writing the dialogue
1. Real spoken language, not a summary: fillers (um, uh, you know, I mean), false starts, self-corrections, trailing off with "-", people cutting each other off (an utterance ends with "-" and the next speaker jumps in), short turns, backchannels ("right", "mm").
2. Follow the assignment's noise settings for each meeting: interruption level, share of unrelated talk (status updates, scheduling, small talk, one tangent if indicated), false starts, pronoun-heavy reference ("that", "it", "the thing from last time" instead of repeating the option's name), and the target length.
3. LENGTH: each meeting must have at least 60 utterances and should be close to the assigned target. Most utterances are short (3-25 words); a few are longer.
4. IMPLICIT resolutions (listed per assignment): the tagged speaker must NOT name the option. Use a bare agreement, or an action that presupposes the decision, and VARY the form: "fine by me, go ahead", "sure, tell finance", "okay, Mateo, lock in the slot", "mm-hm, sounds fine", or simply moving on to the next step. Make sure the thing being agreed to was stated clearly in the preceding turns. Do NOT use "let's go with that" or "let's do that" for these (stock phrases are trivially detectable and make the benchmark too easy). All other resolutions are EXPLICIT: the speaker names the chosen option.
5. Evidence must be concrete and checkable (a measurement, a quote, a budget figure, a deadline), and consistent everywhere it is mentioned. Reasons for a later option must plausibly follow from the evidence and the challenge.
6. Continuity: later meetings refer back naturally ("last week Wei said..."), recap briefly, and the team remembers earlier facts. Nobody speaks as if they know the future.
7. Do not invent other decisions about the topic beyond the arc. Unrelated agenda items are fine but must not touch the topic.
8. Never write the words "beat", "role", "reversal", "supersede", "lineage", or tag IDs (B1, D2...) inside speech. No stage directions, no brackets, no narration; speech only.
9. Everyone in the cast speaks in every meeting, in the voice of their listed style.
10. Gists in the `beat` lines: one specific sentence each, stating the actual content (numbers, names of tools/vendors/venues, constraints), consistent with the dialogue. Fictional names are fine.

## Diversity (matters: the dataset will be judged on variety)
- Use the assigned setting and decision-area hint as a starting point, but pick a specific, non-obvious decision. Avoid the most typical example for that setting. Never use MongoDB vs PostgreSQL.
- Vary: topic wording, option types, numbers, how people open and close meetings, who is blunt or chatty, how arguments are phrased. Do not reuse sentences or stock phrases across sets or across meetings.
- Avoid stock constructions for ALL events ("I think we should...", "Can I make the case for...", "I think this is a problem", "Let me decide: we're..."). People propose, object, give reasons and reopen decisions in many different, often indirect ways ("what if we just...", "I keep coming back to the cost", "hang on, didn't we say..."). Keyword matching must not be enough to find an event.
- Vary pacing: some meetings dense with the topic, others dominated by unrelated items with the topic squeezed in.

## Before you send, silently check
- Exact cast names only; every cast member speaks in every meeting.
- Every tag used exactly where the table says, speaker matches the slot's name, order respected.
- Implicit resolutions name no option; explicit ones do.
- No tag IDs or banned words in speech; every meeting >= 60 utterances.
- The decision state is right at the end of each meeting (e.g. nothing decided early in a deferred set; no change announced in a no-reversal set).
- File format exact: header lines, `== mN` lines, one utterance per line, tags at line ends.

## ASSIGNMENTS
"""


def assignment_block(spec):
    c = {x["slot"]: x for x in spec["cast"]}
    cast = "; ".join(f"{x['name']} [{x['slot']}; style: {x['style']}]" for x in spec["cast"])
    impl = [b["id"] for b in spec["beats"] if b["implicit"]]
    if spec["distractor"]:
        dis = (f"YES - in meeting 2: D1 proposal and D2 rationale by {slot_name(spec, 'supporter')}, "
               f"D3 resolution by {slot_name(spec, 'manager')}")
    else:
        dis = "NO (set \"distractor\": null)"
    noise = []
    for i, n in enumerate(spec["noise"], 1):
        noise.append(f"  - m{i} ({spec['dates'][i-1]}): interruptions={n['interruptions']}, unrelated talk~{n['filler_talk_pct']}%, "
                     f"false starts={n['false_starts']}, pronouns={'heavy' if n['pronoun_heavy'] else 'normal'}, "
                     f"tangent={'yes' if n['digression'] else 'no'}, target~{n['target_utterances']} utterances")
    return (f"### {spec['set_id']}  (seed {spec['seed']})  arc_type: {spec['arc_type']}\n"
            f"- Setting: {spec['domain']}; decision-area hint: {spec['decision_hint']}\n"
            f"- Cast (use exactly these names): {cast}\n"
            f"- Meetings: {spec['n_meetings']}\n"
            f"- Distractor: {dis}\n"
            f"- Implicit resolutions (speaker must NOT name the option): {', '.join(impl) if impl else 'none'}\n"
            f"- Noise per meeting:\n" + "\n".join(noise) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--per-batch", type=int, default=5)
    ap.add_argument("--out", default="prompts_out")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(exist_ok=True)
    sched = arc_schedule(a.n, a.seed)
    specs = [sample_spec(a.seed + i, sched[i]) for i in range(a.n)]
    blocks = [assignment_block(s) for s in specs]
    (out / "PROMPT_base.md").write_text(BASE + "\n(paste assignments below)\n")
    (out / "assignments_all.md").write_text("\n".join(blocks))
    nb = 0
    for i in range(0, a.n, a.per_batch):
        nb += 1
        ids = [s["set_id"] for s in specs[i:i + a.per_batch]]
        body = (BASE + "\n".join(blocks[i:i + a.per_batch]) +
                f"\nStart with {ids[0]} now. Sets in this batch: {', '.join(ids)}. "
                "Write one set per message and wait for me to say \"next\".\n")
        (out / f"batch_{nb:02d}.md").write_text(body)
    print(f"wrote base prompt, {nb} batch files, and assignments for {a.n} sets to {out}/")
    from collections import Counter
    print(Counter(s["arc_type"] for s in specs))


if __name__ == "__main__":
    main()
