# Human spot-check result (40 links; the reviewer is the project user, one rater, no second rater)

| | n | yes | partial | no |
|---|---|---|---|---|
| all | 40 | 34 | 6 | 0 |
| synthetic | 24 | 21 | 3 | 0 |
| AMI | 16 | 13 | 3 | 0 |

## Human vs gold (the gold label is the thing being checked)
- Fully correct (yes): 34/40 = 85% (Wilson 95% CI 71-93%); synthetic 21/24 = 88% (69-96%); AMI 13/16 = 81% (57-93%).
- Correct or arguable (yes or partial): 40/40 = 100% (91-100%). No link was judged wrong, and only 1 of 40 had a role disputed (TS3012 B1, proposal vs context).
- The sample is not a random draw: 6 synthetic links were the ones the panel or the agent had flagged, the other 18 are stratified by role and writer, the AMI links are 3-4 per series. The rates are therefore not an estimate of the error rate of all gold links.

## Human vs automatic judges (binary: did the judge say yes when the human said yes)
| judge | n | agree | rate (95% CI) | kappa |
|---|---|---|---|---|
| Gemini (gemini-3.5-flash-lite) | 40 | 34 | 85% (71-93%) | 0.19 |
| granite4.2:8b | 40 | 35 | 88% (74-95%) | 0.47 |
| agent hand-check | 7 | 6 | 86% (49-97%) | 0.70 |

The judges say yes to almost everything (Gemini 38/40, granite 35/40, all 16 AMI links by both), so agreement is mostly "both say yes" and kappa is low; on AMI kappa is 0 because both judges said yes to every link, including the 3 the human marked partial. The judges caught few of the human's partials, consistent with the earlier finding that they verify content and speaker, not role or span. The agent hand-check has only 7 overlapping links, too few to say more.

## Role-blind Gemini vs gold role on these 40 links
24/40 = 60% (45-74%); on the 34 links the human called fully correct 22/34 = 65% (48-79%). So where a human accepts the gold role, the blind judge still disagrees about a third of the time, which supports reading the rationale/evidence/challenge boundary as partly arbitrary rather than the gold roles as wrong.

## What changed in the data
The 40 links are marked `verification: human_spotcheck` (34 yes, 6 partial) with `human_verdict`, `verification_scope: content_speaker_role_human` and the earlier value kept in `verification_before_human`, in `data/synth/verification.json` and `data/ami/verification.json`. Gold, split and transcripts are unchanged (hashes unaffected). The remaining 253 synthetic and 27 AMI links stay `llm_consensus` (content and speaker only).
