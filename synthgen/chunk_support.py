"""chunk_support.py - applies the pre-registered long-meeting chunking rule (reports/FREEZE.md section 9) around any per-meeting extractor.
Identical for every system. Budget comes from env ADL_CHUNK_BUDGET (default = the pre-registered 6000); only the DEV acceptance test overrides it (1200)."""
import os
import pathlib
import sys

try:
    import chunking as C
except ImportError:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "argdecisionlineage"))
    import chunking as C


def run(meeting, mid, tag, fn):
    """fn(window_meeting, mid, tag) -> links or (links, stats). Returns (links, list_of_stats, windows). One window keeps the original tag (and cache)."""
    budget = int(os.environ.get("ADL_CHUNK_BUDGET", C.BUDGET))
    n = [0]

    def f(win, m):
        t = tag if n[0] == 0 else f"{tag}-w{n[0]}"
        n[0] += 1
        return fn(win, m, t)
    return C.extract_chunked(meeting, mid, f, budget=budget)
