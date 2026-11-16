# Phase 3: every configuration tried (synthetic DEV, 14 sets, tol 1 primary; bootstrap over sets). Nothing here uses TEST.

| config | what | P | R | role-typed F1 [95% CI] | implicit recall (n=6) | links | calls |
|---|---|---|---|---|---|---|---|
| single_pass | one call per meeting | 0.051 | 0.672 | 0.095 [0.07, 0.13] | 1.00 | 1596 | 44 |
| mp_p123 | 3 passes | 0.071 | 0.615 | 0.127 [0.09, 0.19] | 1.00 | 1062 | 132 |
| mp_p123_verify | 3 passes + quote check | 0.070 | 0.525 | 0.124 [0.09, 0.18] | 1.00 | 909 | 132 |
| single_pass, forced 1,200-token chunks | chunking acceptance test | 0.038 | 0.672 | 0.071 [0.05, 0.10] | 1.00 | - | 79 |
| **single_pass_top4** | single_pass, keep 4 most confident links per meeting | 0.308 | 0.434 | **0.361 [0.28, 0.44]** | 0.50 | 172 | 44 |
| mp_p123_top4 | same filter | 0.290 | 0.418 | 0.342 [0.27, 0.41] | 0.33 | 176 | 132 |
| mp_p123_verify_top4 | same filter | 0.244 | 0.352 | 0.289 [0.23, 0.35] | 0.17 | 176 | 132 |

Strict tolerance 0: single_pass_top4 0.354 [0.28, 0.43]; mp_p123_top4 0.336; mp_p123_verify_top4 0.282; unfiltered 0.087 / 0.117 / 0.114 (`results/phase3/main/summary_tol0.md`, `top4_compare.json`).
Not run (SCOPE_4WEEK.md limits Phase 3 to at most three configs): rules, mp_p3, mp_p13, mp_p3_verify, mp_p13_verify, per-role prompts, self-consistency, JUDGE_SECONDARY verification.

**Honest note on how K=4 was chosen.** The improvement round is one change, "keep the K most confident links per meeting", applied identically to every system. I looked at the grid K in {4, 6, 8, 12} and at confidence thresholds {0.8, 0.9, 0.95} on the unfiltered DEV predictions of single_pass and mp_p123 (single_pass F1: K=4 0.367, 6 0.326, 8 0.279, 12 0.217; confidence >= 0.9 0.279) and took the best, which is the edge of the grid. K is therefore tuned on DEV, and it encodes a property of this benchmark (about 2.8 gold links per meeting). It is not a general property of meetings; AMI meetings are long and have more decisions. A K that is fixed here is used unchanged on TEST; the AMI case study reports results with and without it.

## Pre-declarations after the CHECKPOINT 3 review (written 2026-11-04 by the agent on Opus 5.5, from the user's instructions; committed BEFORE the widened cap grid, the decision-scoped scores and the `single_pass_recap_roles` outputs existed)

**P3-A. Two candidates go to Phase 5; the final extraction config is chosen there.** `single_pass` (no cap) and the capped candidate (P3-C) are both carried into Phase 5, and Phase 4 code must accept either. The FINAL extraction config is the candidate with the higher **headline lineage completeness on DEV**: recall of gold supporting links retrieved, pooled over the headline question types (why_changed incl. false-premise, evidence_to_reconsider, full_lineage), single-set corpora (pool size 1), 95% CI by bootstrap over DEV sets (1000 resamples, seed 0). The rule is the point estimate; if the CIs overlap this is reported as a choice, not a demonstrated difference. Exact tie at three decimals: the capped candidate (smaller graph). Everything else in Phase 5 (retrieval, explanation, faithfulness policy) is fixed before the comparison is read.

**P3-B. The extra config `single_pass_recap_roles` (D-17)** joins the Phase 5 comparison under the same rule only if it beats BOTH candidates on all three of: decision-scoped F1 (new metric, `eval/decision_scope.py`), challenge recall, and reconsideration recall (DEV, tol 1, point estimates). It is compared in two forms, uncapped and with the cap variant chosen under P3-C; if both forms qualify, the one with the higher decision-scoped F1 joins. If it does not qualify it is reported as tried and not carried.

**P3-C. Cap variant.** Grid: per-meeting K in {2, 3, 4, 6, 8, no cap}; per-decision K in {1, 2, 3} per (meeting, role, decision name) for configs that output a decision name (only `single_pass_recap_roles`). The capped candidate of `single_pass` is the per-meeting K with the highest DEV decision-scoped F1 (ties: the larger K, i.e. the less aggressive filter). If that K is not 4, it replaces `single_pass_top4` as the capped candidate under P3-A and is named `single_pass_top<K>`; this is reported. Every cell of the grid is reported (`results/phase3/rescore/table.md`). K remains tuned on DEV after seeing output (D-16 still applies).

