"""phase5_pool_transcripts.py - writes the DEV pool-10 corpora as extractor input (transcripts/<corpus>.json), built ONLY from what a system sees:
the pool's plain-text meetings (opaque ids, dates, utterances), in corpus order. No gold, no set ids, no private map. Used to re-extract
`single_pass_recap_roles` on the pooled order (its recap depends on the earlier meetings of the corpus).
  python eval/phase5_pool_transcripts.py --out runtime/kaggle/phase5/pooled_dev_k10
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from argdecisionlineage.retrieve import load_corpus   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="runtime/kaggle/phase5/pooled_dev_k10")
    ap.add_argument("--size", default="10")
    a = ap.parse_args()
    pools = ROOT / "data/synth/pools/dev"
    out = ROOT / a.out / "transcripts"
    out.mkdir(parents=True, exist_ok=True)
    for p in sorted(pools.glob(f"dev_k{a.size}_*")):
        ids = json.loads((p / "corpus.json").read_text(encoding="utf-8"))["meetings"]
        c = load_corpus([(p / "meetings" / f"{m}.txt").read_text(encoding="utf-8") for m in ids])
        (out / f"{p.name}.json").write_text(json.dumps(dict(set_id=p.name, meetings=c["meetings"]), indent=1), encoding="utf-8")
        print(p.name, len(c["meetings"]), "meetings")


if __name__ == "__main__":
    main()
