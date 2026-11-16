# Data licence

## Synthetic benchmark and results
`data/synth/`, `data/synth_work/`, `results/` and the label documentation in `reports/` are licensed under the
**Creative Commons Attribution 4.0 International licence (CC BY 4.0)**, https://creativecommons.org/licenses/by/4.0/.
Please cite the paper (see README) when you use them.

All people, organisations and events in the synthetic meetings are fictional. Real brand names found during generation were
replaced before release (see `reports/label_issues.md`). The meetings were written by an LLM (see `data/synth/DATACARD.md`).

## AMI-derived material
`data/ami/series/`, `data/ami/transcripts/`, `data/ami/transcripts_txt/` and `data/ami/pools/` are adapted from the
**AMI Meeting Corpus**, annotations release 1.6.2 (ami_public_manual_1.6.2), licensed under **CC BY 4.0**.

> Attribution: AMI Meeting Corpus, the AMI Consortium. J. Carletta et al., "The AMI Meeting Corpus: A Pre-announcement",
> in Proc. MLMI 2005, LNCS 3869, pp. 28-39, 2006, doi:10.1007/11677482_3. Licence: CC BY 4.0.

Changes we made: we built series and utterance-level transcripts from the words and segments layers, and we replaced
the recording dates with synthetic per-meeting offsets (meeting k = series date + k hours) to preserve order.
The AMI gold chains and questions (`data/ami/gold/`) and the verification file are our own annotations, also released under CC BY 4.0.
The original audio and the raw annotation archive are not redistributed.

## Third-party models and software (not redistributed; used as released)
| Item | Licence |
|---|---|
| qwen3:14b (generator) | Apache-2.0 |
| granite4.2:8b (judge) | Apache-2.0 |
| mistral-nemo:12b (failed control writer) | Apache-2.0 |
| cross-encoder/nli-deberta-v3-small | Apache-2.0 |
| sentence-transformers/all-MiniLM-L6-v2 | Apache-2.0 |
| graphiti-core 0.31.2 | Apache-2.0 |
| Neo4j Community 5.26.17 (Graphiti backend, run inside Kaggle sessions only) | GPL-3.0 |
| Gemini API (calibration and pairwise judge only) | Google API terms; only synthetic and public text was sent |
