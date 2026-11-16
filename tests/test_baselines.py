"""Tests for the Phase 6 baselines on tiny invented fixtures (fake LLM, toy embedder; no model download, no benchmark data)."""
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from argdecisionlineage.linking import Embedder                  # noqa: E402
from baselines.evowiki_style import evowiki as E                 # noqa: E402
from baselines.vector_rag.vector_rag import VectorRAG            # noqa: E402


def corpus():
    m = lambda mid, d, lines: dict(meeting_id=mid, date=d, utterances=[dict(idx=i, speaker=s, text=t) for i, (s, t) in enumerate(lines)])
    return dict(meetings=[m("x1", "2025-01-01", [("Ana", "I propose the Harbour courier, weekly."), ("Bo", "Fine, Harbour courier it is."), ("Cy", "lunch?")]),
                          m("x2", "2025-01-08", [("Cy", "Harbour missed nine runs."), ("Bo", "Then we switch to Copper courier, daily.")]),
                          m("x3", "2025-01-15", [("Bo", "We stay with Copper.")])])


class FakeLLM:
    """Scripted Build: meeting 1 decides Harbour, meeting 2 replaces it with Copper, meeting 3 reaffirms; plus one undecided proposal that must not be stored."""
    def complete(self, system, user, kind="", temperature=0, tag=""):
        if kind == "evo_extract":
            k = int(user.split("Meeting ")[1].split(" ")[0])
            ups = {1: [dict(entity="depot", attribute="courier", value="Harbour weekly", stage="decided", evidence=[1]),
                       dict(entity="team", attribute="lunch", value="pizza", stage="proposed", evidence=[2])],
                   2: [dict(entity="the depot", attribute="courier vendor", value="Copper daily", stage="decided", evidence=[1, 0])],
                   3: [dict(entity="depot", attribute="courier", value="Copper daily", stage="decided", evidence=[0])]}[k]
            return json.dumps(dict(updates=ups))
        if "(empty wiki)" in user:
            return json.dumps(dict(routes=[dict(update="U0", slot="NEW", entity="depot", attribute="courier", relation="add")]))
        rel = "replace" if "Copper daily" in user and "= Harbour weekly" in user else "same"
        return json.dumps(dict(routes=[dict(update="U0", slot="S0", relation=rel)]))


def test_evowiki_overwrite_protocol():
    w, st = E.build(corpus(), FakeLLM())
    assert len(w.slots) == 1 and st["decided"] == 3 and st["updates"] == 4          # the proposed lunch is parsed but not written as a state
    s = w.slots[0]
    assert [x["label"] for x in s["states"]] == ["Overturned", "Active"]             # at most one Active per slot; the old one is kept, not deleted
    assert s["states"][0]["valid_to"] == 2 and s["states"][1]["valid_from"] == 2
    assert w.edges == [("S0", 0, 1, 2)]                                               # version-replacement edge
    assert s["states"][1]["reaffirmed"][0]["meeting"] == 3                            # "same" creates no new version
    r = E.read(w, corpus(), "Which courier serves the depot?")
    assert {i["text"].split("]")[0] for i in r["items"]} == {"[Overturned", "[Active"}
    act = [i for i in r["items"] if i["text"].startswith("[Active")][0]
    assert act["source_text"].startswith("Bo: Then we switch") and act["idxs"] == [1, 0]  # provenance = source utterances


def test_evowiki_read_truncates_overturned_first():
    w, _ = E.build(corpus(), FakeLLM())
    full = E.read(w, corpus(), "q")
    act = [i for i in full["items"] if i["text"].startswith("[Active")][0]
    r = E.read(w, corpus(), "q", budget=E._tok(act["text"]) + 1)
    assert r["truncated"] and [i["text"][:7] for i in r["items"]] == ["[Active"]


def toy(texts):
    vocab = ["harbour", "copper", "lunch", "courier"]
    return [np.array([t.lower().count(v) + 0.01 for v in vocab], dtype=float) for t in texts]


def test_vector_rag_retrieves_chronological_windows():
    v = VectorRAG(embedder=Embedder(toy), k=2, win=2, stride=1).index(corpus())
    r = v.retrieve("copper courier")
    assert len(r["items"]) == 2 and [i["meeting"] for i in r["items"]] == sorted(i["meeting"] for i in r["items"])
    assert all("Copper" in i["text"] for i in r["items"]) and r["system"] == "vector_rag"
