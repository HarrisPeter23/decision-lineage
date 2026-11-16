# graphiti: the released library (getzep/graphiti, graphiti-core 0.31.2, Apache-2.0), not re-implemented

| Library default | Here | Why / effect |
|---|---|---|
| LLM: OpenAI models (the docs recommend the most capable available and warn that small models break structured output) | `OpenAIGenericClient` to SYSTEM_MODEL qwen3:14b on Ollama, thinking off (`reasoning_effort="none"`, as for every SYSTEM_MODEL call), temperature 0, max_tokens 4096; `small_model` = the same model | Rule 4. Ingestion failures are counted, not hidden |
| Embedder: OpenAI text-embedding (1024-d) | `OpenAIEmbedder` to Ollama `all-minilm` (all-MiniLM-L6-v2, 384-d; `EMBEDDING_DIM=384`) | Same embedding family as every other system; no paid API |
| Reranker: OpenAI | `OpenAIRerankerClient` pointed at the local SYSTEM_MODEL (only used by recipes that rerank; the default `search()` uses RRF hybrid search) | No paid API |
| Graph backend: Neo4j (primary), FalkorDB, Kuzu, Neptune | Neo4j Community 5.26.17 (GPL-3.0), local, inside the Kaggle session. The bundled Kuzu driver was tried first and fails in 0.31.2 (D-24) | Graphiti's primary backend. No configuration beyond the initial password |
| Episodes | One episode per meeting: the plain-text transcript ("Speaker: text" lines), `source=message`, `reference_time` = meeting date, `group_id` = corpus | As the master task specifies. Bi-temporal validity comes from Graphiti itself |
| Custom entity / edge types | None (library defaults) | Using the library as released. Typing it with our schema would turn it into our system |
| Read | `graphiti.search(question, group_ids=[corpus], num_results=12)`: facts (edges) with `valid_at` / `invalid_at` as evidence items for the shared generator | The same 12-item cap as my system and vector_rag |
| Provenance | Graphiti links a fact to its source episodes, not to utterances. **Adapter (an addition that helps Graphiti):** each fact is localized to its most similar 3-utterance window inside its first source episode (EMBED_MODEL cosine), so that lineage completeness and NLI faithfulness on the source text can be computed. A fact with no source episode gets no provenance | Needed to score Graphiti on the same footing. It can only help Graphiti's completeness and faithfulness |
| Answering | The shared generator, citing facts | Rule 4 |
