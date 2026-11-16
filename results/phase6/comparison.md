# Phase 6 DEV comparison (14 sets, 141 questions; 95% CI by bootstrap over sets; unpaired, so overlap is not a test)

## pool size 1, headline questions

| metric | lineage (mine) | vector_rag | evowiki_style | graphiti |
|---|---|---|---|---|
| answer correctness (LLM-judged where not exact) | 0.562 [0.46, 0.67] | 0.525 [0.42, 0.62] | 0.400 [0.29, 0.50] | 0.425 [0.30, 0.54] |
| supported-claim rate (NLI) | 0.484 [0.42, 0.55] | 0.388 [0.32, 0.45] | 0.127 [0.05, 0.21] | 0.283 [0.21, 0.37] |
| citation precision (NLI) | 0.446 [0.38, 0.52] | 0.403 [0.33, 0.47] | 0.125 [0.06, 0.20] | 0.279 [0.20, 0.36] |
| hallucination rate (NLI, lower is better) | 0.466 [0.39, 0.55] | 0.522 [0.46, 0.59] | 0.826 [0.73, 0.92] | 0.658 [0.57, 0.74] |
| lineage completeness, retrieved | 0.633 [0.54, 0.72] | 0.576 [0.46, 0.69] | 0.328 [0.25, 0.41] | 0.440 [0.32, 0.56] |
| lineage completeness, cited | 0.615 [0.53, 0.70] | 0.561 [0.44, 0.69] | 0.235 [0.17, 0.31] | 0.392 [0.28, 0.51] |

## pool size 1, all questions

| metric | lineage (mine) | vector_rag | evowiki_style | graphiti |
|---|---|---|---|---|
| answer correctness (LLM-judged where not exact) | 0.649 [0.54, 0.74] | 0.606 [0.51, 0.71] | 0.532 [0.46, 0.61] | 0.589 [0.48, 0.69] |
| supported-claim rate (NLI) | 0.446 [0.39, 0.50] | 0.404 [0.34, 0.47] | 0.129 [0.07, 0.19] | 0.282 [0.22, 0.35] |
| citation precision (NLI) | 0.433 [0.37, 0.49] | 0.401 [0.34, 0.46] | 0.125 [0.07, 0.19] | 0.282 [0.22, 0.35] |
| hallucination rate (NLI, lower is better) | 0.499 [0.45, 0.57] | 0.500 [0.44, 0.56] | 0.835 [0.77, 0.91] | 0.662 [0.59, 0.73] |
| lineage completeness, retrieved | 0.621 [0.53, 0.70] | 0.566 [0.45, 0.68] | 0.620 [0.57, 0.68] | 0.559 [0.47, 0.65] |
| lineage completeness, cited | 0.601 [0.52, 0.68] | 0.555 [0.44, 0.67] | 0.521 [0.44, 0.60] | 0.510 [0.41, 0.60] |

| per type (correctness, pool 1) | lineage (mine) | vector_rag | evowiki_style | graphiti |
|---|---|---|---|---|
| as_of | 0.71 | 0.43 | 0.64 | 0.54 |
| change_over_time | 0.46 | 0.57 | 0.43 | 0.71 |
| decisions_about | 0.68 | 0.75 | 0.57 | 0.64 |
| distractor | 0.67 | 1.00 | 0.83 | 0.67 |
| evidence_to_reconsider | 0.75 | 0.54 | 0.42 | 0.50 |
| full_lineage | 0.43 | 0.43 | 0.43 | 0.36 |
| lookup_final | 0.86 | 0.71 | 0.64 | 0.64 |
| meetings_contributed | 0.64 | 0.79 | 0.54 | 0.64 |
| who_proposed | 0.71 | 0.71 | 0.57 | 0.86 |
| why_changed | 0.54 | 0.61 | 0.36 | 0.43 |
| false premise (regex, n=2) | 2/2 | 0/2 | 1/2 | 1/2 |
| parse failures | 0 | 0 | 0 | 0 |

