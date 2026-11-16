"""judge_sensitivity.py - can the judges detect bad links? Plant corrupted gold links among real ones and measure detection and false alarms.

DEV sets only (no TEST text is used). Every DEV link is used once: about half stay real, about half get one corruption, stratified by role.
Corruption types (the judge prompt is otherwise the normal panel prompt):
  wrong_role     the link's role label is changed to a confusable role
  wrong_speaker  the expected speaker, and the name in the gist, are changed to another cast member
  shifted_utt    the target becomes the nearest untagged line by the SAME speaker, at least 3 lines away in the same meeting
  unsupportive   the target becomes an untagged line (8+ words) by the SAME speaker from a DIFFERENT meeting of the set
A corrupted link is a positive; detection = verdict is partial or no. strict detection = verdict is no. False alarm = a real link not judged yes.

  python eval/judge_sensitivity.py build
  python eval/judge_sensitivity.py run --judge gemini
  python eval/judge_sensitivity.py report
Real-link prompts are identical to the panel's, so the Gemini cache answers them without a new request.
"""
import argparse
import collections
import copy
import json
import math
import pathlib
import random
import re
import sys
import time

sys.path.insert(0, "eval")
sys.path.insert(0, "synthgen")
import panel                                     # noqa: E402
from llm import LLM, extract_json                # noqa: E402
from prompts import JUDGE_SYSTEM                 # noqa: E402

OUT = pathlib.Path("results/judge_sensitivity")
DATA = pathlib.Path("data/synth")
SEED = 20261103
TYPES = ["wrong_role", "wrong_speaker", "shifted_utt", "unsupportive"]
ROLE_SWAP = dict(proposal="rationale", rationale="evidence", evidence="challenge", challenge="rationale", reconsideration="resolution", resolution="proposal")


def tagged(gold, meeting):
    return {i for l in gold["chain"] if l["meeting"] == meeting for i in l["utterance_idxs"]}


def corrupt(kind, tr, gold, link, rng):
    l = copy.deepcopy(link)
    utts = tr["meetings"][l["meeting"] - 1]["utterances"]
    if kind == "wrong_role":
        l["role"] = ROLE_SWAP[l["role"]]
        return l, f"role {link['role']} -> {l['role']}"
    if kind == "wrong_speaker":
        new = rng.choice([c for c in tr["cast"] if c != l["speaker"]])
        l["gist"] = re.sub(rf"\b{l['speaker']}\b", new, l["gist"])
        old, l["speaker"] = l["speaker"], new
        return l, f"speaker {old} -> {new}"
    if kind == "shifted_utt":
        tag = tagged(gold, l["meeting"])
        a = min(l["utterance_idxs"])
        c = [i for i, u in enumerate(utts) if u["speaker"] == l["speaker"] and i not in tag and abs(i - a) >= 3 and len(u["text"].split()) >= 4]
        if not c:
            return None, ""
        i = min(c, key=lambda x: abs(x - a))
        l["utterance_idxs"] = [i]
        return l, f"target {link['utterance_idxs']} -> [{i}]"
    if kind == "unsupportive":
        c = []
        for k, m in enumerate(tr["meetings"], 1):
            if k != l["meeting"]:
                tag = tagged(gold, k)
                c += [(k, i) for i, u in enumerate(m["utterances"]) if u["speaker"] == l["speaker"] and i not in tag and len(u["text"].split()) >= 8]
        if not c:
            return None, ""
        k, i = rng.choice(c)
        l["meeting"], l["meeting_id"], l["utterance_idxs"] = k, f"m{k}", [i]
        return l, f"target moved to m{k}[{i}]"
    raise ValueError(kind)


