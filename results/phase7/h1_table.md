# H1 tests on TEST (pool 1, headline questions; paired bootstrap over sets, 10,000 resamples, seed 0; Holm within family)

| family | metric | mine vs | diff [95% CI] | one-sided p | Holm threshold | H0 rejected |
|---|---|---|---|---|---|---|
| primary | f1 | evowiki_style | +0.129 [+0.046, +0.216] | 0.0004 | 0.025 | yes |
| primary | f1 | graphiti | +0.126 [+0.023, +0.228] | 0.0069 | 0.05 | yes |
| secondary | r | evowiki_style | +0.119 [+0.012, +0.236] | 0.0145 | 0.00417 | no |
| secondary | p | evowiki_style | +0.154 [+0.063, +0.245] | 0.0004 | 0.00313 | yes |
| secondary | r_at_k | evowiki_style | +0.113 [+0.025, +0.204] | 0.0073 | 0.00333 | no |
| secondary | nli_supported | evowiki_style | +0.156 [+0.076, +0.234] | 0.0000 | 0.00263 | yes |
| secondary | nli_precision | evowiki_style | +0.169 [+0.115, +0.228] | 0.0000 | 0.00278 | yes |
| secondary | correct | evowiki_style | +0.015 [-0.066, +0.099] | 0.3701 | 0.00833 | no |
| secondary | r | graphiti | +0.087 [-0.034, +0.213] | 0.0852 | 0.00625 | no |
| secondary | p | graphiti | +0.199 [+0.094, +0.295] | 0.0000 | 0.00294 | yes |
| secondary | r_at_k | graphiti | +0.117 [+0.016, +0.219] | 0.0110 | 0.00385 | no |
| secondary | nli_supported | graphiti | +0.082 [-0.002, +0.164] | 0.0266 | 0.00455 | no |
| secondary | nli_precision | graphiti | +0.081 [-0.003, +0.163] | 0.0281 | 0.005 | no |
| secondary | correct | graphiti | -0.102 [-0.231, +0.030] | 0.9335 | 0.01667 | no |
| secondary | f1 | vector_rag | +0.046 [-0.056, +0.148] | 0.1897 | 0.00714 | no |
| secondary | r | vector_rag | +0.004 [-0.107, +0.116] | 0.4786 | 0.01 | no |
| secondary | p | vector_rag | +0.121 [+0.023, +0.216] | 0.0080 | 0.00357 | no |
| secondary | r_at_k | vector_rag | +0.069 [-0.022, +0.162] | 0.0735 | 0.00556 | no |
| secondary | nli_supported | vector_rag | -0.127 [-0.214, -0.034] | 0.9953 | 0.025 | no |
| secondary | nli_precision | vector_rag | -0.134 [-0.224, -0.035] | 0.9961 | 0.05 | no |
| secondary | correct | vector_rag | -0.062 [-0.188, +0.062] | 0.8379 | 0.0125 | no |

| system | f1 | r | p | r_at_k | nli_supported | nli_precision | correct |
|---|---|---|---|---|---|---|---|
| mine | 0.384 [0.31, 0.46] | 0.362 [0.27, 0.46] | 0.479 [0.39, 0.56] | 0.333 [0.26, 0.41] | 0.313 [0.24, 0.38] | 0.311 [0.24, 0.38] | 0.367 [0.28, 0.46] |
| evowiki_style | 0.255 [0.21, 0.30] | 0.243 [0.19, 0.29] | 0.325 [0.27, 0.39] | 0.219 [0.18, 0.26] | 0.157 [0.11, 0.21] | 0.142 [0.10, 0.19] | 0.352 [0.28, 0.42] |
| graphiti | 0.258 [0.21, 0.31] | 0.275 [0.23, 0.33] | 0.280 [0.23, 0.34] | 0.216 [0.17, 0.27] | 0.231 [0.17, 0.29] | 0.230 [0.18, 0.29] | 0.470 [0.40, 0.53] |
| vector_rag | 0.337 [0.27, 0.40] | 0.358 [0.28, 0.44] | 0.358 [0.29, 0.43] | 0.263 [0.21, 0.32] | 0.440 [0.38, 0.50] | 0.445 [0.39, 0.50] | 0.430 [0.35, 0.50] |
