# Extraction ablation on `data/synth DEV (14 sets)` (tol=0)

Role-typed = right utterance AND right role. CI = bootstrap 95% over SETS. Precision is a lower bound (gold labels only annotated decisions).

| config | status | role-typed P | R | F1 | F1 95% CI | localization F1 | chain completeness | chain-exact | implicit recall (n) | speaker acc | calls | in tok | out tok | quote drops |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| single_pass_recap_roles | degraded (meetings with no links: ['set_01023-m3', 'set_01045-m3']; worker exit codes: [0, 0, 0, 0]) | 0.151 | 0.721 | 0.250 | [0.21, 0.29] | 0.306 | 0.741 | 0.00 | 0.83 (6) | 0.991 | 44 | 113210 | 32927 | - |

## Per-role F1

| config | proposal | rationale | evidence | challenge | reconsideration | resolution |
|---|---|---|---|---|---|---|
| single_pass_recap_roles | 0.47 | 0.17 | 0.16 | 0.11 | 0.54 | 0.38 |

## Reading this table honestly

- The pilot is small (see `sets` in results.json); differences between configurations inside each other's confidence intervals are not evidence of improvement.
- `rules` was written with knowledge of the pilot phrasing; it is a sanity floor, not a reference baseline.
- Implicit-resolution recall rests on very few examples; do not over-read it.
- Compare `mp_p3` with `single_pass` to see the effect of the prompt change alone, and `mp_p13`, `mp_p123` against `mp_p3` to see what each added pass contributes.
