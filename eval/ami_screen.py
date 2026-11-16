"""ami_screen.py - rule-based screen of AMI series for decision changes (Phase 2.2, step 1). CPU only, no model.

For every series it pairs each DECISIONS sentence of a later meeting with each of an earlier meeting (same series) by shared content words (idf weighted),
labels the pair by polarity cues ('will have' vs 'will not have', 'instead', 'only', 'no longer'), and attaches evidence lines from both transcripts
(utterance index = zero-based position among the utterance lines). Output: data/ami/candidates.csv and data/ami/series_ranking.csv.
The SYSTEM_MODEL pass (Kaggle) then classifies the top pairs; the final choice of series is made from both.
  python eval/ami_screen.py
"""
import collections
import csv
import json
import math
import pathlib
import re

SER = pathlib.Path("data/ami/series")
STOP = set("""a an the of to in on for and or with be is are was were will would shall should can could must may might this that these those it its as at by from
remote control team group they their them we our us there than then also not no only have has had having use used using make made into out up about which who whom what when
where how more most some any each other another such very just""".split())
NEG = re.compile(r"\b(not|no longer|won't|cannot|can't|without|instead of|instead|rather than|dropped|drop|scrapped|removed|never|no)\b", re.I)
SWITCH = re.compile(r"\b(instead|rather than|no longer|changed|change|switch|replace|replaced|dropped|scrapped|abandon)\w*\b", re.I)


def toks(s):
    out = []
    for w in re.findall(r"[a-z][a-z\-']+", s.lower()):
        w = w.strip("'-")
        if w in STOP or len(w) < 3:
            continue
        if w.endswith("ies") and len(w) > 4:
            w = w[:-3] + "y"
        elif w.endswith("s") and not w.endswith("ss") and len(w) > 3:
            w = w[:-1]
        out.append(w)
    return out


def load_lines(series, obs):
    L = (SER / series / f"{obs}.txt").read_text(encoding="utf-8").split("\n")
    body = L[L.index("") + 1:]
    return [l for l in body if l.strip()]


def evidence(lines, terms, k=2):
    sc = []
    for i, l in enumerate(lines):
        t = set(toks(l.partition(": ")[2]))
        n = len(t & terms)
        if n:
            sc.append((n, -len(l), i))
    sc.sort(reverse=True)
    return [(i, lines[i][:170]) for _, _, i in sorted(sc[:k], key=lambda x: x[2])]


def main():
    decs, allsent = {}, []
    for f in sorted(SER.glob("*/decisions.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        decs[f.parent.name] = {obs: (x or {}).get("decisions", []) for obs, x in d.items()}
        for x in decs[f.parent.name].values():
            allsent += x
    df = collections.Counter(t for s in allsent for t in set(toks(s)))
    N = len(allsent)
    idf = {t: math.log((N + 1) / (c + 1)) + 1 for t, c in df.items()}
    rows, rank = [], collections.defaultdict(lambda: dict(contradiction=0, reaffirmation=0, related=0, switch=0))
    for series, byobs in decs.items():
        obs = sorted(byobs)
        cache = {o: load_lines(series, o) for o in obs}
        for j, later in enumerate(obs):
            for early in obs[:j]:
                for dl in byobs[later]:
                    tl = set(toks(dl))
                    for de in byobs[early]:
                        te = set(toks(de))
                        shared = tl & te
                        if not shared:
                            continue
                        w = sum(idf[t] for t in shared)
                        score = w / (sum(idf[t] for t in tl | te) or 1)
                        if score < 0.12 or w < 1.5:
                            continue
                        pe, pl = bool(NEG.search(de)), bool(NEG.search(dl))
                        kind = "contradiction" if pe != pl else ("reaffirmation" if score >= 0.5 else "related")
                        sw = bool(SWITCH.search(dl))
                        ev_e, ev_l = evidence(cache[early], shared), evidence(cache[later], shared)
                        rows.append(dict(series=series, earlier=early, earlier_decision=de, later=later, later_decision=dl, shared_terms=" ".join(sorted(shared)),
                                         score=round(score, 3), polarity_change=int(pe != pl), switch_cue=int(sw), type_guess=kind,
                                         evidence_earlier=" || ".join(f"[{i}] {t}" for i, t in ev_e), evidence_later=" || ".join(f"[{i}] {t}" for i, t in ev_l)))
                        rank[series][kind] += 1
                        rank[series]["switch"] += int(sw)
    rows.sort(key=lambda r: (-(r["polarity_change"] + r["switch_cue"]), -r["score"]))
    with open("data/ami/candidates.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    R = sorted(rank.items(), key=lambda kv: -(2 * kv[1]["contradiction"] + kv[1]["switch"] + 0.2 * kv[1]["reaffirmation"]))
    with open("data/ami/series_ranking.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["series", "contradiction_pairs", "switch_cue_pairs", "reaffirmation_pairs", "related_pairs"])
        for s, c in R:
            w.writerow([s, c["contradiction"], c["switch"], c["reaffirmation"], c["related"]])
    print(len(rows), "candidate pairs over", len(decs), "series;", dict(collections.Counter(r["type_guess"] for r in rows)))
    print("series with >=1 polarity contradiction:", sum(1 for s, c in rank.items() if c["contradiction"]), "| >=3:", sum(1 for s, c in rank.items() if c["contradiction"] >= 3))
    print("top series:", [(s, c["contradiction"], c["switch"]) for s, c in R[:10]])


if __name__ == "__main__":
    main()
