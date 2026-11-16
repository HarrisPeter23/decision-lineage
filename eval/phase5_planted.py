"""phase5_planted.py - planted-negative validation of the Phase 5 judges (FREEZE section 6; phase5.md section 0b(c)). DEV only. seed 0.

Sentences (checked by NLI citation recall): real generated sentences, unaltered (real) or corrupted six ways:
  number      a number in the sentence replaced by a different number
  speaker     the cited speaker's name replaced by another cast member of the same set
  outcome     the decisive verb negated or reversed (agreed -> rejected, decided to -> decided not to, switched to -> refused to switch to, ...)
  role        the argumentative act changed (proposed -> objected to, reported -> doubted, challenged -> supported, ...)
  citation    the sentence kept, its citations replaced by items retrieved for a question of ANOTHER set
  added       an unsupported invented clause appended
Answers (checked by the granite rubric judge): the gold reference answer itself (real; should be judged correct), or the reference corrupted:
  option swap (another option of the set), speaker swap, meeting number shift, change negation ("it did not change" <-> "it changed").
  python eval/phase5_planted.py --tag k1 --stage build     -> results/phase5/planted/{sentences.jsonl, answers_judge_items.jsonl}
  python eval/phase5_planted.py --tag k1 --stage score --judge <dir>   (NLI part runs locally; judge part needs the granite kernel output)
"""
import argparse
import json
import math
import pathlib
import random
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "eval")]
from argdecisionlineage.faithfulness import NLIChecker, premise   # noqa: E402

AT = 0.5
OUTCOME = [(r"\bagreed to\b", "refused to"), (r"\bagreed\b", "rejected it"), (r"\bdecided to\b", "decided not to"), (r"\bapproved\b", "rejected"),
           (r"\bswitch(ed|ing)? to\b", "refused to switch to"), (r"\bchose\b", "ruled out"), (r"\bkept\b", "dropped"), (r"\bconfirmed\b", "cancelled"),
           (r"\bwent with\b", "turned down"), (r"\bsettled on\b", "rejected")]
ROLE = [(r"\bproposed\b", "objected to"), (r"\bsuggested\b", "opposed"), (r"\breported\b", "doubted"), (r"\bchallenged\b", "endorsed"),
        (r"\bobjected\b", "agreed"), (r"\bargued\b", "denied"), (r"\braised concerns?\b", "expressed full support"), (r"\bquestioned\b", "praised"),
        (r"\breopen(ed)?\b", "close"), (r"\bsupported\b", "opposed")]
ADDED = [", and the board signed off on an extra 40,000 euros for it", ", after the CFO vetoed every alternative", ", which the external auditor had demanded in writing",
         ", and the decision was announced to all customers the same day", ", because a competitor had just been fined for the same thing"]
NUMWORD = {"two": "seven", "three": "nine", "four": "eleven", "five": "twelve", "six": "fifteen", "ten": "twenty-three", "twelve": "thirty", "twenty": "eighty"}


def corrupt(kind, s, rng, cast, other_items):
    t = s["text"]
    if kind == "number":
        m = list(re.finditer(r"\d[\d,.]*", t))
        if m:
            x = m[0]
            return t[:x.start()] + str(int(re.sub(r"\D", "", x.group()) or 1) * 3 + 7) + t[x.end():], None
        for w, r in NUMWORD.items():
            if re.search(rf"\b{w}\b", t, re.I):
                return re.sub(rf"\b{w}\b", r, t, count=1, flags=re.I), None
        return None
    if kind == "speaker":
        names = [c for c in cast if re.search(rf"\b{re.escape(c)}\b", t)]
        if not names:
            return None
        n = names[0]
        others = [c for c in cast if c not in names]
        return (re.sub(rf"\b{re.escape(n)}\b", rng.choice(others), t, count=1), None) if others else None
    if kind in ("outcome", "role"):
        for pat, rep in (OUTCOME if kind == "outcome" else ROLE):
            if re.search(pat, t, re.I):
                return re.sub(pat, rep, t, count=1, flags=re.I), None
        return None
    if kind == "citation":
        return (t, [rng.choice(other_items)]) if other_items else None
    if kind == "added":
        return t.rstrip(". ") + rng.choice(ADDED) + ".", None


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(k / n, 3), [round(max(0, c - h), 3), round(min(1, c + h), 3)], n]


