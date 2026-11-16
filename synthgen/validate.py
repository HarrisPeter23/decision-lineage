"""validate.py - automatic checks, dataset stats, human-review sheet, optional LLM judge.

Usage:
  python validate.py OUT_DIR                       # check every set, print issues
  python validate.py OUT_DIR --stats               # + dataset-level diversity stats
  python validate.py OUT_DIR --review-csv rev.csv  # sheet for human verification
  python validate.py OUT_DIR --review-csv rev.csv --judge --provider anthropic --model MODEL
Exit code 1 if any ERROR is found. Use a judge model from a DIFFERENT family than the generator.
"""
import argparse
import csv
import json
import pathlib
import re
import sys
from collections import Counter

from arcs import ROLE_DEFS

ID_LEAK = re.compile(r"\b[BD]\d{1,2}\b")
WORD_LEAK = re.compile(r"\b(reversal|supersed\w*|causal chain|lineage)\b", re.I)
FILLER = re.compile(r"\b(um+|uh+|you know|i mean|like)\b", re.I)
STOP = {"with", "that", "this", "from", "into", "have", "plus", "option", "mock"}


def load_set(out, set_id):
    out = pathlib.Path(out)
    return (json.loads((out / "transcripts" / f"{set_id}.json").read_text()),
            json.loads((out / "gold" / f"{set_id}.json").read_text()))


def list_sets(out):
    return sorted(p.stem for p in (pathlib.Path(out) / "transcripts").glob("*.json"))


def _pos(l):
    return (l["meeting"], l["utterance_idxs"][0])


def _tokens(s):
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) >= 4 and w not in STOP}


def validate_set(tr, gold):
    """Return list of (level, message). level in {ERROR, WARN}."""
    iss = []
    E = lambda m: iss.append(("ERROR", m))
    W = lambda m: iss.append(("WARN", m))
    cast = set(tr["cast"])
    meetings = {m["meeting_id"]: m for m in tr["meetings"]}
    if len(meetings) != gold["meta"]["n_meetings"]:
        E("meeting count differs from gold meta")

    for mid, m in meetings.items():
        n = len(m["utterances"])
        if n < 25:
            E(f"{mid}: only {n} utterances")
        elif n < 50:
            W(f"{mid}: short meeting ({n} utterances)")
        prev = None
        for u in m["utterances"]:
            if u["speaker"] not in cast:
                E(f"{mid}[{u['idx']}]: unknown speaker {u['speaker']!r}")
            if not u["text"].strip():
                E(f"{mid}[{u['idx']}]: empty utterance")
            if ID_LEAK.search(u["text"]):
                E(f"{mid}[{u['idx']}]: event id leaked into text")
            if WORD_LEAK.search(u["text"]):
                W(f"{mid}[{u['idx']}]: meta word in text ({WORD_LEAK.search(u['text']).group(0)})")
            if prev is not None and u["text"] == prev:
                W(f"{mid}[{u['idx']}]: repeated utterance")
            prev = u["text"]

    all_links = list(gold["chain"]) + (gold["distractor"]["chain"] if gold.get("distractor") else [])
    for l in all_links:
        m = meetings.get(l["meeting_id"])
        if not m:
            E(f"{l['link_id']}: meeting {l['meeting_id']} missing")
            continue
        n = len(m["utterances"])
        if not l["utterance_idxs"] or any(not (0 <= i < n) for i in l["utterance_idxs"]):
            E(f"{l['link_id']}: utterance index out of range")
            continue
        spk = m["utterances"][l["utterance_idxs"][0]]["speaker"]
        if spk != l["speaker"]:
            E(f"{l['link_id']}: key utterance spoken by {spk}, expected {l['speaker']}")
        # explicit/implicit heuristics (warnings only)
        if l["role"] in ("resolution", "proposal") and l.get("option"):
            text = " ".join(m["utterances"][i]["text"] for i in l["utterance_idxs"])
            overlap = _tokens(text) & _tokens(l["option"])
            if l.get("implicit") and overlap:
                W(f"{l['link_id']}: marked implicit but names option tokens {sorted(overlap)[:3]}")
            if not l.get("implicit") and not overlap:
                W(f"{l['link_id']}: marked explicit but no option words found")

    # ordering rules on the main chain
    ch = gold["chain"]
    by_role = lambda r: [l for l in ch if l["role"] == r]
    props, res = by_role("proposal"), by_role("resolution")
    if props and res and min(map(_pos, res)) < min(map(_pos, props)):
        E("a resolution occurs before the first proposal")
    for l in ch:
        if l["role"] in ("evidence", "challenge", "reconsideration") and l.get("version"):
            r = [x for x in res if x["version"] == l["version"] and not x["reaffirmation"]]
            if r and _pos(l) < _pos(min(r, key=_pos)):
                E(f"{l['link_id']} ({l['role']}) occurs before the resolution of version {l['version']}")
    for r in res:
        v = r["version"]
        target = v if r["reaffirmation"] else (v - 1 if v and v > 1 else None)
        if target:
            for l in ch:
                if l["role"] in ("evidence", "challenge", "reconsideration") and l["version"] == target:
                    if _pos(l) > _pos(r):
                        E(f"{l['link_id']} occurs after the resolution {r['link_id']} it should precede")
    for l in ch:
        if l["role"] == "rationale" and l.get("version") and not l["reaffirmation"]:
            est = [r for r in res if r["version"] == l["version"] and not r["reaffirmation"]]
            if est and _pos(l) > _pos(min(est, key=_pos)):
                E(f"{l['link_id']} rationale comes after the resolution that adopts its option")

    vs = gold["versions"]
    if gold["meta"]["arc_type"] != "no_reversal" and len(vs) > 1 and vs[0]["option_text"] == vs[-1]["option_text"] \
            and len(vs) == 2:
        E("final option identical to original in a reversal arc")
    for q in gold["questions"]:
        ids = {l["link_id"] for l in all_links}
        for s in q["supporting_links"]:
            if s not in ids:
                E(f"{q['qid']}: supporting link {s} not in chain")
    return iss


