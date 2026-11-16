"""Unit tests for the Phase 4 versioning revision (rules="v2", V2a-V2c in argdecisionlineage/graph.py), the v1 rules R1-R6 still holding under v2,
and the linking adapter (argdecisionlineage/linking.py) with a toy embedder (no model download)."""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from argdecisionlineage import schema as S                                                   # noqa: E402
from argdecisionlineage.graph import DecisionGraph, Link, Params                             # noqa: E402
from argdecisionlineage.linking import Embedder, EmbeddingLinker, LinkParams, links_from_predictions   # noqa: E402

A = "twice weekly Northway van run for the Leeds depot"
B = "daily Brackenfield cross dock delivery for the Leeds depot"
_n = [0]


def L(meeting, role, text, idx=0, conf=1.0, decision="D1"):
    _n[0] += 1
    return Link(link_id=f"V{_n[0]:03d}", meeting=meeting, role=role, speaker="Yuki", idxs=[idx], text=text, meeting_id=f"m{meeting}", date="", confidence=conf, decision=decision)


def v2(links):
    return DecisionGraph(Params(rules="v2", same_at=0.5, modified_at=0.3)).build(links)


def kinds(g):
    return [v["kind"] for v in g.versions["D1"]]


def test_v2a_implicit_change_takes_latest_rationale_not_the_evidence_against():
    g = v2([L(1, "proposal", A), L(1, "resolution", "fine, go ahead", 1),
            L(3, "evidence", "the Northway van run caused seventeen urgent courier orders", 0), L(3, "rationale", "Brackenfield daily cross dock is cheaper overall", 1),
            L(3, "resolution", "right, start the paperwork today", 2)])
    assert kinds(g) == [S.INITIAL, S.CHANGED] and "Brackenfield" in g.versions["D1"][1]["option"]


def test_v1_behaviour_kept_for_reproducibility():
    g = DecisionGraph(Params(rules="v1")).build([L(1, "proposal", A), L(1, "resolution", "fine, go ahead", 1),
                                                 L(3, "evidence", "the Northway van run caused seventeen urgent courier orders", 0), L(3, "resolution", "right, start the paperwork today", 2)])
    assert "Northway" in g.versions["D1"][-1]["option"]          # v1 takes the first evidence: the known weakness V2a fixes


def test_v2b_short_restatement_of_a_long_option_is_the_same_option():
    g = v2([L(1, "resolution", "for launch we go with per seat pricing at twelve dollars, and we revisit if the pilot accounts complain about the bill"),
            L(3, "resolution", "so per seat pricing at twelve dollars it is for launch", 0)])
    assert kinds(g) == [S.INITIAL] and g.versions["D1"][0]["reaffirmed_in"] == [3]


def test_v2c_keep_without_new_proposal_is_a_reaffirmation():
    g = v2([L(1, "resolution", A), L(2, "challenge", "seal orders are costing us", 0), L(3, "resolution", "okay, we're keeping it as it is for this quarter", 0)])
    assert kinds(g) == [S.INITIAL]


def test_v2c_does_not_block_a_real_change_after_a_new_proposal():
    g = v2([L(1, "resolution", A), L(3, "proposal", B, 0), L(3, "resolution", "we still need a daily slot, so Brackenfield daily cross dock it is", 1)])
    assert kinds(g) == [S.INITIAL, S.CHANGED]


def test_v1_rules_still_hold_under_v2():
    g = v2([L(1, "resolution", A), L(2, "resolution", B), L(3, "resolution", A + " again")])
    assert kinds(g) == [S.INITIAL, S.CHANGED, S.RESTORED]                  # R4
    g = v2([L(1, "resolution", A), L(2, "resolution", "Should we move to the " + B + "?")])
    assert kinds(g) == [S.INITIAL]                                          # R6
    g = v2([L(1, "proposal", A), L(2, "proposal", B)])
    assert g.versions["D1"] == []                                           # R5


def toy(texts):
    vocab = ["van", "leeds", "retention", "log", "demo"]
    return [np.array([t.lower().count(w) + 0.01 for w in vocab], dtype=float) for t in texts]


def test_linker_separates_a_side_decision_and_links_across_meetings():
    tr = dict(meetings=[dict(meeting_id="m1", date="d1", utterances=[dict(idx=0, speaker="Hana", text="Leeds should get the van run"),
                                                                        dict(idx=1, speaker="Yuki", text="ok the Leeds van run it is"),
                                                                        dict(idx=2, speaker="Rohan", text="cut log retention to fourteen days log"),
                                                                        dict(idx=3, speaker="Yuki", text="approved, log retention fourteen")]),
                        dict(meeting_id="m2", date="d2", utterances=[dict(idx=0, speaker="Zainab", text="the Leeds van run had urgent orders")])])
    preds = [dict(meeting_id="m1", role="proposal", utterance_idxs=[0], speaker="Hana", confidence=0.9),
             dict(meeting_id="m1", role="resolution", utterance_idxs=[1], speaker="Yuki", confidence=0.9),
             dict(meeting_id="m1", role="proposal", utterance_idxs=[2], speaker="Rohan", confidence=0.9),
             dict(meeting_id="m1", role="resolution", utterance_idxs=[3], speaker="Yuki", confidence=0.9),
             dict(meeting_id="m2", role="evidence", utterance_idxs=[0], speaker="Zainab", confidence=0.9, decision="Leeds delivery")]   # extra field ignored
    links = links_from_predictions(preds, tr, ctx=0)
    DecisionGraph(Params(rules="v2")).build(links, EmbeddingLinker(links, LinkParams(link_at=0.8, proposal_own=True), Embedder(toy)))
    d = [l.decision for l in links]
    assert d[0] == d[1] == d[4] and d[2] == d[3] and d[0] != d[2]
    assert [l.meeting for l in links] == [1, 1, 1, 1, 2]
