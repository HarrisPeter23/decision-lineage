# Phase 5 DEV results, graphiti@test_k1 (final config single_pass_recap_roles_top4; bootstrap over sets)

232 answers, 232 parsed, 1701 sentences, 0 unknown citation ids, 0 unparseable judge verdicts (counted incorrect).

| metric | headline | all types |
|---|---|---|
| correctness_flag | 0.469 [0.41, 0.53] (n=65) | 0.567 [0.52, 0.62] (n=232) |
| correctness_drop | 0.446 [0.38, 0.50] (n=65) | 0.558 [0.50, 0.62] (n=232) |
| supported_claim_rate | 0.238 [0.18, 0.30] (n=65) | 0.233 [0.19, 0.29] (n=232) |
| citation_precision | 0.231 [0.17, 0.29] (n=65) | 0.235 [0.18, 0.30] (n=232) |
| hallucination_rate | 0.724 [0.66, 0.78] (n=65) | 0.724 [0.67, 0.77] (n=232) |
| lexical_ok | 0.974 [0.96, 0.99] (n=65) | 0.958 [0.94, 0.97] (n=232) |
| uncited_share | 0.002 [0.00, 0.01] (n=65) | 0.011 [0.00, 0.02] (n=232) |
| retrieval_completeness | 0.320 [0.27, 0.38] (n=65) | 0.479 [0.41, 0.55] (n=230) |
| expl_completeness_flag | 0.281 [0.24, 0.33] (n=65) | 0.433 [0.36, 0.50] (n=230) |
| expl_completeness_drop | 0.091 [0.06, 0.13] (n=65) | 0.137 [0.08, 0.20] (n=230) |

| type | n | correctness (flag) | supported-claim rate |
|---|---|---|---|
| as_of | 44 | 0.591 [0.43, 0.75] (n=44) | 0.267 [0.20, 0.35] (n=44) |
| change_over_time | 22 | 0.386 [0.27, 0.50] (n=22) | 0.182 [0.10, 0.29] (n=22) |
| decisions_about | 22 | 0.568 [0.46, 0.68] (n=22) | 0.253 [0.19, 0.32] (n=22) |
| distractor | 13 | 1.000 [1.00, 1.00] (n=13) | 0.249 [0.13, 0.38] (n=13) |
| evidence_to_reconsider | 20 | 0.550 [0.45, 0.65] (n=20) | 0.244 [0.17, 0.33] (n=20) |
| full_lineage | 22 | 0.432 [0.36, 0.50] (n=22) | 0.227 [0.13, 0.33] (n=22) |
| lookup_final | 22 | 0.591 [0.41, 0.77] (n=22) | 0.205 [0.14, 0.27] (n=22) |
| meetings_contributed | 22 | 0.591 [0.52, 0.68] (n=22) | 0.222 [0.14, 0.32] (n=22) |
| who_proposed | 22 | 0.682 [0.50, 0.86] (n=22) | 0.212 [0.10, 0.34] (n=22) |
| why_changed | 23 | 0.435 [0.34, 0.52] (n=23) | 0.243 [0.17, 0.33] (n=23) |

False premise: {'n': 4, 'regex_ok': 1, 'judge': [1.0, 0.0, 0.0, 0.0]}
Policy: {'rule': 'drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)', 'deltas': {'headline_correctness': -0.023, 'headline_completeness': -0.19, 'all_correctness': -0.009, 'all_completeness': -0.296}, 'chosen': 'flag'}
Latency: {'mean_s': 27.72, 'mean_in': 1007, 'mean_out': 359}
