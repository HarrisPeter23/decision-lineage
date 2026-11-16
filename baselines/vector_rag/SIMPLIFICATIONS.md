# vector_rag: generic dense-retrieval baseline (no single reference paper; the standard RAG recipe of Lewis et al. 2020)

| Choice | Setting | Why |
|---|---|---|
| Chunks | Windows of 4 consecutive utterances, stride 2, per meeting (never across meetings) | Utterance windows, as the master task specifies. 4 utterances is about one exchange. Not tuned |
| Embeddings | EMBED_MODEL all-MiniLM-L6-v2 (the same model my system uses) | Rule 4 |
| Retrieval | Top 12 chunks by cosine to the question text, ordered chronologically | 12 = the item cap of my system. A chunk holds 4 utterances, so vector_rag sees about 48 utterances per question against my system's about 5.5 links; this is reported next to every completeness number |
| Reranking, query rewriting, hybrid BM25 | None | Kept generic. EvoWiki's paper reports BM25, dense and hybrid variants within about 3 points of each other |
| Answering | The shared generator (SYSTEM_MODEL, same prompt, same settings), citing chunks | Rule 4 |
| Time | Only the meeting position and date printed with each chunk | The baseline is non-temporal by design |
