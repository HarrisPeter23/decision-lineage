"""make_spotcheck.py - the optional human spot-check sheet (Phase 1.3 and 2.3), sized for about one hour of human work.

Rows: 24 synthetic links (6 that the panel or the agent flagged + 18 stratified by role x writer, Claude-written sets only) and 16 AMI links
(3-4 per series, all roles covered where possible). Seeded (20261103). Columns for the human: human_verdict (yes / partial / no), notes.
The sheet is the only place a human verdict can enter; a filled sheet upgrades those links to verification 'human_spotcheck'.
"""
import collections
import csv
import json
import pathlib
import random
import sys

sys.path.insert(0, "eval")
import handcheck_sample as hs        # noqa: E402

SEED = 20261103


def synthetic_rows(rng):
    L = [l for l in hs.load_links() if l["writer"].startswith("claude-")]
    ver = json.loads(pathlib.Path("data/synth/verification.json").read_text(encoding="utf-8"))
    flag = [l for l in L if ver[f"{l['set_id']}/{l['link_id']}"]["verification"] == "none"]
    rng.shuffle(flag)
    chosen = flag[:6]
    rest = [l for l in L if l not in chosen]
    rng.shuffle(rest)
    strata = collections.defaultdict(list)
    for l in rest:
        strata[(l["role"], l["writer"])].append(l)
    keys, i = sorted(strata), 0
    while len(chosen) < 24:
        k = keys[i % len(keys)]
        if strata[k]:
            chosen.append(strata[k].pop())
        i += 1
    return [dict(source="synthetic", data="data/synth", **l) for l in chosen]


def ami_rows(rng):
    out = []
    for gp in sorted(pathlib.Path("data/ami/gold").glob("*.json")):
        g = json.loads(gp.read_text(encoding="utf-8"))
        links = list(g["chain"])
        rng.shuffle(links)
        by_role = {}
        for l in links:
            by_role.setdefault(l["role"], l)
        pick = list(by_role.values())[:3]
        out += [dict(source="AMI", data="data/ami", set_id=g["set_id"], link_id=l["link_id"], role=l["role"], implicit=l.get("implicit", False),
                     writer="AMI real speech", meeting=l["meeting"], idxs=l["utterance_idxs"], speaker=l["speaker"], gist=l["gist"]) for l in pick]
    extra = [r for r in out]
    while len(out) < 16:                                           # top up with one more link from the longest chains
        g = json.loads(sorted(pathlib.Path("data/ami/gold").glob("*.json"), key=lambda p: -len(json.loads(p.read_text(encoding="utf-8"))["chain"]))[len(out) - 15].read_text(encoding="utf-8"))
        have = {(r["set_id"], r["link_id"]) for r in out}
        cand = [l for l in g["chain"] if (g["set_id"], l["link_id"]) not in have]
        l = rng.choice(cand)
        out.append(dict(source="AMI", data="data/ami", set_id=g["set_id"], link_id=l["link_id"], role=l["role"], implicit=l.get("implicit", False),
                        writer="AMI real speech", meeting=l["meeting"], idxs=l["utterance_idxs"], speaker=l["speaker"], gist=l["gist"]))
    return out


def main():
    rng = random.Random(SEED)
    rows = []
    for l in synthetic_rows(rng) + ami_rows(rng):
        tr = json.loads(pathlib.Path(l["data"], "transcripts", f"{l['set_id']}.json").read_text(encoding="utf-8"))
        m = tr["meetings"][l["meeting"] - 1]["utterances"]
        a, b = min(l["idxs"]), max(l["idxs"])
        ctx = "\n".join(f"[{j}] {m[j]['speaker']}: {m[j]['text']}" for j in range(max(0, a - 4), a))
        tgt = "\n".join(f"{'*' if j in l['idxs'] else ' '}[{j}] {m[j]['speaker']}: {m[j]['text']}" for j in range(a, min(len(m), b + 3)))
        rows.append(dict(row=len(rows) + 1, source=l["source"], set_id=l["set_id"], link_id=l["link_id"], role=l["role"] + (" (implicit)" if l["implicit"] else ""),
                         expected_speaker=l["speaker"], gist_to_check=l["gist"], context_before=ctx, marked_lines_with_star_and_after=tgt,
                         marked_line_numbers=",".join(map(str, l["idxs"])), human_verdict="", notes=""))
    p = pathlib.Path("reports/human_spotcheck.csv")
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "rows ->", p, dict(collections.Counter(r["source"] for r in rows)), dict(collections.Counter(r["role"].split()[0] for r in rows)))


if __name__ == "__main__":
    main()
