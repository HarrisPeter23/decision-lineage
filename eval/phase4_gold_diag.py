"""phase4_gold_diag.py - versioning on GOLD links (CHECKPOINT 4 review, item 3). DEV only.
Condition (i): gold links + gold decision assignment (main / distractor) given to the graph, so only the versioning rules are tested. This is an
evaluation condition; nothing at runtime reads gold. Condition (ii): gold links + the Phase 4 linker. Prints, per resolution link, what the graph did
next to what gold says (assemble.py: a version is created by the first resolution of each spec version; reaffirmation=True resolutions create none).
  HF_HUB_OFFLINE=1 python eval/phase4_gold_diag.py [--rules v1] [--quiet]   -> results/phase4/gold_diag_<rules>.json
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "synthgen"), str(ROOT / "eval")]
import phase4_graph as P                                                         # noqa: E402
from argdecisionlineage.graph import DecisionGraph, LexicalMatcher, Params       # noqa: E402
from argdecisionlineage.linking import EmbeddingLinker, LinkParams, links_from_predictions   # noqa: E402
from score import gold_links                                                    # noqa: E402

LP = LinkParams(link_at=0.4, gap=60)


def params(rules, **kw):
    return Params(same_at=0.4, modified_at=0.2, rules=rules, **kw)


def run_set(g, tr, rules, oracle_linking, kw):
    golds = gold_links(g)
    preds = [dict(meeting_id=l["meeting_id"], role=l["role"], utterance_idxs=l["utterance_idxs"], speaker=l["speaker"], confidence=1.0) for l in golds]
    links = links_from_predictions(preds, tr)
    key = {(l["meeting_id"], tuple(sorted(l["utterance_idxs"]))): l for l in golds}
    for l in links:
        gl = key[(l.meeting_id, tuple(l.idxs))]
        l.gold = gl
        if oracle_linking:
            l.decision = "main" if gl["chain"] == "main" else "distractor"
    p = params(rules, **kw)
    graph = DecisionGraph(p, LexicalMatcher(p)).build(links, None if oracle_linking else EmbeddingLinker(links, LP, P.EMB))
    keys, vecs = P.option_keys(g)
    anchor = "main"
    if not oracle_linking:
        ds = [l.decision for l in links if l.gold["chain"] == "main"]
        anchor = max(set(ds), key=ds.count)
    vs = graph.versions.get(anchor, [])
    pv = [P.map_option(v["option"], keys, vecs, g) for v in vs]
    gv = [v["option"] for v in g["versions"]]
    by_res = {v["resolved_by"]: v for v in vs}
    events = []
    for l in links:
        if l.role != "resolution" or l.decision != anchor:
            continue
        node = graph.g.nodes[("link", l.link_id)]
        if node.get("tentative"):
            did = "tentative (R6)"
        elif l.link_id in by_res:
            v = by_res[l.link_id]
            did = f"new version {v['n']} ({v['kind']}) -> {P.map_option(v['option'], keys, vecs, g)}"
        else:
            did = "reaffirmation (no version)"
        gl = l.gold
        events.append(dict(link=gl["link_id"], meeting=l.meeting, gold_version=gl["version"], gold_option=gl["option_key"], gold_reaffirmation=gl["reaffirmation"],
                           implicit=gl["implicit"], graph=did, text=l.text[:160]))
    return dict(set_id=g["set_id"], arc=g["meta"]["arc_type"], ok=pv == gv, pred=pv, gold=gv, events=events)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", default="v1")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    dev, G, T = P.load("data/synth")
    out = {}
    for cond, ol in (("i_gold_assignment", True), ("ii_phase4_linker", False)):
        rs = [run_set(G[s], T[s], a.rules, ol, {}) for s in dev]
        out[cond] = rs
        print(f"== {cond} ({a.rules}): exact sequences {sum(r['ok'] for r in rs)}/{len(rs)}")
        if not a.quiet:
            for r in rs:
                if not r["ok"]:
                    print(f"  {r['set_id']} {r['arc']}: pred {r['pred']} gold {r['gold']}")
                    for e in r["events"]:
                        print(f"     m{e['meeting']} {e['link']:<4} gold v{e['gold_version']} {e['gold_option']} reaff={e['gold_reaffirmation']} impl={e['implicit']} | {e['graph']} | {e['text'][:90]}")
    (ROOT / "results/phase4" / f"gold_diag_{a.rules}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
