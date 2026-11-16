"""pool_corpora.py - merge sets into pooled corpora of size {1, 10} within a split (SCOPE_4WEEK) (Phase 1.4).

Pools group sets of the same business domain (sorted by domain, then chunked) to create realistic confusion: several decisions in one
domain compete for the same question words. Meetings are concatenated in time order with distinct dates and OPAQUE meeting ids
(mtg_0001...), so nothing in the corpus reveals a set boundary. Questions keep their set_id; the private map from opaque id to
(set_id, meeting_id) lives in <out>/private_map.json and is read only by the harness, never by a system.

  python eval/pool_corpora.py --split test --out data/synth/pools
"""
import argparse
import datetime
import json
import pathlib
import sys

sys.path.insert(0, "synthgen")
from ingest import meeting_to_text  # noqa: E402

DATA = pathlib.Path("data/synth")


def build_pool(set_ids, name, out):
    items = []
    for sid in set_ids:
        tr = json.loads((DATA / "transcripts" / f"{sid}.json").read_text(encoding="utf-8"))
        for m in tr["meetings"]:
            items.append((m["date"], sid, m["meeting_id"], tr, m))
    items.sort(key=lambda x: (x[0], x[1], x[2]))
    d = out / name
    (d / "meetings").mkdir(parents=True, exist_ok=True)
    prev = None
    private, listing = {}, []
    for n, (date, sid, mid, tr, m) in enumerate(items, 1):
        day = datetime.date.fromisoformat(date)
        if prev is not None and day <= prev:
            day = prev + datetime.timedelta(days=1)         # distinct, increasing dates; only touched on collisions
        prev = day
        oid = f"mtg_{n:04d}"
        mm = dict(m, meeting_id=oid, date=day.isoformat())
        (d / "meetings" / f"{oid}.txt").write_text(meeting_to_text(tr, mm), encoding="utf-8", newline="\n")
        private[oid] = dict(set_id=sid, meeting_id=mid, original_date=date)
        listing.append(oid)
    (d / "corpus.json").write_text(json.dumps(dict(corpus_id=name, meetings=listing), indent=1), encoding="utf-8")
    (d / "private_map.json").write_text(json.dumps(dict(private, _sets=list(set_ids)), indent=1), encoding="utf-8")
    return len(listing)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    ap.add_argument("--out", default="data/synth/pools")
    a = ap.parse_args()
    split = json.loads((DATA / "split.json").read_text(encoding="utf-8"))
    prov = json.loads((DATA / "provenance.json").read_text(encoding="utf-8"))
    ids = sorted(split[a.split], key=lambda s: (prov[s]["domain"], s))
    out = pathlib.Path(a.out) / a.split
    index = {}
    for size in (1, 10):        # SCOPE_4WEEK: sizes {1, 10} only
        k = len(ids) if size == "all" else size
        for i in range(0, len(ids), k):
            chunk = ids[i:i + k]
            name = f"{a.split}_k{size}_{i // k:02d}"
            n = build_pool(chunk, name, out)
            index[name] = dict(sets=chunk, meetings=n)
    (out / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    print(a.split, "pools:", len(index), {k: v["meetings"] for k, v in list(index.items())[-3:]})


if __name__ == "__main__":
    main()
