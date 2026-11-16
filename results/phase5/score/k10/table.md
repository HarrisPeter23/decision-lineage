# Phase 5 DEV results, k10 (final config single_pass_recap_roles_top4; bootstrap over sets)

141 answers, 141 parsed, 869 sentences, 0 unknown citation ids, 0 unparseable judge verdicts (counted incorrect).

| metric | headline | all types |
|---|---|---|
| correctness_flag | 0.400 [0.26, 0.53] (n=40) | 0.521 [0.38, 0.66] (n=141) |
| correctness_drop | 0.388 [0.25, 0.52] (n=40) | 0.514 [0.38, 0.65] (n=141) |
| supported_claim_rate | 0.427 [0.35, 0.50] (n=40) | 0.433 [0.36, 0.51] (n=141) |
| citation_precision | 0.396 [0.33, 0.47] (n=40) | 0.428 [0.36, 0.51] (n=141) |
| hallucination_rate | 0.529 [0.46, 0.59] (n=40) | 0.529 [0.47, 0.59] (n=141) |
| lexical_ok | 0.753 [0.66, 0.84] (n=40) | 0.653 [0.59, 0.71] (n=141) |
| uncited_share | 0.025 [0.00, 0.08] (n=40) | 0.053 [0.04, 0.07] (n=141) |
| retrieval_completeness | 0.377 [0.23, 0.53] (n=40) | 0.457 [0.30, 0.61] (n=137) |
| expl_completeness_flag | 0.367 [0.23, 0.52] (n=40) | 0.446 [0.29, 0.60] (n=137) |
| expl_completeness_drop | 0.257 [0.15, 0.37] (n=40) | 0.335 [0.20, 0.46] (n=137) |

| type | n | correctness (flag) | supported-claim rate |
|---|---|---|---|
| as_of | 28 | 0.536 [0.36, 0.71] (n=28) | 0.402 [0.29, 0.51] (n=28) |
| change_over_time | 14 | 0.464 [0.25, 0.68] (n=14) | 0.467 [0.31, 0.60] (n=14) |
| decisions_about | 14 | 0.536 [0.29, 0.75] (n=14) | 0.533 [0.36, 0.71] (n=14) |
| distractor | 3 | 1.000 [1.00, 1.00] (n=3) | 0.467 [0.00, 1.00] (n=3) |
| evidence_to_reconsider | 12 | 0.417 [0.21, 0.62] (n=12) | 0.312 [0.17, 0.49] (n=12) |
| full_lineage | 14 | 0.357 [0.25, 0.46] (n=14) | 0.616 [0.53, 0.70] (n=14) |
| lookup_final | 14 | 0.643 [0.36, 0.86] (n=14) | 0.315 [0.20, 0.45] (n=14) |
| meetings_contributed | 14 | 0.536 [0.50, 0.61] (n=14) | 0.554 [0.41, 0.68] (n=14) |
| who_proposed | 14 | 0.643 [0.43, 0.86] (n=14) | 0.366 [0.18, 0.59] (n=14) |
| why_changed | 14 | 0.429 [0.19, 0.65] (n=14) | 0.335 [0.26, 0.42] (n=14) |

False premise: {'n': 2, 'regex_ok': 0, 'judge': [0.0, 0.0]}
Policy: {'rule': 'drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)', 'deltas': {'headline_correctness': -0.012, 'headline_completeness': -0.11, 'all_correctness': -0.007, 'all_completeness': -0.111}, 'chosen': 'flag'}
Latency: {'mean_s': 20.3, 'mean_in': 590, 'mean_out': 279}
