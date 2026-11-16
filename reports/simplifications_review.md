# Simplifications review: why each baseline comparison is fair (for the user at CHECKPOINT 7; draft 2026-11-06)

Per-baseline details: `baselines/<name>/SIMPLIFICATIONS.md`. The common rules are in `reports/phase6.md` section 0.

**Common to all three.**
- Same SYSTEM_MODEL (qwen3:14b, thinking off, temperature 0) for every LLM call, including baseline construction (rule 4).
- Same transcripts, same chunking rule, same answer generator and prompt, same metrics and judges.
- No system reads gold. Faithfulness is checked against the source utterances behind every citation, never against a system's own paraphrase (phase6.md A1).
- The main cost of fairness: the small local model handicaps the LLM-heavy baselines (EvoWiki's Build, Graphiti's ingestion) more than retrieval-only ones. Absolute numbers are not comparable to the papers. This is stated as a limitation, and no baseline is given a bigger model.

**vector_rag.**
- A standard dense-retrieval recipe with no tuning. It sees about 48 utterances per question against my system's about 5.5 links, so on raw recall it is, if anything, favoured.
- It is the right control for "does the graph help beyond plain retrieval".

**evowiki_style.** The risk is under-implementation, since no code or prompts were released.
- The four Build functions, the State-Overwrite Protocol (eq. 7-8) and Wiki-only Read are implemented as described, and unit-tested on a fixture (Overturned/Active, version edge, reaffirmation, truncation).
- Departures:
  - (a) two calls instead of four steps;
  - (b) the 6,000-token Read cap forced by the 8K context;
  - (c) my prompts.
- (b) can only bite at pool size 10, and truncations are counted.
- The pre-declared sanity check is that evowiki_style must do at least as well as vector_rag on lookup_final / as_of on DEV, its design target. If it fails, its build is inspected before any comparison is reported.
- It stores no rationale, as in the paper. That absence is exactly what H1 tests, not a handicap added here.

**graphiti.** The released library with defaults, except the model, embedder and backend that rule 4 and zero cost require.
- The backend is Neo4j, its primary one (Kuzu failed, D-24).
- One addition helps it: an adapter maps its episode-level provenance to utterance windows so that lineage completeness and faithfulness can be scored at all.
- Its own docs warn about small models, so its ingestion failure rate is reported next to its scores.

**Where the comparison could still be unfair.**
- The benchmark is built from my schema's arcs (lesson (e)).
- The router and retrieval design of my system were developed on DEV with these question templates, while the baselines answer the raw question.
- Synthetic casts make the L2 speaker-continuity linker strong.

All three are stated in the paper's limitations.
