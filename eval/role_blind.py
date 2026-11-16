"""role_blind.py - role-blind check of the gold role labels. A judge sees the context and the target utterances only (no role, no speaker, no gist)
and must name the role. Compared with the gold role, per role, with a confusion matrix. Label VERIFICATION, not a system evaluation; gold is never edited from it.

  python eval/role_blind.py build            # all 293 links of data/synth -> results/role_blind/items.jsonl (+ key.json)
  python eval/role_blind.py run --judge gemini
  python eval/role_blind.py report
"""
import argparse
import collections
import json
import pathlib
import sys
import time

sys.path.insert(0, "eval")
sys.path.insert(0, "synthgen")
import panel                                     # noqa: E402
from arcs import ROLE_DEFS                       # noqa: E402
from llm import LLM, extract_json                # noqa: E402

OUT = pathlib.Path("results/role_blind")
DATA = pathlib.Path("data/synth")
ROLES = ["proposal", "rationale", "evidence", "challenge", "reconsideration", "resolution"]
SYSTEM = "You are a careful annotator of workplace meetings. Output ONLY valid JSON."


def prompt(tr, link):
    m = tr["meetings"][link["meeting"] - 1]["utterances"]
    first = min(link["utterance_idxs"])
    ctx = "\n".join(f"[{i}] {u['speaker']}: {u['text']}" for i, u in enumerate(m) if max(0, first - panel.CONTEXT) <= i < first) or "(start of meeting)"
    tgt = "\n".join(f"[{i}] {m[i]['speaker']}: {m[i]['text']}" for i in link["utterance_idxs"])
    roles = "\n".join(f"- {r}: {ROLE_DEFS[r]}" for r in ROLES)
    return (f"A team is deciding something across several meetings. Read the TARGET utterances in their context and decide which ONE role they play in the "
            f"decision process.\n\nRoles:\n{roles}\n\nCONTEXT (preceding lines):\n{ctx}\n\nTARGET utterances:\n{tgt}\n\n"
            f'Answer JSON: {{"role": "proposal" | "rationale" | "evidence" | "challenge" | "reconsideration" | "resolution", "reason": "one sentence"}}')


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    items, key = [], {}
    for sid, tr, gold, l in panel.iter_links(str(DATA)):
        item = f"r{len(items):03d}"
        items.append(dict(item=item, set_id=sid, link_id=item, mode="role", prompt=prompt(tr, l)))
        key[item] = dict(set_id=sid, link_id=l["link_id"], role=l["role"], implicit=bool(l.get("implicit")))
    (OUT / "items.jsonl").write_text("\n".join(json.dumps(i) for i in items) + "\n", encoding="utf-8")
    (OUT / "key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    print(len(items), "items;", dict(collections.Counter(k["role"] for k in key.values())))


def run(judge):
    items = [json.loads(l) for l in (OUT / "items.jsonl").read_text(encoding="utf-8").splitlines()]
    out = OUT / f"{judge}.jsonl"
    done = {json.loads(l)["item"] for l in out.read_text(encoding="utf-8").splitlines()} if out.exists() else set()
    llm = LLM("gemini_free", "gemini-3.5-flash-lite", temperature=0, max_tokens=300, cache_dir="runtime/cache/role_blind_gemini", log_path="runtime/role_blind_gemini_log.jsonl")
    last = 0.0
    with out.open("a", encoding="utf-8") as f:
        for it in items:
            if it["item"] in done:
                continue
            wait = 5.0 - (time.time() - last)
            if wait > 0:
                time.sleep(wait)
            last = time.time()
            try:
                r = extract_json(llm.complete(SYSTEM, it["prompt"], kind="judge", temperature=0))
                v, why = str(r.get("role", "")).lower().strip(), str(r.get("reason", ""))[:200]
                v = v if v in ROLES else "invalid"
            except Exception as e:
                v, why = "error", type(e).__name__
            f.write(json.dumps(dict(item=it["item"], verdict=v, reason=why)) + "\n")
            f.flush()
    print("done")


def report():
    key = json.loads((OUT / "key.json").read_text(encoding="utf-8"))
    summary = {}
    for f in sorted(OUT.glob("*.jsonl")):
        if f.name == "items.jsonl":
            continue
        V = {r["item"]: r["verdict"] for r in map(json.loads, f.read_text(encoding="utf-8").splitlines())}
        n = len(V)
        ok = sum(V[i] == key[i]["role"] for i in V)
        print(f"== {f.stem}: n={n} role accuracy {ok}/{n} = {ok / n:.3f}; invalid/error {sum(v not in ROLES for v in V.values())}")
        per = {}
        for r in ROLES:
            ids = [i for i in V if key[i]["role"] == r]
            c = sum(V[i] == r for i in ids)
            per[r] = (c, len(ids))
            print(f"   gold {r:16} {c:3}/{len(ids):3} = {c / max(1, len(ids)):.2f}")
        imp = [i for i in V if key[i]["implicit"]]
        print(f"   implicit resolutions {sum(V[i] == 'resolution' for i in imp)}/{len(imp)}")
        conf = collections.Counter((key[i]["role"], V[i]) for i in V if V[i] != key[i]["role"])
        print("   top confusions (gold -> judge):", conf.most_common(8))
        summary[f.stem] = dict(n=n, accuracy=round(ok / n, 3), per_role=per, confusions={f"{a}->{b}": c for (a, b), c in conf.items()})
    (OUT / "report.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "run", "report"])
    ap.add_argument("--judge", default="gemini")
    a = ap.parse_args()
    dict(build=build, report=report).get(a.cmd, lambda: run(a.judge))()
