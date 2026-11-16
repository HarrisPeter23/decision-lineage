"""Tests for the single_pass_recap_roles extractor (synthgen/extract_recap.py): the recap uses only the system's own earlier outputs, never gold."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "synthgen"))
import extract_recap as er          # noqa: E402


class FakeLLM:
    def __init__(self):
        self.prompts = []

    def complete(self, system, user, kind="", temperature=0, tag=""):
        self.prompts.append(user)
        if "first meeting" in user:
            return json.dumps({"links": [{"role": "proposal", "utterance_idxs": [1], "speaker": "Ana", "confidence": 0.9, "decision": "office printer vendor", "option": "Inkwell"},
                                         {"role": "resolution", "utterance_idxs": [2, 99], "speaker": "Bo", "confidence": 0.8, "decision": "office printer vendor", "option": "Inkwell"},
                                         {"role": "banana", "utterance_idxs": [0], "speaker": "Bo"}]})
        return "not json at all"


def _fixture(tmp):
    meetings = [dict(meeting_id=f"m{k}", date=f"2025-02-0{k}", utterances=[dict(idx=i, speaker=["Ana", "Bo"][i % 2], text=f"meeting {k} line {i} about printers") for i in range(4)])
                for k in (1, 2)]
    (tmp / "transcripts").mkdir()
    (tmp / "transcripts" / "set_x.json").write_text(json.dumps(dict(set_id="set_x", meetings=meetings)), encoding="utf-8")
    (tmp / "gold").mkdir()
    (tmp / "gold" / "set_x.json").write_text(json.dumps({"SECRET_GOLD_MARKER": True}), encoding="utf-8")


def test_recap_uses_own_outputs_and_no_gold(tmp_path):
    _fixture(tmp_path)
    llm = FakeLLM()
    total, failed = er.run_dir(tmp_path, tmp_path / "out", llm)
    assert (total, failed) == (2, 1)                                  # meeting 2 returns bad JSON -> recorded as a failure, no links
    p1, p2 = llm.prompts
    assert "first meeting" in p1 and "Earlier meetings" not in p1
    assert "Earlier meetings" in p2 and "office printer vendor" in p2 and "meeting 1 line 2 about printers" in p2   # own resolution and its utterance text
    assert all("SECRET_GOLD_MARKER" not in p for p in llm.prompts)
    out = json.loads((tmp_path / "out" / "set_x.json").read_text(encoding="utf-8"))
    assert [l["role"] for l in out["links"]] == ["proposal", "resolution"]          # unknown role dropped
    assert out["links"][1]["utterance_idxs"] == [2]                                # out-of-range index dropped
    assert out["links"][0]["decision"] == "office printer vendor"


def test_contrastive_examples_are_not_dev_text():
    dev = json.loads((ROOT / "data" / "synth" / "split.json").read_text(encoding="utf-8"))["dev"]          # DEV only: TEST is not read before the freeze
    for s in dev:
        t = (ROOT / "data" / "synth" / "transcripts" / f"{s}.json").read_text(encoding="utf-8")
        for name in ("Brightway", "Clearline"):
            assert name not in t, f"{name} occurs in {s}"
