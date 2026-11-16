"""ami_gold.py - AMI real-speech subset (Phase 2): agent-drafted gold chains, built into the same transcript + gold format as the synthetic benchmark.

Drafted by the agent (Opus 5.5) from the AMI transcripts and abstractive summaries; verification status 'none' until the LLM panel runs, at best
'llm_consensus' afterwards. Questions come from synthgen/assemble.py's build_questions (unchanged). Speakers are AMI role codes (PM, ME, UI, ID).
Meetings are numbered 1-4 for a-d. Utterance index = zero-based position among the utterance lines of data/ami/series/<series>/<meeting>.txt.
AMI Meeting Corpus, CC BY 4.0; attribution in LICENSES.md.

  python eval/ami_gold.py          # writes data/ami/transcripts/<series>.json, data/ami/gold/<series>.json, data/ami/transcripts_txt/
"""
import json
import pathlib
import random
import shutil
import sys

sys.path.insert(0, "synthgen")
from assemble import build_questions        # noqa: E402

SER = pathlib.Path("data/ami/series")
OUT = pathlib.Path("data/ami")


def L(lid, role, m, spk, idxs, gist, version, option_key, implicit=False, reaffirmation=False):
    return dict(link_id=lid, role=role, meeting=m, meeting_id=f"m{m}", speaker=spk, utterance_idxs=idxs, gist=gist, version=version,
                option_key=option_key, implicit=implicit, reaffirmation=reaffirmation)