def build():
    split = json.loads((DATA / "split.json").read_text(encoding="utf-8"))
    rng = random.Random(SEED)
    by_role = collections.defaultdict(list)
    sets = {}
    for sid in split["dev"]:
        gold = json.loads((DATA / "gold" / f"{sid}.json").read_text(encoding="utf-8"))
        tr = json.loads((DATA / "transcripts" / f"{sid}.json").read_text(encoding="utf-8"))
        sets[sid] = (tr, gold)
        for l in gold["chain"]:
            by_role[l["role"]].append((sid, l))
    items, t = [], 0
    for role in sorted(by_role):
        L = by_role[role]
        rng.shuffle(L)
        for n, (sid, l) in enumerate(L):
            tr, gold = sets[sid]
            kind, note, link = "real", "", l
            if n % 2 == 0:
                for off in range(len(TYPES)):              # if a type is impossible for this link, try the next one
                    k = TYPES[(t + off) % len(TYPES)]
                    c, why = corrupt(k, tr, gold, l, rng)
                    if c is not None:
                        kind, note, link = k, why, c
                        t = (t + off + 1) % len(TYPES)
                        break
            items.append(dict(set_id=sid, link_id=l["link_id"], role=l["role"], kind=kind, note=note, prompt=panel.link_prompt(tr, gold, link)))
    rng.shuffle(items)
    for i, it in enumerate(items):
        it["item"] = f"s{i:03d}"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "items.jsonl").write_text("\n".join(json.dumps(dict(item=i["item"], set_id=i["set_id"], link_id=i["item"], prompt=i["prompt"])) for i in items) + "\n", encoding="utf-8")
    (OUT / "key.json").write_text(json.dumps({i["item"]: {k: i[k] for k in ("set_id", "link_id", "role", "kind", "note")} for i in items}, indent=1), encoding="utf-8")
    print(len(items), dict(collections.Counter(i["kind"] for i in items)))


def run(judge):
    items = [json.loads(l) for l in (OUT / "items.jsonl").read_text(encoding="utf-8").splitlines()]
    out = OUT / f"{judge}.jsonl"
    done = {json.loads(l)["item"] for l in out.read_text(encoding="utf-8").splitlines()} if out.exists() else set()
    llm = LLM("gemini_free", "gemini-3.5-flash-lite", temperature=0, max_tokens=300, cache_dir="runtime/cache/judge_gemini", log_path="runtime/judge_gemini_log.jsonl")
    gap, last = 5.0, 0.0
    with out.open("a", encoding="utf-8") as f:
        for it in items:
            if it["item"] in done:
                continue
            wait = gap - (time.time() - last)
            if wait > 0:
                time.sleep(wait)
            last = time.time()
            try:
                r = extract_json(llm.complete(JUDGE_SYSTEM, it["prompt"], kind="judge", temperature=0))
                v, why = str(r.get("verdict", "")).lower(), str(r.get("reason", ""))[:300]
                v = v if v in ("yes", "partial", "no") else "invalid"
            except Exception as e:
                v, why = "error", type(e).__name__
            f.write(json.dumps(dict(item=it["item"], verdict=v, reason=why)) + "\n")
            f.flush()
    print("done")


def wilson(k, n):
    if not n:
        return (None, None)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))


def report():
    key = json.loads((OUT / "key.json").read_text(encoding="utf-8"))
    res = {}
    for f in sorted(OUT.glob("*.jsonl")):
        if f.name == "items.jsonl":
            continue
        V = {r["item"]: r["verdict"] for r in map(json.loads, f.read_text(encoding="utf-8").splitlines())}
        rows = {}
        for kind in ["real"] + TYPES + ["ALL_CORRUPTED"]:
            ids = [i for i in V if (key[i]["kind"] == kind or (kind == "ALL_CORRUPTED" and key[i]["kind"] != "real"))]
            c = collections.Counter(V[i] for i in ids)
            flagged = c["partial"] + c["no"]
            rows[kind] = dict(n=len(ids), yes=c["yes"], partial=c["partial"], no=c["no"], other=c["invalid"] + c["error"],
                              rate_flagged=round(flagged / len(ids), 3) if ids else None, ci95=wilson(flagged, len(ids)),
                              rate_no=round(c["no"] / len(ids), 3) if ids else None)
        res[f.stem] = rows
        print("==", f.stem)
        for k, r in rows.items():
            print(f"  {k:14} n={r['n']:3} yes={r['yes']:3} partial={r['partial']:3} no={r['no']:3} flagged={r['rate_flagged']} CI{r['ci95']} strict_no={r['rate_no']}")
    (OUT / "report.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "run", "report"])
    ap.add_argument("--judge", default="gemini")
    a = ap.parse_args()
    dict(build=build, report=report).get(a.cmd, lambda: run(a.judge))()
