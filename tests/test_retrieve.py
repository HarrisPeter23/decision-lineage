"""Router and retrieval tests on a tiny invented corpus (toy embedder, no model download)."""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from argdecisionlineage.linking import Embedder          # noqa: E402
from argdecisionlineage.retrieve import LineageSystem, route   # noqa: E402


def test_router_covers_every_template():
    T = "the courier for the north depot"
    cases = {f"What did the team finally decide about {T}?": "final", f"What decisions were made about {T}?": "decisions_about",
             f"What was the decision about {T} as of the end of meeting 2?": "as_of", f"How did the decision about {T} change over time?": "change_over_time",
             f"Why did the team change its decision about {T}?": "why_changed", f"Why was the original decision about {T} changed?": "why_changed",
             f"Who proposed the original decision about {T}?": "who_proposed", f"What evidence caused the team to reconsider its decision about {T}?": "evidence_to_reconsider",
             f"Which meetings contributed to the final decision about {T}?": "meetings_contributed",
             f"Show the complete lineage of the decision about {T} from proposal to final outcome.": "full_lineage", f"What was decided about {T}?": "final"}
    for q, intent in cases.items():
        i, topic, k = route(q)
        assert i == intent and topic == T, q
    assert route(f"What was the decision about {T} as of the end of meeting 2?")[2] == 2
    assert route(f"Why did the decision about {T} change at meeting 4?") == ("why_changed", T, 4)                     # RF1
    assert route("Who proposed a daily cross-dock run through the north depot?") == ("who_proposed_option", "a daily cross-dock run through the north depot", None)


def toy(texts):
    vocab = ["courier", "depot", "laptop", "harbour", "copper"]
    return [np.array([t.lower().count(w) + 0.01 for w in vocab], dtype=float) for t in texts]


SWITCH = "okay, we switch to Copper then"


def corpus():
    m = lambda mid, lines: dict(meeting_id=mid, date="2025-01-0" + mid[-1], utterances=[dict(idx=i, speaker=s, text=t) for i, (s, t) in enumerate(lines)])
    return dict(meetings=[m("x1", [("Ana", "for the depot courier I propose Harbour courier weekly"), ("Bo", "fine, Harbour courier for the depot it is"), ("Di", "right, next item"), ("Di", "okay"),
                                   ("Cy", "laptop refresh: I propose new laptops in May"), ("Bo", "agreed, laptops in May")]),
                          m("x2", [("Cy", "the Harbour courier missed nine depot runs"), ("Ana", "we should reopen the depot courier question"),
                                   ("Ana", "Copper courier is cheaper overall for the depot"), ("Bo", SWITCH)])])


def links():
    L = lambda mid, i, role, sp: dict(meeting_id=mid, role=role, utterance_idxs=[i], speaker=sp, confidence=0.95)
    return [L("x1", 0, "proposal", "Ana"), L("x1", 1, "resolution", "Bo"), L("x1", 4, "proposal", "Cy"), L("x1", 5, "resolution", "Bo"),
            L("x2", 0, "evidence", "Cy"), L("x2", 1, "reconsideration", "Ana"), L("x2", 2, "rationale", "Ana"), L("x2", 3, "resolution", "Bo")]


def test_retrieval_anchors_and_follows_supersession():
    s = LineageSystem(embedder=Embedder(toy), fallback=False).index(corpus(), links())
    r = s.retrieve("Why was the original decision about the depot courier changed?")
    got = {(it["meeting_id"], it["idxs"][0]) for it in r["items"]}
    assert r["changed"] and {("x2", 0), ("x2", 1), ("x2", 3)} <= got and ("x1", 4) not in got
    r = s.retrieve("What was the decision about the depot courier as of the end of meeting 1?")
    assert r["as_of"]["corpus_meeting"] == 1 and "Harbour" in r["versions"][0]["option"]
    r = s.retrieve("Who proposed the original decision about the depot courier?")
    assert [it["speaker"] for it in r["items"]] == ["Ana"]


import pytest  # noqa: E402


@pytest.mark.xfail(strict=True, reason="KNOWN LIMITATION of the frozen v4 rules (phase5.md): with containment similarity at same_at 0.4, a switch that repeats "
                                       "the topic words ('the depot courier') looks like the same option, so the change is read as a reaffirmation")
def test_known_limitation_switch_sharing_topic_words():
    global SWITCH
    old, SWITCH = SWITCH, "okay, we switch the depot courier to Copper courier"
    try:
        s = LineageSystem(embedder=Embedder(toy), fallback=False).index(corpus(), links())
        assert s.retrieve("Why was the original decision about the depot courier changed?")["changed"]
    finally:
        SWITCH = old
