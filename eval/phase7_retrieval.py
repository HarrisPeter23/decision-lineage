"""phase7_retrieval.py - Phase 7 harness (FREEZE): evidence selection for every system on TEST pools (sizes 1 and 10) and the shared AMI pools, in the
Phase 5 row format, with the frozen system and baseline code unchanged. The harness alone reads gold and private maps, for scoring.
  HF_HUB_OFFLINE=1 python eval/phase7_retrieval.py --system lineage|no_typing|no_conflict_resolution|static_graph|vector_rag|evowiki_style|graphiti --scope test_k1|test_k10|ami
  -> results/phase7/retrieval/<system>@<scope>.jsonl
Inputs: my extraction  results/phase7/extract/preds/<corpus>.json (kernel adl-p7-extract; top-4 applied here, frozen rule);
        evowiki_style  results/phase7/evowiki/<corpus>/wiki.json;  graphiti  results/phase7/graphiti/graphiti_out/{search,episodes}_<corpus>.json.
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "eval"), str(ROOT / "synthgen")]
from argdecisionlineage.linking import Embedder                      # noqa: E402
from argdecisionlineage.retrieve import LineageSystem, load_corpus   # noqa: E402
from baselines.evowiki_style import evowiki as E                     # noqa: E402
from baselines.vector_rag.vector_rag import VectorRAG                # noqa: E402
from phase3_topk import topk                                         # noqa: E402
from phase5_retrieval import completeness                            # noqa: E402
from phase6_retrieval import graphiti_items                          # noqa: E402
from score import gold_links                                         # noqa: E402

SCOPES = {"test_k1": ("data/synth/pools/test", "test_k1_*", "data/synth/gold"), "test_k10": ("data/synth/pools/test", "test_k10_*", "data/synth/gold"),
          "ami": ("data/ami/pools", "ami_*", "data/ami/gold")}
ABL = {"lineage": None, "no_typing": "no_typing", "no_conflict_resolution": "no_conflict_resolution", "static_graph": "static_graph"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", required=True)
    ap.add_argument("--scope", required=True, choices=list(SCOPES))
    a = ap.parse_args()
    root, pat, gdir = SCOPES[a.scope]
    emb = Embedder()
    out = ROOT / "results/phase7/retrieval"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for pdir in sorted((ROOT / root).glob(pat)):
        ids = json.loads((pdir / "corpus.json").read_text(encoding="utf-8"))["meetings"]
        corpus = load_corpus([(pdir / "meetings" / f"{m}.txt").read_text(encoding="utf-8") for m in ids])
        priv = json.loads((pdir / "private_map.json").read_text(encoding="utf-8"))
        inv = {(v["set_id"], v["meeting_id"]): oid for oid, v in priv.items() if oid != "_sets"}
        if a.system in ABL:
            links = topk(json.loads((ROOT / "results/phase7/extract/preds" / f"{pdir.name}.json").read_text(encoding="utf-8"))["links"], 4)
            sysm = LineageSystem(embedder=emb, ablation=ABL[a.system]).index(corpus, links)
            get = sysm.retrieve
        elif a.system == "vector_rag":
            get = VectorRAG(embedder=emb).index(corpus).retrieve
        elif a.system == "evowiki_style":
            wiki = E.Wiki.from_json(json.loads((ROOT / "results/phase7/evowiki" / pdir.name / "wiki.json").read_text(encoding="utf-8")))
            get = lambda q, wiki=wiki, corpus=corpus: E.read(wiki, corpus, q)
        else:
            G = ROOT / "results/phase7/graphiti/graphiti_out"
            S = {x["qid"]: x for x in json.loads((G / f"search_{pdir.name}.json").read_text(encoding="utf-8"))}
            u2m = {e["episode_uuid"]: e["meeting_id"] for e in json.loads((G / f"episodes_{pdir.name}.json").read_text(encoding="utf-8")) if e.get("ok")}
            for x in S.values():
                for f in x["facts"]:
                    f["episode_names"] = [u2m[u] for u in f["episodes"] if u in u2m]
            get = lambda q, S=S, corpus=corpus: None
        for s in priv["_sets"]:
            g = json.loads((ROOT / gdir / f"{s}.json").read_text(encoding="utf-8"))
            gl = {l["link_id"]: dict(l, meeting_id=inv[(s, l["meeting_id"])]) for l in gold_links(g)}
            for q in g["questions"]:
                if a.system == "graphiti":
                    x = S.get(q["qid"], dict(facts=[]))
                    r = dict(system="graphiti", intent=None, items=graphiti_items(x["facts"], corpus, emb), versions=[], meetings=list(range(1, len(corpus["meetings"]) + 1)),
                             search_error=x.get("error"), header="The evidence below are facts from a temporal knowledge graph built from the meetings, with their validity.")
                else:
                    r = get(q["question"])
                sup = [gl[i] for i in q["supporting_links"] if i in gl]
                rows.append(dict(qid=q["qid"], set_id=s, type=q["type"], false_premise=bool(q["answer_facts"].get("false_premise")), pool=pdir.name,
                                 completeness=completeness([it for it in r["items"] if it.get("meeting_id")], sup), n_items=len(r["items"]), retrieval=r))
    (out / f"{a.system}@{a.scope}.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    print(a.system, a.scope, len(rows), "questions")


if __name__ == "__main__":
    main()
