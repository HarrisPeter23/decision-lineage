# Phase 5 DEV results, lineage@test_k1 (final config single_pass_recap_roles_top4; bootstrap over sets)

232 answers, 232 parsed, 1229 sentences, 3 unknown citation ids, 0 unparseable judge verdicts (counted incorrect).

| metric | headline | all types |
|---|---|---|
| correctness_flag | 0.331 [0.25, 0.41] (n=65) | 0.534 [0.45, 0.61] (n=232) |
| correctness_drop | 0.331 [0.25, 0.40] (n=65) | 0.532 [0.45, 0.61] (n=232) |
| supported_claim_rate | 0.315 [0.24, 0.39] (n=65) | 0.391 [0.33, 0.45] (n=232) |
| citation_precision | 0.311 [0.24, 0.38] (n=64) | 0.398 [0.34, 0.46] (n=227) |
| hallucination_rate | 0.645 [0.57, 0.71] (n=64) | 0.546 [0.49, 0.60] (n=227) |
| lexical_ok | 0.596 [0.52, 0.66] (n=64) | 0.665 [0.61, 0.72] (n=227) |
| uncited_share | 0.090 [0.04, 0.15] (n=64) | 0.044 [0.03, 0.06] (n=227) |
| retrieval_completeness | 0.369 [0.27, 0.47] (n=65) | 0.524 [0.43, 0.62] (n=230) |
| expl_completeness_flag | 0.357 [0.27, 0.45] (n=65) | 0.513 [0.42, 0.60] (n=230) |
| expl_completeness_drop | 0.194 [0.13, 0.26] (n=65) | 0.323 [0.25, 0.40] (n=230) |

| type | n | correctness (flag) | supported-claim rate |
|---|---|---|---|
| as_of | 44 | 0.591 [0.43, 0.73] (n=44) | 0.455 [0.34, 0.59] (n=44) |
| change_over_time | 22 | 0.364 [0.20, 0.55] (n=22) | 0.446 [0.32, 0.58] (n=20) |
| decisions_about | 22 | 0.568 [0.43, 0.70] (n=22) | 0.560 [0.41, 0.71] (n=20) |
| distractor | 13 | 0.808 [0.61, 1.00] (n=13) | 0.463 [0.29, 0.65] (n=13) |
| evidence_to_reconsider | 20 | 0.350 [0.23, 0.50] (n=20) | 0.305 [0.19, 0.43] (n=19) |
| full_lineage | 22 | 0.432 [0.32, 0.52] (n=22) | 0.451 [0.36, 0.53] (n=22) |
| lookup_final | 22 | 0.727 [0.55, 0.91] (n=22) | 0.339 [0.20, 0.50] (n=22) |
| meetings_contributed | 22 | 0.568 [0.48, 0.66] (n=22) | 0.432 [0.36, 0.49] (n=22) |
| who_proposed | 22 | 0.773 [0.59, 0.91] (n=22) | 0.323 [0.17, 0.51] (n=22) |
| why_changed | 23 | 0.217 [0.12, 0.33] (n=23) | 0.207 [0.12, 0.32] (n=23) |

False premise: {'n': 4, 'regex_ok': 2, 'judge': [0.5, 0.0, 0.5, 0.0]}
Policy: {'rule': 'drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)', 'deltas': {'headline_correctness': 0.0, 'headline_completeness': -0.163, 'all_correctness': -0.002, 'all_completeness': -0.19}, 'chosen': 'flag'}
Latency: {'mean_s': 20.47, 'mean_in': 613, 'mean_out': 245}
