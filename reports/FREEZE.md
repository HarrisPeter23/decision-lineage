<!-- RELEASE HEADER (added for the public release; everything below this block is unchanged)
Frozen at commit 309776048cd8ee9ed09fba341a269514ffdd2f53, 2026-11-08 02:06:23 +0530, in the authors' development repository.
The hash was recorded in this file by the next commit, fbcc33969437e60daa68760a7ae293d2eb3d73d0 (2026-11-08 02:06:33 +0530); the file has not changed since.
The first TEST results were committed at 2026-11-08 12:50 +0530, after the freeze.
SHA-256 of the text below this block: 9044c6d215135645cfa7e2252ca4ef3aadb4236b3d27db2a4ca94fefb1fcbd2c
This release is a fresh repository without that history. Changes after the freeze are logged in reports/deviations.md.
-->
# FREEZE.md: pre-registration - FROZEN 2026-11-08 at commit 309776048cd8ee9ed09fba341a269514ffdd2f53 (approved by the user). Not to be edited; any later change is a new, post-hoc configuration.

Status: draft started 2026-11-03. It becomes the freeze only when complete, committed, and approved by the user at CHECKPOINT 7 (HARD). No TEST run happens before that.
Sections marked OPEN are not decided yet. Sections without that mark record decisions already made by the user.

## 1. Fixed so far
- Split: `data/synth/split.json`. DEV 14 sets, TEST 22 sets. SHA-256 of the sorted set lists: DEV `1515952fdf86363db3d9285f7c91a86f053cf25b316691e34431f7e819e7ffd7`, TEST `6176494f2a17c153431ce7ad264c006f8cce4488165cead2f487cb681adbaada`, all `fe55a904c0f1d79bedbcef322c1f3ebd00f17bbef2c5406d820ab3037a09277c`. The split will not change.
- SYSTEM_MODEL and judges: `runtime/models.json`. If vLLM is adopted, the exact weights are recorded here before Phase 3.

## 2. Hypotheses
- **H1 (primary):** on headline questions, the chain-typed lineage system has higher explanation faithfulness and lineage completeness than each baseline, evowiki_style and graphiti in particular.
- **H2:** on lookup_final and as_of it is NOT expected to beat vector_rag or graphiti; where it loses is reported.
- **H3:** the advantage persists on real speech. Reported as a small-N, qualitative AMI case study (about 5 series), with its verification status. Not a quantitative claim.
- **H4: DROPPED** (user decision, 2026-11-03). See section 4.

## 3. H1 primary test
- **The primary test pools all headline question types**: why_changed (including the false-premise variant), evidence_to_reconsider, full_lineage. That is 65 TEST questions in the pre-freeze count.
- Uncertainty comes from a bootstrap over TEST sets, never over questions.
- **Per-type results are exploratory** and labelled so.
- Primary metrics: lineage completeness, explanation faithfulness, answer correctness. Everything else is secondary or exploratory.
- Fixed in section 14 (paired bootstrap over TEST sets, 10,000 resamples, Holm within the primary and the secondary family).

## 4. Writer leakage is not controlled
H4 was to test whether the advantage holds on sets written by a non-Claude local model. It was dropped because no valid control sets could be produced. Negative results, reported as such (deviation D-10):
1. `mistral-nemo:12b`, Claude procedure: 8-19 lines against 60-120 required, in 8 of 8 attempts.
2. `llama3.1:8b`, Claude procedure: 0 of 4 test meetings passed QC.
3. `phi4:14b`, Claude procedure: 0 of 4.
4. `olmo-3:7b`, Claude procedure: 0 of 4.
A chunked `mistral-nemo` procedure (v3c, v3c2) was also tried. It gave two complete sets, one failing the validator and one rejected because its tagged lines did not realize the planned events.

**Limitation to state in the paper:** writer leakage is not controlled. All TEST synthetic sets were written by one model, Sonnet 5.5. The AMI case study partly addresses this concern, because its speech is not written by any model, but it is small and qualitative, so it does not replace the control.

