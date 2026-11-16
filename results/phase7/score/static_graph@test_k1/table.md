# Phase 5 DEV results, static_graph@test_k1 (final config single_pass_recap_roles_top4; bootstrap over sets)

232 answers, 232 parsed, 1358 sentences, 0 unknown citation ids, 0 unparseable judge verdicts (counted incorrect).

| metric | headline | all types |
|---|---|---|
| correctness_flag | 0.415 [0.35, 0.48] (n=65) | 0.614 [0.55, 0.68] (n=232) |
| correctness_drop | 0.423 [0.36, 0.48] (n=65) | 0.616 [0.56, 0.68] (n=232) |
| supported_claim_rate | 0.392 [0.32, 0.46] (n=65) | 0.390 [0.33, 0.45] (n=232) |
| citation_precision | 0.399 [0.34, 0.46] (n=61) | 0.404 [0.35, 0.46] (n=224) |
| hallucination_rate | 0.539 [0.47, 0.61] (n=61) | 0.543 [0.49, 0.59] (n=224) |
| lexical_ok | 0.702 [0.63, 0.76] (n=61) | 0.732 [0.68, 0.78] (n=224) |
| uncited_share | 0.000 [0.00, 0.00] (n=61) | 0.019 [0.01, 0.03] (n=224) |
| retrieval_completeness | 0.435 [0.33, 0.55] (n=65) | 0.590 [0.49, 0.68] (n=230) |
| expl_completeness_flag | 0.409 [0.31, 0.50] (n=65) | 0.571 [0.47, 0.66] (n=230) |
| expl_completeness_drop | 0.269 [0.20, 0.33] (n=65) | 0.358 [0.28, 0.44] (n=230) |

| type | n | correctness (flag) | supported-claim rate |
|---|---|---|---|
| as_of | 44 | 0.636 [0.50, 0.77] (n=44) | 0.416 [0.32, 0.53] (n=44) |
| change_over_time | 22 | 0.500 [0.32, 0.70] (n=22) | 0.353 [0.23, 0.49] (n=20) |
| decisions_about | 22 | 0.614 [0.46, 0.77] (n=22) | 0.485 [0.34, 0.64] (n=20) |
| distractor | 13 | 0.885 [0.69, 1.00] (n=13) | 0.290 [0.14, 0.45] (n=13) |
| evidence_to_reconsider | 20 | 0.425 [0.30, 0.57] (n=20) | 0.395 [0.29, 0.49] (n=17) |
| full_lineage | 22 | 0.409 [0.29, 0.50] (n=22) | 0.449 [0.35, 0.55] (n=22) |
| lookup_final | 22 | 0.773 [0.59, 0.91] (n=22) | 0.468 [0.38, 0.56] (n=22) |
| meetings_contributed | 22 | 0.750 [0.64, 0.86] (n=22) | 0.489 [0.40, 0.58] (n=22) |
| who_proposed | 22 | 0.818 [0.64, 0.95] (n=22) | 0.239 [0.10, 0.41] (n=22) |
| why_changed | 23 | 0.413 [0.31, 0.50] (n=23) | 0.403 [0.31, 0.49] (n=22) |

False premise: {'n': 4, 'regex_ok': 1, 'judge': [1.0, 0.0, 0.0, 0.0]}
Policy: {'rule': 'drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)', 'deltas': {'headline_correctness': 0.008, 'headline_completeness': -0.14, 'all_correctness': 0.002, 'all_completeness': -0.213}, 'chosen': 'flag'}
Latency: {'mean_s': 23.05, 'mean_in': 635, 'mean_out': 280}
