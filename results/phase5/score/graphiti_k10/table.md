# Phase 5 DEV results, graphiti_k10 (final config single_pass_recap_roles_top4; bootstrap over sets)

141 answers, 141 parsed, 1016 sentences, 0 unknown citation ids, 0 unparseable judge verdicts (counted incorrect).

| metric | headline | all types |
|---|---|---|
| correctness_flag | 0.338 [0.26, 0.42] (n=40) | 0.418 [0.33, 0.49] (n=141) |
| correctness_drop | 0.338 [0.28, 0.39] (n=40) | 0.418 [0.33, 0.50] (n=141) |
| supported_claim_rate | 0.113 [0.07, 0.17] (n=40) | 0.165 [0.12, 0.20] (n=141) |
| citation_precision | 0.106 [0.07, 0.15] (n=40) | 0.169 [0.12, 0.21] (n=141) |
| hallucination_rate | 0.844 [0.78, 0.89] (n=40) | 0.799 [0.75, 0.85] (n=141) |
| lexical_ok | 0.938 [0.90, 0.97] (n=40) | 0.919 [0.88, 0.95] (n=141) |
| uncited_share | 0.034 [0.01, 0.07] (n=40) | 0.051 [0.03, 0.08] (n=141) |
| retrieval_completeness | 0.254 [0.19, 0.33] (n=40) | 0.426 [0.32, 0.53] (n=137) |
| expl_completeness_flag | 0.223 [0.15, 0.30] (n=40) | 0.356 [0.25, 0.47] (n=137) |
| expl_completeness_drop | 0.061 [0.02, 0.11] (n=40) | 0.131 [0.06, 0.21] (n=137) |

| type | n | correctness (flag) | supported-claim rate |
|---|---|---|---|
| as_of | 28 | 0.464 [0.25, 0.68] (n=28) | 0.199 [0.12, 0.29] (n=28) |
| change_over_time | 14 | 0.429 [0.29, 0.61] (n=14) | 0.161 [0.07, 0.27] (n=14) |
| decisions_about | 14 | 0.536 [0.39, 0.68] (n=14) | 0.202 [0.12, 0.30] (n=14) |
| distractor | 3 | 1.000 [1.00, 1.00] (n=3) | 0.333 [0.25, 0.50] (n=3) |
| evidence_to_reconsider | 12 | 0.333 [0.17, 0.50] (n=12) | 0.125 [0.05, 0.23] (n=12) |
| full_lineage | 14 | 0.286 [0.14, 0.39] (n=14) | 0.152 [0.07, 0.25] (n=14) |
| lookup_final | 14 | 0.643 [0.36, 0.86] (n=14) | 0.176 [0.10, 0.27] (n=14) |
| meetings_contributed | 14 | 0.143 [0.04, 0.25] (n=14) | 0.107 [0.05, 0.17] (n=14) |
| who_proposed | 14 | 0.357 [0.07, 0.64] (n=14) | 0.220 [0.10, 0.39] (n=14) |
| why_changed | 14 | 0.393 [0.23, 0.61] (n=14) | 0.062 [0.02, 0.10] (n=14) |

False premise: {'n': 2, 'regex_ok': 1, 'judge': [1.0, 0.0]}
Policy: {'rule': 'drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)', 'deltas': {'headline_correctness': 0.0, 'headline_completeness': -0.162, 'all_correctness': 0.0, 'all_completeness': -0.225}, 'chosen': 'flag'}
Latency: {'mean_s': 29.36, 'mean_in': 981, 'mean_out': 365}
