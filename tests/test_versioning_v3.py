"""Unit tests for rules v3 (definition alignment with assemble.py) and v4 (tightening for system links) in argdecisionlineage/graph.py.
Texts are invented (no benchmark text)."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from argdecisionlineage import schema as S                       # noqa: E402
from argdecisionlineage.graph import DecisionGraph, Link, Params  # noqa: E402

A = "the Harbourline courier on a fixed weekly collection"
B = "the Copperfield courier on daily on-demand pickups"
_n = [0]


def L(meeting, role, text, idx=0, conf=1.0):
    _n[0] += 1
    return Link(link_id=f"T{_n[0]:03d}", meeting=meeting, role=role, speaker="Ola", idxs=[idx + _n[0]], text=text, meeting_id=f"m{meeting}", confidence=conf, decision="D1")


def build(links, rules="v3", **kw):
    return DecisionGraph(Params(rules=rules, same_at=0.4, modified_at=0.2, **kw)).build(links)


def kinds(g):
    return [v["kind"] for v in g.versions["D1"]]


def test_v3a_request_question_is_an_instruction_not_a_hypothetical():
    links = [L(1, "resolution", A), L(2, "rationale", "Copperfield daily on-demand pickups fix the late parcels"),
             L(2, "resolution", "Okay, we're moving to Copperfield daily pickups. Jun, can you set up the account this week?")]
    assert kinds(build(links)) == [S.INITIAL, S.CHANGED]
    assert kinds(build(links, rules="v1")) == [S.INITIAL]                      # v1: the trailing request made it tentative


def test_v3a_hedges_about_the_decision_stay_tentative():
    for text in ("Should we move to " + B + "?", "Maybe we should go with " + B, "What if we tried " + B):
        assert kinds(build([L(1, "resolution", A), L(2, "resolution", text)])) == [S.INITIAL], text


def test_v3b_instruction_without_option_words_adopts_the_pending_proposal():
    g = build([L(1, "proposal", A), L(1, "resolution", "Fine. Ravi, book the first slot for Monday.")])
    assert g.versions["D1"][0]["option"] == A


def test_v3b_resolution_naming_the_option_keeps_its_own_words():
    g = build([L(1, "resolution", A), L(2, "evidence", "Harbourline missed eleven of forty weekly collections"),
               L(2, "rationale", "Copperfield does daily on-demand pickups"), L(2, "resolution", "We're switching to Copperfield.")])
    assert kinds(g) == [S.INITIAL, S.CHANGED] and "Copperfield" in g.versions["D1"][1]["option"]


def test_v3c_flip_it_back_restores_the_previous_version():
    g = build([L(1, "resolution", A), L(2, "resolution", B), L(3, "rationale", "the daily fees ate the savings"),
               L(3, "resolution", "Sure. Nadia, flip the booking setting back tonight.")])
    assert kinds(g)[-1] == S.RESTORED and g.versions["D1"][-1]["option"] == A


def test_v3d_keep_with_an_added_clause_is_a_partial_override():
    g = build([L(1, "resolution", A), L(3, "resolution", "So we're keeping Harbourline weekly, with a Friday express van for the two hospital clinics.")])
    assert kinds(g) == [S.INITIAL, S.MODIFIED]


def test_v3d_plain_keep_is_still_a_reaffirmation():
    g = build([L(1, "resolution", A), L(3, "resolution", "Okay, so we're keeping Harbourline weekly.")])
    assert kinds(g) == [S.INITIAL] and g.versions["D1"][0]["reaffirmed_in"] == [3]


def test_v4a_low_confidence_resolution_creates_no_version():
    g = build([L(1, "resolution", A), L(2, "resolution", B, conf=0.6)], rules="v4", min_confidence=0.7)
    assert kinds(g) == [S.INITIAL]


def test_v4b_two_resolutions_in_one_meeting_are_one_event():
    g = build([L(1, "resolution", A), L(2, "resolution", B), L(2, "resolution", "Copperfield daily pickups, starting Monday, final answer")], rules="v4")
    assert len(g.versions["D1"]) == 2 and kinds(g)[1] in (S.CHANGED, S.MODIFIED)      # A and B share "courier", so B may count as a modification
    g3 = build([L(1, "resolution", A), L(2, "resolution", B), L(2, "resolution", "Copperfield daily pickups, starting Monday, final answer")], rules="v3")
    assert len(g3.versions["D1"]) >= 2


def test_v4b_going_back_within_the_meeting_undoes_the_version():
    g = build([L(1, "resolution", A), L(2, "resolution", B), L(2, "resolution", "No, scrap that, stay on " + A)], rules="v4")
    assert kinds(g) == [S.INITIAL] and g.as_of("D1", 2)["option"] == A and g.versions["D1"][0]["valid_to"] is None
    assert not [e for e in g.g.edges(data=True) if e[2]["etype"] == S.SUPERSEDED_BY]
