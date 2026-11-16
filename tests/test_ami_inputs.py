"""Every system receives identical AMI inputs (FREEZE section 18): the shared pools of eval/ami_pools.py are the only AMI source; dates are normalised
there once (ISO + k hours, order-preserving); utterances equal the source transcripts; Graphiti's builder reads the same files as everyone else."""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from argdecisionlineage.retrieve import load_corpus     # noqa: E402

POOLS = ROOT / "data/ami/pools"


def test_pools_dates_ordered_and_utterances_identical():
    for f in sorted((ROOT / "data/ami/transcripts").glob("*.json")):
        t = json.loads(f.read_text(encoding="utf-8"))
        d = POOLS / t["set_id"]
        ids = json.loads((d / "corpus.json").read_text(encoding="utf-8"))["meetings"]
        c = load_corpus([(d / "meetings" / f"{m}.txt").read_text(encoding="utf-8") for m in ids])      # what retrieval, extraction and EvoWiki read
        dates = [m["date"] for m in c["meetings"]]
        assert all(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:00:00", x) for x in dates) and dates == sorted(dates) and len(set(dates)) == len(dates)
        for src, got in zip(t["meetings"], c["meetings"]):
            assert [(u["speaker"], u["text"]) for u in src["utterances"]] == [(u["speaker"], u["text"]) for u in got["utterances"]]


def test_no_system_reads_raw_ami_transcripts():
    allowed = {"eval/ami_pools.py", "tests/test_ami_inputs.py"}
    hits = []
    for p in list((ROOT / "argdecisionlineage").rglob("*.py")) + list((ROOT / "baselines").rglob("*.py")) + list((ROOT / "runtime/kaggle").rglob("build*.py")):
        rel = p.relative_to(ROOT).as_posix()
        if rel not in allowed and "data/ami/transcripts" in p.read_text(encoding="utf-8", errors="ignore"):
            hits.append(rel)
    assert not hits, hits
