# Phase 5 DEV results, evowiki_style_k1 (final config single_pass_recap_roles_top4; bootstrap over sets)

141 answers, 141 parsed, 911 sentences, 0 unknown citation ids, 0 unparseable judge verdicts (counted incorrect).

| metric | headline | all types |
|---|---|---|
| correctness_flag | 0.400 [0.29, 0.50] (n=40) | 0.532 [0.46, 0.61] (n=141) |
| correctness_drop | 0.412 [0.33, 0.49] (n=40) | 0.532 [0.47, 0.60] (n=141) |
| supported_claim_rate | 0.127 [0.05, 0.21] (n=40) | 0.129 [0.07, 0.19] (n=141) |
| citation_precision | 0.125 [0.06, 0.20] (n=40) | 0.125 [0.07, 0.19] (n=141) |
| hallucination_rate | 0.826 [0.73, 0.92] (n=40) | 0.835 [0.77, 0.91] (n=141) |
| lexical_ok | 0.923 [0.87, 0.96] (n=40) | 0.905 [0.86, 0.94] (n=141) |
| uncited_share | 0.021 [0.00, 0.05] (n=40) | 0.026 [0.00, 0.06] (n=141) |
| retrieval_completeness | 0.328 [0.25, 0.41] (n=40) | 0.620 [0.57, 0.68] (n=137) |
| expl_completeness_flag | 0.235 [0.17, 0.31] (n=40) | 0.521 [0.44, 0.60] (n=137) |
| expl_completeness_drop | 0.053 [0.03, 0.08] (n=40) | 0.119 [0.07, 0.18] (n=137) |

| type | n | correctness (flag) | supported-claim rate |
|---|---|---|---|
| as_of | 28 | 0.643 [0.46, 0.82] (n=28) | 0.054 [0.02, 0.09] (n=28) |
| change_over_time | 14 | 0.429 [0.18, 0.68] (n=14) | 0.223 [0.09, 0.38] (n=14) |
| decisions_about | 14 | 0.571 [0.43, 0.71] (n=14) | 0.140 [0.05, 0.23] (n=14) |
| distractor | 3 | 0.833 [0.50, 1.00] (n=3) | 0.000 [0.00, 0.00] (n=3) |
| evidence_to_reconsider | 12 | 0.417 [0.25, 0.58] (n=12) | 0.073 [0.01, 0.17] (n=12) |
| full_lineage | 14 | 0.429 [0.29, 0.54] (n=14) | 0.140 [0.06, 0.23] (n=14) |
| lookup_final | 14 | 0.643 [0.36, 0.86] (n=14) | 0.134 [0.04, 0.25] (n=14) |
| meetings_contributed | 14 | 0.536 [0.50, 0.61] (n=14) | 0.125 [0.06, 0.19] (n=14) |
| who_proposed | 14 | 0.571 [0.29, 0.79] (n=14) | 0.205 [0.08, 0.36] (n=14) |
| why_changed | 14 | 0.357 [0.19, 0.50] (n=14) | 0.161 [0.06, 0.26] (n=14) |

False premise: {'n': 2, 'regex_ok': 1, 'judge': [0.0, 1.0]}
Policy: {'rule': 'drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)', 'deltas': {'headline_correctness': 0.012, 'headline_completeness': -0.182, 'all_correctness': 0.0, 'all_completeness': -0.402}, 'chosen': 'flag'}
Latency: {'mean_s': 27.01, 'mean_in': 1196, 'mean_out': 312}