def realism_stats(tr):
    utts = [u["text"] for m in tr["meetings"] for u in m["utterances"]]
    n = max(len(utts), 1)
    return dict(utts=len(utts), filler_rate=sum(bool(FILLER.search(t)) for t in utts) / n,
                cutoff_rate=sum(t.rstrip().endswith(("-", "—", "...")) for t in utts) / n,
                mean_words=sum(len(t.split()) for t in utts) / n)


def dataset_stats(out):
    ids = list_sets(out)
    arcs, doms, names, firsts, implicit, rs = Counter(), Counter(), Counter(), {}, [0, 0], []
    qtypes = Counter()
    for sid in ids:
        tr, g = load_set(out, sid)
        arcs[g["meta"]["arc_type"]] += 1
        doms[g["meta"]["domain"]] += 1
        for c in tr["cast"]:
            names[c] += 1
        firsts[sid] = set(re.findall(r"[a-z']+", " ".join(u["text"] for u in tr["meetings"][0]["utterances"]).lower()))
        for l in g["chain"]:
            if l["role"] == "resolution":
                implicit[0] += l["implicit"]
                implicit[1] += 1
        rs.append(realism_stats(tr))
        for q in g["questions"]:
            qtypes[q["type"]] += 1
    dup = 0
    keys = list(firsts)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = firsts[keys[i]], firsts[keys[j]]
            if a and b and len(a & b) / len(a | b) > 0.6:
                dup += 1
    print(f"\n== dataset stats ({len(ids)} sets) ==")
    print("arc types:", dict(arcs))
    print("domains:", dict(doms))
    print("question types:", dict(qtypes))
    print(f"implicit resolutions: {implicit[0]}/{implicit[1]}")
    print(f"most reused name: {names.most_common(1)}")
    print(f"near-duplicate set pairs (first-meeting vocab Jaccard>0.6): {dup}")
    if rs:
        print("mean utterances/set: %.0f | filler rate %.2f | cut-off rate %.2f | words/utt %.1f" % (
            sum(r["utts"] for r in rs) / len(rs), sum(r["filler_rate"] for r in rs) / len(rs),
            sum(r["cutoff_rate"] for r in rs) / len(rs), sum(r["mean_words"] for r in rs) / len(rs)))


def review_sheet(out, path, judge=None):
    rows = []
    for sid in list_sets(out):
        tr, g = load_set(out, sid)
        meetings = {m["meeting_id"]: m["utterances"] for m in tr["meetings"]}
        for l in g["chain"] + (g["distractor"]["chain"] if g.get("distractor") else []):
            utts = meetings[l["meeting_id"]]
            lo = max(0, l["utterance_idxs"][0] - 2)
            ctx = "\n".join(f"[{u['idx']}] {u['speaker']}: {u['text']}" for u in utts[lo:l["utterance_idxs"][0]])
            tgt = "\n".join(f"[{i}] {utts[i]['speaker']}: {utts[i]['text']}" for i in l["utterance_idxs"])
            auto = ""
            if judge:
                from prompts import judge_prompt, JUDGE_SYSTEM
                from llm import extract_json
                try:
                    r = extract_json(judge.complete(JUDGE_SYSTEM, judge_prompt(
                        l["role"], l["gist"], l["speaker"], ctx or "(start)", tgt), kind="judge",
                        temperature=0, tag=f"{sid}-{l['link_id']}"))
                    auto = r.get("verdict", "")
                except Exception as e:  # keep the sheet usable
                    auto = f"error: {e}"
            rows.append(dict(set_id=sid, link_id=l["link_id"], role=l["role"], meeting=l["meeting_id"],
                             speaker=l["speaker"], intended_content=l["gist"], context=ctx, target=tgt,
                             implicit=l["implicit"], auto_judge=auto, human_verdict="", notes=""))
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {path}")
    if judge:
        print("auto_judge:", dict(Counter(r["auto_judge"] for r in rows)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--review-csv")
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--provider", default="anthropic")
    ap.add_argument("--model")
    a = ap.parse_args()
    n_err = n_warn = 0
    for sid in list_sets(a.out):
        tr, g = load_set(a.out, sid)
        iss = validate_set(tr, g)
        e = [m for lv, m in iss if lv == "ERROR"]
        w = [m for lv, m in iss if lv == "WARN"]
        n_err += len(e)
        n_warn += len(w)
        if e or w:
            print(f"{sid}: {len(e)} errors, {len(w)} warnings")
            for lv, m in iss[:12]:
                print(f"   {lv}: {m}")
    print(f"\nchecked {len(list_sets(a.out))} sets: {n_err} errors, {n_warn} warnings")
    if a.stats:
        dataset_stats(a.out)
    if a.review_csv:
        judge = None
        if a.judge:
            from llm import LLM
            judge = LLM(a.provider, a.model, temperature=0)
        review_sheet(a.out, a.review_csv, judge)
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
