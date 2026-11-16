"""Tests for the Phase 7 ablations of the frozen system (LineageSystem(ablation=...)); invented toy corpus from tests/test_retrieve.py."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from argdecisionlineage.linking import Embedder                 # noqa: E402
from argdecisionlineage.retrieve import LineageSystem           # noqa: E402
from test_retrieve import corpus, links, toy                    # noqa: E402

Q_WHY = "Why was the original decision about the depot courier changed?"


def build(ablation):
    return LineageSystem(embedder=Embedder(toy), fallback=False, ablation=ablation).index(corpus(), links())


def test_full_system_reference():
    r = build(None).retrieve(Q_WHY)
    assert r["changed"] and {i["role"] for i in r["items"]} >= {"evidence", "reconsideration", "resolution"}


def test_no_typing_keeps_versions_but_drops_roles():
    s = build("no_typing")
    assert {l.role for l in s.links} <= {"proposal", "resolution", "statement"}
    r = s.retrieve(Q_WHY)
    assert r["changed"] and "statement" in {i["role"] for i in r["items"]}         # temporal graph intact; arguments only as untyped statements


def test_no_conflict_resolution_versions_every_resolution():
    s = build("no_conflict_resolution")
    vs = [v for d, v in s.graph.versions.items() if v]
    assert all(len(v) == sum(1 for l in s.by_dec[d] if l.role == "resolution") for d, v in s.graph.versions.items() if v)
    assert vs


def test_static_graph_has_no_versions_or_supersession():
    s = build("static_graph")
    assert all(not v for v in s.graph.versions.values())
    assert not [e for e in s.graph.g.edges(data=True) if e[2]["etype"] == "SUPERSEDED_BY"]
    r = s.retrieve(Q_WHY)
    assert r["system"] == "lineage_static" and r["versions"] == [] and r["changed"] is None and r["items"]
