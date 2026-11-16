"""vector_rag - generic dense-retrieval baseline (phase6.md section 0).
Chunks: windows of WIN consecutive utterances (stride STRIDE) per meeting, embedded with EMBED_MODEL; retrieve the top K chunks by cosine to the question,
order them chronologically, and hand them to the shared generator. No graph, no versions, no topic reasoning. Never reads gold.
retrieve(question) returns the same subgraph-like dict as LineageSystem.retrieve, so the same generator and harness apply.
"""
import numpy as np

from argdecisionlineage.linking import Embedder

WIN, STRIDE, K = 4, 2, 12


class VectorRAG:
    name = "vector_rag"

    def __init__(self, embedder=None, k=K, win=WIN, stride=STRIDE):
        self.emb = embedder or Embedder()
        self.k, self.win, self.stride = k, win, stride

    def index(self, corpus, links=None):
        self.corpus = corpus
        self.chunks = []
        for pos, m in enumerate(corpus["meetings"], 1):
            us = m["utterances"]
            starts = list(range(0, max(1, len(us) - self.win + 1), self.stride))
            if starts and starts[-1] + self.win < len(us):
                starts.append(len(us) - self.win)
            for s in starts:
                w = us[s:s + self.win]
                self.chunks.append(dict(meeting_id=m["meeting_id"], meeting=pos, date=m.get("date", ""), idxs=[u["idx"] for u in w],
                                        speaker=w[0]["speaker"] if len({u["speaker"] for u in w}) == 1 else "several speakers",
                                        text=" ".join(f"{u['speaker']}: {u['text']}" for u in w)))
        self.vec = self.emb([c["text"] for c in self.chunks]) if self.chunks else np.zeros((0, 1))
        return self

    def retrieve(self, question):
        (q,) = self.emb([question])
        top = np.argsort(-(self.vec @ q))[:self.k] if len(self.chunks) else []
        items = []
        for i in sorted(top, key=lambda i: (self.chunks[i]["meeting"], self.chunks[i]["idxs"][0])):
            c = self.chunks[i]
            items.append(dict(link_id=f"C{i}", role=None, version=None, source="vector", **c))
        return dict(system=self.name, intent=None, items=items, versions=[], meetings=list(range(1, len(self.corpus["meetings"]) + 1)),
                    header="The evidence below are transcript excerpts retrieved for this question.")
