# Phase 5 DEV results, evowiki_style@test_k1 (final config single_pass_recap_roles_top4; bootstrap over sets)

232 answers, 232 parsed, 1495 sentences, 0 unknown citation ids, 0 unparseable judge verdicts (counted incorrect).

| metric | headline | all types |
|---|---|---|
| correctness_flag | 0.338 [0.27, 0.41] (n=65) | 0.582 [0.53, 0.64] (n=232) |
| correctness_drop | 0.362 [0.31, 0.42] (n=65) | 0.588 [0.54, 0.64] (n=232) |
| supported_claim_rate | 0.145 [0.11, 0.19] (n=65) | 0.180 [0.14, 0.23] (n=232) |
| citation_precision | 0.130 [0.10, 0.17] (n=65) | 0.177 [0.14, 0.22] (n=232) |
| hallucination_rate | 0.799 [0.73, 0.86] (n=65) | 0.762 [0.70, 0.81] (n=232) |
| lexical_ok | 0.897 [0.85, 0.94] (n=65) | 0.923 [0.90, 0.95] (n=232) |
| uncited_share | 0.040 [0.01, 0.07] (n=65) | 0.038 [0.02, 0.06] (n=232) |
| retrieval_completeness | 0.311 [0.25, 0.38] (n=65) | 0.611 [0.54, 0.67] (n=230) |
| expl_completeness_flag | 0.243 [0.20, 0.29] (n=65) | 0.515 [0.46, 0.57] (n=230) |
| expl_completeness_drop | 0.070 [0.04, 0.11] (n=65) | 0.231 [0.17, 0.30] (n=230) |

| type | n | correctness (flag) | supported-claim rate |
|---|---|---|---|
| as_of | 44 | 0.727 [0.61, 0.84] (n=44) | 0.182 [0.11, 0.27] (n=44) |
| change_over_time | 22 | 0.523 [0.36, 0.70] (n=22) | 0.233 [0.15, 0.32] (n=22) |
| decisions_about | 22 | 0.568 [0.46, 0.68] (n=22) | 0.182 [0.10, 0.27] (n=22) |
| distractor | 13 | 0.846 [0.65, 1.00] (n=13) | 0.372 [0.13, 0.60] (n=13) |
| evidence_to_reconsider | 20 | 0.275 [0.15, 0.38] (n=20) | 0.140 [0.07, 0.21] (n=20) |
| full_lineage | 22 | 0.409 [0.32, 0.48] (n=22) | 0.163 [0.10, 0.23] (n=22) |
| lookup_final | 22 | 0.864 [0.73, 1.00] (n=22) | 0.174 [0.10, 0.25] (n=22) |
| meetings_contributed | 22 | 0.545 [0.46, 0.64] (n=22) | 0.114 [0.06, 0.17] (n=22) |
| who_proposed | 22 | 0.682 [0.50, 0.86] (n=22) | 0.180 [0.10, 0.27] (n=22) |
| why_changed | 23 | 0.326 [0.23, 0.43] (n=23) | 0.132 [0.06, 0.22] (n=23) |

False premise: {'n': 4, 'regex_ok': 2, 'judge': [0.0, 0.0, 1.0, 0.0]}
Policy: {'rule': 'drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)', 'deltas': {'headline_correctness': 0.024, 'headline_completeness': -0.173, 'all_correctness': 0.006, 'all_completeness': -0.284}, 'chosen': 'flag'}
Latency: {'mean_s': 23.44, 'mean_in': 1361, 'mean_out': 316}
