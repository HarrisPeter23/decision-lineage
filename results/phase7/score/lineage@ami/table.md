# Phase 5 DEV results, lineage@ami (final config single_pass_recap_roles_top4; bootstrap over sets)

50 answers, 50 parsed, 178 sentences, 0 unknown citation ids, 0 unparseable judge verdicts (counted incorrect).

| metric | headline | all types |
|---|---|---|
| correctness_flag | 0.033 [0.00, 0.10] (n=15) | 0.190 [0.08, 0.29] (n=50) |
| correctness_drop | 0.100 [0.00, 0.23] (n=15) | 0.230 [0.09, 0.37] (n=50) |
| supported_claim_rate | 0.150 [0.02, 0.29] (n=15) | 0.178 [0.07, 0.29] (n=50) |
| citation_precision | 0.254 [0.04, 0.44] (n=12) | 0.215 [0.10, 0.32] (n=45) |
| hallucination_rate | 0.781 [0.58, 0.98] (n=12) | 0.756 [0.62, 0.90] (n=45) |
| lexical_ok | 0.500 [0.40, 0.61] (n=12) | 0.539 [0.40, 0.67] (n=45) |
| uncited_share | 0.271 [0.04, 0.48] (n=12) | 0.156 [0.06, 0.29] (n=45) |
| retrieval_completeness | 0.038 [0.00, 0.12] (n=15) | 0.041 [0.00, 0.09] (n=47) |
| expl_completeness_flag | 0.038 [0.00, 0.12] (n=15) | 0.041 [0.00, 0.09] (n=47) |
| expl_completeness_drop | 0.038 [0.00, 0.12] (n=15) | 0.041 [0.00, 0.09] (n=47) |

| type | n | correctness (flag) | supported-claim rate |
|---|---|---|---|
| as_of | 10 | 0.400 [0.10, 0.70] (n=10) | 0.254 [0.06, 0.46] (n=10) |
| change_over_time | 5 | 0.200 [0.00, 0.60] (n=5) | 0.125 [0.00, 0.38] (n=4) |
| decisions_about | 5 | 0.100 [0.00, 0.30] (n=5) | 0.250 [0.00, 0.75] (n=4) |
| evidence_to_reconsider | 4 | 0.000 [0.00, 0.00] (n=4) | 0.000 [0.00, 0.00] (n=1) |
| full_lineage | 5 | 0.000 [0.00, 0.00] (n=5) | 0.150 [0.03, 0.28] (n=5) |
| lookup_final | 5 | 0.400 [0.00, 0.80] (n=5) | 0.150 [0.03, 0.33] (n=5) |
| meetings_contributed | 5 | 0.100 [0.00, 0.30] (n=5) | 0.175 [0.00, 0.38] (n=5) |
| who_proposed | 5 | 0.200 [0.00, 0.60] (n=5) | 0.200 [0.00, 0.60] (n=5) |
| why_changed | 6 | 0.083 [0.00, 0.30] (n=6) | 0.250 [0.00, 0.70] (n=6) |

False premise: {'n': 1, 'regex_ok': 1, 'judge': [0.5]}
Policy: {'rule': 'drop iff it lowers neither expl. completeness nor correctness by more than 0.02 (headline and all)', 'deltas': {'headline_correctness': 0.067, 'headline_completeness': 0.0, 'all_correctness': 0.04, 'all_completeness': 0.0}, 'chosen': 'drop'}
Latency: {'mean_s': 12.2, 'mean_in': 512, 'mean_out': 145}
