"""phase6_retrieval.py - retrieval (evidence selection) for the Phase 6 baselines on DEV pooled corpora, in the Phase 5 row format, plus lineage completeness.
  HF_HUB_OFFLINE=1 python eval/phase6_retrieval.py --system vector_rag --sizes 1,10
  ... --system evowiki_style   (needs results/phase6/evowiki/<pool>/wiki.json from kernel adl-p6-evowiki-build)
  ... --system graphiti        (needs results/phase6/graphiti/<kernel>/search_<pool>.json; facts localized to utterance windows, phase6.md section 0)
Writes results/phase6/retrieval/<system>@k<size>.jsonl and summary.json. The harness (not the systems) reads private_map.json for scoring only.
"""
import argparse
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "eval"), str(ROOT / "synthgen")]
from argdecisionlineage.linking import Embedder                     # noqa: E402
from argdecisionlineage.retrieve import load_corpus                 # noqa: E402
from baselines.evowiki_style import evowiki as E                    # noqa: E402
from baselines.vector_rag.vector_rag import VectorRAG               # noqa: E402
from phase5_retrieval import HEADLINE, boot, completeness           # noqa: E402
from score import gold_links                                        # noqa: E402


def graphiti_items(facts, corpus, emb, k=12):
    """Adapter: Graphiti facts carry episode-level provenance. Localize each fact to its most similar 3-utterance window inside its source episode
    (EMBED_MODEL cosine); a fact whose episode is not a corpus meeting gets no provenance (unsupported in faithfulness)."""
    ms = {m["meeting_id"]: (p, m) for p, m in enumerate(corpus["meetings"], 1)}
    items = []
    for n, f in enumerate(facts[:k]):
        ep = next((e for e in f.get("episode_names") or [] if e in ms), None)
        validity = f"valid from {f['valid_at'][:10]}" if f.get("valid_at") else "validity unknown"
        if f.get("invalid_at"):
            validity += f", invalid from {f['invalid_at'][:10]}"
        it = dict(link_id=f"F{n}", role=None, version=None, source="graphiti", text=f"{f['fact']} ({validity})")
        if ep is None:
            items.append(dict(it, meeting_id=None, meeting=0, date="", idxs=[], speaker="", source_text=""))
            continue
        pos, m = ms[ep]
        us = m["utterances"]
        wins = [(i, " ".join(u["text"] for u in us[i:i + 3])) for i in range(0, max(1, len(us) - 2))]
        (fv,) = emb([f["fact"]])
        wv = emb([w for _, w in wins])
        i0 = wins[int(np.argmax(wv @ fv))][0]
        idxs = [u["idx"] for u in us[i0:i0 + 3]]
        items.append(dict(it, meeting_id=ep, meeting=pos, date=m.get("date", ""), idxs=idxs, speaker=us[i0]["speaker"],
                          source_text=" ".join(f"{u['speaker']}: {u['text']}" for u in us[i0:i0 + 3])))
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", required=True, choices=["vector_rag", "evowiki_style", "graphiti"])
    ap.add_argument("--sizes", default="1,10")
    ap.add_argument("--graphiti-run", default="adl-p6-graphiti")
    a = ap.parse_args()
    dev = json.loads((ROOT / "data/synth/split.json").read_text(encoding="utf-8"))["dev"]
    index = json.loads((ROOT / "data/synth/pools/dev/index.json").read_text(encoding="utf-8"))
    emb = Embedder()
    out = ROOT / "results/phase6/retrieval"
    out.mkdir(parents=True, exist_ok=True)
    sp = out / "summary.json"
    summary = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
    for size in a.sizes.split(","):
        rows = []
        for pname in [p for p in index if p.startswith(f"dev_k{size}_")]:
            pdir = ROOT / "data/synth/pools/dev" / pname
            ids = json.loads((pdir / "corpus.json").read_text(encoding="utf-8"))["meetings"]
            corpus = load_corpus([(pdir / "meetings" / f"{m}.txt").read_text(encoding="utf-8") for m in ids])
            priv = json.loads((pdir / "private_map.json").read_text(encoding="utf-8"))
            inv = {(v["set_id"], v["meeting_id"]): oid for oid, v in priv.items() if oid != "_sets"}
            if a.system == "vector_rag":
                sysm = VectorRAG(embedder=emb).index(corpus)
                get = sysm.retrieve
            elif a.system == "evowiki_style":
                wiki = E.Wiki.from_json(json.loads((ROOT / "results/phase6/evowiki" / pname / "wiki.json").read_text(encoding="utf-8")))
                get = lambda q, wiki=wiki, corpus=corpus: E.read(wiki, corpus, q)
            else:
                S = {x["qid"]: x for x in json.loads((ROOT / "results/phase6/graphiti" / a.graphiti_run / f"search_{pname}.json").read_text(encoding="utf-8"))}
                epn = json.loads((ROOT / "results/phase6/graphiti" / a.graphiti_run / f"episodes_{pname}.json").read_text(encoding="utf-8"))
                uuid2m = {e["episode_uuid"]: e["meeting_id"] for e in epn if e.get("ok")}
                for x in S.values():
                    for f in x["facts"]:
                        f["episode_names"] = [uuid2m[u] for u in f["episodes"] if u in uuid2m]
                get = None
            for s in priv["_sets"]:
                g = json.loads((ROOT / "data/synth/gold" / f"{s}.json").read_text(encoding="utf-8"))
                gl = {l["link_id"]: dict(l, meeting_id=inv[(s, l["meeting_id"])]) for l in gold_links(g)}
                for q in g["questions"]:
                    if a.system == "graphiti":
                        x = S.get(q["qid"], dict(facts=[]))
                        r = dict(system="graphiti", intent=None, items=graphiti_items(x["facts"], corpus, emb), versions=[],
                                 meetings=list(range(1, len(corpus["meetings"]) + 1)), search_error=x.get("error"),
                                 header="The evidence below are facts from a temporal knowledge graph built from the meetings, with their validity.")
                    else:
                        r = get(q["question"])
                    sup = [gl[i] for i in q["supporting_links"] if i in gl]
                    items_with_prov = [it for it in r["items"] if it.get("meeting_id")]
                    rows.append(dict(qid=q["qid"], set_id=s, type=q["type"], false_premise=bool(q["answer_facts"].get("false_premise")),
                                     completeness=completeness(items_with_prov, sup), n_items=len(r["items"]), retrieval=r, pool=pname))
        tag = f"{a.system}@k{size}"
        (out / f"{tag}.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        summary[tag] = dict(headline=boot(rows, dev, lambda r: r["type"] in HEADLINE), all=boot(rows, dev), mean_items=round(sum(r["n_items"] for r in rows) / len(rows), 2),
                            truncated=sum(bool(r["retrieval"].get("truncated")) for r in rows))
        print(tag, summary[tag])
    sp.write_text(json.dumps(summary, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
