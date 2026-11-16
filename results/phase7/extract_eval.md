# Extraction-level metrics, single_pass_recap_roles_top4 (tol 1; bootstrap 1,000 over sets)

| split / roles | sets | localization F1 | role-typed P | role-typed R | role-typed F1 [95% CI] | chain completeness | implicit-res. recall |
|---|---|---|---|---|---|---|---|
| test_six | 22 | 0.535 | 0.407 | 0.489 | 0.444 [0.41, 0.49] | 0.566 | 0.667 (n=12) |
| test_four | 22 | 0.535 | 0.471 | 0.566 | 0.515 [0.47, 0.56] | 0.657 | 0.667 (n=12) |
| dev_six | 14 | 0.653 | 0.485 | 0.648 | 0.554 [0.48, 0.62] | 0.668 | 0.5 (n=6) |
| dev_four | 14 | 0.653 | 0.540 | 0.721 | 0.618 [0.53, 0.69] | 0.748 | 0.5 (n=6) |

Per role (TEST, six roles): proposal F1 0.58 (n=37), rationale F1 0.18 (n=60), evidence F1 0.31 (n=25), challenge F1 0.34 (n=19), reconsideration F1 0.71 (n=20), resolution F1 0.54 (n=58)
Per class (TEST, four classes; 'rationale' = argument): proposal F1 0.58 (n=37), rationale F1 0.43 (n=104), reconsideration F1 0.71 (n=20), resolution F1 0.54 (n=58)
