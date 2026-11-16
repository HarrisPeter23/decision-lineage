"""lineage_f1.py - the H1 primary metric adopted on 2026-11-08 (FREEZE section 14; deviation D-30): CITED-LINEAGE F1 over the headline question types.

Per headline question q (why_changed incl. false premise, evidence_to_reconsider, full_lineage) with gold lineage L = q.supporting_links (|L| >= 1):
  cited items C   = the distinct evidence items the answer cites, in order of first appearance across its sentences (an item = (meeting, utterance indexes))
  item c matches a gold link g  iff  same meeting AND min |utterance index distance| <= 1 (role ignored) - the rule used everywhere since Phase 0 (tol 1)
  precision = |{c in C : c matches some g in L}| / |C|
  recall    = |{g in L : some c in C matches g}| / |L|          (= cited lineage completeness)
  F1        = 2PR / (P + R); F1 = 0 if C is empty, if P + R = 0, or if the answer did not parse
  completeness@k = recall computed on the first k items of C only, k = k_type fixed in advance (median |L| per type over DEV gold only)
False-premise questions are scored like any other: their gold lineage is the challenge / evidence / reconsideration / reaffirming-resolution links that
explain why the decision did NOT change (assemble.py). Items without provenance (a Graphiti fact with no source episode) count as cited, non-matching.
evowiki_style: only the Wiki states the answer CITES count; each is matched through its provenance anchor (its evidence utterances). The rest of the Wiki,
which is all "retrieved", plays no role. Aggregation: mean per set, then mean over sets; uncertainty by bootstrap over sets.
  HF_HUB_OFFLINE=1 python eval/lineage_f1.py -> results/lineage_f1_dev.json   (DEV, for information; the metric does not change after this)
"""
import json
import pathlib
import random
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "eval"), str(ROOT / "synthgen")]
from score import gold_links      # noqa: E402

HEADLINE = ("why_changed", "evidence_to_reconsider", "full_lineage")
TOL = 1


def k_at_from_dev_gold():
    """k per headline type = median gold lineage length over DEV gold (gold only, fixed before TEST)."""
    dev = json.loads((ROOT / "data/synth/split.json").read_text(encoding="utf-8"))["dev"]
    by = {}
    for s in dev:
        for q in json.loads((ROOT / "data/synth/gold" / f"{s}.json").read_text(encoding="utf-8"))["questions"]:
            if q["type"] in HEADLINE and q["supporting_links"]:
                by.setdefault(q["type"], []).append(len(q["supporting_links"]))
    return {t: int(round(statistics.median(v))) for t, v in sorted(by.items())}


def match(item, g):
    return item[0] == g["meeting_id"] and min(abs(a - b) for a in item[1] for b in g["utterance_idxs"]) <= TOL


def score_question(cited, gold_lineage, k):
    C = list(dict.fromkeys((m, tuple(i)) for m, i in cited if m is not None and i))
    nprov = len({(m, tuple(i or [])) for m, i in cited if m is None or not i})    # cited items without provenance: cited, non-matching
    n_cited = len(C) + nprov
    if not n_cited or not gold_lineage:
        return dict(p=0.0, r=0.0, f1=0.0, r_at_k=0.0, n_cited=n_cited)
    p = sum(any(match(c, g) for g in gold_lineage) for c in C) / n_cited
    r = sum(any(match(c, g) for c in C) for g in gold_lineage) / len(gold_lineage)
    rk = sum(any(match(c, g) for c in C[:k]) for g in gold_lineage) / len(gold_lineage)
    return dict(p=p, r=r, f1=(2 * p * r / (p + r)) if p + r else 0.0, r_at_k=rk, n_cited=n_cited)


def set_means(rows, key):
    by = {}
    for r in rows:
        by.setdefault(r["set_id"], []).append(r[key])
    return {s: sum(v) / len(v) for s, v in by.items()}


def boot(sm, n=1000, seed=0):
    sets = sorted(sm)
    rng = random.Random(seed)
    xs = sorted(sum(sm[sets[rng.randrange(len(sets))]] for _ in sets) / len(sets) for _ in range(n))
    return [round(sum(sm.values()) / len(sm), 3), [round(xs[int(0.025 * n)], 3), round(xs[min(int(0.975 * n), n - 1)], 3)]]


def paired(a, b, n=1000, seed=0):
    sets = sorted(set(a) & set(b))
    rng = random.Random(seed)
    d = [a[s] - b[s] for s in sets]
    xs = sorted(sum(d[rng.randrange(len(d))] for _ in d) / len(d) for _ in range(n))
    return dict(diff=round(sum(d) / len(d), 3), ci=[round(xs[int(0.025 * n)], 3), round(xs[min(int(0.975 * n), n - 1)], 3)],
                p_one_sided=round(sum(x <= 0 for x in xs) / n, 4))


