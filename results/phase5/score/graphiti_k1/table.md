# Phase 5 DEV results, graphiti_k1 (final config single_pass_recap_roles_top4; bootstrap over sets)

141 answers, 141 parsed, 1047 sentences, 0 unknown citation ids, 0 unparseable judge verdicts (counted incorrect).

| metric | headline | all types |
|---|---|---|
| correctness_flag | 0.425 [0.30, 0.54] (n=40) | 0.589 [0.48, 0.69] (n=141) |
| correctness_drop | 0.412 [0.30, 0.52] (n=40) | 0.578 [0.46, 0.68] (n=141) |
| supported_claim_rate | 0.283 [0.21, 0.37] (n=40) | 0.282 [0.22, 0.35] (n=141) |
| citation_precision | 0.279 [0.20, 0.36] (n=40) | 0.282 [0.22, 0.35] (n=141) |
| hallucination_rate | 0.658 [0.57, 0.74] (n=40) | 0.662 [0.59, 0.73] (n=141) |
| lexical_ok | 0.994 [0.98, 1.00] (n=40) | 0.968 [0.95, 0.99] (n=141) |
| uncited_share | 0.000 [0.00, 0.00] (n=40) | 0.008 [0.00, 0.02] (n=141) |
| retrieval_completeness | 0.440 [0.32, 0.56] (n=40) | 0.559 [0.47, 0.65] (n=137) |
| expl_completeness_flag | 0.392 [0.28, 0.51] (n=40) | 0.510 [0.41, 0.60] (n=137) |
| expl_completeness_drop | 0.154 [0.09, 0.22] (n=40) | 0.194 [0.13, 0.27] (n=137) |

| type | n | correctness (flag) | supported-claim rate |
|---|---|---|---|
| as_of | 28 | 0.536 [0.32, 0.71] (n=28) | 0.326 [0.25, 0.41] (n=28) |
| change_over_time | 14 | 0.714 [0.57, 0.86] (n=14) | 0.250 [0.14, 0.37] (n=14) |
| decisions_about | 14 | 0.643 [0.50, 0.79] (n=14) | 0.277 [0.17, 0.38] (n=14) |
| distractor | 3 | 0.667 [0.00, 1.00] (n=3) | 0.208 [0.00, 0.38] (n=3) |
| evidence_to_reconsider | 12 | 0.500 [0.29, 0.71] (n=12) | 0.292 [0.19, 0.41] (n=12) |
| full_lineage | 14 | 0.357 [0.25, 0.46] (n=14) | 0.273 [0.17, 0.37] (n=14) |
| lookup_final | 14 | 0.643 [0.36, 0.86] (n=14) | 0.304 [0.20, 0.42] (n=14) |
| meetings_contributed | 14 | 0.643 [0.54, 0.75] (n=14) | 0.321 [0.25, 0.39] (n=14) |
| who_proposed | 14 | 0.857 [0.64, 1.00] (n=14) | 0.179 [0.07, 0.29] (n=14) |
| why_changed | 14 | 0.429 [0.29, 0.58] (n=14) | 0.286 [0.17, 0.39] (n=14) |

False premise: {'n': 2, 'regex_ok': 1, 'judge': [0.5, 0.0]}
Policy: {'rule': 'drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)', 'deltas': {'headline_correctness': -0.013, 'headline_completeness': -0.238, 'all_correctness': -0.011, 'all_completeness': -0.316}, 'chosen': 'flag'}
Latency: {'mean_s': 29.56, 'mean_in': 1010, 'mean_out': 366}