## 5. Scope cuts (copied from SCOPE_4WEEK.md, all to be stated in the limitations)
- Baselines: vector_rag, evowiki_style, graphiti only. Meeting Decision Tracker, meeting-KG GraphRAG and static GraphRAG are related work, not evaluated (reason: time).
- All systems on TEST at pool size 1. Pool size 10 only for my system, evowiki_style, graphiti.
- 4 ablations, pool size 1: no chain typing; no conflict resolution; no faithfulness checker; static graph (versions, validity windows and supersession disabled).
- Single-pass and no-quote-verification comparisons come from Phase 3 DEV results, labelled DEV.
- AMI about 5 series, no ELITR.
- Local NLI on all sentences; JUDGE_SECONDARY on all rubric correctness; Gemini only on a fixed, stratified, pre-drawn sample (about 1,500 sentences and 1,500 answers) to report agreement.
- The LLM pairwise comparison on about 40 questions stays, against evowiki_style and graphiti.

## 6. Judge validation
- Link-judge sensitivity on planted negatives (`results/judge_sensitivity/`, DEV only, 56 real and 57 corrupted links). Gemini `gemini-3.5-flash-lite`, counting partial or no as flagged, with 95% Wilson intervals:

| Corruption | n | Flagged | 95% CI |
|---|---|---|---|
| wrong speaker | 14 | 100% | 79-100% |
| unsupportive quote | 14 | 100% | 79-100% |
| shifted utterance | 14 | 79% | 52-92% |
| **wrong role** | 15 | **7%** | **1-30%** |
| all corrupted | 57 | 70% | 57-81% |
| real links (false alarms) | 56 | 0% | 0-6% |

  **Consequence: the panel validates speaker and content, not the role label.** `llm_consensus` must not be read as verifying a link's role. Some wrong_role items are soft negatives (a challenge relabelled as rationale can still be a reason against an option), but resolution relabelled as proposal is a clean negative and was also missed. `granite4.2:8b` has not been tested: it needs a GPU, which this test was not allowed to use. Its prompts are ready in `results/judge_sensitivity/items.jsonl`.
- **Phase 5 requirement:** the faithfulness and correctness judges get the same planted-negative validation on DEV before they are trusted. Corrupted sentences and answers are mixed with real ones (for example a wrong number, a swapped speaker, a wrong outcome, a wrong argumentative role, a citation to an unrelated link, an unsupported added claim), and each judge's detection and false-alarm rates are reported with Wilson intervals.
- Fixed in section 17 (qualification rule and results).

## 7. Scoring rules still to fix before any system output exists
- **Span tolerance (decided 2026-11-03, before any system output exists, from structure alone):** a predicted link matches a gold link when it is in the same meeting and its utterance span is within **1 utterance** of the gold span (`score.py --tol 1`, the primary matching); a role-typed match also needs the same role. Exact-overlap matching (`--tol 0`, the pair shares at least one line) is reported as a secondary, stricter result for every system. Reason: five gold links mark only the key lines while part of the gist is spoken in the adjacent line (`reports/label_issues.md`). The same tolerance applies to every system and to citations in the lineage-completeness metric. It is not tuned on any output.

## 8. To complete at the freeze
Filled in section 13 (configs, digests; the commit hash at approval) and `reports/simplifications_review.md` (simplifications). Venues: Phase 8, not part of the freeze.

