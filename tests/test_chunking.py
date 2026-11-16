"""Tests for the long-meeting chunking rule: coverage, overlap, the 3-utterance guarantee, and oracle merging on real DEV gold (no model)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from argdecisionlineage import chunking as C        # noqa: E402

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "synth"


def fake_meeting(n, words=10):
    return dict(meeting_id="m1", utterances=[dict(idx=i, speaker="A" if i % 2 else "B", text=" ".join(["w"] * words)) for i in range(n)])


def test_short_meeting_is_one_window_and_unchanged():
    m = fake_meeting(100)
    assert C.make_windows(m["utterances"]) == [(0, 100)]
    links = [dict(meeting_id="m1", role="proposal", utterance_idxs=[3], speaker="A", confidence=0.9)]
    out, stats, wins = C.extract_chunked(m, "m1", lambda w, mid: links)
    assert out == links and wins == [(0, 100)]


def test_windows_cover_everything_respect_budget_and_overlap():
    for n, words, budget in [(1200, 10, 6000), (800, 25, 6000), (500, 40, 1500), (300, 12, 600)]:
        m = fake_meeting(n, words)
        w = C.make_windows(m["utterances"], budget=budget)
        assert w[0][0] == 0 and w[-1][1] == n
        for (s, e) in w:
            assert sum(C.utt_tokens(u) for u in m["utterances"][s:e]) <= budget or e - s == 1
        for (s1, e1), (s2, e2) in zip(w, w[1:]):
            assert e1 - s2 >= C.MIN_OVERLAP and s2 > s1 and e2 > e1


def test_every_span_of_up_to_three_utterances_is_inside_some_window():
    m = fake_meeting(400, 18)
    w = C.make_windows(m["utterances"], budget=900)
    assert len(w) > 3
    for length in (1, 2, 3):
        for s in range(0, 400 - length + 1):
            assert any(a <= s and s + length <= b for a, b in w), (s, length)


def _dev_meetings():
    split = json.loads((DATA / "split.json").read_text(encoding="utf-8"))
    for sid in split["dev"]:
        tr = json.loads((DATA / "transcripts" / f"{sid}.json").read_text(encoding="utf-8"))
        gold = json.loads((DATA / "gold" / f"{sid}.json").read_text(encoding="utf-8"))
        for m in tr["meetings"]:
            links = [dict(meeting_id=m["meeting_id"], role=l["role"], utterance_idxs=list(l["utterance_idxs"]), speaker=l["speaker"], confidence=0.9)
                     for l in gold["chain"] if l["meeting_id"] == m["meeting_id"]]
            yield sid, m, links


def test_oracle_merge_returns_exactly_the_gold_links_on_dev_for_forced_small_windows():
    checked = windows_seen = 0
    for sid, m, gold in _dev_meetings():
        for budget in (400, 700, 1200):
            def oracle(win, mid, _m=m, _g=gold):
                # the window is the re-indexed slice; recover its offset from the first utterance text identity
                first = win["utterances"][0]["text"]
                off = next(i for i, u in enumerate(_m["utterances"]) if u["text"] == first and u["speaker"] == win["utterances"][0]["speaker"]
                           and all(_m["utterances"][off_ + k]["text"] == win["utterances"][k]["text"] for off_ in [i] for k in range(min(3, len(win["utterances"])))))
                lo, hi = off, off + len(win["utterances"])
                return [dict(l, utterance_idxs=[i - off for i in l["utterance_idxs"]]) for l in _g if lo <= min(l["utterance_idxs"]) and max(l["utterance_idxs"]) < hi]
            out, _, wins = C.extract_chunked(m, m["meeting_id"], oracle, budget=budget)
            windows_seen += len(wins)
            key = lambda ls: sorted((min(l["utterance_idxs"]), l["role"], tuple(l["utterance_idxs"])) for l in ls)
            assert key(out) == key(gold), (sid, m["meeting_id"], budget)
            checked += 1
    assert checked >= 100 and windows_seen > checked        # forced windows really did split the meetings


def test_duplicate_in_overlap_keeps_the_link_farthest_from_a_window_edge():
    wins = [(0, 100), (90, 190)]
    a = dict(role="rationale", utterance_idxs=[97, 98], speaker="X", confidence=0.9)      # near the right edge of window 0
    b = dict(role="rationale", utterance_idxs=[98], speaker="X", confidence=0.5)          # 8 from the left edge of window 1
    out = C.merge([[a], [b]], wins)
    assert out == [b]


def test_same_role_neighbours_with_other_speakers_are_not_merged():
    wins = [(0, 50), (40, 90)]
    a = dict(role="evidence", utterance_idxs=[45], speaker="X", confidence=0.9)
    b = dict(role="evidence", utterance_idxs=[46], speaker="Y", confidence=0.9)
    assert len(C.merge([[a], [b]], wins)) == 2


def test_different_roles_on_the_same_line_are_both_kept():
    wins = [(0, 50), (40, 90)]
    a = dict(role="challenge", utterance_idxs=[45], speaker="X", confidence=0.9)
    b = dict(role="evidence", utterance_idxs=[45], speaker="X", confidence=0.9)
    assert len(C.merge([[a], [b]], wins)) == 2


def test_links_outside_their_window_are_not_invented_by_the_wrapper():
    m = fake_meeting(300, 30)
    wins = C.make_windows(m["utterances"], budget=1500)
    assert len(wins) > 2
    out, _, _ = C.extract_chunked(m, "m1", lambda w, mid: [dict(role="proposal", utterance_idxs=[0], speaker="B", confidence=1.0)], budget=1500)
    assert sorted(min(l["utterance_idxs"]) for l in out) == sorted({s for s, _ in wins})
