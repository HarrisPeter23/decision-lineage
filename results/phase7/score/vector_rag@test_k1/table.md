# Phase 5 DEV results, vector_rag@test_k1 (final config single_pass_recap_roles_top4; bootstrap over sets)

232 answers, 232 parsed, 1834 sentences, 0 unknown citation ids, 0 unparseable judge verdicts (counted incorrect).

| metric | headline | all types |
|---|---|---|
| correctness_flag | 0.438 [0.37, 0.52] (n=65) | 0.582 [0.52, 0.64] (n=232) |
| correctness_drop | 0.446 [0.38, 0.52] (n=65) | 0.582 [0.52, 0.65] (n=232) |
| supported_claim_rate | 0.442 [0.38, 0.50] (n=65) | 0.427 [0.38, 0.47] (n=232) |
| citation_precision | 0.444 [0.39, 0.50] (n=65) | 0.416 [0.37, 0.46] (n=232) |
| hallucination_rate | 0.479 [0.44, 0.53] (n=65) | 0.488 [0.45, 0.53] (n=232) |
| lexical_ok | 0.908 [0.88, 0.94] (n=65) | 0.894 [0.86, 0.92] (n=232) |
| uncited_share | 0.000 [0.00, 0.00] (n=65) | 0.002 [0.00, 0.01] (n=232) |
| retrieval_completeness | 0.410 [0.34, 0.48] (n=65) | 0.483 [0.40, 0.56] (n=230) |
| expl_completeness_flag | 0.359 [0.29, 0.43] (n=65) | 0.460 [0.37, 0.54] (n=230) |
| expl_completeness_drop | 0.181 [0.13, 0.23] (n=65) | 0.280 [0.21, 0.34] (n=230) |

| type | n | correctness (flag) | supported-claim rate |
|---|---|---|---|
| as_of | 44 | 0.659 [0.50, 0.82] (n=44) | 0.511 [0.43, 0.59] (n=44) |
| change_over_time | 22 | 0.477 [0.34, 0.61] (n=22) | 0.364 [0.28, 0.44] (n=22) |
| decisions_about | 22 | 0.591 [0.46, 0.73] (n=22) | 0.426 [0.35, 0.50] (n=22) |
| distractor | 13 | 1.000 [1.00, 1.00] (n=13) | 0.529 [0.42, 0.64] (n=13) |
| evidence_to_reconsider | 20 | 0.525 [0.40, 0.68] (n=20) | 0.450 [0.36, 0.54] (n=20) |
| full_lineage | 22 | 0.409 [0.32, 0.48] (n=22) | 0.438 [0.35, 0.52] (n=22) |
| lookup_final | 22 | 0.727 [0.55, 0.91] (n=22) | 0.432 [0.35, 0.51] (n=22) |
| meetings_contributed | 22 | 0.682 [0.59, 0.77] (n=22) | 0.335 [0.26, 0.43] (n=22) |
| who_proposed | 22 | 0.455 [0.27, 0.64] (n=22) | 0.307 [0.22, 0.40] (n=22) |
| why_changed | 23 | 0.391 [0.29, 0.50] (n=23) | 0.440 [0.34, 0.54] (n=23) |

False premise: {'n': 4, 'regex_ok': 1, 'judge': [0.5, 0.0, 0.0, 0.0]}
Policy: {'rule': 'drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)', 'deltas': {'headline_correctness': 0.008, 'headline_completeness': -0.178, 'all_correctness': 0.0, 'all_completeness': -0.18}, 'chosen': 'flag'}
Latency: {'mean_s': 33.06, 'mean_in': 1473, 'mean_out': 391}
