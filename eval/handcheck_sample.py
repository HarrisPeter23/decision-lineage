"""handcheck_sample.py - draw the stratified link sample that the agent hand-checks (Phase 1.3), and print it for reading.

Sample = every link any judge called partial/no + 10 implicit resolutions + a seeded stratified fill over (role, writer) up to the target.
Labelled "agent-checked, not human". Seed 20261102.
  python eval/handcheck_sample.py draw --n 66 --out results/panel/handcheck_sample.json
  python eval/handcheck_sample.py show results/panel/handcheck_sample.json 0 22
"""
import collections
import json
import pathlib
import random
import sys

DATA = pathlib.Path("data/synth")
PANEL = [pathlib.Path("results/panel/gemini_synth.jsonl"), pathlib.Path("results/panel/granite_synth.jsonl")]


def load_links():
    prov = json.loads((DATA / "provenance.json").read_text(encoding="utf-8"))
    L = []
    for gp in sorted((DATA / "gold").glob("*.json")):
        g = json.loads(gp.read_text(encoding="utf-8"))
        for l in g["chain"]:
            L.append(dict(set_id=g["set_id"], link_id=l["link_id"], role=l["role"], implicit=bool(l.get("implicit")), writer=prov[g["set_id"]]["writer"][:18],
                          arc=g["meta"]["arc_type"], meeting=l["meeting"], idxs=l["utterance_idxs"], speaker=l["speaker"], gist=l["gist"]))
    return L


def draw(n, out):
    rng = random.Random(20261102)
    L = load_links()
    key = lambda l: (l["set_id"], l["link_id"])
    flagged = set()
    for p in PANEL:
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                if r["verdict"] != "yes":
                    flagged.add((r["set_id"], r["link_id"]))
    chosen = [l for l in L if key(l) in flagged]
    imp = [l for l in L if l["implicit"] and key(l) not in flagged]
    rng.shuffle(imp)
    chosen += imp[:10]
    rest = [l for l in L if l not in chosen]
    rng.shuffle(rest)
    strata = collections.defaultdict(list)
    for l in rest:
        strata[(l["role"], l["writer"])].append(l)
    keys = sorted(strata)
    i = 0
    while len(chosen) < n and any(strata.values()):
        k = keys[i % len(keys)]
        if strata[k]:
            chosen.append(strata[k].pop())
        i += 1
    chosen.sort(key=key)
    pathlib.Path(out).write_text(json.dumps(chosen, indent=1), encoding="utf-8")
    print(len(chosen), "links;", collections.Counter(l["role"] for l in chosen), collections.Counter(l["writer"] for l in chosen),
          "implicit", sum(l["implicit"] for l in chosen), "flagged", sum(key(l) in flagged for l in chosen))


def show(path, a, b):
    S = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))[a:b]
    for n, l in enumerate(S, a):
        tr = json.loads((DATA / "transcripts" / f"{l['set_id']}.json").read_text(encoding="utf-8"))
        m = tr["meetings"][l["meeting"] - 1]["utterances"]
        i0 = min(l["idxs"])
        prev = " | ".join(f"{m[i]['speaker']}: {m[i]['text'][:90]}" for i in range(max(0, i0 - 2), i0))
        tgt = " || ".join(f"[{i}] {m[i]['speaker']}: {m[i]['text'][:260]}" for i in l["idxs"])
        print(f"#{n} {l['set_id']} {l['link_id']} {l['role']}{' IMPLICIT' if l['implicit'] else ''} spk={l['speaker']} ({l['writer']})")
        print(f"  gist: {l['gist'][:210]}")
        print(f"  prev: {prev}")
        print(f"  TGT : {tgt}")


if __name__ == "__main__":
    if sys.argv[1] == "draw":
        draw(int(sys.argv[sys.argv.index("--n") + 1]), sys.argv[sys.argv.index("--out") + 1])
    else:
        show(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