def inv_maps(size, split="dev"):
    index = json.loads((ROOT / f"data/synth/pools/{split}/index.json").read_text(encoding="utf-8"))
    INV = {}
    for pname in index:
        if pname.startswith(f"{split}_k{size}_"):
            priv = json.loads((ROOT / f"data/synth/pools/{split}" / pname / "private_map.json").read_text(encoding="utf-8"))
            for oid, v in priv.items():
                if oid != "_sets":
                    INV.setdefault(v["set_id"], {})[v["meeting_id"]] = oid
    return INV


def rows_for(items_by_qid, size, K, split="dev"):
    """items_by_qid: qid -> list of (meeting_id, idxs) in order. Returns per-question rows for headline questions."""
    sets = json.loads((ROOT / "data/synth/split.json").read_text(encoding="utf-8"))[split]
    INV = inv_maps(size, split)
    rows = []
    for s in sets:
        g = json.loads((ROOT / "data/synth/gold" / f"{s}.json").read_text(encoding="utf-8"))
        gl = {l["link_id"]: dict(l, meeting_id=INV[s][l["meeting_id"]]) for l in gold_links(g)}
        for q in g["questions"]:
            if q["type"] not in HEADLINE or not q["supporting_links"]:
                continue
            L = [gl[i] for i in q["supporting_links"] if i in gl]
            r = score_question(items_by_qid.get(q["qid"], []), L, K[q["type"]])
            rows.append(dict(r, qid=q["qid"], set_id=s, type=q["type"]))
    return rows


def cited_from_answers(tag):
    out = {}
    for l in (ROOT / f"results/phase5/score/{tag}/answers.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            a = json.loads(l)
            out[a["qid"]] = [(m, i) for s_ in a["sentences"] for m, i in s_["cites"]] if a["parse_ok"] else []
    return out


def main():
    K = k_at_from_dev_gold()
    print("k per type (median DEV gold lineage length):", K)
    res = dict(k_at=K, cited={}, retrieved={}, paired={})
    setf1 = {}
    for size in ("1", "10"):
        for name, tag in (("lineage", f"k{size}"), ("vector_rag", f"vector_rag_k{size}"), ("evowiki_style", f"evowiki_style_k{size}"), ("graphiti", f"graphiti_k{size}")):
            rows = rows_for(cited_from_answers(tag), size, K)
            res["cited"][f"{name}@k{size}"] = dict({m: boot(set_means(rows, m)) for m in ("f1", "p", "r", "r_at_k")}, mean_cited=round(sum(r["n_cited"] for r in rows) / len(rows), 2), n=len(rows))
            setf1[f"{name}@k{size}"] = set_means(rows, "f1")
        for b in ("evowiki_style", "graphiti", "vector_rag"):
            res["paired"][f"lineage_vs_{b}@k{size}"] = paired(setf1[f"lineage@k{size}"], setf1[f"{b}@k{size}"])
    import phase5_retrieval as PR
    from argdecisionlineage.linking import Embedder
    dev = json.loads((ROOT / "data/synth/split.json").read_text(encoding="utf-8"))["dev"]
    gold = {s: json.loads((ROOT / "data/synth/gold" / f"{s}.json").read_text(encoding="utf-8")) for s in dev}
    index = json.loads((ROOT / "data/synth/pools/dev/index.json").read_text(encoding="utf-8"))
    emb = Embedder()
    for ab in (None, "no_typing", "no_conflict_resolution", "static_graph"):
        rr = []
        for p in [p for p in index if p.startswith("dev_k1_")]:
            rr += PR.run_pool(ROOT / "data/synth/pools/dev" / p, "single_pass_recap_roles_top4", emb, gold, ablation=ab)
        items = {r["qid"]: [(it["meeting_id"], it["idxs"]) for it in r["retrieval"]["items"]] for r in rr}
        rows = rows_for(items, "1", K)
        res["retrieved"][f"lineage{'' if ab is None else ':' + ab}@k1"] = {m: boot(set_means(rows, m)) for m in ("f1", "p", "r")}
    for b in ("vector_rag", "evowiki_style", "graphiti"):
        rr = [json.loads(l) for l in (ROOT / f"results/phase6/retrieval/{b}@k1.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        items = {r["qid"]: [(it.get("meeting_id"), it.get("idxs") or []) for it in r["retrieval"]["items"]] for r in rr}
        rows = rows_for(items, "1", K)
        res["retrieved"][f"{b}@k1"] = {m: boot(set_means(rows, m)) for m in ("f1", "p", "r")}
    (ROOT / "results/lineage_f1_dev.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, v in res["cited"].items():
        print("cited", k, v)
    for k, v in res["paired"].items():
        print("paired", k, v)
    for k, v in res["retrieved"].items():
        print("retrieved", k, v)


if __name__ == "__main__":
    main()
