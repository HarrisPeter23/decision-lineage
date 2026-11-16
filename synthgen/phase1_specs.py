"""phase1_specs.py - build a per-meeting writer spec that hides the future (anti-foreshadowing).

Plan file: data/synth_work/plans/<set>.txt, in the header format of text_to_tagged.py (written with knowledge of the arc).
Each spec shows a writer ONLY: this meeting's events and ending, options already on the table, and earlier transcripts.
It never shows the arc name, later events, later options, or the number of meetings left.

  python phase1_specs.py set_01013 2            # writes data/synth_work/specs/set_01013/m2.md
  python phase1_specs.py assemble set_01013     # joins plan + meetings into inbox/set_01013.txt
"""
import pathlib
import random
import re
import sys

from arcs import ROLE_DEFS, sample_spec, slot_name
from text_to_tagged import parse

W = pathlib.Path("../data/synth_work")
PV = "v2"
OTHER_NAMES = """Abena Aiko Alejandra Anders Anika Bao Beatriz Bilal Caio Camille Chidi Clara Daan Dalia Davor Delphine Emeka Esra Fabian Farah
Gabor Giulia Goran Hamid Hedda Ibrahim Ines Irina Jamal Joao Kaveh Keiko Klara Laszlo Leila Linh Lucia Magnus Malik Marisol Marta Milan Nadia Nikos
Oksana Olivier Paolo Petra Rafael Rania Rosa Rui Salma Samir Sanne Sergei Sione Stefan Sunita Tadeusz Thandi Tomasz Umar Valeria Vikram Wanjiru
Xavier Yara Yusuf Zofia""".split()

ENDINGS = {
    "simple_reversal": {1: "The team settles on A in this meeting.",
                        2: "New information and an objection come up, but nothing changes: the lead postpones. A stays in force."},
    "re_reversal": {1: "The team settles on A in this meeting.",
                    2: "New information and an objection lead the team to switch to B in this same meeting.",
                    3: "New information and an objection against B come up, and the meeting ends unresolved: revisit next time. B stays in force."},
    "partial_override": {1: "The team settles on A in this meeting.",
                         2: "New information and an objection come up, and the meeting ends unresolved. A stays in force."},
    "no_reversal": {1: "The team settles on A in this meeting.",
                    2: "New information and a serious objection come up, and the meeting ends unresolved. A stays in force.",
                    3: "The lead reopens it, the proposer answers the concerns with specific reasons, and A stands. Nobody announces 'we are not changing anything'; it simply stays."},
    "deferred": {1: "A is proposed with a reason, but NOBODY decides. The question stays open.",
                 2: "New information arrives and a competing option B is proposed with a reason. Still nobody decides."},
    "external_trigger": {1: "The team settles on A in this meeting.",
                         2: "The lead brings an outside constraint and reopens the question; a colleague gives the reason for B; the lead decides B in this same meeting. Nobody is being challenged.",
                         3: "Nothing is decided about the topic. The team discusses implementing the standing decision, plus unrelated agenda items."},
}
FINAL = "The lead reopens the question and the team reaches a decision in this meeting. See the events below for the outcome."


def option_for(spec, b):
    v = b.get("version")
    if b.get("option"):
        return b["option"]
    return next((x["option"] for x in spec["versions"] if x["version"] == v), None)


def strip_tags(text):
    return "\n".join(re.sub(r"\s@[A-Z]\d+(,[A-Z]\d+)*\s*$", "", l) for l in text.splitlines())


def build(sid, m):
    seed = int(sid.split("_")[1])
    plan = parse(W / "plans" / f"{sid}.txt")
    spec = sample_spec(seed, plan["arc_type"], sid)
    n = spec["noise"][m - 1]
    all_beats = spec["beats"] + (spec["distractor"]["beats"] if spec["distractor"] else [])
    here = [b for b in all_beats if b["meeting"] == m]
    gist = dict(plan["beats"], **((plan["distractor"] or {}).get("beats") or {}))
    seen = set()
    for b in spec["beats"]:
        if b["meeting"] <= m and option_for(spec, b):
            seen.add(option_for(spec, b))
    out = [f"# Meeting spec: {sid}, meeting {m}", "", f"Team: {spec['domain']}", f"Date: {spec['dates'][m - 1]}",
           f"Topic under discussion: {plan['topic']}", "", "Options on the table so far (the only ones anyone knows about):"]
    out += [f"- {k}: {plan['options'][k]}" for k in sorted(seen) if k in plan["options"]]
    out += ["", "Cast (exact names; everyone speaks):"]
    out += [f"- {c['name']}: {'manager, leads the meeting' if c['slot'] == 'manager' else 'team member'}; style: {c['style']}" for c in spec["cast"]]
    ending = ENDINGS[plan["arc_type"]].get(m, FINAL)
    cast = {c["name"] for c in spec["cast"]}
    others = random.Random(seed).sample([x for x in OTHER_NAMES if x not in cast], 6)
    out += ["", "Other people (colleagues, suppliers, clients) if anyone outside the cast is mentioned: " + ", ".join(others)]
    out += ["", f"How this meeting goes: {ending}", "", "Events that must happen, in this order. Tag the key line with the tag shown:"]
    for b in here:
        sp = slot_name(spec, b["slot"])
        impl = " IMPLICIT: the speaker must NOT name the option." if b.get("implicit") else ""
        out.append(f"- @{b['id']} ({b['role']}: {ROLE_DEFS[b['role']]}) spoken by {sp}. Content: {gist[b['id']]}{impl}")
    if not here:
        out.append("- None. Write no tags in this meeting.")
    if spec["distractor"] and spec["distractor"]["beats"][0]["meeting"] == m:
        out += ["", f"Side decision also settled here, unrelated to the topic: {plan['distractor']['topic']} (outcome: {plan['distractor']['option']})."]
    out += ["", "Noise for this meeting:", f"- interruptions: {n['interruptions']}", f"- unrelated talk: about {n['filler_talk_pct']}%",
            f"- false starts: {n['false_starts']}", f"- pronoun-heavy reference: {'yes' if n['pronoun_heavy'] else 'normal'}",
            f"- one tangent: {'yes' if n['digression'] else 'no'}", f"- target length: about {n['target_utterances']} utterances (minimum 60)"]
    if m > 1:
        out += ["", "## Transcripts of the earlier meetings"]
        for k in range(1, m):
            t = (W / "meetings" / sid / f"m{k}.txt").read_text(encoding="utf-8")
            out += ["", f"### Meeting {k} ({spec['dates'][k - 1]})", strip_tags(t).strip()]
    p = W / "specs" / sid / f"m{m}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(p)


def assemble_set(sid):
    head = (W / "plans" / f"{sid}.txt").read_text(encoding="utf-8").rstrip()
    parts = [head]
    for i, p in enumerate(sorted((W / "meetings" / sid).glob("m*.txt")), 1):
        parts += [f"== m{i}", p.read_text(encoding="utf-8").strip()]
    (W / "inbox").mkdir(exist_ok=True)
    (W / "inbox" / f"{sid}.txt").write_text("\n".join(parts) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1] == "assemble":
        assemble_set(sys.argv[2])
    else:
        build(sys.argv[1], int(sys.argv[2]))
