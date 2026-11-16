# Phase 5 DEV results, evowiki_style_k10 (final config single_pass_recap_roles_top4; bootstrap over sets)

141 answers, 136 parsed, 852 sentences, 0 unknown citation ids, 0 unparseable judge verdicts (counted incorrect).

| metric | headline | all types |
|---|---|---|
| correctness_flag | 0.275 [0.19, 0.37] (n=40) | 0.383 [0.33, 0.44] (n=141) |
| correctness_drop | 0.312 [0.23, 0.41] (n=40) | 0.390 [0.34, 0.45] (n=141) |
| supported_claim_rate | 0.093 [0.05, 0.13] (n=40) | 0.121 [0.08, 0.16] (n=141) |
| citation_precision | 0.117 [0.07, 0.17] (n=40) | 0.147 [0.10, 0.20] (n=136) |
| hallucination_rate | 0.909 [0.87, 0.95] (n=40) | 0.866 [0.82, 0.91] (n=136) |
| lexical_ok | 0.905 [0.86, 0.95] (n=40) | 0.848 [0.79, 0.90] (n=136) |
| uncited_share | 0.013 [0.00, 0.04] (n=40) | 0.066 [0.02, 0.13] (n=136) |
| retrieval_completeness | 0.295 [0.23, 0.37] (n=40) | 0.562 [0.48, 0.64] (n=137) |
| expl_completeness_flag | 0.230 [0.16, 0.29] (n=40) | 0.406 [0.31, 0.51] (n=137) |
| expl_completeness_drop | 0.023 [0.01, 0.04] (n=40) | 0.128 [0.07, 0.21] (n=137) |

| type | n | correctness (flag) | supported-claim rate |
|---|---|---|---|
| as_of | 28 | 0.464 [0.25, 0.68] (n=28) | 0.053 [0.02, 0.10] (n=25) |
| change_over_time | 14 | 0.464 [0.32, 0.61] (n=14) | 0.134 [0.05, 0.22] (n=14) |
| decisions_about | 14 | 0.571 [0.50, 0.68] (n=14) | 0.211 [0.12, 0.31] (n=14) |
| distractor | 3 | 0.667 [0.00, 1.00] (n=3) | 0.153 [0.04, 0.33] (n=3) |
| evidence_to_reconsider | 12 | 0.292 [0.17, 0.42] (n=12) | 0.080 [0.02, 0.15] (n=12) |
| full_lineage | 14 | 0.286 [0.14, 0.39] (n=14) | 0.116 [0.04, 0.20] (n=14) |
| lookup_final | 14 | 0.429 [0.21, 0.71] (n=14) | 0.152 [0.09, 0.23] (n=14) |
| meetings_contributed | 14 | 0.036 [0.00, 0.11] (n=14) | 0.223 [0.12, 0.33] (n=14) |
| who_proposed | 14 | 0.500 [0.21, 0.79] (n=14) | 0.122 [0.00, 0.30] (n=12) |
| why_changed | 14 | 0.250 [0.12, 0.42] (n=14) | 0.080 [0.02, 0.14] (n=14) |

False premise: {'n': 2, 'regex_ok': 0, 'judge': [0.0, 0.0]}
Policy: {'rule': 'drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)', 'deltas': {'headline_correctness': 0.037, 'headline_completeness': -0.207, 'all_correctness': 0.007, 'all_completeness': -0.278}, 'chosen': 'flag'}
Latency: {'mean_s': 46.91, 'mean_in': 7665, 'mean_out': 354}
