# Extraction ablation on `data/synth DEV (14 sets)` (tol=1)

Role-typed = right utterance AND right role. CI = bootstrap 95% over SETS. Precision is a lower bound (gold labels only annotated decisions).

| config | status | role-typed P | R | F1 | F1 95% CI | localization F1 | chain completeness | chain-exact | implicit recall (n) | speaker acc | calls | in tok | out tok | quote drops |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mp_p123 | ok | 0.071 | 0.615 | 0.127 | [0.09, 0.19] | 0.181 | 0.603 | 0.00 | 1.00 (6) | 0.935 | 132 | 385716 | 108671 | 0 |
| mp_p123_verify | ok | 0.070 | 0.525 | 0.124 | [0.09, 0.18] | 0.188 | 0.512 | 0.00 | 1.00 (6) | 0.928 | 132 | 379232 | 99682 | 66 |
| single_pass | ok | 0.051 | 0.672 | 0.095 | [0.07, 0.13] | 0.130 | 0.665 | 0.07 | 1.00 (6) | 0.911 | 44 | 80788 | 61164 | - |

## Per-role F1

| config | proposal | rationale | evidence | challenge | reconsideration | resolution |
|---|---|---|---|---|---|---|
| mp_p123 | 0.13 | 0.21 | 0.12 | 0.05 | 0.17 | 0.12 |
| mp_p123_verify | 0.13 | 0.18 | 0.09 | 0.03 | 0.15 | 0.13 |
| single_pass | 0.19 | 0.11 | 0.06 | 0.05 | 0.19 | 0.10 |

## Reading this table honestly

- The pilot is small (see `sets` in results.json); differences between configurations inside each other's confidence intervals are not evidence of improvement.
- `rules` was written with knowledge of the pilot phrasing; it is a sanity floor, not a reference baseline.
- Implicit-resolution recall rests on very few examples; do not over-read it.
- Compare `mp_p3` with `single_pass` to see the effect of the prompt change alone, and `mp_p13`, `mp_p123` against `mp_p3` to see what each added pass contributes.
