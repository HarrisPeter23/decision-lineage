"""phase7_pairwise.py - pairwise comparison (FREEZE section 19; exploratory, LLM-judged), exactly as frozen.
Sample: 40 questions with seed 0, stratified: 20 why_changed (false premise included) + 20 full_lineage, pool size 1. The sample is drawn from GOLD
question metadata only (type, qid), before any answer is read.
Pairs: my system vs evowiki_style and vs graphiti. Each pair is shown in both orders (A/B swapped), system names hidden: 40 x 2 x 2 = 160 judgements per
judge. The judge sees the question, the gold reference answer and the two answers with explanations, and prefers A / B / tie on faithfulness and on
completeness. Judges: granite4.2:8b (Kaggle batch kernel) and gemini-3.5-flash-lite (free tier, single item, 450/day guard).
Reported: win/tie/loss (from my system's side), inter-judge agreement (Cohen's kappa), position-bias rate (verdicts that flip with the order).

  python eval/phase7_pairwise.py items  --split dev|test            -> results/<phase>/pairwise/{sample.json, items.jsonl, granite_config.json}
  python eval/phase7_pairwise.py kernel --split test --kernel adl-p7-pair   (builds the granite batch kernel; push separately)
  python eval/phase7_pairwise.py gemini --split dev|test [--limit N]  (resumable; --limit only for the DEV dry run)
  python eval/phase7_pairwise.py report --split dev|test [--granite <dir with batch_out.jsonl>]
DEV dry-run answers: results/phase5/score/{k1,evowiki_style_k1,graphiti_k1}. TEST: results/phase7/score/{lineage,evowiki_style,graphiti}@test_k1.
"""
import argparse
import json
import pathlib
import random
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "eval"), str(ROOT / "synthgen")]

SEED, N_PER_TYPE, TYPES = 0, 20, ("why_changed", "full_lineage")
BASES = ("evowiki_style", "graphiti")
CRITERIA = ("faithfulness", "completeness")
TAGS = {"dev": dict(score="results/phase5/score", mine="k1", evowiki_style="evowiki_style_k1", graphiti="graphiti_k1"),
        "test": dict(score="results/phase7/score", mine="lineage@test_k1", evowiki_style="evowiki_style@test_k1", graphiti="graphiti@test_k1")}
OUT = {"dev": ROOT / "results/phase5/pairwise_dryrun", "test": ROOT / "results/phase7/pairwise"}
LOG = "runtime/gemini_pairwise_log.jsonl"
PAIR_SYSTEM = "You compare two answers to a question about meeting decisions against a reference. Output ONLY valid JSON."


def sample(split):
    sets = json.loads((ROOT / "data/synth/split.json").read_text(encoding="utf-8"))[split]
    by = {t: [] for t in TYPES}
    for s in sorted(sets):
        for q in json.loads((ROOT / "data/synth/gold" / f"{s}.json").read_text(encoding="utf-8"))["questions"]:
            if q["type"] in by:
                by[q["type"]].append(q["qid"])
    if split == "test":
        assert all(len(by[t]) >= N_PER_TYPE for t in TYPES), {t: len(v) for t, v in by.items()}
    rng = random.Random(SEED)                     # DEV dry run only: DEV has 14 + 14, so all are taken (TEST has 23 + 22; 20 + 20 drawn as frozen)
    return {t: sorted(rng.sample(sorted(by[t]), min(N_PER_TYPE, len(by[t])))) for t in TYPES}, {t: len(v) for t, v in by.items()}


def gold_questions(split):
    sets = json.loads((ROOT / "data/synth/split.json").read_text(encoding="utf-8"))[split]
    return {q["qid"]: q for s in sets for q in json.loads((ROOT / "data/synth/gold" / f"{s}.json").read_text(encoding="utf-8"))["questions"]}


def answers(split, who):
    T = TAGS[split]
    f = ROOT / T["score"] / T[who] / "answers.jsonl"
    return {json.loads(l)["qid"]: json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()}


def show(a):
    if a is None or not a.get("parse_ok"):
        return "(no answer)", "(no explanation)"
    return a.get("answer") or "(no answer)", " ".join(s["text"] for s in a["sentences"]) or "(no explanation)"


def prompt(q, A, B):
    (aa, ae), (ba, be) = show(A), show(B)
    return f"""Compare ANSWER A and ANSWER B to the QUESTION, using the REFERENCE ANSWER as the truth.
- faithfulness: which answer states fewer wrong or unsupported facts (options, people, meetings, reasons, evidence) relative to the reference?
- completeness: which answer covers more of the key facts in the reference?
Prefer "tie" when the answers are equally good on a criterion. Do not prefer an answer for its length or its position.

QUESTION: {q['question']}
REFERENCE ANSWER: {q['answer_text']}

ANSWER A: {aa}
EXPLANATION A: {ae}

ANSWER B: {ba}
EXPLANATION B: {be}

Return JSON: {{"faithfulness": "A" | "B" | "tie", "completeness": "A" | "B" | "tie", "reason": "<one sentence>"}}"""


