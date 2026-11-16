"""diag_edges_vs_positions.py - post-hoc diagnostic: would reading the typed edges (JUSTIFIED_BY, CHALLENGED_BY, REOPENED_BY) retrieve different links
than the position windows retrieve.py uses? For every decision with >= 2 versions in the TEST pool-1 graphs (frozen system, cached extraction), compare
for each superseded version v: (a) the links its typed out-edges point to, and (b) the argument links positioned between v's resolution and the next
version's resolution (the why_changed window of retrieve.py). Read-only; no system change.
  HF_HUB_OFFLINE=1 python eval/diag_edges_vs_positions.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "eval"), str(ROOT / "synthgen")]
from argdecisionlineage import schema as S                     # noqa: E402
from argdecisionlineage.linking import Embedder                # noqa: E402
from argdecisionlineage.retrieve import LineageSystem, load_corpus   # noqa: E402
from phase3_topk import topk                                   # noqa: E402

ARG = ("challenge", "evidence", "reconsideration", "rationale")
ET = {S.JUSTIFIED_BY, S.CHALLENGED_BY, S.REOPENED_BY}
emb = Embedder()
tot = dict(versions=0, same=0, edge_only=0, pos_only=0, edge_links=0, pos_links=0)
for pdir in sorted((ROOT / "data/synth/pools/test").glob("test_k1_*")):
    ids = json.loads((pdir / "corpus.json").read_text(encoding="utf-8"))["meetings"]
    corpus = load_corpus([(pdir / "meetings" / f"{m}.txt").read_text(encoding="utf-8") for m in ids])
    links = topk(json.loads((ROOT / "results/phase7/extract/preds" / f"{pdir.name}.json").read_text(encoding="utf-8"))["links"], 4)
    sysm = LineageSystem(embedder=emb).index(corpus, links)
    g = sysm.graph
    for did, vs in g.versions.items():
        if len(vs) < 2:
            continue
        vp = sysm._vpos(did)
        ls = sysm.by_dec[did]
        for (v0, p0), (v1, p1) in zip(vp, vp[1:]):
            node = ("version", did, v0["n"])
            by_edge = {v[1] for _, v, d in g.g.out_edges(node, data=True) if d["etype"] in ET}
            by_pos = {l.link_id for l in ls if l.role in ARG and p0 < l.pos < p1}
            tot["versions"] += 1
            tot["same"] += by_edge == by_pos
            tot["edge_only"] += len(by_edge - by_pos)
            tot["pos_only"] += len(by_pos - by_edge)
            tot["edge_links"] += len(by_edge)
            tot["pos_links"] += len(by_pos)
print(tot)