DRAFTS = {
    "ES2002": dict(
        arc_type="re_reversal",
        topic="how the remote control is powered",
        options={"A": "regular (non-rechargeable) batteries", "B": "kinetic power with a backup battery"},
        versions=[("A", 2, 3), ("B", 3, 4), ("A", 4, None)],
        chain=[
            L("B1", "proposal", 2, "PM", [342], "The Project Manager raises the power question and asks whether to add a charging unit or simply run on regular batteries.", 1, "A"),
            L("B2", "rationale", 2, "ID", [346], "The Industrial Designer argues that a rechargeable design adds complexity, cost and a docking cradle, and that users are used to buying batteries.", 1, "A"),
            L("B3", "resolution", 2, "PM", [356], "The Project Manager settles on sticking to regular batteries.", 1, "A"),
            L("B4", "proposal", 3, "ID", [190], "The Industrial Designer suggests a battery plus something else, finding the kinetic option the most interesting because people like to fiddle with it and it is a sales gimmick.", 2, "B"),
            L("B5", "reconsideration", 3, "PM", [363], "The Project Manager brings the power question back and says he likes kinetic power with a battery as backup.", 1, "A"),
            L("B6", "challenge", 3, "ME", [365, 372], "The Marketing Expert warns that kinetic power commits the user to moving the remote, and that a device left unused, for example during a holiday, runs down.", 2, "B"),
            L("B7", "rationale", 3, "ME", [369], "The Marketing Expert notes that people who wear kinetic watches all the time find them always powered, with no battery to change.", 2, "B"),
            L("B8", "resolution", 3, "PM", [376], "The Project Manager concludes that the battery would keep the kinetic remote ticking over when it is not moved, adopting kinetic power with a backup battery.", 2, "B", implicit=True),
            L("B9", "reconsideration", 4, "PM", [127, 128], "The Project Manager opens the price sheet to see whether anything in the design has to be rethought.", 2, "B"),
            L("B10", "resolution", 4, "PM", [130], "The Project Manager confirms that the remote has a battery but no kinetic power: just battery.", 3, "A"),
            L("B11", "rationale", 4, "PM", [135], "The Project Manager gives cost constraints as the reason for dropping kinetic power, phrased as a question to the team.", 3, "A"),
        ],
        changes=[dict(from_version=1, to_version=2, at_meeting=3, triggered_by=["B5"], new_rationale=["B4", "B7"]),
                 dict(from_version=2, to_version=3, at_meeting=4, triggered_by=["B9"], new_rationale=["B11"])],
        notes="Abstractive summaries: b 'regular batteries', c 'kinetic battery', d 'not contain a kinetic battery'. The reason in meeting d is stated only "
              "briefly (B11, as a question); the detailed cost overrun in meeting d (16.8 against a 12.5 Euro target) comes later and concerns the whole design.",
    ),
    "TS3012": dict(
        arc_type="simple_reversal",
        topic="whether the remote controls only the TV or is a universal remote",
        options={"A": "a remote for the TV only", "B": "a universal remote for several devices"},
        versions=[("A", 1, 2), ("B", 2, None)],
        chain=[
            L("B1", "proposal", 1, "PM", [129], "The Project Manager says the project he was given is for a TV-only remote.", 1, "A"),
            L("B2", "rationale", 1, "PM", [129], "The reason given is the project brief itself: it asks for a TV remote control.", 1, "A"),
            L("B3", "resolution", 1, "UI", [130], "The User Interface Designer accepts that it is just a TV remote control.", 1, "A"),
            L("B4", "evidence", 2, "ID", [124], "The Industrial Designer explains that a universal remote needs the processor to send different codes per device, which makes it much more complex.", 1, "A"),
            L("B5", "reconsideration", 2, "ID", [192], "The Industrial Designer asks the team to decide now whether the remote is universal, since it determines all of his design work.", 1, "A"),
            L("B6", "proposal", 2, "PM", [193], "The Project Manager says he thinks it is universal.", 2, "B"),
            L("B7", "rationale", 2, "PM", [194], "The Project Manager argues for universal because the company makes separate remote controls to sell to many different people.", 2, "B"),
            L("B8", "resolution", 2, "PM", [202], "The Project Manager confirms that universal is good.", 2, "B"),
        ],
        changes=[dict(from_version=1, to_version=2, at_meeting=2, triggered_by=["B5", "B4"], new_rationale=["B7"])],
        notes="Summary of meeting b lists both 'The remote will only be used for TV' and 'The remote is going to be a universal one'; the transcript supports "
              "the change to universal at b[192-202]. B1 and B2 share one utterance because the brief is stated and justified in a single line.",
    ),
    "TS3004": dict(
        arc_type="simple_reversal",
        topic="whether the remote has speech recognition",
        options={"A": "no speech recognition", "B": "speech recognition included, with the advanced chip it needs"},
        versions=[("A", 2, 3), ("B", 3, None)],
        chain=[
            L("B1", "proposal", 2, "ME", [94], "The Marketing Expert proposes skipping speech recognition straight away because it is not reachable for twenty-five Euros.", 1, "A"),
            L("B2", "rationale", 2, "ME", [487], "The Marketing Expert adds that the many languages make speech recognition difficult.", 1, "A"),
            L("B3", "rationale", 2, "UI", [489], "The User Interface Designer says speech recognition is not useful enough to justify the design effort.", 1, "A"),
            L("B4", "resolution", 2, "ME", [506], "The Marketing Expert concludes: no speech recognition.", 1, "A"),
            L("B5", "reconsideration", 3, "ME", [51], "The Marketing Expert says the earlier decision against an LCD and speech recognition is now a point of discussion.", 1, "A"),
            L("B6", "rationale", 3, "ME", [91], "The Marketing Expert argues that the main requirement is to be technologically innovative, so the remote needs some kind of gadget, perhaps speech.", 2, "B"),
            L("B7", "evidence", 3, "UI", [102], "The User Interface Designer reports that the technology department has researched speech and recommends using it.", 1, "A"),
            L("B8", "resolution", 3, "PM", [683], "The Project Manager puts speech recognition into the design as well (phrased as a question, accepted by the team).", 2, "B"),
            L("B9", "resolution", 4, "PM", [61], "In the last meeting the Project Manager keeps speech recognition, with one button to turn it on or off.", 2, "B", reaffirmation=True),
        ],
        changes=[dict(from_version=1, to_version=2, at_meeting=3, triggered_by=["B5", "B7"], new_rationale=["B6"])],
        notes="Summaries: b 'will not feature speech recognition', c 'eventually decided to incorporate speech recognition and an advanced chip', d 'will feature "
              "speech recognition'. The meeting-c decision at c[683] is phrased as a question; the summary confirms it. Earlier in c (c[667]) the Project "
              "Manager first suggests skipping it again; that exchange is part of the same discussion and is not tagged.",
    ),
    "ES2003": dict(
        arc_type="simple_reversal",
        topic="the material of the remote's case",
        options={"A": "a flexible spongy rubber case", "B": "a solid plastic case with a single-curved design"},
        versions=[("A", 3, 4), ("B", 4, None)],
        chain=[
            L("B1", "proposal", 3, "UI", [125], "The User Interface Designer proposes going straight for rubber.", 1, "A"),
            L("B2", "rationale", 3, "ME", [191], "The Marketing Expert argues that a spongy case can be dropped any number of times without breaking.", 1, "A"),
            L("B3", "resolution", 3, "PM", [211], "The Project Manager notes the team has pretty much decided on some kind of flexible rubber, possibly with an inner frame.", 1, "A"),
            L("B4", "evidence", 4, "PM", [89], "The Project Manager reports the design is four Euros over budget, about half of it from the LCD and the chip it needs.", 1, "A"),
            L("B5", "proposal", 4, "PM", [90], "The Project Manager proposes changing to a solid plastic unit with a single-curved design, which brings the cost back within budget with 0.2 Euro to spare.", 2, "B"),
            L("B6", "rationale", 4, "PM", [107], "The Project Manager explains that plastic adds no cost while rubber costs two Euros per unit.", 2, "B"),
            L("B7", "resolution", 4, "PM", [164], "The Project Manager asks the team to go ahead with a plastic solid case so the LCD can be kept (phrased as a question, accepted).", 2, "B"),
        ],
        changes=[dict(from_version=1, to_version=2, at_meeting=4, triggered_by=["B4"], new_rationale=["B6"])],
        notes="Summaries: c 'a case made of rubber', d 'made of plastic instead of rubber'. The meeting-d decision at d[164] is phrased as a question. The "
              "team also kept the LCD in the same exchange; that is a separate decision and not tagged. The prototype shown at d[19] already used a plastic casing.",
    ),
    "ES2013": dict(
        arc_type="no_reversal",
        topic="the remote's energy source",
        options={"A": "kinetic energy", "B": "a standard battery"},
        versions=[("A", 3, None)],
        chain=[
            L("B1", "proposal", 3, "ID", [106], "The Industrial Designer proposes the kinetic energy source, where the user powers the remote by moving it.", 1, "A"),
            L("B2", "rationale", 3, "PM", [281], "The Project Manager summarises that kinetic power only needs the remote to be moved, unlike a battery that must be recharged or replaced.", 1, "A"),
            L("B3", "evidence", 3, "ID", [284], "The Industrial Designer says he has no costing information; the two workable front-runners are a standard battery or kinetic.", 1, "A"),
            L("B4", "rationale", 3, "ME", [288], "The Marketing Expert says kinetic watches are very handy because you do not even notice it.", 1, "A"),
            L("B5", "resolution", 3, "PM", [297], "The Project Manager concludes that the consensus is to use kinetic if at all possible.", 1, "A"),
            L("B6", "reconsideration", 4, "UI", [206], "The User Interface Designer raises the energy question again in the last meeting, asking whether it is kinetic.", 1, "A"),
            L("B7", "rationale", 4, "ME", [212], "The Marketing Expert says kinetic can be marketed as cost-saving and environmentally friendly.", 1, "A", reaffirmation=True),
            L("B8", "resolution", 4, "UI", [262], "Filling in the component sheet, the User Interface Designer confirms just kinetic.", 1, "A", reaffirmation=True),
        ],
        changes=[],
        notes="Control series: the energy decision is made in c and kept in d (summaries: c and d both 'will use a kinetic battery'). There is no serious "
              "challenge; the only doubt is missing cost information (B3).",
    ),
}


