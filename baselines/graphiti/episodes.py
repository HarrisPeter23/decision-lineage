"""episodes.py - Graphiti episodes per meeting under the FREEZE section 9 chunking rule (FREEZE section 18, AMI protocol).
A meeting that fits the budget is ONE episode named by its meeting id (synthetic meetings always fit, so DEV/TEST synthetic runs are unchanged).
A longer meeting (AMI) becomes one episode per chunk window, named "<meeting_id>#w<i>", each with the meeting's date; windows overlap exactly as in
argdecisionlineage/chunking.make_windows, the function every system uses. The meeting id is kept on every episode for the provenance adapter.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from argdecisionlineage import chunking as C     # noqa: E402


def parse_body(body):
    """'Speaker: text' lines -> utterance dicts (the plain-text transcript format)."""
    utts = []
    for line in body.splitlines():
        if line.strip():
            sp, _, tx = line.partition(": ")
            utts.append(dict(idx=len(utts), speaker=sp.strip(), text=tx.strip()))
    return utts


def episodes_for(meeting_id, body, budget=C.BUDGET):
    utts = parse_body(body)
    wins = C.make_windows(utts, budget=budget)
    if len(wins) == 1:
        return [dict(name=meeting_id, meeting_id=meeting_id, start=0, end=len(utts), text=body.strip())]
    return [dict(name=f"{meeting_id}#w{i}", meeting_id=meeting_id, start=s, end=e, text="\n".join(f"{u['speaker']}: {u['text']}" for u in utts[s:e]))
            for i, (s, e) in enumerate(wins)]
