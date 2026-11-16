"""phase5_retrieval.py - harness for Layer 4 on DEV pooled corpora: lineage completeness of the retrieved subgraph (pre-declared, reports/phase5.md section 0),
per question type and pooled over headline types, for each extraction candidate; P3-A selection at pool size 1. Also writes the retrieved subgraphs for Layer 5.
The harness (not the system) reads private_map.json to place per-meeting extraction outputs on opaque meeting ids and to map gold links for scoring.
  HF_HUB_OFFLINE=1 python eval/phase5_retrieval.py [--sizes 1] [--sources single_pass,single_pass_top4,single_pass_recap_roles_top4]
"""
import argparse
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "synthgen"), str(ROOT / "eval")]
from argdecisionlineage.linking import Embedder                       # noqa: E402
from argdecisionlineage.retrieve import LineageSystem, load_corpus    # noqa: E402
from phase3_topk import div_topk, topk                                # noqa: E402
from score import gold_links                                          # noqa: E402

HEADLINE = ("why_changed", "evidence_to_reconsider", "full_lineage")
TYPE2INTENT = dict(lookup_final="final", distractor="final", as_of="as_of", decisions_about="decisions_about", change_over_time="change_over_time",
                   why_changed="why_changed", who_proposed="who_proposed", evidence_to_reconsider="evidence_to_reconsider",
                   meetings_contributed="meetings_contributed", full_lineage="full_lineage")
PRED = dict(single_pass=("results/phase3/main/merged/single_pass/preds", None), single_pass_top4=("results/phase3/main/merged/single_pass/preds", 4),
            single_pass_recap_roles_top4=("results/phase3/recap/merged/single_pass_recap_roles/preds", 4),
            recap_roles_div4=("results/phase3/recap/merged/single_pass_recap_roles/preds", "div4"),                 # P3-F
            recap_args_div4=("results/phase3/p3f/merged/single_pass_recap_args/preds", "div4"),
            recap_args_v2_div4=("results/phase3/p3f/merged/single_pass_recap_args_v2/preds", "div4"))                     # P3-F


def load_preds(src, sets):
    d, k = PRED[src]
    out = {}
    for s in sets:
        ls = json.loads((ROOT / d / f"{s}.json").read_text(encoding="utf-8"))["links"]
        out[s] = div_topk(ls, 4) if k == "div4" else (topk(ls, k) if k else ls)
    return out


def completeness(items, sup, tol=1):
    if not sup:
        return None
    hit = 0
    for g in sup:
        hit += any(it["meeting_id"] == g["meeting_id"] and min(abs(a - b) for a in it["idxs"] for b in g["utterance_idxs"]) <= tol for it in items)
    return hit / len(sup)


def run_pool(pdir, src, emb, gold, fallback=True, link_params=None, ablation=None):
    corpus_ids = json.loads((pdir / "corpus.json").read_text(encoding="utf-8"))["meetings"]
    corpus = load_corpus([(pdir / "meetings" / f"{m}.txt").read_text(encoding="utf-8") for m in corpus_ids])
    priv = json.loads((pdir / "private_map.json").read_text(encoding="utf-8"))
    sets = priv["_sets"]
    inv = {(v["set_id"], v["meeting_id"]): oid for oid, v in priv.items() if oid != "_sets"}
    if src.endswith("_pooled"):                     # re-extracted on the pooled order: links already carry the corpus's opaque meeting ids
        f = next((ROOT / "results/phase5/recap_k10/raw/out").glob(f"w*/single_pass_recap_roles/preds/{pdir.name}.json"))
        links = topk(json.loads(f.read_text(encoding="utf-8"))["links"], 4)
    else:
        preds = load_preds(src, sets)
        links = [dict(l, meeting_id=inv[(s, l["meeting_id"])]) for s in sets for l in preds[s]]
    sysm = LineageSystem(embedder=emb, fallback=fallback, link_params=link_params, ablation=ablation).index(corpus, links)
    rows = []
    for s in sets:
        g = gold[s]
        gl = {l["link_id"]: dict(l, meeting_id=inv[(s, l["meeting_id"])]) for l in gold_links(g)}
        for q in g["questions"]:
            r = sysm.retrieve(q["question"])
            sup = [gl[i] for i in q["supporting_links"] if i in gl]
            rows.append(dict(qid=q["qid"], set_id=s, type=q["type"], false_premise=bool(q["answer_facts"].get("false_premise")), intent=r["intent"],
                             route_ok=r["intent"] == TYPE2INTENT[q["type"]] or (q["type"] == "who_proposed" and r["intent"] == "who_proposed_option"), completeness=completeness(r["items"], sup), n_items=len(r["items"]),
                             fallback=r["fallback"], anchor_score=r["anchor_score"], retrieval=r))
    return rows


def boot(rows, sets, key=lambda r: True, n=1000, seed=0):
    by = {}
    for r in rows:
        if key(r) and r["completeness"] is not None:
            by.setdefault(r["set_id"], []).append(r["completeness"])
    sets = [s for s in sets if s in by]
    mean = lambda ss: (lambda xs: sum(xs) / len(xs) if xs else 0.0)([x for s in ss for x in by[s]])
    rng = random.Random(seed)
    bs = sorted(mean([sets[rng.randrange(len(sets))] for _ in sets]) for _ in range(n))
    return round(mean(sets), 3), [round(bs[int(0.025 * n)], 3), round(bs[min(int(0.975 * n), n - 1)], 3)], sum(len(by[s]) for s in sets)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="1")
    ap.add_argument("--sources", default="single_pass,single_pass_top4,single_pass_recap_roles_top4")
    ap.add_argument("--out", default="results/phase5/retrieval_rf1")
    a = ap.parse_args()
    split = json.loads((ROOT / "data/synth/split.json").read_text(encoding="utf-8"))
    dev = split["dev"]
    gold = {s: json.loads((ROOT / "data/synth/gold" / f"{s}.json").read_text(encoding="utf-8")) for s in dev}
    index = json.loads((ROOT / "data/synth/pools/dev/index.json").read_text(encoding="utf-8"))
    emb = Embedder()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    summary = {}
    for size in a.sizes.split(","):
        pools = [p for p in index if p.startswith(f"dev_k{size}_")]
        for src in a.sources.split(","):
            rows = []
            for p in pools:
                assert all(s in dev for s in index[p]["sets"])
                rows += run_pool(ROOT / "data/synth/pools/dev" / p, src, emb, gold)
            tag = f"{src}@k{size}"
            (out / f"{tag}.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
            S = dict(headline=boot(rows, dev, lambda r: r["type"] in HEADLINE), all=boot(rows, dev),
                     route_acc=round(sum(r["route_ok"] for r in rows) / len(rows), 3), fallback_rate=round(sum(r["fallback"] for r in rows) / len(rows), 3),
                     mean_items=round(sum(r["n_items"] for r in rows) / len(rows), 2))
            for t in sorted({r["type"] for r in rows}):
                S[t] = boot(rows, dev, lambda r, t=t: r["type"] == t)
            S["why_changed_false_premise"] = boot(rows, dev, lambda r: r["type"] == "why_changed" and r["false_premise"])
            summary[tag] = S
            print(tag, "headline", S["headline"], "all", S["all"], "route", S["route_acc"], "fallback", S["fallback_rate"], "items", S["mean_items"])
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
