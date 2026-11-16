"""The chunking wrapper in synthgen: one window leaves tags and links unchanged; a forced small budget splits a real DEV meeting and every call gets a distinct tag."""
import json, os, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "synthgen"))
import chunk_support as cs   # noqa: E402

def _meeting():
    split = json.loads((ROOT / "data/synth/split.json").read_text(encoding="utf-8"))
    tr = json.loads((ROOT / "data/synth/transcripts" / f"{split['dev'][0]}.json").read_text(encoding="utf-8"))
    return max(tr["meetings"], key=lambda m: len(m["utterances"]))

def test_one_window_keeps_tag_and_links():
    m, seen = _meeting(), []
    def fn(w, mid, t):
        seen.append(t); return [dict(meeting_id=mid, role="proposal", utterance_idxs=[2], speaker="A", confidence=0.9)]
    os.environ.pop("ADL_CHUNK_BUDGET", None)
    links, _, wins = cs.run(m, "m", "tagX", fn)
    assert len(wins) == 1 and seen == ["tagX"] and links[0]["utterance_idxs"] == [2]

def test_forced_small_budget_splits_and_tags_are_unique():
    m, seen = _meeting(), []
    def fn(w, mid, t):
        seen.append(t); return []
    os.environ["ADL_CHUNK_BUDGET"] = "700"
    try:
        _, sts, wins = cs.run(m, "m", "tagX", fn)
    finally:
        os.environ.pop("ADL_CHUNK_BUDGET")
    assert len(wins) > 1 and len(set(seen)) == len(seen) == len(wins) and seen[0] == "tagX"
