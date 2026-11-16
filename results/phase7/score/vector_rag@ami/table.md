# Phase 5 DEV results, vector_rag@ami (final config single_pass_recap_roles_top4; bootstrap over sets)

50 answers, 50 parsed, 386 sentences, 0 unknown citation ids, 0 unparseable judge verdicts (counted incorrect).

| metric | headline | all types |
|---|---|---|
| correctness_flag | 0.200 [0.07, 0.37] (n=15) | 0.360 [0.22, 0.55] (n=50) |
| correctness_drop | 0.200 [0.07, 0.37] (n=15) | 0.380 [0.23, 0.57] (n=50) |
| supported_claim_rate | 0.333 [0.25, 0.41] (n=15) | 0.312 [0.24, 0.39] (n=50) |
| citation_precision | 0.336 [0.27, 0.39] (n=15) | 0.303 [0.23, 0.38] (n=50) |
| hallucination_rate | 0.517 [0.40, 0.64] (n=15) | 0.555 [0.45, 0.67] (n=50) |
| lexical_ok | 0.850 [0.72, 0.93] (n=15) | 0.848 [0.78, 0.90] (n=50) |
| uncited_share | 0.000 [0.00, 0.00] (n=15) | 0.003 [0.00, 0.01] (n=50) |
| retrieval_completeness | 0.222 [0.02, 0.48] (n=15) | 0.191 [0.03, 0.36] (n=47) |
| expl_completeness_flag | 0.222 [0.02, 0.48] (n=15) | 0.188 [0.03, 0.36] (n=47) |
| expl_completeness_drop | 0.127 [0.01, 0.27] (n=15) | 0.132 [0.03, 0.24] (n=47) |

| type | n | correctness (flag) | supported-claim rate |
|---|---|---|---|
| as_of | 10 | 0.700 [0.50, 0.90] (n=10) | 0.312 [0.21, 0.39] (n=10) |
| change_over_time | 5 | 0.400 [0.10, 0.70] (n=5) | 0.200 [0.07, 0.38] (n=5) |
| decisions_about | 5 | 0.100 [0.00, 0.30] (n=5) | 0.175 [0.07, 0.28] (n=5) |
| evidence_to_reconsider | 4 | 0.250 [0.00, 0.50] (n=4) | 0.312 [0.25, 0.38] (n=4) |
| full_lineage | 5 | 0.100 [0.00, 0.30] (n=5) | 0.325 [0.15, 0.47] (n=5) |
| lookup_final | 5 | 0.400 [0.00, 0.80] (n=5) | 0.275 [0.20, 0.35] (n=5) |
| meetings_contributed | 5 | 0.500 [0.50, 0.50] (n=5) | 0.500 [0.23, 0.78] (n=5) |
| who_proposed | 5 | 0.200 [0.00, 0.60] (n=5) | 0.350 [0.03, 0.70] (n=5) |
| why_changed | 6 | 0.250 [0.08, 0.42] (n=6) | 0.354 [0.23, 0.45] (n=6) |

False premise: {'n': 1, 'regex_ok': 0, 'judge': [0.0]}
Policy: {'rule': 'drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)', 'deltas': {'headline_correctness': 0.0, 'headline_completeness': -0.095, 'all_correctness': 0.02, 'all_completeness': -0.056}, 'chosen': 'flag'}
Latency: {'mean_s': 28.94, 'mean_in': 2137, 'mean_out': 366}