## 9. Long-meeting chunking rule (decided 2026-11-03, before any system output; applies identically to every system that sends a meeting to an LLM)
Reason: the SYSTEM_MODEL context is 12,288 tokens; AMI meetings run up to about 19,000 transcript tokens, while synthetic meetings (at most 120 utterances, about 2,500 tokens) always fit.
The rule (`argdecisionlineage/chunking.py`, constants fixed here):
- Token estimate per utterance: ceil(1.4 x words) + 6. **BUDGET = 6,000** estimated transcript tokens per call. If the meeting fits, there is one window and nothing changes, so on synthetic data the rule never triggers.
- Otherwise greedy windows of consecutive utterances up to BUDGET; each next window starts OVERLAP utterances before the previous one ended, **OVERLAP = max(8, utterances in the last 12% of the window's tokens)**.
- Each window is re-indexed from 0 so the unchanged extractors work; links are mapped back to global indices.
- **Cross-chunk merging:** two links are duplicates if they have the same role and share an utterance, or are at most one utterance apart with the same speaker; of duplicates, the link farthest from its own window's edge is kept (ties: higher confidence, then earlier window). Different roles on the same line are both kept.
- Guarantee, tested exhaustively: any span of up to 3 consecutive utterances (the longest event) lies fully inside at least one window.
- Baselines and ablations use the same function and constants for any LLM call that reads a meeting. A system that never sends a whole meeting to an LLM (a retrieval-only system) is not affected.
Tests on CPU (`tests/test_chunking.py`, 8 tests, mutation-checked: shrinking the overlap, removing deduplication and ignoring the role each make a test fail), including an oracle merge on all 44 DEV meetings at three forced small budgets (132 cases) that returns exactly the gold links.
**Pre-declared acceptance test on synthetic DEV (GPU, Phase 3):** run single_pass on DEV once unchunked and once with the budget forced to 1,200 tokens (about two windows per meeting); the rule is accepted if role-typed F1 under chunking is no more than 0.05 absolute below the unchunked F1. If not, OVERLAP may be changed once on DEV, the change recorded here, and the test repeated. BUDGET = 6,000 is not tuned. The result, either way, is reported.
No result on AMI is used to change the rule.

## 10. Questions phrased as decisions (rule (f) = R6 of `argdecisionlineage/graph.py`)
- Assumption stated: the user's "rule (f), section 8.3" is read as the rule that low-confidence or hypothetical statements do not supersede a version (master task Phase 4 step 3), implemented as R6 and listed sixth. No section 8.3 exists in the files I have.
- R6 is kept as specified: a resolution that is a question, a "what if", a "maybe we should", or below the confidence threshold never creates or supersedes a version. Its threshold and patterns are tuned on **synthetic DEV only**; AMI is not used for tuning.
- **Finding (not a result):** in AMI, three of five series have a decisive line phrased as a question that the team then accepts (ES2003 d[164], TS3004 c[683], ES2002 d[130]). A system following R6 may miss those versions. This is recorded as a limitation and as a finding.
- **Exploratory config `question_accepted_binding`** (optional, post-hoc, AMI-informed): a question-form resolution counts as binding if the next speaker or the next utterance accepts it. It is never the primary result, is labelled post-hoc everywhere, and will be run on synthetic DEV and on AMI separately if run at all.

## 11. Label scope and role verification
- Link-level `llm_consensus` means **content and speaker only**. The panel judges saw the intended role and could not detect wrong roles (judge sensitivity, section 6). It is labelled `verification_scope: content_speaker_only` in `data/synth/verification.json` and `data/ami/verification.json`.
- Roles are verified only by **role-blind agreement** (judge picks one of six roles without seeing the gold role; `reports/role_verification.md`) and by the human spot-check if returned (`reports/human_spotcheck.csv`, 24 synthetic and 16 AMI links).
**Role-blind result (2026-11-04, all 293 synthetic and 43 AMI links, `reports/role_verification.md`).** Gemini names the gold role for proposal 40/40, evidence 41/41, reconsideration 31/32, resolution 71/73, but only rationale 16/77 (21%, 95% CI 13-31%) and challenge 3/30 (10%, 3-26%); it calls 47 of 77 rationales "evidence" and 18 of 30 challenges "rationale". Accuracy 0.689, kappa 0.623; on AMI accuracy 0.442, kappa 0.306 (n=43). `granite` accuracy 0.444 on synthetic. Two readings that this check cannot separate: the gold boundary between rationale, evidence and challenge is partly arbitrary, or a 14-line window lacks the context that the arc supplies. Either way a system will find these three roles hard to tell apart, and the role-typed metric will be harsh on them.
**Pre-registered consequence (decided now, before any system output exists):** besides the primary six-role metrics, every system is also scored on a **four-class metric** in which rationale, evidence and challenge are merged into one class "argument" (classes: proposal, argument, reconsideration, resolution). It is a secondary, exploratory result reported next to the six-role result for every system; it does not replace the primary. It is not tuned and not chosen after seeing outputs.
- Batched judging: validated for the link-content judge (49 of 50 identical to single-item, kappa 0.96). **Not valid for role-blind judging**: exact agreement 0.837 on 49 links, below the pre-declared 0.90, so the role-blind check was run single-item (deviation D-13). Batched and single role-blind verdicts differ materially, a finding about the judge, not about the labels.

## 12. Extraction outcome (synthetic DEV; rewritten 2026-11-08 for the freeze)
- **Final extraction config: `single_pass_recap_roles_top4`.** Chosen by rule P3-A, the highest headline lineage completeness on DEV at pool size 1: 0.595 [0.49, 0.70], against `single_pass_top4` 0.351 and `single_pass` 0.223. It was confirmed after the P3-F round (`reports/CHECKPOINT_3b.md`), where neither new config met the pre-declared rule.
- DEV role-typed F1 0.554 [0.48, 0.62], decision-scoped F1 0.608, implicit-resolution recall 3/6.
- K = 4 was tuned on DEV after seeing output (D-16), and the recap role guide was written after reading the DEV error analysis (D-17), so DEV numbers are optimistic.
- Chunking rule accepted (section 9 test: drop 0.024 <= 0.05).
- vLLM not adopted (D-15).
- The earlier selection `single_pass_top4` (CHECKPOINT 3) is superseded. Every configuration tried: `reports/phase3_configs.md`.

## 13. Final configuration (frozen; nothing below changes after approval)
| component | frozen setting |
|---|---|
| Extractor | `single_pass_recap_roles_top4`: `synthgen/extract_recap.py`, prompt `recap_roles_v1` (own-output recap + contrastive role guide), then K = 4 most confident links per meeting (`eval/phase3_topk.topk`, ties: earlier utterance). Pool 10: re-extracted on the pooled order (the recap depends on corpus order) |
| Chunking | FREEZE section 9 (BUDGET 6,000, OVERLAP max(8, 12%)), for every LLM call of every system that reads a meeting |
| Graph | `argdecisionlineage/graph.py`, rules **v4**: `Params(rules="v4", same_at=0.4, modified_at=0.2, min_confidence=0.9, own_at=0.2, new_tokens=3)`, `LexicalMatcher` |
| Linker | `argdecisionlineage/linking.py`, **L2**: `LinkParams(link_at=0.4, gap=60, team_at=0.2)`, EMBED_MODEL all-MiniLM-L6-v2 (HF revision 1110a243fdf4), batch size 1 |
| Retrieval | `argdecisionlineage/retrieve.py`: router with **RF1**, anchoring 0.5 x cosine + 0.5 x idf overlap, N = 12, vector fallback (anchor score < 0.35 or no version, for final / as_of / who_proposed) |
| Generator | `argdecisionlineage/explain.py`; SYSTEM_MODEL **qwen3:14b, digest bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8**, Ollama, thinking off, temperature 0, seed 7, num_predict 700; num_ctx 8192 for my system, 12288 for baselines (prompt room only, D-25) |
| Faithfulness checker | `argdecisionlineage/faithfulness.py`: NLI cross-encoder/nli-deberta-v3-small revision fa2804872c3b, entail >= 0.5, premise = source utterances; load-time self-check; GPU or CPU (agreement 400/400). **Flag policy: *flag*** |
| Correctness | exact match (`eval/phase5_score.py`; option mapper v1, validated 35/40 hand-labelled and identical to `option_map.py` v1) for who_proposed / as_of / lookup_final; otherwise JUDGE_SECONDARY **granite4.2:8b, digest f586c02fdecdf151b656207c339aa003997345774a41768bac1fd6d2fb85913b**, rubric 1 / 0.5 / 0 |
| JUDGE_PRIMARY (calibration and pairwise only) | gemini-3.5-flash-lite, free tier, single item, 450/day guard |
| Baselines | vector_rag (4-utterance windows, stride 2, top 12); evowiki_style (`baselines/evowiki_style`, two Build calls per meeting, State-Overwrite Protocol, Wiki-only Read capped at 6,000 estimated tokens); graphiti (graphiti-core 0.31.2, Neo4j Community 5.26.17, Ollama all-minilm digest 1b226e2802dbb772b5fc32a58f103ca1804ef7501331012de126ab22f67475ef, top 12 facts, provenance adapter). See `reports/simplifications_review.md` |
| Runtime | Kaggle T4, Ollama (see `runtime/models.json`), torch 2.15.0+cpu and sentence-transformers 6.2.0 locally |
| Split | `data/synth/split.json` (section 1 hashes). TEST pools: `data/synth/pools/test` (sizes 1 and 10, built in Phase 1) |
| Commit | **309776048cd8ee9ed09fba341a269514ffdd2f53** (approved by the user on 2026-11-08; FREEZE.md is locked from this commit on) |

## 14. H1 operationalised (primary); changed on 2026-11-08 (D-30)
**Primary metric (one): cited-lineage F1 over the headline question types** (`eval/lineage_f1.py`, committed in b1e006b before any number was computed with it).
- **Questions:** every TEST headline question (why_changed incl. false premise, evidence_to_reconsider, full_lineage) with a gold lineage L = its `supporting_links` (|L| >= 1), pooled across the three types.
- **Cited items C:** the distinct evidence items the answer cites, in order of first appearance across its sentences. An item is (meeting, utterance indexes): an utterance link for my system, a 4-utterance window for vector_rag, the provenance anchor of a cited Wiki state for evowiki_style, the localized 3-utterance window of a cited fact for graphiti (Phase 6 adapter).
- **Match (the same rule for every system):** an item matches a gold link iff it is in the same meeting and some utterance index of the item is within 1 of some utterance index of the gold link (role ignored; the tol-1 rule used since Phase 0). A wider item (a window) matches more easily; this is stated, not corrected.
- **Precision** = matched cited items / all cited items. **Recall** = gold links matched by at least one cited item / |L|. **F1** = 2PR / (P + R).
- **F1 = 0** when the answer cites nothing, when it does not parse, or when P + R = 0. A cited item without provenance (a Graphiti fact with no source episode) counts as cited and non-matching.
- **False-premise questions** are scored like any other: their gold lineage is the challenge / evidence / reconsideration / reaffirming-resolution links that explain why the decision did not change.
- **evowiki_style:** only the Wiki states the answer cites count, each through its provenance anchor. The rest of the Wiki (its whole "retrieved" set) plays no role.
- **Aggregation:** mean over a set's headline questions, then mean over sets.
- **No LLM judge is involved; the metric is computed against gold only.**
- **Comparisons (primary family, 2 tests):** my system vs evowiki_style, and my system vs graphiti, at pool size 1.
- **Test:** paired bootstrap over the 22 TEST sets. 10,000 resamples, seed 0. Each resample draws 22 sets with replacement and computes d = mean over drawn sets of (mine - baseline) set-level F1. One-sided p = share of resamples with d <= 0. **Holm over the 2 tests at alpha 0.05.** Report d with its 95% percentile CI.
- **Secondary family** (Holm within the family at alpha 0.05; same paired procedure; two-sided 95% CIs reported):
  - (i) vs evowiki_style and vs graphiti (12 tests): cited lineage completeness (= recall above), cited precision, **cited completeness@k**, NLI citation recall (supported-claim rate), NLI citation precision, answer correctness;
  - (ii) vs vector_rag (7 tests): the primary metric and the same six.
  - **completeness@k:** recall computed on the first k cited items in the answer's citation order (first appearance; every system's answers have this order). k is fixed per type as the median gold lineage length over **DEV gold only**: evidence_to_reconsider 3, why_changed 6, full_lineage 8.
  - NLI-based metrics are strict lower bounds (section 17).
