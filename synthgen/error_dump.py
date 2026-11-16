"""error_dump.py - list what an extraction config got wrong, with the actual utterance text.

  python error_dump.py --pred results/ablation/mp_p123/preds --data data/pilot [--tol 0] [--max 15] [--out errors.md]

Missed gold links (false negatives) show the gold role, speaker, intended content, the utterance, and what (if anything)
was predicted on that utterance. False positives show the predicted role and the utterance, and the gold role there if
the position matched but the role was wrong. Use it to categorize failures (implicit decision missed, wrong role,
unlabelled-but-legitimate decision, ...) rather than only reading aggregate scores.
"""
import argparse
import json
import pathlib

from score import gold_links, load_preds, match_links


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--tol", type=int, default=0)
    ap.add_argument("--max", type=int, default=15)
    ap.add_argument("--out")
    a = ap.parse_args()
    data = pathlib.Path(a.data)
    fn_lines, fp_lines = [], []
    for gp in sorted((data / "gold").glob("*.json")):
        gold = json.loads(gp.read_text())
        sid = gold["set_id"]
        tr = json.loads((data / "transcripts" / f"{sid}.json").read_text())
        text = {(m["meeting_id"], u["idx"]): f"{u['speaker']}: {u['text']}" for m in tr["meetings"] for u in m["utterances"]}
        golds = gold_links(gold)
        preds = load_preds(a.pred, sid) or []
        pairs = match_links(preds, golds, a.tol)
        gmatch = {j: i for i, j in pairs}
        pmatch = {i: j for i, j in pairs}
        for j, g in enumerate(golds):
            if j in gmatch and preds[gmatch[j]].get("role") == g["role"]:
                continue
            got = f"predicted `{preds[gmatch[j]].get('role')}`" if j in gmatch else "no prediction"
            fn_lines.append(f"- **{sid} {g['meeting_id']}[{g['utterance_idxs'][0]}] gold `{g['role']}`** ({g['speaker']}"
                            f"{', IMPLICIT' if g.get('implicit') else ''}) - {got}\n"
                            f"  - intended: {g['gist']}\n  - utterance: {text.get((g['meeting_id'], g['utterance_idxs'][0]), '?')}")
        for i, p in enumerate(preds):
            if i in pmatch and golds[pmatch[i]]["role"] == p.get("role"):
                continue
            idx = (p.get("utterance_idxs") or [None])[0]
            note = (f"gold role here is `{golds[pmatch[i]]['role']}`" if i in pmatch
                    else "no gold link here (may be a legitimate but unlabelled decision event)")
            fp_lines.append(f"- **{sid} {p.get('meeting_id')}[{idx}] predicted `{p.get('role')}`** - {note}\n"
                            f"  - utterance: {text.get((p.get('meeting_id'), idx), '?')}")
    out = [f"# Errors for `{a.pred}`\n", f"## Missed or mis-typed gold links ({len(fn_lines)})\n",
           *fn_lines[:a.max], f"\n(showing {min(a.max, len(fn_lines))} of {len(fn_lines)})\n",
           f"## Unmatched or mis-typed predictions ({len(fp_lines)})\n", *fp_lines[:a.max],
           f"\n(showing {min(a.max, len(fp_lines))} of {len(fp_lines)})\n"]
    txt = "\n".join(out)
    if a.out:
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
