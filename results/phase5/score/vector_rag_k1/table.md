# Phase 5 DEV results, vector_rag_k1 (final config single_pass_recap_roles_top4; bootstrap over sets)

141 answers, 141 parsed, 1117 sentences, 0 unknown citation ids, 0 unparseable judge verdicts (counted incorrect).

| metric | headline | all types |
|---|---|---|
| correctness_flag | 0.525 [0.42, 0.62] (n=40) | 0.606 [0.51, 0.71] (n=141) |
| correctness_drop | 0.525 [0.43, 0.62] (n=40) | 0.578 [0.48, 0.67] (n=141) |
| supported_claim_rate | 0.388 [0.32, 0.45] (n=40) | 0.404 [0.34, 0.47] (n=141) |
| citation_precision | 0.403 [0.33, 0.47] (n=40) | 0.401 [0.34, 0.46] (n=141) |
| hallucination_rate | 0.522 [0.46, 0.59] (n=40) | 0.500 [0.44, 0.56] (n=141) |
| lexical_ok | 0.900 [0.84, 0.95] (n=40) | 0.896 [0.85, 0.93] (n=141) |
| uncited_share | 0.000 [0.00, 0.00] (n=40) | 0.002 [0.00, 0.01] (n=141) |
| retrieval_completeness | 0.576 [0.46, 0.69] (n=40) | 0.566 [0.45, 0.68] (n=137) |
| expl_completeness_flag | 0.561 [0.44, 0.69] (n=40) | 0.555 [0.44, 0.67] (n=137) |
| expl_completeness_drop | 0.317 [0.22, 0.41] (n=40) | 0.360 [0.26, 0.46] (n=137) |

| type | n | correctness (flag) | supported-claim rate |
|---|---|---|---|
| as_of | 28 | 0.429 [0.18, 0.68] (n=28) | 0.464 [0.35, 0.56] (n=28) |
| change_over_time | 14 | 0.571 [0.39, 0.75] (n=14) | 0.295 [0.19, 0.42] (n=14) |
| decisions_about | 14 | 0.750 [0.61, 0.89] (n=14) | 0.482 [0.35, 0.62] (n=14) |
| distractor | 3 | 1.000 [1.00, 1.00] (n=3) | 0.417 [0.12, 0.58] (n=3) |
| evidence_to_reconsider | 12 | 0.542 [0.33, 0.75] (n=12) | 0.396 [0.27, 0.53] (n=12) |
| full_lineage | 14 | 0.429 [0.32, 0.50] (n=14) | 0.375 [0.29, 0.46] (n=14) |
| lookup_final | 14 | 0.714 [0.50, 0.93] (n=14) | 0.464 [0.40, 0.52] (n=14) |
| meetings_contributed | 14 | 0.786 [0.64, 0.89] (n=14) | 0.307 [0.17, 0.44] (n=14) |
| who_proposed | 14 | 0.714 [0.50, 0.93] (n=14) | 0.393 [0.24, 0.55] (n=14) |
| why_changed | 14 | 0.607 [0.43, 0.79] (n=14) | 0.393 [0.26, 0.53] (n=14) |

False premise: {'n': 2, 'regex_ok': 0, 'judge': [0.0, 0.0]}
Policy: {'rule': 'drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)', 'deltas': {'headline_correctness': 0.0, 'headline_completeness': -0.244, 'all_correctness': -0.028, 'all_completeness': -0.195}, 'chosen': 'flag'}
Latency: {'mean_s': 34.87, 'mean_in': 1561, 'mean_out': 402}