- Everything else (per type, per arc, retrieved completeness and retrieved F1, hallucination rate, false-premise accuracy, latency, pool size 10) is descriptive and exploratory.
- **H2:** descriptive only; correctness on lookup_final + as_of with 95% CIs for every system, and where my system loses is stated.
- **H3 (AMI):** qualitative (section 18).

**DEV values, for information only** (the metric does not change after this; `results/lineage_f1_dev.json`; 1,000 resamples):

| system (DEV, pool 1, cited) | lineage F1 [CI] | precision | recall | recall@k | items cited / answer |
|---|---|---|---|---|---|
| mine | 0.602 [0.54, 0.66] | 0.648 | 0.607 | 0.560 | 5.5 |
| vector_rag | 0.498 [0.41, 0.60] | 0.487 | 0.565 | 0.347 | 8.5 |
| evowiki_style | 0.276 [0.21, 0.35] | 0.421 | 0.237 | 0.237 | 4.3 |
| graphiti | 0.360 [0.26, 0.45] | 0.385 | 0.382 | 0.276 | 6.4 |

- Paired DEV differences in F1: vs evowiki_style +0.33 [0.24, 0.41]; vs graphiti +0.24 [0.12, 0.36]; vs vector_rag +0.10 [-0.03, 0.21].
- Pool size 10: mine 0.389, vector_rag 0.290, evowiki_style 0.222, graphiti 0.218.
- Ablations (retrieval-level F1, because DEV ablation answers would need GPU): system 0.597, no typing 0.587, no conflict resolution 0.586, static graph 0.579. With precision counted, the static graph no longer scores above the system (its retrieval-level completeness is 0.676 vs 0.623). All CIs overlap.

