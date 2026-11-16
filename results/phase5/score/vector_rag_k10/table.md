# Phase 5 DEV results, vector_rag_k10 (final config single_pass_recap_roles_top4; bootstrap over sets)

141 answers, 141 parsed, 1076 sentences, 0 unknown citation ids, 0 unparseable judge verdicts (counted incorrect).

| metric | headline | all types |
|---|---|---|
| correctness_flag | 0.237 [0.13, 0.38] (n=40) | 0.372 [0.27, 0.48] (n=141) |
| correctness_drop | 0.312 [0.19, 0.45] (n=40) | 0.404 [0.30, 0.50] (n=141) |
| supported_claim_rate | 0.396 [0.34, 0.46] (n=40) | 0.394 [0.35, 0.44] (n=141) |
| citation_precision | 0.384 [0.32, 0.46] (n=40) | 0.389 [0.34, 0.44] (n=141) |
| hallucination_rate | 0.529 [0.47, 0.59] (n=40) | 0.536 [0.48, 0.59] (n=141) |
| lexical_ok | 0.875 [0.82, 0.93] (n=40) | 0.848 [0.82, 0.87] (n=141) |
| uncited_share | 0.000 [0.00, 0.00] (n=40) | 0.012 [0.00, 0.03] (n=141) |
| retrieval_completeness | 0.322 [0.23, 0.43] (n=40) | 0.363 [0.28, 0.44] (n=137) |
| expl_completeness_flag | 0.317 [0.22, 0.43] (n=40) | 0.344 [0.26, 0.43] (n=137) |
| expl_completeness_drop | 0.193 [0.12, 0.28] (n=40) | 0.216 [0.15, 0.29] (n=137) |

| type | n | correctness (flag) | supported-claim rate |
|---|---|---|---|
| as_of | 28 | 0.429 [0.21, 0.64] (n=28) | 0.357 [0.25, 0.45] (n=28) |
| change_over_time | 14 | 0.321 [0.18, 0.50] (n=14) | 0.355 [0.21, 0.50] (n=14) |
| decisions_about | 14 | 0.500 [0.32, 0.68] (n=14) | 0.595 [0.50, 0.69] (n=14) |
| distractor | 3 | 1.000 [1.00, 1.00] (n=3) | 0.333 [0.12, 0.62] (n=3) |
| evidence_to_reconsider | 12 | 0.292 [0.08, 0.50] (n=12) | 0.360 [0.26, 0.47] (n=12) |
| full_lineage | 14 | 0.214 [0.07, 0.36] (n=14) | 0.446 [0.37, 0.54] (n=14) |
| lookup_final | 14 | 0.500 [0.29, 0.71] (n=14) | 0.454 [0.37, 0.54] (n=14) |
| meetings_contributed | 14 | 0.107 [0.00, 0.29] (n=14) | 0.268 [0.16, 0.38] (n=14) |
| who_proposed | 14 | 0.571 [0.36, 0.86] (n=14) | 0.384 [0.26, 0.51] (n=14) |
| why_changed | 14 | 0.214 [0.07, 0.39] (n=14) | 0.375 [0.27, 0.51] (n=14) |

False premise: {'n': 2, 'regex_ok': 0, 'judge': [0.0, 0.0]}
Policy: {'rule': 'drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)', 'deltas': {'headline_correctness': 0.075, 'headline_completeness': -0.124, 'all_correctness': 0.032, 'all_completeness': -0.128}, 'chosen': 'flag'}
Latency: {'mean_s': 33.98, 'mean_in': 1598, 'mean_out': 388}
