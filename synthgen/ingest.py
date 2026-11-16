"""ingest.py - Layer 1 (ingestion): plain-text meeting transcripts <-> the structured form used for scoring.

Plain-text transcript format (what a real system would receive; gold labels never appear in it):

    Meeting: m1
    Date: 2025-09-13
    Participants: Diego, Henrik, Ingrid, Sven, Wei

    Diego: Okay, okay, hi everyone. Can everyone hear me?
    Henrik: So I think we charge per seat...

Utterance index = zero-based position among the utterance lines (the lines after the first blank line).
Scoring uses these indexes, so ingestion must preserve line order.

  python ingest.py export data/pilot transcripts_txt     # writes transcripts_txt/<set_id>/<meeting_id>.txt
  python ingest.py roundtrip data/pilot                  # export -> parse -> compare with the JSON transcripts
"""
import json
import pathlib
import sys


def meeting_to_text(set_tr, meeting):
    head = [f"Meeting: {meeting['meeting_id']}", f"Date: {meeting['date']}",
            f"Participants: {', '.join(set_tr['cast'])}", ""]
    return "\n".join(head + [f"{u['speaker']}: {u['text']}" for u in meeting["utterances"]]) + "\n"


def parse_meeting_text(text):
    meta, utts, in_body = {}, [], False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not in_body:
            if not line.strip():
                in_body = True
                continue
            k, _, v = line.partition(":")
            meta[k.strip().lower()] = v.strip()
            continue
        if not line.strip():
            continue
        sp, sep, tx = line.partition(": ")
        if not sep:
            raise ValueError(f"utterance line without 'Speaker: text': {line!r}")
        utts.append(dict(idx=len(utts), speaker=sp.strip(), text=tx.strip()))
    return dict(meeting_id=meta.get("meeting"), date=meta.get("date"),
                participants=[p.strip() for p in meta.get("participants", "").split(",") if p.strip()],
                utterances=utts)


def export(data, out):
    data, out = pathlib.Path(data), pathlib.Path(out)
    n = 0
    for p in sorted((data / "transcripts").glob("*.json")):
        tr = json.loads(p.read_text())
        d = out / tr["set_id"]
        d.mkdir(parents=True, exist_ok=True)
        for m in tr["meetings"]:
            (d / f"{m['meeting_id']}.txt").write_text(meeting_to_text(tr, m))
            n += 1
    return n


def roundtrip(data):
    import tempfile
    data = pathlib.Path(data)
    with tempfile.TemporaryDirectory() as tmp:
        export(data, tmp)
        bad = 0
        for p in sorted((data / "transcripts").glob("*.json")):
            tr = json.loads(p.read_text())
            for m in tr["meetings"]:
                got = parse_meeting_text((pathlib.Path(tmp) / tr["set_id"] / f"{m['meeting_id']}.txt").read_text())
                want = [(u["idx"], u["speaker"], u["text"]) for u in m["utterances"]]
                have = [(u["idx"], u["speaker"], u["text"]) for u in got["utterances"]]
                if want != have or got["meeting_id"] != m["meeting_id"] or got["date"] != m["date"]:
                    bad += 1
                    print(f"MISMATCH {tr['set_id']}/{m['meeting_id']}")
    return bad


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "export":
        print(export(sys.argv[2], sys.argv[3]), "meeting files written")
    elif cmd == "roundtrip":
        bad = roundtrip(sys.argv[2])
        print("roundtrip OK" if not bad else f"{bad} meetings differ")
        sys.exit(1 if bad else 0)
    else:
        print(__doc__)
