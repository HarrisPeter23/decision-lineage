"""Tests for the Graphiti chunked episodes (baselines/graphiti/episodes.py) used on AMI (FREEZE section 18). Invented text; no Graphiti, no model."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from argdecisionlineage import chunking as C              # noqa: E402
from baselines.graphiti.episodes import episodes_for, parse_body   # noqa: E402

BODY = "\n".join(f"{['Ana', 'Bo', 'Cy'][i % 3]}: line {i} " + "word " * (8 + i % 5) for i in range(120))


def test_fitting_meeting_is_one_unchanged_episode():
    eps = episodes_for("mtg_0001", BODY, budget=10 ** 6)
    assert len(eps) == 1 and eps[0]["name"] == "mtg_0001" and eps[0]["text"] == BODY.strip()


def test_long_meeting_is_split_exactly_like_every_other_system():
    eps = episodes_for("mtg_0002", BODY, budget=400)
    wins = C.make_windows(parse_body(BODY), budget=400)
    assert len(eps) == len(wins) > 1
    assert [(e["start"], e["end"]) for e in eps] == wins
    assert all(e["meeting_id"] == "mtg_0002" and e["name"] == f"mtg_0002#w{i}" for i, e in enumerate(eps))
    covered = set()
    for e in eps:
        covered |= set(range(e["start"], e["end"]))
    assert covered == set(range(120))                      # every utterance is in some episode
    assert eps[1]["start"] < eps[0]["end"]                 # windows overlap, as in the shared rule
