# Extraction ablation on `data/synth DEV (14 sets)` (tol=0)

Role-typed = right utterance AND right role. CI = bootstrap 95% over SETS. Precision is a lower bound (gold labels only annotated decisions).

| config | status | role-typed P | R | F1 | F1 95% CI | localization F1 | chain completeness | chain-exact | implicit recall (n) | speaker acc | calls | in tok | out tok | quote drops |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| single_pass | ok | 0.032 | 0.566 | 0.060 | [0.04, 0.09] | 0.099 | 0.557 | 0.07 | 1.00 (6) | 1.000 | 79 | 98515 | 76576 | - |

## Per-role F1

| config | proposal | rationale | evidence | challenge | reconsideration | resolution |
|---|---|---|---|---|---|---|
| single_pass | 0.12 | 0.05 | 0.05 | 0.02 | 0.07 | 0.07 |

## Reading this table honestly

- The pilot is small (see `sets` in results.json); differences between configurations inside each other's confidence intervals are not evidence of improvement.
- `rules` was written with knowledge of the pilot phrasing; it is a sanity floor, not a reference baseline.
- Implicit-resolution recall rests on very few examples; do not over-read it.
- Compare `mp_p3` with `single_pass` to see the effect of the prompt change alone, and `mp_p13`, `mp_p123` against `mp_p3` to see what each added pass contributes.
