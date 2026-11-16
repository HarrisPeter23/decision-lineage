# Phase 5 DEV results, no_conflict_resolution@test_k1 (final config single_pass_recap_roles_top4; bootstrap over sets)

232 answers, 232 parsed, 1258 sentences, 22 unknown citation ids, 0 unparseable judge verdicts (counted incorrect).

| metric | headline | all types |
|---|---|---|
| correctness_flag | 0.392 [0.32, 0.46] (n=65) | 0.560 [0.47, 0.64] (n=232) |
| correctness_drop | 0.400 [0.33, 0.46] (n=65) | 0.556 [0.47, 0.63] (n=232) |
| supported_claim_rate | 0.317 [0.26, 0.37] (n=65) | 0.397 [0.34, 0.46] (n=232) |
| citation_precision | 0.327 [0.27, 0.38] (n=63) | 0.412 [0.36, 0.47] (n=226) |
| hallucination_rate | 0.625 [0.57, 0.68] (n=63) | 0.540 [0.48, 0.60] (n=226) |
| lexical_ok | 0.613 [0.54, 0.69] (n=63) | 0.658 [0.61, 0.70] (n=226) |
| uncited_share | 0.062 [0.02, 0.12] (n=63) | 0.050 [0.03, 0.08] (n=226) |
| retrieval_completeness | 0.364 [0.28, 0.46] (n=65) | 0.518 [0.42, 0.61] (n=230) |
| expl_completeness_flag | 0.340 [0.26, 0.43] (n=65) | 0.505 [0.41, 0.60] (n=230) |
| expl_completeness_drop | 0.215 [0.15, 0.27] (n=65) | 0.336 [0.25, 0.42] (n=230) |

| type | n | correctness (flag) | supported-claim rate |
|---|---|---|---|
| as_of | 44 | 0.636 [0.50, 0.77] (n=44) | 0.498 [0.39, 0.62] (n=44) |
| change_over_time | 22 | 0.386 [0.25, 0.55] (n=22) | 0.502 [0.37, 0.63] (n=20) |
| decisions_about | 22 | 0.523 [0.41, 0.64] (n=22) | 0.563 [0.45, 0.68] (n=20) |
| distractor | 13 | 0.731 [0.54, 0.92] (n=13) | 0.342 [0.16, 0.52] (n=13) |
| evidence_to_reconsider | 20 | 0.425 [0.30, 0.55] (n=20) | 0.222 [0.14, 0.31] (n=18) |
| full_lineage | 22 | 0.455 [0.36, 0.55] (n=22) | 0.442 [0.36, 0.52] (n=22) |
| lookup_final | 22 | 0.818 [0.68, 0.95] (n=22) | 0.362 [0.22, 0.52] (n=22) |
| meetings_contributed | 22 | 0.591 [0.50, 0.68] (n=22) | 0.436 [0.35, 0.52] (n=22) |
| who_proposed | 22 | 0.727 [0.55, 0.91] (n=22) | 0.288 [0.15, 0.45] (n=22) |
| why_changed | 23 | 0.304 [0.19, 0.42] (n=23) | 0.299 [0.20, 0.41] (n=23) |

False premise: {'n': 4, 'regex_ok': 2, 'judge': [0.5, 0.0, 1.0, 0.0]}
Policy: {'rule': 'drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)', 'deltas': {'headline_correctness': 0.008, 'headline_completeness': -0.125, 'all_correctness': -0.004, 'all_completeness': -0.169}, 'chosen': 'flag'}
Latency: {'mean_s': 20.79, 'mean_in': 655, 'mean_out': 250}
