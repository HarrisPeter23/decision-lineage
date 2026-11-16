# Phase 5 DEV results, evowiki_style@ami (final config single_pass_recap_roles_top4; bootstrap over sets)

50 answers, 50 parsed, 315 sentences, 0 unknown citation ids, 0 unparseable judge verdicts (counted incorrect).

| metric | headline | all types |
|---|---|---|
| correctness_flag | 0.200 [0.08, 0.37] (n=15) | 0.380 [0.27, 0.50] (n=50) |
| correctness_drop | 0.233 [0.10, 0.39] (n=15) | 0.400 [0.29, 0.53] (n=50) |
| supported_claim_rate | 0.125 [0.03, 0.23] (n=15) | 0.122 [0.01, 0.24] (n=50) |
| citation_precision | 0.112 [0.05, 0.17] (n=15) | 0.104 [0.02, 0.21] (n=50) |
| hallucination_rate | 0.808 [0.72, 0.90] (n=15) | 0.809 [0.70, 0.91] (n=50) |
| lexical_ok | 0.703 [0.54, 0.88] (n=15) | 0.806 [0.73, 0.90] (n=50) |
| uncited_share | 0.175 [0.04, 0.36] (n=15) | 0.080 [0.03, 0.12] (n=50) |
| retrieval_completeness | 0.192 [0.10, 0.32] (n=15) | 0.218 [0.14, 0.32] (n=47) |
| expl_completeness_flag | 0.126 [0.08, 0.20] (n=15) | 0.179 [0.09, 0.29] (n=47) |
| expl_completeness_drop | 0.022 [0.00, 0.07] (n=15) | 0.042 [0.00, 0.11] (n=47) |

| type | n | correctness (flag) | supported-claim rate |
|---|---|---|---|
| as_of | 10 | 0.400 [0.20, 0.50] (n=10) | 0.100 [0.01, 0.21] (n=10) |
| change_over_time | 5 | 0.300 [0.10, 0.50] (n=5) | 0.200 [0.00, 0.60] (n=5) |
| decisions_about | 5 | 0.400 [0.20, 0.50] (n=5) | 0.100 [0.00, 0.20] (n=5) |
| evidence_to_reconsider | 4 | 0.125 [0.00, 0.38] (n=4) | 0.062 [0.00, 0.12] (n=4) |
| full_lineage | 5 | 0.400 [0.20, 0.50] (n=5) | 0.200 [0.03, 0.40] (n=5) |
| lookup_final | 5 | 1.000 [1.00, 1.00] (n=5) | 0.150 [0.00, 0.38] (n=5) |
| meetings_contributed | 5 | 0.500 [0.50, 0.50] (n=5) | 0.075 [0.00, 0.23] (n=5) |
| who_proposed | 5 | 0.200 [0.00, 0.60] (n=5) | 0.125 [0.00, 0.38] (n=5) |
| why_changed | 6 | 0.083 [0.00, 0.30] (n=6) | 0.104 [0.02, 0.23] (n=6) |

False premise: {'n': 1, 'regex_ok': 0, 'judge': [0.0]}
Policy: {'rule': 'drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)', 'deltas': {'headline_correctness': 0.033, 'headline_completeness': -0.104, 'all_correctness': 0.02, 'all_completeness': -0.137}, 'chosen': 'flag'}
Latency: {'mean_s': 25.55, 'mean_in': 2073, 'mean_out': 315}