## 15. Ablations (frozen; each reuses the cached TEST extraction of the final extractor; only graph and retrieval change)
| ablation | definition | code |
|---|---|---|
| no chain typing | rationale / evidence / challenge / reconsideration collapsed to an untyped "statement"; decisions, versions and supersession kept; role filters in retrieval match any statement | `LineageSystem(ablation="no_typing")` |
| no conflict resolution | every resolution becomes the new version ("last statement wins"): no reaffirmation, no tentative filter (R6), no V2-V4 rules | `ablation="no_conflict_resolution"` (graph rules "last") |
| static graph | no versions, validity windows or supersession; every intent reads the decision's links without time logic; non-temporal header | `ablation="static_graph"` (graph rules "static") |
| no faithfulness checker | **no effect by construction under the *flag* policy**: the checker only marks sentences, so answers, citations and every metric are identical. Recorded, not run |
- Tests: `tests/test_ablations.py` (4).
- DEV smoke values: section 14. No expectation is pre-registered for the ablations; they are reported on TEST with every metric.
- **Replacement for the checker ablation: checker evaluation.**
  - Flag precision and recall against unsupported sentences, on the 52-sentence agent check (DEV; agent-checked, not human): flags precision 0.65 (17/26), recall 0.94 (17/18).
  - On TEST, the same against Gemini's verdicts on the 600-sentence calibration sample, labelled LLM-judged. Gemini is not qualified for sentences (section 17), so this is a bound.

