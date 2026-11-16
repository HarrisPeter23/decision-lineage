"""Unit tests for the decision graph's versioning rules R1-R6 (tiny hand-made fixtures; no model, no data files)."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from argdecisionlineage import schema as S                        # noqa: E402
from argdecisionlineage.graph import DecisionGraph, Link          # noqa: E402

A = "twice weekly Northway van run for the Leeds depot"
B = "daily Brackenfield cross dock delivery for the Leeds depot"
_n = [0]


def L(meeting, role, text, idx=0, conf=1.0, decision="D1", speaker="Yuki"):
    _n[0] += 1
    return Link(link_id=f"L{_n[0]:03d}", meeting=meeting, role=role, speaker=speaker, idxs=[idx], text=text, meeting_id=f"m{meeting}", date=f"2025-01-{meeting:02d}", confidence=conf, decision=decision)


def build(links):
    return DecisionGraph().build(links)


def kinds(g, did="D1"):
    return [v["kind"] for v in g.versions[did]]


def test_r1_reversal_supersedes_and_closes_windows():
    g = build([L(1, "proposal", A), L(1, "rationale", "slow movers", 1), L(1, "resolution", A, 2), L(2, "evidence", "seal orders spiked", 0), L(2, "challenge", "savings are gone", 1),
               L(3, "reconsideration", "let us reopen it", 0), L(3, "rationale", B, 1), L(3, "resolution", B, 2)])
    v = g.versions["D1"]
    assert kinds(g) == [S.INITIAL, S.CHANGED]
    assert (v[0]["valid_from"], v[0]["valid_to"]) == (1, 3) and (v[1]["valid_from"], v[1]["valid_to"]) == (3, None)
    assert g.g.has_edge(("version", "D1", 1), ("version", "D1", 2))
    assert g.as_of("D1", 2)["option"] == A and g.as_of("D1", 3)["option"] == B
    assert g.as_of("D1", 0) is None                                  # 'no decision yet'


def test_r2_reaffirmation_creates_no_new_version():
    g = build([L(1, "proposal", A), L(1, "resolution", A, 1), L(2, "challenge", "too risky", 0), L(3, "reconsideration", "reopen", 0), L(3, "resolution", "so we keep the " + A, 1)])
    assert kinds(g) == [S.INITIAL]
    assert g.versions["D1"][0]["reaffirmed_in"] == [3]
    assert len(g.edges_of(("version", "D1", 1), S.RESOLVED_BY)) == 2


def test_r3_partial_override_is_a_modified_version():
    felt = "felt wall panels across the whole floor"
    mod = "felt wall panels across the whole floor except corridor which gets mineral wool core panel rated fireproof"
    g = build([L(1, "proposal", felt), L(1, "resolution", felt, 1), L(2, "challenge", "corridor rating", 0), L(3, "resolution", mod, 0)])
    assert kinds(g) == [S.INITIAL, S.MODIFIED]


def test_r4_back_to_the_first_option_is_a_third_version():
    g = build([L(1, "resolution", A), L(2, "resolution", B), L(3, "resolution", A + " again")])
    assert kinds(g) == [S.INITIAL, S.CHANGED, S.RESTORED]
    assert [v["valid_from"] for v in g.versions["D1"]] == [1, 2, 3]
    assert g.as_of("D1", 2)["option"] == B


def test_r5_deferred_decision_has_no_version():
    g = build([L(1, "proposal", A), L(1, "rationale", "fewer vans", 1), L(2, "evidence", "new quote", 0), L(2, "proposal", B, 1), L(2, "rationale", "daily is safer", 2)])
    assert g.versions["D1"] == [] and g.as_of("D1", 2) is None
    assert ("decision", "D1") in g.g.nodes


def test_r5_a_proposal_that_never_wins_leaves_the_decision_unchanged():
    g = build([L(1, "resolution", A), L(2, "proposal", B), L(2, "rationale", "cheaper overall", 1), L(3, "challenge", "no it is not", 0)])
    assert kinds(g) == [S.INITIAL] and g.current("D1")["option"] == A


def test_r6_question_and_hedged_resolutions_do_not_supersede():
    for text in ("Should we move to the " + B + "?", "What if we went with the " + B, "Maybe we should switch to the " + B, "How about the " + B):
        g = build([L(1, "resolution", A), L(2, "resolution", text)])
        assert kinds(g) == [S.INITIAL], text
        assert g.g.nodes[("link", g.links and [k for k, v in g.links.items() if v.text == text][0])].get("tentative")


def test_r6_low_confidence_resolution_does_not_supersede():
    g = build([L(1, "resolution", A), L(2, "resolution", B, conf=0.3)])
    assert kinds(g) == [S.INITIAL]


def test_hedging_speaker_who_actually_decides_still_creates_a_version():
    g = build([L(1, "resolution", A), L(2, "resolution", "I think maybe we'll say we move to the " + B)])
    assert kinds(g) == [S.INITIAL, S.CHANGED]


def test_implicit_agreement_takes_the_option_proposed_before_it():
    g = build([L(1, "proposal", A), L(1, "resolution", "fine by me, go ahead", 1), L(3, "proposal", B), L(3, "rationale", "daily avoids the seal orders", 1), L(3, "resolution", "okay Mei, start the paperwork", 2)])
    assert [v["option"] for v in g.versions["D1"]] == [A, B] and kinds(g) == [S.INITIAL, S.CHANGED]


def test_reopening_and_challenge_attach_to_the_current_version():
    g = build([L(1, "resolution", A), L(2, "challenge", "seals missed the four hour term", 0), L(3, "reconsideration", "reopen the question", 0)])
    v1 = ("version", "D1", 1)
    assert len(g.edges_of(v1, S.CHALLENGED_BY)) == 1 and len(g.edges_of(v1, S.REOPENED_BY)) == 1


def test_side_decision_in_the_same_meeting_is_not_merged_into_the_main_one():
    links = [Link("a1", 1, "proposal", "Hana", [0], "move the Leeds depot to a twice weekly Northway van run", "m1", "d1"),
             Link("a2", 1, "resolution", "Yuki", [5], "so Leeds moves to the twice weekly Northway van run", "m1", "d1"),
             Link("b1", 1, "proposal", "Rohan", [20], "cut debug log retention from thirty days to fourteen", "m1", "d1"),
             Link("b2", 1, "resolution", "Yuki", [24], "approved, debug log retention drops to fourteen days", "m1", "d1"),
             Link("a3", 2, "evidence", "Zainab", [3], "the Leeds depot expedite log shows seventeen urgent courier orders", "m2", "d2")]
    g = DecisionGraph().build(links)
    ds = {l.decision for l in links}
    assert len(ds) == 2
    assert links[0].decision == links[1].decision == links[4].decision and links[2].decision == links[3].decision != links[0].decision
    assert all(len(v) == 1 for v in g.versions.values())