def load_meeting(series, obs):
    L_ = (SER / series / f"{obs}.txt").read_text(encoding="utf-8").split("\n")
    head = dict(l.split(": ", 1) for l in L_[:L_.index("")] if ": " in l)
    utts = [l for l in L_[L_.index("") + 1:] if l.strip()]
    return head, [dict(idx=i, speaker=u.split(": ", 1)[0], text=u.split(": ", 1)[1] if ": " in u else u) for i, u in enumerate(utts)]


def build(series, d):
    obs = [f"{series}{c}" for c in "abcd"]
    meetings = []
    for k, o in enumerate(obs, 1):
        head, utts = load_meeting(series, o)
        meetings.append(dict(meeting_id=f"m{k}", ami_id=o, date=head.get("Date", ""), utterances=utts))
    tr = dict(set_id=f"ami_{series}", cast=["PM", "ME", "UI", "ID"], meetings=meetings, source="AMI Meeting Corpus (CC BY 4.0)")
    for l in d["chain"]:
        m = meetings[l["meeting"] - 1]["utterances"]
        for i in l["utterance_idxs"]:
            assert 0 <= i < len(m), (series, l["link_id"], i)
            assert m[i]["speaker"] == l["speaker"], (series, l["link_id"], i, m[i]["speaker"], l["speaker"])
    versions = [dict(version=n, option=k, option_text=d["options"][k], valid_from=a, valid_to=b) for n, (k, a, b) in enumerate(d["versions"], 1)]
    chain = []
    for l in d["chain"]:
        c = dict(l)
        c["option"] = d["options"][l["option_key"]]
        chain.append(c)
    gold = dict(set_id=f"ami_{series}", meta=dict(arc_type=d["arc_type"], n_meetings=4, source="ami", series=series, ami_meetings=obs,
                                                  drafted_by="agent (claude-opus-5-5)", verification="none", notes=d["notes"]),
                topic=d["topic"], options=d["options"], cast=tr["cast"], versions=versions, chain=chain, changes=d["changes"], distractor=None)
    gold["questions"] = build_questions(gold, random.Random(sum(map(ord, series))))
    if d["arc_type"] == "no_reversal":
        # the toolkit's no-change answer says 'decided in meeting 1'; in AMI the decision comes later. Corrected here, not in the toolkit (logged).
        first = versions[0]["valid_from"]
        for q in gold["questions"]:
            if q["type"] == "change_over_time":
                q["answer_text"] = q["answer_text"].replace("was decided in meeting 1", f"was decided in meeting {first}")
    return tr, gold


def main():
    for sub in ("transcripts", "gold", "transcripts_txt"):
        shutil.rmtree(OUT / sub, ignore_errors=True)
        (OUT / sub).mkdir(parents=True)
    for series, d in DRAFTS.items():
        tr, gold = build(series, d)
        (OUT / "transcripts" / f"ami_{series}.json").write_text(json.dumps(tr, indent=1), encoding="utf-8")
        (OUT / "gold" / f"ami_{series}.json").write_text(json.dumps(gold, indent=1), encoding="utf-8")
        tdir = OUT / "transcripts_txt" / f"ami_{series}"
        tdir.mkdir()
        for m in tr["meetings"]:
            (tdir / f"{m['meeting_id']}.txt").write_text("\n".join([f"Meeting: {m['meeting_id']}", f"Date: {m['date']}", "Participants: PM, ME, UI, ID", ""] +
                                                                  [f"{u['speaker']}: {u['text']}" for u in m["utterances"]]) + "\n", encoding="utf-8", newline="\n")
        print(series, len(gold["chain"]), "links,", len(gold["questions"]), "questions,", [q["type"] for q in gold["questions"]])


if __name__ == "__main__":
    main()
