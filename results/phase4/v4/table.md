# Phase 4 versioning: v1 vs v3 vs v4 on synthetic DEV (oracle anchoring; 95% CI bootstrap over 14 sets)

v4 selected by the pre-declared objective (mean supersession-edge F1 over the three candidates): min_confidence=0.9, own_at=0.2, same_at=0.4 (modified_at 0.2; linker link_at 0.4, gap 60). Grid of 45 cells in `results.json`.

| rules | source | supersession P / R / F1 [CI] | predicted / gold edges | as_of + final acc [CI] (n=42) | version seq exact |
|---|---|---|---|---|---|
| v1 (Phase 4 selection) | oracle | 0.67 / 0.67 / 0.667 [0.4, 0.88] | 12 / 12 | 0.810 [0.643, 0.929] | 0.500 |
| v1 (Phase 4 selection) | single_pass | 0.21 / 1.00 / 0.343 [0.237, 0.429] | 58 / 12 | 0.643 [0.429, 0.833] | 0.000 |
| v1 (Phase 4 selection) | single_pass_top4 | 0.32 / 0.58 / 0.412 [0.194, 0.595] | 22 / 12 | 0.595 [0.381, 0.786] | 0.071 |
| v1 (Phase 4 selection) | single_pass_recap_roles_top4 | 0.33 / 0.75 / 0.462 [0.364, 0.556] | 27 / 12 | 0.738 [0.548, 0.905] | 0.214 |
| v3 (gold-link alignment, defaults) | oracle | 1.00 / 1.00 / 1.000 [1.0, 1.0] | 12 / 12 | 1.000 [1.0, 1.0] | 0.929 |
| v3 (gold-link alignment, defaults) | single_pass | 0.20 / 1.00 / 0.338 [0.237, 0.418] | 59 / 12 | 0.619 [0.405, 0.833] | 0.000 |
| v3 (gold-link alignment, defaults) | single_pass_top4 | 0.39 / 0.75 / 0.514 [0.294, 0.667] | 23 / 12 | 0.690 [0.5, 0.857] | 0.071 |
| v3 (gold-link alignment, defaults) | single_pass_recap_roles_top4 | 0.40 / 0.83 / 0.541 [0.417, 0.651] | 25 / 12 | 0.714 [0.5, 0.881] | 0.286 |
| v4 (tightened, tuned) | oracle | 1.00 / 1.00 / 1.000 [1.0, 1.0] | 12 / 12 | 1.000 [1.0, 1.0] | 1.000 |
| v4 (tightened, tuned) | single_pass | 0.48 / 0.92 / 0.629 [0.432, 0.78] | 23 / 12 | 0.690 [0.571, 0.81] | 0.000 |
| v4 (tightened, tuned) | single_pass_top4 | 0.64 / 0.58 / 0.609 [0.267, 0.815] | 11 / 12 | 0.690 [0.5, 0.857] | 0.429 |
| v4 (tightened, tuned) | single_pass_recap_roles_top4 | 0.75 / 0.75 / 0.750 [0.5, 0.917] | 12 / 12 | 0.762 [0.571, 0.905] | 0.571 |
