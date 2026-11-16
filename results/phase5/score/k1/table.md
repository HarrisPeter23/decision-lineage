# Phase 5 DEV results, k1 (final config single_pass_recap_roles_top4; bootstrap over sets)

141 answers, 141 parsed, 903 sentences, 0 unknown citation ids, 0 unparseable judge verdicts (counted incorrect).

| metric | headline | all types |
|---|---|---|
| correctness_flag | 0.562 [0.46, 0.67] (n=40) | 0.649 [0.54, 0.74] (n=141) |
| correctness_drop | 0.512 [0.43, 0.60] (n=40) | 0.628 [0.53, 0.71] (n=141) |
| supported_claim_rate | 0.484 [0.42, 0.55] (n=40) | 0.446 [0.39, 0.50] (n=141) |
| citation_precision | 0.446 [0.38, 0.52] (n=40) | 0.433 [0.37, 0.49] (n=141) |
| hallucination_rate | 0.466 [0.39, 0.55] (n=40) | 0.499 [0.45, 0.57] (n=141) |
| lexical_ok | 0.706 [0.58, 0.82] (n=40) | 0.653 [0.59, 0.71] (n=141) |
| uncited_share | 0.019 [0.00, 0.05] (n=40) | 0.024 [0.01, 0.04] (n=141) |
| retrieval_completeness | 0.633 [0.54, 0.72] (n=40) | 0.621 [0.53, 0.70] (n=137) |
| expl_completeness_flag | 0.615 [0.53, 0.70] (n=40) | 0.601 [0.52, 0.68] (n=137) |
| expl_completeness_drop | 0.448 [0.36, 0.53] (n=40) | 0.441 [0.35, 0.53] (n=137) |

| type | n | correctness (flag) | supported-claim rate |
|---|---|---|---|
| as_of | 28 | 0.714 [0.50, 0.89] (n=28) | 0.393 [0.26, 0.52] (n=28) |
| change_over_time | 14 | 0.464 [0.25, 0.68] (n=14) | 0.404 [0.24, 0.55] (n=14) |
| decisions_about | 14 | 0.679 [0.46, 0.86] (n=14) | 0.554 [0.36, 0.75] (n=14) |
| distractor | 3 | 0.667 [0.00, 1.00] (n=3) | 0.500 [0.00, 0.83] (n=3) |
| evidence_to_reconsider | 12 | 0.750 [0.62, 0.88] (n=12) | 0.469 [0.31, 0.62] (n=12) |
| full_lineage | 14 | 0.429 [0.29, 0.57] (n=14) | 0.518 [0.45, 0.59] (n=14) |
| lookup_final | 14 | 0.857 [0.64, 1.00] (n=14) | 0.409 [0.30, 0.53] (n=14) |
| meetings_contributed | 14 | 0.643 [0.54, 0.79] (n=14) | 0.482 [0.35, 0.60] (n=14) |
| who_proposed | 14 | 0.714 [0.50, 0.93] (n=14) | 0.368 [0.17, 0.57] (n=14) |
| why_changed | 14 | 0.536 [0.36, 0.71] (n=14) | 0.464 [0.36, 0.60] (n=14) |

False premise: {'n': 2, 'regex_ok': 2, 'judge': [0.5, 0.5]}
Policy: {'rule': 'drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)', 'deltas': {'headline_correctness': -0.05, 'headline_completeness': -0.167, 'all_correctness': -0.021, 'all_completeness': -0.16}, 'chosen': 'flag'}
Latency: {'mean_s': 20.48, 'mean_in': 712, 'mean_out': 293}
