# Phase 5 DEV results, no_typing@test_k1 (final config single_pass_recap_roles_top4; bootstrap over sets)

232 answers, 232 parsed, 1272 sentences, 0 unknown citation ids, 0 unparseable judge verdicts (counted incorrect).

| metric | headline | all types |
|---|---|---|
| correctness_flag | 0.338 [0.25, 0.42] (n=65) | 0.537 [0.45, 0.61] (n=232) |
| correctness_drop | 0.362 [0.27, 0.45] (n=65) | 0.539 [0.45, 0.62] (n=232) |
| supported_claim_rate | 0.312 [0.26, 0.37] (n=65) | 0.389 [0.33, 0.45] (n=232) |
| citation_precision | 0.300 [0.25, 0.35] (n=64) | 0.394 [0.34, 0.45] (n=227) |
| hallucination_rate | 0.635 [0.57, 0.69] (n=64) | 0.543 [0.49, 0.60] (n=227) |
| lexical_ok | 0.597 [0.53, 0.66] (n=64) | 0.662 [0.61, 0.71] (n=227) |
| uncited_share | 0.048 [0.01, 0.09] (n=64) | 0.026 [0.01, 0.05] (n=227) |
| retrieval_completeness | 0.391 [0.29, 0.49] (n=65) | 0.530 [0.43, 0.62] (n=230) |
| expl_completeness_flag | 0.367 [0.28, 0.46] (n=65) | 0.515 [0.42, 0.60] (n=230) |
| expl_completeness_drop | 0.185 [0.14, 0.23] (n=65) | 0.323 [0.25, 0.40] (n=230) |

| type | n | correctness (flag) | supported-claim rate |
|---|---|---|---|
| as_of | 44 | 0.591 [0.43, 0.73] (n=44) | 0.415 [0.31, 0.53] (n=44) |
| change_over_time | 22 | 0.364 [0.20, 0.55] (n=22) | 0.446 [0.32, 0.58] (n=20) |
| decisions_about | 22 | 0.568 [0.43, 0.70] (n=22) | 0.560 [0.41, 0.71] (n=20) |
| distractor | 13 | 0.846 [0.65, 1.00] (n=13) | 0.492 [0.32, 0.67] (n=13) |
| evidence_to_reconsider | 20 | 0.375 [0.25, 0.53] (n=20) | 0.307 [0.22, 0.40] (n=19) |
| full_lineage | 22 | 0.409 [0.32, 0.48] (n=22) | 0.445 [0.37, 0.51] (n=22) |
| lookup_final | 22 | 0.727 [0.55, 0.91] (n=22) | 0.329 [0.21, 0.47] (n=22) |
| meetings_contributed | 22 | 0.545 [0.46, 0.64] (n=22) | 0.499 [0.41, 0.57] (n=22) |
| who_proposed | 22 | 0.773 [0.59, 0.91] (n=22) | 0.323 [0.17, 0.51] (n=22) |
| why_changed | 23 | 0.239 [0.14, 0.35] (n=23) | 0.201 [0.12, 0.30] (n=23) |

False premise: {'n': 4, 'regex_ok': 2, 'judge': [0.5, 0.0, 0.5, 0.0]}
Policy: {'rule': 'drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)', 'deltas': {'headline_correctness': 0.024, 'headline_completeness': -0.182, 'all_correctness': 0.002, 'all_completeness': -0.192}, 'chosen': 'flag'}
Latency: {'mean_s': 21.15, 'mean_in': 631, 'mean_out': 256}
