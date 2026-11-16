"""extract_multipass.py - multi-pass chain extraction with optional quote verification.

  pass 1  flag decision utterances (propose / decide-or-agree / reopen)
  pass 2  resolve references: rewrite each flagged utterance as a self-contained statement
  pass 3  type every event into a role (receives hints from passes 1-2 when they ran)

  python extract_multipass.py --data data/pilot --out preds/mp_p123 --passes 1,2,3 --provider anthropic --model MODEL
  python extract_multipass.py ... --passes 3          # pass 3 only (same family as the single-pass baseline, +quote field)
  python extract_multipass.py ... --verify-quotes     # drop links whose quote is not in the cited utterance(s)

Quote verification is a cheap hallucination filter: the model must copy words from the key utterance, and a link
whose quote cannot be found (after normalizing case and punctuation) in any cited utterance is dropped and counted.
Pass 2 requires pass 1; pass 3 is always required. Untested against live APIs (no network where this was written).
"""
import argparse
import json
import pathlib
import re

from arcs import ROLE_DEFS
from llm import LLM, extract_json
from prompts import MP_SYSTEM, mp_flag_prompt, mp_resolve_prompt, mp_type_prompt

ROLES = list(ROLE_DEFS)


def _norm(s):
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split())


def quote_ok(link, meeting):
    q = _norm(link.get("quote"))
    if not q:
        return False
    by_idx = {u["idx"]: u["text"] for u in meeting["utterances"]}
    return any(q in _norm(by_idx.get(i, "")) for i in link["utterance_idxs"])


def _json(llm, user, kind, tag):
    return extract_json(llm.complete(MP_SYSTEM, user, kind=kind, temperature=0, tag=tag))


def build_hints(meeting, flagged, resolved):
    by_idx = {u["idx"]: u for u in meeting["utterances"]}
    lines = []
    res = {r["idx"]: r for r in resolved}
    for i in flagged:
        if i in res:
            r = res[i]
            lines.append(f"- [{i}] {by_idx[i]['speaker']}: resolved meaning: {r.get('resolved_text')} "
                         f"(about: {r.get('refers_to')}; looks like: {r.get('speech_act')})")
        else:
            lines.append(f"- [{i}] flagged as a proposal, decision/agreement, or reopening")
    return "\n".join(lines)


def extract_meeting(meeting, mid, llm, tag, passes=(3,), verify=False):
    """Returns (links, stats). stats: dict(calls, p1_failed, p2_failed, p3_failed, dropped_quote, flagged)."""
    n = len(meeting["utterances"])
    st = dict(calls=0, p1_failed=0, p2_failed=0, p3_failed=0, dropped_quote=0, flagged=0)
    flagged, resolved = [], []
    if 1 in passes:
        try:
            st["calls"] += 1
            out = _json(llm, mp_flag_prompt(meeting), "mp_flag", f"{tag}-p1")
            flagged = sorted({int(i) for i in out["flagged"] if 0 <= int(i) < n})
            st["flagged"] = len(flagged)
        except Exception:
            st["p1_failed"] += 1
    if 2 in passes and flagged:
        try:
            st["calls"] += 1
            out = _json(llm, mp_resolve_prompt(meeting, flagged), "mp_resolve", f"{tag}-p2")
            resolved = [r for r in out["resolved"] if isinstance(r, dict) and "idx" in r]
            for r in resolved:
                r["idx"] = int(r["idx"])
        except Exception:
            st["p2_failed"] += 1
    hints = build_hints(meeting, flagged, resolved) if flagged else ""
    links = []
    try:
        st["calls"] += 1
        out = _json(llm, mp_type_prompt(meeting, hints), "mp_type", f"{tag}-p3")
        raw = out["links"] if isinstance(out, dict) else out
    except Exception:
        st["p3_failed"] += 1
        return [], st
    for l in raw:
        try:
            role = str(l["role"]).strip().lower()
            idxs = [int(i) for i in l["utterance_idxs"] if 0 <= int(i) < n]
            if role not in ROLES or not idxs:
                continue
            link = dict(meeting_id=mid, role=role, utterance_idxs=idxs, speaker=l.get("speaker"),
                        quote=l.get("quote"), confidence=float(l.get("confidence", 0.5)))
            if verify and not quote_ok(link, meeting):
                st["dropped_quote"] += 1
                continue
            links.append(link)
        except Exception:
            continue
    return links, st


def parse_passes(s):
    ps = sorted({int(x) for x in str(s).split(",")})
    if 3 not in ps or any(p not in (1, 2, 3) for p in ps) or (2 in ps and 1 not in ps):
        raise SystemExit("--passes must include 3, and 2 requires 1 (valid: 3 | 1,3 | 1,2,3)")
    return tuple(ps)


def run_dir(data, out, llm, passes, verify):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    tot = dict(calls=0, p1_failed=0, p2_failed=0, p3_failed=0, dropped_quote=0, flagged=0, meetings=0)
    for p in sorted((pathlib.Path(data) / "transcripts").glob("*.json")):
        tr = json.loads(p.read_text())
        links = []
        for m in tr["meetings"]:
            import chunk_support
            ls, sts, _w = chunk_support.run(m, m["meeting_id"], f"{tr['set_id']}-{m['meeting_id']}", lambda w, mid, t: extract_meeting(w, mid, llm, t, passes, verify))
            links += ls
            for st in sts:
                for k in st:
                    tot[k] += st[k]
            tot["meetings"] += 1
        (out / f"{tr['set_id']}.json").write_text(json.dumps(
            dict(set_id=tr["set_id"], method=f"multipass:{','.join(map(str, passes))}:verify={verify}",
                 links=links), indent=1))
    (out / "_stats.json").write_text(json.dumps(tot, indent=1))
    return tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--passes", default="1,2,3")
    ap.add_argument("--verify-quotes", action="store_true")
    ap.add_argument("--provider", default="anthropic")
    ap.add_argument("--model")
    a = ap.parse_args()
    passes = parse_passes(a.passes)
    llm = LLM(a.provider, a.model, temperature=0)
    tot = run_dir(a.data, a.out, llm, passes, a.verify_quotes)
    print(tot)
    if tot["p3_failed"] == tot["meetings"]:
        raise SystemExit("every pass-3 call failed - scores would be misleading")


if __name__ == "__main__":
    main()
