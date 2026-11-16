"""phase5_anchor_diag.py - diagnosis of pooled retrieval (DEV): is the loss at pool size 10 anchoring (wrong decision) or linking (the right decision is
split or merged with another set's decision)? For each question: does the anchored graph decision contain any localized gold link of the question's set
(right anchor)? How many graph decisions hold the set's main-chain links (fragments)? Do the anchor's links come from several sets (cross-set merge)?
  HF_HUB_OFFLINE=1 python eval/phase5_anchor_diag.py --size 10 --source single_pass_recap_roles_top4_pooled
"""
import argparse
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "eval"), str(ROOT / "synthgen")]
from argdecisionlineage.linking import Embedder                     # noqa: E402
from argdecisionlineage.retrieve import LineageSystem, load_corpus  # noqa: E402
from phase3_topk import topk                                        # noqa: E402
from phase5_retrieval import load_preds                             # noqa: E402
from score import gold_links                                        # noqa: E402


def near(l, g, tol=1):
    return l.meeting_id == g["meeting_id"] and min(abs(a - b) for a in l.idxs for b in g["utterance_idxs"]) <= tol


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", default="10")
    ap.add_argument("--source", default="single_pass_recap_roles_top4_pooled")
    a = ap.parse_args()
    index = json.loads((ROOT / "data/synth/pools/dev/index.json").read_text(encoding="utf-8"))
    emb = Embedder()
    tot = collections.Counter()
    for pname in [p for p in index if p.startswith(f"dev_k{a.size}_")]:
        pdir = ROOT / "data/synth/pools/dev" / pname
        ids = json.loads((pdir / "corpus.json").read_text(encoding="utf-8"))["meetings"]
        corpus = load_corpus([(pdir / "meetings" / f"{m}.txt").read_text(encoding="utf-8") for m in ids])
        priv = json.loads((pdir / "private_map.json").read_text(encoding="utf-8"))
        sets = priv["_sets"]
        inv = {(v["set_id"], v["meeting_id"]): oid for oid, v in priv.items() if oid != "_sets"}
        owner = {oid: v["set_id"] for oid, v in priv.items() if oid != "_sets"}
        if a.source.endswith("_pooled"):
            f = next((ROOT / "results/phase5/recap_k10/raw/out").glob(f"w*/single_pass_recap_roles/preds/{pname}.json"))
            links = topk(json.loads(f.read_text(encoding="utf-8"))["links"], 4)
        else:
            P = load_preds(a.source, sets)
            links = [dict(l, meeting_id=inv[(s, l["meeting_id"])]) for s in sets for l in P[s]]
        S = LineageSystem(embedder=emb).index(corpus, links)
        for s in sets:
            g = json.loads((ROOT / "data/synth/gold" / f"{s}.json").read_text(encoding="utf-8"))
            main = [dict(l, meeting_id=inv[(s, l["meeting_id"])]) for l in gold_links(g) if l["chain"] == "main"]
            holders = collections.Counter(l.decision for l in S.links for gl in main if near(l, gl))
            for q in g["questions"]:
                if q["type"] == "distractor":
                    continue
                r = S.retrieve(q["question"])
                d = r["anchor"]
                ls = S.by_dec.get(d, [])
                right = d in holders
                sets_in = collections.Counter(owner[l.meeting_id] for l in ls)
                tot["q"] += 1
                tot["right_anchor"] += right
                tot["anchor_multi_set"] += len(sets_in) > 1
                tot["anchor_foreign_majority"] += bool(sets_in) and sets_in.most_common(1)[0][0] != s
                tot["main_holders_sum"] += len(holders)
                tot["best_holder_is_anchor"] += bool(holders) and holders.most_common(1)[0][0] == d
    q = tot["q"]
    print(dict(questions=q, right_anchor=round(tot["right_anchor"] / q, 3), best_holder_is_anchor=round(tot["best_holder_is_anchor"] / q, 3),
               anchor_spans_several_sets=round(tot["anchor_multi_set"] / q, 3), anchor_mostly_other_set=round(tot["anchor_foreign_majority"] / q, 3),
               mean_graph_decisions_holding_main_chain=round(tot["main_holders_sum"] / q, 2)))


if __name__ == "__main__":
    main()
