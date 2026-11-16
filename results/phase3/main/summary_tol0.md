# Extraction ablation on `data/synth DEV (14 sets)` (tol=0)

Role-typed = right utterance AND right role. CI = bootstrap 95% over SETS. Precision is a lower bound (gold labels only annotated decisions).

| config | status | role-typed P | R | F1 | F1 95% CI | localization F1 | chain completeness | chain-exact | implicit recall (n) | speaker acc | calls | in tok | out tok | quote drops |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mp_p123 | ok | 0.065 | 0.566 | 0.117 | [0.08, 0.18] | 0.179 | 0.550 | 0.00 | 0.83 (6) | 1.000 | 132 | 385716 | 108671 | 0 |
| mp_p123_verify | ok | 0.065 | 0.484 | 0.114 | [0.09, 0.16] | 0.184 | 0.468 | 0.00 | 0.67 (6) | 1.000 | 132 | 379232 | 99682 | 66 |
| single_pass | ok | 0.047 | 0.615 | 0.087 | [0.07, 0.12] | 0.128 | 0.608 | 0.00 | 1.00 (6) | 0.991 | 44 | 80788 | 61164 | - |

## Per-role F1

| config | proposal | rationale | evidence | challenge | reconsideration | resolution |
|---|---|---|---|---|---|---|
| mp_p123 | 0.13 | 0.15 | 0.12 | 0.03 | 0.17 | 0.11 |
| mp_p123_verify | 0.13 | 0.14 | 0.09 | 0.00 | 0.15 | 0.12 |
| single_pass | 0.19 | 0.08 | 0.06 | 0.03 | 0.19 | 0.10 |

## Reading this table honestly

- The pilot is small (see `sets` in results.json); differences between configurations inside each other's confidence intervals are not evidence of improvement.
- `rules` was written with knowledge of the pilot phrasing; it is a sanity floor, not a reference baseline.
- Implicit-resolution recall rests on very few examples; do not over-read it.
- Compare `mp_p3` with `single_pass` to see the effect of the prompt change alone, and `mp_p13`, `mp_p123` against `mp_p3` to see what each added pass contributes.
