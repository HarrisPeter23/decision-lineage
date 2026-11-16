"""ami_pools.py - SHARED AMI data preparation (FREEZE section 18): every system reads AMI from these corpora, never from data/ami/transcripts directly.
Each AMI series becomes one pool-1 corpus in data/ami/pools/<series>/ in the same plain-text format as the synthetic pools (corpus.json, meetings/*.txt
with Meeting / Date / Participants headers, private_map.json read only by the harness). Opaque meeting ids mtg_0001.. as in the synthetic pools.
Dates: AMI records one date per series (dd-mm-yy or dd-mm-yyyy) shared by its four meetings, so each meeting's date is normalised ONCE, here, to
ISO date + k hours (meeting k = 0..3 at 09:00, 10:00, ...). The offset is synthetic and only preserves meeting order; every system sees the same string.
  python eval/ami_pools.py -> data/ami/pools/
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "synthgen"))
from ingest import meeting_to_text   # noqa: E402


def norm_date(d, k):
    m = re.fullmatch(r"(\d\d)-(\d\d)-(\d\d|\d{4})", d)
    if not m:
        raise ValueError(f"unexpected AMI date {d!r}")
    dd, mm, yy = m.groups()
    return f"{yy if len(yy) == 4 else '20' + yy}-{mm}-{dd}T{9 + k:02d}:00:00"


def main():
    out = ROOT / "data/ami/pools"
    index = {}
    for f in sorted((ROOT / "data/ami/transcripts").glob("*.json")):
        t = json.loads(f.read_text(encoding="utf-8"))
        d = out / t["set_id"]
        (d / "meetings").mkdir(parents=True, exist_ok=True)
        ids, priv = [], {}
        for k, m in enumerate(t["meetings"]):
            oid = f"mtg_{k + 1:04d}"
            mm = dict(m, meeting_id=oid, date=norm_date(m["date"], k))
            (d / "meetings" / f"{oid}.txt").write_text(meeting_to_text(t, mm), encoding="utf-8", newline="\n")
            ids.append(oid)
            priv[oid] = dict(set_id=t["set_id"], meeting_id=m["meeting_id"], original_date=m["date"])
        (d / "corpus.json").write_text(json.dumps(dict(corpus_id=t["set_id"], meetings=ids), indent=1), encoding="utf-8")
        (d / "private_map.json").write_text(json.dumps(dict(priv, _sets=[t["set_id"]]), indent=1), encoding="utf-8")
        index[t["set_id"]] = dict(sets=[t["set_id"]], meetings=len(ids))
    (out / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    print({k: v["meetings"] for k, v in index.items()})


if __name__ == "__main__":
    main()
