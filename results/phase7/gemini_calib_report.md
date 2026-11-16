# Gemini calibration on TEST (FREEZE sections 15, 20). LLM-judged; bounds, not human evaluation

Unparsed Gemini verdicts: 0 sentences, 0 answers (excluded).

| system | sentences n | Gemini yes | NLI supported | agreement | kappa | flag precision | flag recall |
|---|---|---|---|---|---|---|---|
| all | 600 | 0.733 | 0.288 | 0.485 | 0.14 | 0.326 | 0.869 |
| evowiki_style@test_k1 | 150 | 0.72 | 0.147 | 0.36 | 0.024 | 0.289 | 0.881 |
| graphiti@test_k1 | 150 | 0.667 | 0.24 | 0.44 | 0.045 | 0.351 | 0.8 |
| lineage@test_k1 | 150 | 0.747 | 0.427 | 0.64 | 0.329 | 0.407 | 0.921 |
| vector_rag@test_k1 | 150 | 0.8 | 0.34 | 0.5 | 0.161 | 0.273 | 0.9 |

| system | rubric n | 3-class agr. | 3-class kappa | binary agr. | binary kappa | exact n | exact agr. | exact kappa |
|---|---|---|---|---|---|---|---|---|
| all | 366 | 0.661 | 0.508 | 0.801 | 0.551 | 234 | 0.872 | 0.728 |
| evowiki_style@test_k1 | 94 | 0.67 | 0.523 | 0.83 | 0.586 | 56 | 0.839 | 0.647 |
| graphiti@test_k1 | 91 | 0.648 | 0.462 | 0.78 | 0.492 | 59 | 0.831 | 0.662 |
| lineage@test_k1 | 92 | 0.641 | 0.49 | 0.772 | 0.504 | 58 | 0.914 | 0.802 |
| vector_rag@test_k1 | 89 | 0.685 | 0.524 | 0.82 | 0.618 | 61 | 0.902 | 0.794 |
