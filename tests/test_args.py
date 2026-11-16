"""Tests for the P3-F argument-completion pass (synthgen/extract_args.py) and the role-balanced cap (eval/phase3_topk.div_topk). Invented fixtures."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "synthgen"), str(ROOT / "eval")]
import extract_args as ea              # noqa: E402
from phase3_topk import div_topk, topk  # noqa: E402


class FakeLLM:
    def __init__(self):
        self.prompts = []

    def complete(self, system, user, kind="", temperature=0, tag=""):
        self.prompts.append(user)
        return json.dumps({"links": [{"role": "rationale", "utterance_idxs": [3], "speaker": "Bo", "confidence": 0.7, "decision": "printer vendor"},
                                     {"role": "rationale", "utterance_idxs": [1], "speaker": "Ana", "confidence": 0.6},        # duplicate of a pass-1 link
                                     {"role": "proposal", "utterance_idxs": [2], "speaker": "Ana", "confidence": 0.9}]})      # not an argument role


def test_args_pass_adds_only_new_arguments_and_never_reads_gold(tmp_path):
    us = [dict(idx=i, speaker=["Ana", "Bo"][i % 2], text=f"line {i} about printers") for i in range(4)]
    (tmp_path / "transcripts").mkdir()
    (tmp_path / "transcripts" / "set_x.json").write_text(json.dumps(dict(set_id="set_x", meetings=[dict(meeting_id="m1", date="d", utterances=us)])), encoding="utf-8")
    (tmp_path / "base_preds").mkdir()
    base = [dict(meeting_id="m1", role="proposal", utterance_idxs=[0], speaker="Ana", confidence=0.9, decision="printer vendor", option="Inkwell"),
            dict(meeting_id="m1", role="rationale", utterance_idxs=[1], speaker="Bo", confidence=0.8, decision="printer vendor", option="")]
    (tmp_path / "base_preds" / "set_x.json").write_text(json.dumps(dict(set_id="set_x", links=base)), encoding="utf-8")
    (tmp_path / "gold").mkdir()
    (tmp_path / "gold" / "set_x.json").write_text(json.dumps({"SECRET_GOLD_MARKER": 1}), encoding="utf-8")
    llm = FakeLLM()
    total, failed = ea.run_dir(tmp_path, tmp_path / "out", llm)
    out = json.loads((tmp_path / "out" / "set_x.json").read_text(encoding="utf-8"))["links"]
    assert (total, failed) == (1, 0) and len(out) == 3                      # 2 pass-1 + 1 new rationale; duplicate and proposal dropped
    assert out[-1]["utterance_idxs"] == [3] and out[-1]["source"] == "args"
    assert "printer vendor (option: Inkwell)" in llm.prompts[0] and "SECRET_GOLD_MARKER" not in llm.prompts[0]


def test_examples_use_no_benchmark_cast_names():
    sys.path.insert(0, str(ROOT / "synthgen"))
    from arcs import NAMES
    for n in NAMES:
        assert n not in ea.GUIDE, n


def test_div_topk_spreads_the_budget_across_roles():
    L = lambda r, c, i: dict(meeting_id="m1", role=r, confidence=c, utterance_idxs=[i])
    ls = [L("resolution", .95, 1), L("resolution", .95, 2), L("resolution", .9, 3), L("proposal", .9, 4), L("rationale", .6, 5), L("evidence", .5, 6)]
    assert [l["role"] for l in topk(ls, 4)] == ["resolution", "resolution", "resolution", "proposal"]
    assert sorted(l["role"] for l in div_topk(ls, 4)) == ["evidence", "proposal", "rationale", "resolution"]
    assert len(div_topk(ls[:2], 4)) == 2                                       # never more than exist