## pool size 10, headline questions

| metric | lineage (mine) | vector_rag | evowiki_style | graphiti |
|---|---|---|---|---|
| answer correctness (LLM-judged where not exact) | 0.400 [0.26, 0.53] | 0.237 [0.13, 0.38] | 0.275 [0.19, 0.37] | 0.338 [0.26, 0.42] |
| supported-claim rate (NLI) | 0.427 [0.35, 0.50] | 0.396 [0.34, 0.46] | 0.093 [0.05, 0.13] | 0.113 [0.07, 0.17] |
| citation precision (NLI) | 0.396 [0.33, 0.47] | 0.384 [0.32, 0.46] | 0.117 [0.07, 0.17] | 0.106 [0.07, 0.15] |
| hallucination rate (NLI, lower is better) | 0.529 [0.46, 0.59] | 0.529 [0.47, 0.59] | 0.909 [0.87, 0.95] | 0.844 [0.78, 0.89] |
| lineage completeness, retrieved | 0.377 [0.23, 0.53] | 0.322 [0.23, 0.43] | 0.295 [0.23, 0.37] | 0.254 [0.19, 0.33] |
| lineage completeness, cited | 0.367 [0.23, 0.52] | 0.317 [0.22, 0.43] | 0.230 [0.16, 0.29] | 0.223 [0.15, 0.30] |

## pool size 10, all questions

| metric | lineage (mine) | vector_rag | evowiki_style | graphiti |
|---|---|---|---|---|
| answer correctness (LLM-judged where not exact) | 0.521 [0.38, 0.66] | 0.372 [0.27, 0.48] | 0.383 [0.33, 0.44] | 0.418 [0.33, 0.49] |
| supported-claim rate (NLI) | 0.433 [0.36, 0.51] | 0.394 [0.35, 0.44] | 0.121 [0.08, 0.16] | 0.165 [0.12, 0.20] |
| citation precision (NLI) | 0.428 [0.36, 0.51] | 0.389 [0.34, 0.44] | 0.147 [0.10, 0.20] | 0.169 [0.12, 0.21] |
| hallucination rate (NLI, lower is better) | 0.529 [0.47, 0.59] | 0.536 [0.48, 0.59] | 0.866 [0.82, 0.91] | 0.799 [0.75, 0.85] |
| lineage completeness, retrieved | 0.457 [0.30, 0.61] | 0.363 [0.28, 0.44] | 0.562 [0.48, 0.64] | 0.426 [0.32, 0.53] |
| lineage completeness, cited | 0.446 [0.29, 0.60] | 0.344 [0.26, 0.43] | 0.406 [0.31, 0.51] | 0.356 [0.25, 0.47] |

| per type (correctness, pool 10) | lineage (mine) | vector_rag | evowiki_style | graphiti |
|---|---|---|---|---|
| as_of | 0.54 | 0.43 | 0.46 | 0.46 |
| change_over_time | 0.46 | 0.32 | 0.46 | 0.43 |
| decisions_about | 0.54 | 0.50 | 0.57 | 0.54 |
| distractor | 1.00 | 1.00 | 0.67 | 1.00 |
| evidence_to_reconsider | 0.42 | 0.29 | 0.29 | 0.33 |
| full_lineage | 0.36 | 0.21 | 0.29 | 0.29 |
| lookup_final | 0.64 | 0.50 | 0.43 | 0.64 |
| meetings_contributed | 0.54 | 0.11 | 0.04 | 0.14 |
| who_proposed | 0.64 | 0.57 | 0.50 | 0.36 |
| why_changed | 0.43 | 0.21 | 0.25 | 0.39 |
| false premise (regex, n=2) | 0/2 | 0/2 | 0/2 | 1/2 |
| parse failures | 0 | 0 | 5 | 0 |

