"""chunking.py - the long-meeting rule (pre-registered in reports/FREEZE.md, section 9). Applies IDENTICALLY to every system that sends a meeting to an LLM.

Why: the SYSTEM_MODEL context is 12,288 tokens, of which about 700 are instructions and up to 3,000 are output. A real meeting (AMI: up to about 19,000 transcript tokens)
does not fit. Synthetic meetings (at most 120 utterances, about 2,500 tokens) always fit, so on synthetic data the rule never triggers and results are identical with and without it.

The rule:
  * token estimate of an utterance = ceil(1.4 * words) + 6   (the +6 covers '[idx] SPEAKER: ' and the newline)
  * BUDGET = 6,000 estimated tokens of transcript per call; if the whole meeting fits, there is ONE window and nothing changes
  * otherwise windows are filled greedily with consecutive utterances up to BUDGET; the next window starts OVERLAP utterances before the previous one ended,
    OVERLAP = max(MIN_OVERLAP, number of utterances in the last 12 percent of the window's tokens), MIN_OVERLAP = 8
  * each window is re-indexed 0..k-1 so the unchanged extractors and their index validation work; links are mapped back to global indices
  * merging: links from different windows are duplicates when they have the same role and share at least one utterance, or are within one utterance of each other
    with the same speaker and role; of duplicates the link FARTHEST from its own window's edge is kept (ties: higher confidence, then earlier window)
  * guarantee (tested exhaustively): any span of up to 3 consecutive utterances (the longest event the schema allows) lies entirely inside at least one window,
    because MIN_OVERLAP >= 3
Any change to these constants is a new configuration, reported as post-hoc.
"""
import math
from dataclasses import dataclass

BUDGET = 6000
OVERLAP_FRAC = 0.12
MIN_OVERLAP = 8


def utt_tokens(u):
    return math.ceil(1.4 * len(u["text"].split())) + 6


def make_windows(utterances, budget=BUDGET, overlap_frac=OVERLAP_FRAC, min_overlap=MIN_OVERLAP):
    """Returns a list of (start, end) half-open global index ranges."""
    n = len(utterances)
    toks = [utt_tokens(u) for u in utterances]
    if sum(toks) <= budget:
        return [(0, n)]
    wins, start = [], 0
    while True:
        end, used = start, 0
        while end < n and (used + toks[end] <= budget or end == start):
            used += toks[end]
            end += 1
        wins.append((start, end))
        if end >= n:
            return wins
        tail, k = 0, 0
        while k < end - start - 1 and tail < overlap_frac * used:       # utterances covering the last overlap_frac of the window's tokens
            tail += toks[end - 1 - k]
            k += 1
        ov = max(min_overlap, k)
        start = max(start + 1, end - ov)


def window_meeting(meeting, start, end):
    us = meeting["utterances"][start:end]
    return dict(meeting_id=meeting.get("meeting_id"), date=meeting.get("date"),
                utterances=[dict(idx=i, speaker=u["speaker"], text=u["text"]) for i, u in enumerate(us)])


def to_global(links, start):
    out = []
    for l in links:
        g = dict(l)
        g["utterance_idxs"] = [i + start for i in l["utterance_idxs"]]
        out.append(g)
    return out


@dataclass
class _Cand:
    link: dict
    win: int
    edge: int            # distance from the nearest edge of its own window, in utterances


def _edge(link, start, end):
    lo, hi = min(link["utterance_idxs"]), max(link["utterance_idxs"])
    return min(lo - start, (end - 1) - hi)


def _same_event(a, b):
    if a["role"] != b["role"]:
        return False
    A, B = set(a["utterance_idxs"]), set(b["utterance_idxs"])
    if A & B:
        return True
    return a.get("speaker") == b.get("speaker") and min(abs(x - y) for x in A for y in B) <= 1


def merge(window_links, windows):
    """window_links[i]: links of window i with GLOBAL indices. Returns the merged list sorted by position."""
    cands = []
    for w, (links, (s, e)) in enumerate(zip(window_links, windows)):
        for l in links:
            cands.append(_Cand(l, w, _edge(l, s, e)))
    cands.sort(key=lambda c: (-c.edge, -float(c.link.get("confidence", 0.0)), c.win))      # best candidates first
    kept = []
    for c in cands:
        if not any(_same_event(c.link, k.link) for k in kept):
            kept.append(c)
    return sorted((k.link for k in kept), key=lambda l: (min(l["utterance_idxs"]), l["role"]))


def extract_chunked(meeting, mid, extract_fn, budget=BUDGET, **kw):
    """extract_fn(window_meeting, mid) -> links or (links, stats), with indices local to the window. Returns (links, stats, windows)."""
    wins = make_windows(meeting["utterances"], budget=budget, **kw)
    per, stats = [], []
    for s, e in wins:
        r = extract_fn(window_meeting(meeting, s, e), mid)
        links, st = (r if isinstance(r, tuple) else (r, None))
        per.append(to_global(links, s))
        stats.append(st)
    return (per[0] if len(wins) == 1 else merge(per, wins)), stats, wins
