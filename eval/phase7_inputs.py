"""phase7_inputs.py - Phase 7 (after FREEZE): extractor input built ONLY from the shared pools (system-visible text: opaque meeting ids, dates,
utterances; no gold, no set ids, no private map): TEST pool-1 corpora, TEST pool-10 corpora (pooled order, needed by the recap) and the shared AMI pools.
Each corpus becomes one transcripts/<corpus>.json for the frozen extractor (single_pass_recap_roles, then top-4 at retrieval time).
  python eval/phase7_inputs.py -> runtime/kaggle/phase7/extract_in/transcripts/
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from argdecisionlineage.retrieve import load_corpus   # noqa: E402

SOURCES = [("data/synth/pools/test", "test_k1_*"), ("data/synth/pools/test", "test_k10_*"), ("data/ami/pools", "ami_*")]


def main():
    out = ROOT / "runtime/kaggle/phase7/extract_in/transcripts"
    out.mkdir(parents=True, exist_ok=True)
    n = {}
    for root, pat in SOURCES:
        for p in sorted((ROOT / root).glob(pat)):
            if not p.is_dir():
                continue
            ids = json.loads((p / "corpus.json").read_text(encoding="utf-8"))["meetings"]
            c = load_corpus([(p / "meetings" / f"{m}.txt").read_text(encoding="utf-8") for m in ids])
            (out / f"{p.name}.json").write_text(json.dumps(dict(set_id=p.name, meetings=c["meetings"])), encoding="utf-8")
            n[p.name] = len(c["meetings"])
    print(len(n), "corpora,", sum(n.values()), "meetings")


if __name__ == "__main__":
    main()
