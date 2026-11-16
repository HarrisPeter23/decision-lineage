"""phase3_topk.py - the single Phase 3 improvement round: keep the K highest-confidence links per meeting (ties: earlier utterance). Same rule for every system.
K was chosen on DEV only, from {4,6,8,12} (single_pass DEV F1 best at 4; the grid was looked at after seeing the unfiltered results - reported in reports/phase3_configs.md).
  python eval/phase3_topk.py --src results/phase3/main/merged/<cfg>/preds --dst <dir> --k 4"""
import argparse, collections, json, pathlib

def topk(links, k):
    by = collections.defaultdict(list)
    for l in links:
        by[l["meeting_id"]].append(l)
    out = []
    for ls in by.values():
        out += sorted(ls, key=lambda l: (-float(l.get("confidence", 0)), min(l["utterance_idxs"])))[:k]
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--src", required=True); ap.add_argument("--dst", required=True); ap.add_argument("--k", type=int, default=4)
    a = ap.parse_args(); dst = pathlib.Path(a.dst); dst.mkdir(parents=True, exist_ok=True)
    for f in pathlib.Path(a.src).glob("set_*.json"):
        d = json.loads(f.read_text(encoding="utf-8")); d["links"] = topk(d["links"], a.k); d["method"] = d.get("method", "") + f"+top{a.k}"
        (dst / f.name).write_text(json.dumps(d, indent=1), encoding="utf-8")


def div_topk(links, k):
    """P3-F role-balanced cap (configs recap_roles_div4, recap_args_div4): per meeting, first the highest-confidence link of each role present (roles taken in
    order of their best confidence; ties: earlier utterance), up to k; then fill to k by confidence. Same budget as topk, spread across roles."""
    by = {}
    for l in links:
        by.setdefault(l["meeting_id"], []).append(l)
    key = lambda l: (-float(l.get("confidence", 0)), min(l["utterance_idxs"]))
    out = []
    for ls in by.values():
        ls = sorted(ls, key=key)
        best = {}
        for l in ls:
            best.setdefault(l["role"], l)
        picked = sorted(best.values(), key=key)[:k]
        ids = {id(l) for l in picked}
        picked += [l for l in ls if id(l) not in ids][:max(0, k - len(picked))]
        out += picked
    return out