**P3-D. Primary variant on AMI.** On AMI, the primary result is the FINAL extraction config exactly as frozen (same cap rule and the same K, no AMI-specific tuning). Secondary, labelled: the uncapped output (and the per-meeting K=4 output, if the final config is uncapped). Not done: any K rescaled or re-tuned for AMI. Rationale: one frozen system; per-meeting K is known to encode synthetic decision density (about 2.8 gold links per meeting), which is stated as a limitation rather than corrected on real data.

**P3-E. Metrics.** The old role-typed P/R/F1 stays the Phase 3 headline metric as pre-registered; decision-scoped precision/F1 is a NEW metric added after seeing results, reported next to it and labelled new. Its threshold TAU is fixed from gold only (10th percentile of gold-link-to-own-decision similarity), never from system output.

## Outcome of P3-A to P3-E (2026-11-04, after the pre-declarations above were committed in 9747ee2)
Full grid: `results/phase3/rescore/table.md` (generated by `eval/phase3_caps.py`). TAU = 0.275 (gold only); at that TAU 47% of all DEV utterances are in scope of the decision-scoped metric, and 98.4% of gold links are most similar to their own decision.

| config | cap | links | role-typed F1 [CI] | NEW decision-scoped P / F1 [CI] | implicit | challenge R | reconsideration R |
|---|---|---|---|---|---|---|---|
| single_pass | none | 1596 | 0.095 [0.07, 0.13] | 0.105 / 0.181 [0.14, 0.23] | 6/6 | 0.55 | 0.17 |
| single_pass | per-meeting K=4 | 172 | 0.361 [0.28, 0.44] | 0.453 / 0.444 [0.36, 0.52] | 3/6 | 0.09 | 0.17 |
| single_pass_recap_roles | none | 583 | 0.261 [0.22, 0.31] | 0.235 / 0.359 [0.31, 0.42] | 6/6 | 0.73 | 1.00 |
| **single_pass_recap_roles** | **per-meeting K=4** | 163 | **0.554 [0.48, 0.62]** | 0.572 / **0.608 [0.53, 0.68]** | 3/6 | 0.64 | 1.00 |

- **P3-C:** per-meeting K=4 has the highest decision-scoped F1 for single_pass (K=3 0.434, K=6 0.420), so the capped candidate stays `single_pass_top4`. Per-decision caps (recap config only) are below per-meeting K=4 (best: per-decision K=3, F1_ds 0.581).
- **P3-B:** `single_pass_recap_roles` with the P3-C cap (per-meeting K=4) beats both candidates on all three criteria (F1_ds 0.608 vs 0.181 / 0.444; challenge recall 0.64 vs 0.55 / 0.09; reconsideration recall 1.00 vs 0.17 / 0.17), so **`single_pass_recap_roles_top4` joins the Phase 5 comparison** under the P3-A rule. Uncapped it does not qualify (F1_ds 0.359 < 0.444).
- Its role-typed F1 CI [0.48, 0.62] does not overlap single_pass_top4's [0.28, 0.44] (separate, not paired, bootstraps). Caveats: the role guide was written after reading the DEV error analysis, K is DEV-tuned (D-16), and the challenge and reconsideration supports are 11 and 12 gold links. Rationale is still weak (F1 0.31).
- The new config emits about a third as many links uncapped (583 vs 1596) and about half the output tokens (32.9k vs 61.2k), and took 0.31 GPU h.
- One recap meeting (set_01023 m3) has no links: the model returned an empty list (13 characters; worker exit codes all 0), which is not a parse failure. `phase3_score.py` lists it as a meeting without links.
- Sensitivity for D-18: with set_01019 excluded, single_pass F1 is 0.094 (none) and 0.354 (K=4).
- **Phase 5 therefore carries three extraction candidates:** `single_pass`, `single_pass_top4`, `single_pass_recap_roles_top4`. The final one is chosen by P3-A (headline lineage completeness on DEV).

**P3-A outcome (2026-11-04, `reports/phase5.md` section 1):** final extraction config = **`single_pass_recap_roles_top4`** (headline lineage completeness 0.595 [0.49, 0.70] vs single_pass_top4 0.351 [0.24, 0.49] and single_pass 0.223 [0.15, 0.30]; DEV, pool 1).


## P3-F. Phase 3 improvement round requested on 2026-11-06 (pre-declared BEFORE any new config output exists; agent model Opus 5.5)
(Named P3-F because P3-A to P3-E are already used above. SCOPE_4WEEK's single improvement round was already spent on the top-K cap, D-16, and D-17 added configs
at the user's request, so this round is logged as deviation D-27, at the user's explicit request.)