## 16. Seeds and CI method
- Seeds:
  - generation seed 7, temperature 0;
  - bootstrap seed 0;
  - Gemini calibration sample seed 0;
  - pairwise sample seed 0;
  - tune/check split seed 20261106 (DEV only);
  - Phase 1 split as recorded in `split.json`.
- CIs: percentile bootstrap over TEST sets, 10,000 resamples for every reported TEST number (DEV used 1,000).
- Per-question means are pooled; questions are never resampled independently of their sets.

## 17. Judge qualification (rule fixed by the user, 2026-11-08) and results on DEV planted errors
**Rule.** A judge's numbers are primary for an error type only if, on DEV planted errors, it catches >= 80% of that type AND flags <= 10% of real items. Otherwise they are reported as bounds; NLI counts as a strict lower bound. "Catches": for sentence judges, verdict "not supported"; for answer judges, any verdict other than "correct".

| judge | task | error type (n) | caught | real items flagged | qualifies |
|---|---|---|---|---|---|
| NLI | sentences | number (10) | 10/10 | 35/60 = 0.58 | no |
| NLI | sentences | speaker (10) | 6/10 | 0.58 | no |
| NLI | sentences | outcome (10) | 10/10 | 0.58 | no |
| NLI | sentences | role (10) | 8/10 | 0.58 | no |
| NLI | sentences | citation to an unrelated item (10) | 10/10 | 0.58 | no |
| NLI | sentences | unsupported added claim (10) | 10/10 | 0.58 | no |
| Gemini | sentences | number (10) | 3/10 | 16/60 = 0.27 | no |
| Gemini | sentences | speaker (10) | 10/10 | 0.27 | no |
| Gemini | sentences | outcome (10) | 9/10 | 0.27 | no |
| Gemini | sentences | role (10) | 5/10 | 0.27 | no |
| Gemini | sentences | citation (10) | 10/10 | 0.27 | no |
| Gemini | sentences | added claim (10) | 10/10 | 0.27 | no |
| granite | answers | option swap (2) | 2/2 | 0/43 = 0.00 | yes (n=2, uninformative) |
| granite | answers | speaker swap (7) | 7/7 | 0.00 | yes (all 7 "partial": correctness is lenient for speaker errors) |
| granite | answers | meeting shift (7) | 7/7 | 0.00 | yes |
| granite | answers | change negation (10) | 10/10 | 0.00 | yes |
| Gemini | answers | option swap (2) | 1/2 | 0/43 = 0.00 | no |
| Gemini | answers | speaker swap (7) | 7/7 | 0.00 | yes |
| Gemini | answers | meeting shift (7) | 6/7 = 0.86 | 0.00 | yes |
| Gemini | answers | change negation (10) | 10/10 | 0.00 | yes |

