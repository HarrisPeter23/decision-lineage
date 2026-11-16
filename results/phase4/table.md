# Phase 4 graph quality on synthetic DEV (14 sets; tol 1; bootstrap over sets; ORACLE ANCHORING)

Selected on DEV by the pre-declared objective (mean over single_pass and single_pass_top4 of (linking F1 + as_of accuracy)/2): linker link_at=0.4, gap=60, proposal_own=False; matcher lexical same_at=0.4 modified_at=0.2, versioning rules v1. Best v1 matcher (reported for comparison): ('lexical', 0.4, 0.2, 'v1'). Grids: `results.json`. Linking pairs are dominated by within-main pairs (2 gold decisions a set), so linking P is high by construction; read the false-merge column for distractor separation.

| source | links | graph decisions | localized | linking P / R / F1 [CI] | main-distractor false merges | link-to-decision [CI] | main fragments | as_of+final acc [CI] (n) | version seq exact | supersession P / R / F1 [CI] |
|---|---|---|---|---|---|---|---|---|---|---|
| oracle | 122 | 25 | 122 | 0.91 / 0.84 / 0.874 [0.787, 0.954] | 36 | 0.861 [0.765, 0.944] | 1.64 | 0.810 [0.643, 0.929] (42) | 0.500 | 0.67 / 0.67 / 0.667 [0.4, 0.88] |
| single_pass | 1596 | 58 | 112 | 0.92 / 0.86 / 0.886 [0.82, 0.946] | 28 | 0.884 [0.819, 0.945] | 1.57 | 0.643 [0.429, 0.833] (42) | 0.000 | 0.21 / 1.00 / 0.343 [0.237, 0.429] |
| single_pass_top4 | 172 | 41 | 77 | 0.97 / 0.82 / 0.887 [0.722, 0.964] | 5 | 0.857 [0.75, 0.938] | 1.57 | 0.595 [0.381, 0.786] (42) | 0.071 | 0.32 / 0.58 / 0.412 [0.194, 0.595] |
| single_pass_recap_roles | 583 | 34 | 111 | 0.97 / 0.86 / 0.912 [0.823, 0.963] | 8 | 0.892 [0.804, 0.952] | 1.64 | 0.619 [0.452, 0.786] (42) | 0.214 | 0.25 / 0.67 / 0.364 [0.235, 0.449] |
| single_pass_recap_roles_top4 | 163 | 25 | 93 | 1.00 / 0.88 / 0.939 [0.852, 0.985] | 0 | 0.914 [0.826, 0.978] | 1.36 | 0.738 [0.548, 0.905] (42) | 0.214 | 0.33 / 0.75 / 0.462 [0.364, 0.556] |
| single_pass_recap_roles_dec1 | 86 | 27 | 42 | 0.77 / 0.63 / 0.696 [0.579, 0.792] | 7 | 0.762 [0.684, 0.837] | 1.57 | 0.429 [0.238, 0.619] (42) | 0.214 | 0.31 / 0.33 / 0.320 [0.0, 0.444] |