def build(a):
    rng = random.Random(0)
    A = [json.loads(l) for l in (ROOT / f"results/phase5/score/{a.tag}/answers.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    R = {json.loads(l)["qid"]: json.loads(l) for l in (ROOT / f"results/phase5/retrieval_rf1/single_pass_recap_roles_top4@{a.tag}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    gold = {}
    pool = []
    for x in A:
        items = {(it["meeting_id"], tuple(it["idxs"])): it for it in R[x["qid"]]["retrieval"]["items"]}
        for s in x["sentences"]:
            cites = [items[(m, tuple(i))] for m, i in s["cites"] if (m, tuple(i)) in items]
            if cites:
                pool.append(dict(qid=x["qid"], set_id=x["set_id"], text=s["text"], cites=cites))
    rng.shuffle(pool)
    out, used = [], set()
    for kind in ("number", "speaker", "outcome", "role", "citation", "added"):
        k = 0
        for s in pool:
            if k >= 10:
                break
            if s["set_id"] not in gold:
                gold[s["set_id"]] = json.loads((ROOT / "data/synth/gold" / f"{s['set_id']}.json").read_text(encoding="utf-8"))
            cast = [c["name"] for c in gold[s["set_id"]]["cast"]]
            other = [it for q, r in R.items() if r["set_id"] != s["set_id"] for it in r["retrieval"]["items"] if it.get("role")]
            c = corrupt(kind, s, rng, cast, other)
            if c and (s["qid"], s["text"]) not in used:
                used.add((s["qid"], s["text"]))
                out.append(dict(kind=kind, qid=s["qid"], original=s["text"], text=c[0], cites=c[1] or s["cites"]))
                k += 1
    reals = [s for s in pool if (s["qid"], s["text"]) not in used][:60]
    out += [dict(kind="real", qid=s["qid"], original=s["text"], text=s["text"], cites=s["cites"]) for s in reals]
    d = ROOT / "results/phase5/planted"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"sentences_{a.tag}.jsonl").write_text("\n".join(json.dumps(x) for x in out) + "\n", encoding="utf-8")
    print({k: sum(x["kind"] == k for x in out) for k in ("number", "speaker", "outcome", "role", "citation", "added", "real")})


def build_answers(a):
    """Reference answers (real) and corrupted references for the granite rubric judge. Non-exact question types only (the ones the judge grades)."""
    sys.path.insert(0, str(ROOT / "eval"))
    from phase5_score import judge_prompt
    rng = random.Random(1)
    dev = json.loads((ROOT / "data/synth/split.json").read_text(encoding="utf-8"))["dev"]
    qs = []
    for s_ in dev:
        g = json.loads((ROOT / "data/synth/gold" / f"{s_}.json").read_text(encoding="utf-8"))
        qs += [(g, q) for q in g["questions"] if q["type"] not in ("as_of", "lookup_final", "who_proposed")]
    rng.shuffle(qs)
    items, meta = [], []
    for n, (g, q) in enumerate(qs[:120]):
        t = q["answer_text"]
        kind = "real" if n % 2 == 0 else ["option", "speaker", "meeting", "change"][(n // 2) % 4]
        if kind == "option":
            opts = list(g["options"].values())
            hit = [o for o in opts if o in t]
            others = [o for o in opts if o not in hit] or ([g["distractor"]["option"]] if g.get("distractor") else [])
            t = t.replace(hit[0], rng.choice(others)) if hit and others else None
        elif kind == "speaker":
            names = [c["name"] for c in g["cast"] if re.search(rf"\b{c['name']}\b", t)]
            others = [c["name"] for c in g["cast"] if c["name"] not in names]
            t = re.sub(rf"\b{names[0]}\b", rng.choice(others), t) if names and others else None
        elif kind == "meeting":
            t = re.sub(r"meeting (\d)", lambda m: f"meeting {int(m.group(1)) % 4 + 1}", t) if re.search(r"meeting \d", t) else None
        elif kind == "change":
            t = ("It did not change; the original decision stayed in place." if g["changes"] else "The decision was reversed and replaced by a different option.")
        if t is None:
            continue
        iid = f"planted@{q['qid']}@{kind}"
        items.append(dict(id=iid, prompt=judge_prompt(q, t, [])))
        meta.append(dict(id=iid, kind=kind, qid=q["qid"], type=q["type"]))
    d = ROOT / "results/phase5/planted"
    d.mkdir(parents=True, exist_ok=True)
    (d / "answers_judge_items.jsonl").write_text("\n".join(json.dumps(x) for x in items) + "\n", encoding="utf-8")
    (d / "answers_meta.jsonl").write_text("\n".join(json.dumps(x) for x in meta) + "\n", encoding="utf-8")
    print({k: sum(m["kind"] == k for m in meta) for k in ("real", "option", "speaker", "meeting", "change")})


def score(a):
    d = ROOT / "results/phase5/planted"
    S = [json.loads(l) for l in (d / f"sentences_{a.tag}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    nli = NLIChecker()
    res = {}
    for x in S:
        p = nli.probs([(premise(x["cites"]), x["text"])])[0]
        x["flagged"] = p < AT
        x["p"] = round(p, 4)
    for k in ("number", "speaker", "outcome", "role", "citation", "added", "real"):
        xs = [x for x in S if x["kind"] == k]
        res[k] = wilson(sum(x["flagged"] for x in xs), len(xs))
    xs = [x for x in S if x["kind"] != "real"]
    res["all_corrupted"] = wilson(sum(x["flagged"] for x in xs), len(xs))
    (d / f"sentences_{a.tag}_nli.json").write_text(json.dumps(dict(rates=res, items=S), indent=1), encoding="utf-8")
    print(json.dumps(res))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="k1")
    ap.add_argument("--stage", choices=["build", "score"], required=True)
    a = ap.parse_args()
    if a.stage == "build":
        build(a)
        build_answers(a)
    else:
        score(a)