def build_items(split):
    S, avail = sample(split)
    G = gold_questions(split)
    ans = {w: answers(split, w) for w in ("mine",) + BASES}
    items = []
    for t in TYPES:
        for qid in S[t]:
            for b in BASES:
                for order in (0, 1):                      # order 0: A = mine; order 1: A = baseline
                    A, B = (ans["mine"].get(qid), ans[b].get(qid)) if order == 0 else (ans[b].get(qid), ans["mine"].get(qid))
                    items.append(dict(id=f"{qid}|{b}|{order}", prompt=prompt(G[qid], A, B)))
    out = OUT[split]
    out.mkdir(parents=True, exist_ok=True)
    (out / "sample.json").write_text(json.dumps(dict(seed=SEED, available=avail, sample=S), indent=1), encoding="utf-8")
    (out / "items.jsonl").write_text("\n".join(json.dumps(x) for x in items) + "\n", encoding="utf-8")
    (out / "granite_config.json").write_text(json.dumps(dict(model="granite4.2:8b", ctx=8192, think=False, num_predict=200, temperature=0, seed=7,
                                                             system=PAIR_SYSTEM), indent=1), encoding="utf-8")
    print(len(items), "items (", {t: len(v) for t, v in S.items()}, "questions; available", avail, ") ->", out)


def load_items(split):
    return [json.loads(l) for l in (OUT[split] / "items.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def gemini(split, limit=None):
    import gemini_batch as GB
    if LOG not in GB.LOGS:
        GB.LOGS.append(LOG)
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    from llm import LLM, DailyQuotaExceeded
    out = OUT[split] / "gemini_out.jsonl"
    done = {json.loads(l)["id"] for l in out.read_text(encoding="utf-8").splitlines() if l.strip()} if out.exists() else set()
    llm = LLM("gemini_free", GB.MODEL, temperature=0, cache_dir=f"runtime/cache/gemini_pairwise_{split}", log_path=LOG)
    n = 0
    for it in load_items(split):
        if it["id"] in done:
            continue
        if limit is not None and n >= limit:
            break
        if GB.used_today() >= GB.BUDGET:
            print("daily budget reached; resume after the reset")
            break
        try:
            raw = llm.complete(PAIR_SYSTEM, it["prompt"], kind="judge", temperature=0, tag=it["id"])
        except DailyQuotaExceeded:
            print("daily quota error; stopping")
            break
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(dict(id=it["id"], raw=raw[:600])) + "\n")
        n += 1
    print("gemini judgements:", len(done) + n, "of", len(load_items(split)))


def parse(raw):
    v = {}
    for c in CRITERIA:
        m = re.search(rf'"{c}"\s*:\s*"(A|B|tie)"', raw or "", re.I)
        v[c] = None if not m else ("tie" if m.group(1).lower() == "tie" else m.group(1).upper())
    return v


def mine_side(v, order):
    """Verdict from my system's side: win / tie / loss (None = unparseable)."""
    if v is None:
        return None
    if v == "tie":
        return "tie"
    mine = "A" if order == 0 else "B"
    return "win" if v == mine else "loss"


def summarise(raws):
    """raws: {item id: raw text}. Returns win/tie/loss per baseline x criterion, position-bias rate, and the per-judgement verdicts (mine side)."""
    V = {}
    for iid, raw in raws.items():
        qid, b, order = iid.split("|")
        for c, v in parse(raw).items():
            V[(qid, b, int(order), c)] = mine_side(v, int(order))
    res = {}
    for b in BASES:
        for c in CRITERIA:
            vs = [v for (q, bb, o, cc), v in V.items() if bb == b and cc == c]
            pairs = [(V[(q, bb, 0, cc)], V[(q, bb, 1, cc)]) for (q, bb, o, cc) in V if bb == b and cc == c and o == 0 and (q, bb, 1, cc) in V]
            flips = [x != y for x, y in pairs if x is not None and y is not None]
            res[f"{b}/{c}"] = dict(n=len(vs), win=vs.count("win"), tie=vs.count("tie"), loss=vs.count("loss"), unparsed=vs.count(None),
                                   position_bias=round(sum(flips) / len(flips), 3) if flips else None, n_order_pairs=len(flips))
    return res, V


def report(split, granite_dir=None):
    import gemini_batch as GB
    J = {}
    gf = OUT[split] / "gemini_out.jsonl"
    if gf.exists():
        J["gemini"] = {json.loads(l)["id"]: json.loads(l)["raw"] for l in gf.read_text(encoding="utf-8").splitlines() if l.strip()}
    if granite_dir:
        J["granite"] = {}
        for f in pathlib.Path(granite_dir).rglob("batch_out.jsonl"):
            for l in f.read_text(encoding="utf-8").splitlines():
                if l.strip():
                    x = json.loads(l)
                    J["granite"][x["id"]] = x.get("raw")
    R, V = {}, {}
    for j, raws in J.items():
        R[j], V[j] = summarise(raws)
    agree = None
    if len(V) == 2:
        common = [(V["granite"][k], V["gemini"][k]) for k in V["granite"] if k in V["gemini"] and V["granite"][k] is not None and V["gemini"][k] is not None]
        agree = dict(n=len(common), **dict(zip(("observed", "kappa"), GB.kappa(common)))) if common else None
    out = dict(split=split, n_items=len(load_items(split)), judged={j: len(r) for j, r in J.items()}, results=R, inter_judge=agree)
    (OUT[split] / "pairwise_report.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["items", "kernel", "gemini", "report"])
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    ap.add_argument("--kernel")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--granite")
    a = ap.parse_args()
    if a.limit is not None and a.split != "dev":
        raise SystemExit("--limit is only for the DEV dry run")
    if a.stage == "items":
        build_items(a.split)
    elif a.stage == "kernel":
        d = OUT[a.split]
        subprocess.run([sys.executable, "runtime/kaggle/batch/build.py", a.kernel, str(d / "granite_config.json"), str(d / "items.jsonl")], cwd=ROOT, check=True)
    elif a.stage == "gemini":
        gemini(a.split, a.limit)
    else:
        report(a.split, a.granite)