**Comparison point:** `single_pass_recap_roles_top4` (role-typed F1 0.554; leakage audit PASS, `results/phase3/leak_audit_p3b.json`).
**Tune / check split** (fixed, `results/phase3/p3f_split.json`, seed 20261106, stratified by arc):
- tune = set_01000, set_01002, set_01003, set_01014, set_01019, set_01023, set_01030;
- check = set_01004, set_01006, set_01012, set_01013, set_01015, set_01016, set_01045.
Changes were chosen from the TUNE-half error counts only (`reports/phase3_error_analysis.md`). Caveat: earlier rounds (D-17 recap guide, D-20 versioning rules) were developed with all 14 DEV sets in view, so the check half guards against THIS round's tuning only.

**The two new configs (at most two):**
1. `recap_roles_div4`: the existing `single_pass_recap_roles` output, no new model calls. Role-balanced cap of 4 links per meeting: first the highest-confidence link of each role present in the meeting (roles ordered by their best confidence, ties: earlier utterance), up to 4; then fill to 4 by confidence. Targets FN_cap (tune: 8 FN, 7 headline-relevant; 4 resolutions).
2. `recap_args_div4`: `single_pass_recap_roles` + ONE argument-completion call per meeting. The call sees the meeting transcript and the decisions and options the system itself extracted from that meeting (its own pass-1 output, never gold). It returns the utterances that give a REASON for or against an option (rationale) or OBJECT to a decided option (challenge), with contrast definitions and invented examples (names outside the benchmark's cast pool). New links are merged with pass 1 (a new link duplicating an existing one with the same role, sharing an utterance or adjacent with the same speaker, is dropped; the chunking merge rule). Then the same role-balanced cap of 4. Targets missed and mistyped rationale (tune rationale recall 0.28; FN_role + FN_cross + FN_within = 11 of 13 rationale misses).
Same model, decoding, chunking rule and kernel as Phase 3. One prompt revision of the argument pass is allowed, judged on the TUNE half only, before the full DEV run; if it is used, both versions are reported.

**Primary metrics** (both pre-declared):
- (i) decision-scoped role-typed F1 (`eval/decision_scope.py`, tol 1, TAU from gold);
- (ii) headline retrieval-level lineage completeness at pool size 1, through the frozen Phase 4/5 system (graph v4, linker L2, router RF1, N = 12; `eval/phase5_retrieval.py`).
Secondary: role-typed F1, per-role P/R/F1, implicit-resolution recall, the error taxonomy before and after. 95% CIs by bootstrap over the sets of each half (1000, seed 0).

**Selection rule.** A new config goes forward to Phase 4/5 iff ALL of:
- on the CHECK half its point estimates beat `single_pass_recap_roles_top4` on BOTH primary metrics;
- on the TUNE half it is not lower on either;
- on all 14 sets its role-typed F1 is not more than 0.02 below 0.554.
Forward set: `single_pass_recap_roles_top4` plus at most the two new configs (at most 3, SCOPE_4WEEK). If several go forward, the final extraction config is re-chosen in Phase 5 by P3-A (headline lineage completeness on all of DEV, pool 1). CIs are reported; overlap means a choice, not a demonstrated difference.

**GPU estimate.** `recap_roles_div4`: 0 h. `recap_args_div4`: 44 calls of about 3k input / 400 output tokens (about 16 s each by the Phase 5 fit) + 0.05 h start-up = about 0.3 h for all of DEV; a tune-half development run (22 calls) about 0.2 h; a possible revision run on the tune half about 0.2 h. Total about **0.7 h**, against the 8 h limit. Stop and report if a run would push this task past 8 h.

**P3-F development log (tune half only; the check half has not been scored for any argument-pass version).**
- `recap_roles_div4`, all halves (`results/phase3/p3f_partial_eval.json`): does NOT qualify. Headline completeness tune 0.538 vs 0.638 and check 0.582 vs 0.627; decision-scoped F1 tune 0.609 vs 0.618, check 0.613 vs 0.597.
- `recap_args_div4` with args_v1, tune half (`results/phase3/p3f_tune_v1_eval.json`, 22 calls, 0 failed): decision-scoped F1 0.615 vs 0.618, headline completeness 0.683 vs 0.638, role F1 0.591 vs 0.568, rationale recall 0.333 vs 0.278, challenge 0.60 vs 0.40. The pass added 217 links; the cap keeps few of them.
- **The one allowed revision, args_v2 (rule fixed before v2 exists):** the argument pass returns at most ONE reason for and ONE reason against per decision (the clearest, explicit ones), and skips restatements and passing remarks. Nothing else changes. **Version used for the full DEV run:** v2 iff on the tune half its decision-scoped F1 >= the baseline's (0.618) AND its headline completeness > v1's (0.683); otherwise v1. Both versions are reported.

**P3-F result (`reports/CHECKPOINT_3b.md`):** neither config qualifies under the pre-declared rule; the forward set stays `single_pass_recap_roles_top4`. args_v2 was not used (tune HC 0.632 not above v1's 0.683); v1 on the check half: DS-F1 0.677 vs 0.597 (better), HC 0.617 vs 0.627 (worse).
