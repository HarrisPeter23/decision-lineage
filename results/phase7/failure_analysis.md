# Failure analysis: my system, TEST pool 1, headline questions (65)
Script: `python -I eval/phase7_failure_analysis.py`. Extraction-level metrics: `results/phase7/extract_eval.md`. Agent analysis on synthetic text; not human-checked.

## Quantified
- **Where gold lineage links are lost.** There are 365 gold links in the supporting lineages of the 65 headline questions.
  - **232 (64%)** are among the extracted links kept by the top-4 cap.
  - **76 (21%)** were extracted but **cut by the top-4 cap**.
  - **57 (16%)** were **never extracted**.
  So about 36% of the lineage is gone before retrieval starts. This bounds cited recall (0.362), and the cap is the larger loss.
- **Extraction, TEST vs DEV** (tol 1):
  - localization recall 0.589 vs 0.762;
  - six-role F1 0.444 [0.41, 0.49] vs 0.554;
  - four-class F1 0.515 [0.47, 0.56] vs 0.618;
  - role accuracy given localization 0.83 (six roles), 0.96 (four classes);
  - most frequent misses: rationale not extracted (34), resolution not extracted (18), rationale typed as evidence (17).
- **Zero-completeness answers:** 14 of 65 cite no gold lineage link.
- **False premise:** 2 of 4 answers reject the premise (regex check).
- **NLI-unsupported sentences:** 275 of 412 headline sentences. This is a strict lower bound on faithfulness: NLI flags 58% of real sentences on DEV.

## Examples (quoted from system output and gold)
1. **Lineage never extracted** (set_01031-q08, evidence_to_reconsider). Q: "What evidence caused the team to reconsider its decision about the in-office policy for all teams?" The gold evidence is in meeting 2, line 19: Mateo reports "a pulse survey found 34 percent of staff with a commute over 90 minutes would consider leaving, and two recent engineering resignations…". It was never extracted, and the system answered "no decision had been made yet". In the same set, the rationale that answers it (Tariq, meeting 3, lines 22/29: "only 18 of 310 staff have a commute over 90 minutes…") was extracted but cut by the top-4 cap.
2. **False premise accepted** (set_01024-q06, no_reversal arc). Q: "Why did the team change its decision about the device policy for contractors with production access?" Gold: "It did not change. The team kept issue company-managed laptops to all 38 contractors who have production data access…". System: "The team changed its decision … because they decided to park the issue for now due to other priorities and logistical concerns." A deferral was read as a change.
3. **Unfaithful temporal detail** (set_01031-q10). The sentence "In meeting 1 on 2025-04-17, Chloe proposed that every new hire gets a buddy from outside their own team" cites a line of the second meeting, whose date is 2025-04-17. The ordinal is wrong although the date and content are right, and the NLI checker flagged it.

## Reading
- The losses are mostly upstream, in extraction and the cap, not in versioning or typing. **Update (D-45):** counting citations too, 90 of the 232 kept pairs (25% of 365) are not cited in the final answer, so retrieval and generation together lose more than the cap (21%); see `results/phase7/stage_loss.json`. This matches the ablations, which show no evidence that typing or versioning improved F1.
- Typing errors are frequent (rationale F1 0.18 on TEST), yet removing typing changed nothing measurable. One plausible reading: the six-way types are too noisy to steer retrieval.
- The gain over the graph/wiki baselines is in cited **precision**, where link-level citations of 1--3 utterances help.