Sources: NLI `results/phase5/planted/sentences_k1_nli.json`; granite `answers_granite.json`; Gemini `gemini_qualification.json` (189 single-item requests on 2026-11-08, same prompts as the DEV calibration and the granite rubric).

**Consequences:**
- **No judge qualifies for sentence-level faithfulness.** NLI faithfulness numbers are strict lower bounds; Gemini's sentence verdicts are reported as bounds too.
- Correctness (granite) is primary for option, speaker, meeting and change errors, with the speaker-error leniency stated.
- Gemini's answer verdicts are a qualified cross-check for speaker, meeting and change errors.
- The primary metric (section 14) uses no judge.

## 18. AMI protocol (H3, qualitative)
- **Shared AMI inputs (all systems):** `eval/ami_pools.py` writes `data/ami/pools/<series>/`, the ONLY AMI source for every system (the extractor, retrieval, evowiki_style, vector_rag, graphiti), in the synthetic pools' plain-text format with opaque meeting ids. AMI records one date per series, shared by its four meetings, so each meeting's date is normalised once there to ISO date + k hours (meeting k at 09:00 + k). The offset is synthetic and only preserves meeting order; every system receives the identical string. Test: `tests/test_ami_inputs.py` (ordered ISO dates, utterances identical to the source transcripts, no system reads the raw transcripts).
- **Data:** 5 scenario series, 20 meetings, about 9,400 utterances, 50 questions (`data/ami`). Gold drafted by the agent (Phase 2), `llm_consensus` (content and speaker only) plus the human spot-check of 16 AMI links.
- **Systems:** all four at pool size 1, with the frozen configuration unchanged (P3-D). Nothing is tuned on AMI.
- **Chunking:** AMI meetings exceed the model context, so the section 9 rule applies to every LLM call that reads a meeting, identically for all systems:
  - my extractor: as implemented;
  - evowiki_style Build call 1: as implemented;
  - **graphiti: one episode per chunk window** (`baselines/graphiti/episodes.py`; name = meeting + window index; reference_time = the meeting's date as given by the shared AMI pools). Written, unit-tested and dry-run (DEV with a forced small budget; AMI bundle built, 48 episodes from 20 meetings, not run);
  - vector_rag: no LLM reads a whole meeting.
- **Reported:** the same metrics as synthetic, with n stated; per-series case narratives (one changed decision traced through each system's answer). Secondary: retrieval-level results of the uncapped extraction (CPU).
- **Known risk (section 10):** decisions stated as accepted questions in 3 of 5 series; R6 may miss them; reported as a finding.
- H3 is a small-N qualitative case study, not a test.

## 19. Pairwise comparison protocol (exploratory, LLM-judged)
- **Sample:** 40 TEST questions drawn with seed 0, stratified 20 why_changed (including false premise) + 20 full_lineage, pool size 1.
- **Pairs:** my system vs evowiki_style, and my system vs graphiti.
- **Procedure:** each pair is shown in both orders (A/B swapped) with system names hidden: 40 x 2 x 2 = 160 judgements per judge. The judge sees the question, the gold reference answer and the two answers with explanations, and prefers A / B / tie on faithfulness and on completeness.
- **Judges:** granite4.2:8b and gemini-3.5-flash-lite.
- **Reported:** win/tie/loss, inter-judge agreement (kappa), and the position-bias rate (verdicts that flip with order).

## 20. Gemini calibration on TEST
- **Sample:** 600 generated sentences and 600 answers, drawn with seed 0 by `eval/phase7_gemini_sample.py` (committed and dry-run on DEV, deterministic), stratified equally across the four systems at pool size 1: 150 sentences with at least one citation + 150 answers per system.
- Answers are drawn from **all** question types: TEST has about 140 rubric-judged answers per system, too few for 150. For exact-match types Gemini calibrates the exact-match scoring.
- **Mode:** single item, gemini-3.5-flash-lite, the same prompts as the DEV calibration. 1,200 requests + 160 pairwise = about 3.1 days at the 450/day guard.
- **Reported:** agreement with NLI and with granite; flag precision and recall of the checker against Gemini (section 15).

## 21. Failed TEST runs
- Every failed call, kernel error, timeout, parse failure and ingestion failure is logged and counted per system.
- A failed kernel or call is **retried once with the identical configuration and seed**. With temperature 0 a model-output failure will usually repeat, and is then final.
- No configuration change and no other re-run.
- Items still missing are reported per system and scored as failures (empty answer: completeness 0, incorrect, no supported sentences). Graphiti episodes that fail ingestion after the retry stay missing.

## 22. Phase 7 run order, GPU plan and model plan
Quota: 30 h per window, resets Saturdays 00:00 UTC; at most 2 concurrent GPU sessions; script limit about 1 MB.
Windows: Nov 8-13 (30 h free; reset Nov 14 00:00 UTC), Nov 14-20, Nov 21-27, Nov 28-30.

**Model plan (user, 2026-11-08, revised at approval):** the agent runs ALL of Phase 7 on Opus 5.5, not Sonnet (deviation D-31). This does not affect results: SYSTEM_MODEL, the judges and every frozen setting are unchanged.

**Order:**
1. TEST extraction: pool 1 + pooled order.
2. evowiki_style Build and graphiti ingestion (parallel sessions).
3. Retrieval for all systems and ablations (CPU).
4. Generation kernels.
5. NLI (GPU).
6. granite judging.
7. Primary and secondary tables.
8. AMI (extraction, baselines with chunked episodes, generation, scoring).
9. Gemini calibration and pairwise (laptop, about 3 days, in parallel).
10. Failure analysis and CHECKPOINT 8 (Opus 5.5, as the rest of Phase 7).

| block | GPU h | planned window |
|---|---|---|
| my extraction (pool 1 + pooled order) | 1.3 | Nov 11 |
| evowiki_style Build (pools 1 + 10) | 1.3 | Nov 11 |
| graphiti ingestion (pools 1 + 10) | 8.0 | Nov 11-12 (parallel session) |
| generation (mine p1/p10, 3 ablations, vector_rag p1, evowiki_style p1/p10, graphiti p1/p10) | 8.6 | Nov 12-13 |
| NLI + granite + pairwise (granite) | 1.7 | Nov 13 |
| AMI (graphiti about 48 chunked episodes) | 5.6 | Nov 14-15 |
| kernel start-ups | 1.5 | - |
| **total about 28 h (34 h with contingency)** | | Nov 8-13: about 22 h; Nov 14-20: about 6-12 h |

GPU slack by Nov 20: about 26 h. The Gemini work (laptop) runs Nov 12-15.

## 23. Still open at approval
- Nothing. The commit hash is recorded in section 13.
- Venues are not part of the statistical freeze; they are handled in Phase 8 (`reports/paper_notes.md`).

