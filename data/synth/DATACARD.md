# Data card: synthetic corporate-meeting benchmark for decision lineage

Version of 2026-11-03. Location: `data/synth/`. All people, companies, products and vendors are fictional. No real personal data.

## 1. What it is
36 sets of 3-4 internal corporate meetings (113 meetings, 293 gold chain links, 373 questions). In each set a team proposes a decision, gives reasons and
evidence, meets a challenge, and then keeps, changes, modifies or defers the decision. Each set has a gold causal chain (roles: proposal, rationale, evidence,
challenge, reconsideration, resolution), gold decision versions with validity windows, and questions with deterministic gold answers.
Arcs: simple_reversal 9, external_trigger 7, no_reversal 6 (control for false-premise questions), partial_override 5, re_reversal 5, deferred 4.
Twelve business functions are covered. Question types (373): lookup_final 36, decisions_about 36, as_of 72, change_over_time 36, why_changed 37 (including the
false-premise variant on no_reversal sets), who_proposed 36, evidence_to_reconsider 32, meetings_contributed 36, full_lineage 36, distractor 16.

## 2. How it was made
1. **Structure first.** `synthgen/arcs.py` fixes the gold structure in code (who speaks which event, which option is valid when). A seeded sampler picks the arc, cast, noise level and which resolutions are implicit.
2. **Plan.** For each set a plan gives the topic, options and one concrete sentence per event. Written by Claude (Opus 5.5 for sets 01013-01016, Sonnet 5.5 for the rest). A check (`synthgen/phase1_check_plans.py`) makes sure each sentence names the speaker the arc assigns.
3. **Dialogue, one meeting at a time.** Each meeting was written by a fresh Claude subagent that saw only: the writer prompt, that meeting's events, the cast and noise settings, and the earlier meetings' transcripts. It never saw later events, later options, or the arc name. `eval/leakcheck.py` verifies this on every spec that was shown to a writer (94 of 94 clean, and the check was tested to catch planted leaks).
4. **Import.** `synthgen/import_tagged.py` rebuilds transcripts and gold from the seed and the tags, then `validate.py` runs structural checks (0 errors on all 36 sets; 30 warnings, mostly repeated short utterances and a few implicit decisions that use a generic word such as "weekly").
5. **Panel verification.** Every link was judged by two independent LLM judges (see section 4).

| Writer group | Sets | Meetings | Utterances/meeting (mean, range) | Words/utt | Filler rate | Cut-off rate |
|---|---|---|---|---|---|---|
| claude-opus-5.5, prompt v1 (tuning sets 01013-01016) | 4 | 13 | 102 (77-120) | 11.7 | 0.113 | 0.127 |
| claude-sonnet-5.5, prompts v2/v3 | 26 | 81 | 100 (73-119) | 10.0 | 0.086 | 0.044 |
| toolkit pilot sets (earlier Claude session, model not recorded) | 6 | 19 | 30 (25-38) | 9.3 | 0.055 | 0.025 |

Prompt versions are in `data/synth_work/writer_prompts/CHANGELOG.md` and per set in `data/synth/provenance.json`. Sets 01017-01019 used v2 for meetings 1-2 and v3 afterwards.
The pilot sets have short meetings (below the 60-120 target) and are in DEV only.

Edits after generation, all logged in `reports/label_issues.md`: real brand names replaced in 4 sets; 3 plan sentences corrected to name the arc's speaker; one tag moved to the correct line;
one meeting rewritten after an incomplete file; two meetings trimmed to the 120-utterance cap by removing untagged tangents.

## 3. Split
`data/synth/split.json`, frozen 2026-11-03. DEV = 14 sets (6 pilot, 4 prompt-tuning, 4 others), TEST = 22 sets, all written by Sonnet 5.5. TEST has 232 questions, of which 65 are headline types
(why_changed 23, evidence_to_reconsider 20, full_lineage 22). SHA-256 of the sorted set lists: DEV `1515952f...`, TEST `6176494f...`, all `fe55a904...`.
Pooled corpora (`data/synth/pools/`) have sizes 1 and 10 only (4-week scope); sets are grouped by business domain; meeting ids are opaque and dates are distinct.

## 4. Verification
Two judges from different families (Gemini `gemini-3.5-flash-lite` and `granite4.2:8b`) judged all 293 links. Both said yes for 284 links (`verification: llm_consensus`, **scope: content and speaker only, not the role label**).
Nine links were flagged partial by a judge or by the agent hand-check; the agent re-read each and kept it (`verification: none` with the reason in `data/synth/verification.json`).
Neither judge said no for any link, so no gold label was edited.

| Check | n | Agreement | Cohen's kappa |
|---|---|---|---|
| Gemini vs granite | 293 | 97.6% | 0.354 |
| Gemini vs agent hand-check | 66 | 97.0% | 0.735 |
| granite vs agent hand-check | 66 | 98.5% | 0.881 |

Kappa is low for the judge pair only because "yes" is nearly universal (about 97%); raw agreement is the honest figure, and it also means the judges barely discriminate on this data.
The agent hand-check (66 links, stratified by role and writer, including all flagged links and 10 implicit resolutions) found 61 yes, 5 partial, 0 no. **It is an agent check, not a human check.**
No link has `human_spotcheck` or `human` status. An optional 30-row sheet for a human is at `reports/human_spotcheck.csv`.

**What the panel can and cannot catch.** A planted-negative test on DEV (`results/judge_sensitivity/`, 56 real and 57 corrupted links, Gemini only) flagged 100% of wrong-speaker links, 100% of unsupportive quotes and 79% of shifted utterances, with 0 of 56 false alarms, but only 1 of 15 wrong-role links (7%, 95% CI 1-30%). So `llm_consensus` means **content and speaker only**; it does not verify the role label, which is checked only by the role-blind agreement (`reports/role_verification.md`) and by the human spot-check if returned. Role labels rest on the arc structure and the agent hand-check of 66 links. granite was not tested.

Known pattern: for 5 links the gold utterance span marks only the key line(s) while part of the gist is spoken in adjacent untagged lines. Scoring will use a span tolerance fixed before any system output is seen.

## 5. The control-writer set (H4) is missing
The plan included 6 control sets written by a local model of another family to check for writer leakage. This did not work (deviations D-01, D-02, D-09, D-10): four local models
(`mistral-nemo:12b`, `llama3.1:8b`, `phi4:14b`, `olmo-3:7b`) failed QC under the Claude procedure; a chunked procedure for `mistral-nemo` gave 12 of 19 passing meetings after a disclosed tag-position repair,
but only two complete sets, one failing the validator and one rejected because its tagged lines do not realize the events. **There are no control-writer sets in this benchmark, so H4 cannot be tested.**
The rejected files are kept in `data/synth_work/rejected_control/` for the record, unedited.

## 6. Limitations
- Synthetic, LLM-written, and schema-shaped: the arcs come from the same schema the system uses, so a schema-aware system has a built-in advantage.
- All headline TEST sets share one writer (Sonnet 5.5) and one prompt family; writer style may favour or hurt particular systems, and there is no cross-writer check.
- Cleaner than real speech: filler and cut-off rates are about 0.09 and 0.04, and no overlapping speech; real-speech evidence comes only from the small AMI case study.
- Labels are LLM-verified, not human-verified. Both judges are strongly biased toward "yes".
- Small N: 22 TEST sets, so bootstrap intervals over sets will be wide, and the headline question types number 65.
- Some questions say "as of the end of meeting 2", an ordinal within the topic; in pooled corpora this relies on the topic wording.
- The 6 pilot sets are shorter than the rest and live in DEV.

## 7. Intended use
Evaluating whether systems can explain how and why a decision changed across meetings: lineage completeness, explanation faithfulness, answer correctness. Not for training, and not evidence about real organisations.
Licence: not yet decided. The text is original synthetic content generated for this project with Claude (interactive use on the user's Pro plan, no scripted API use). The release licence will be chosen in Phase 8 after checking the generating models' terms, and recorded in `LICENSES.md`.

## 8. Why 36 sets (the scale floor)
The master task aims for 60 sets (6 pilots + 54 new) and allows a floor of 36 with the same arc proportions if 60 does not fit the free resources, decided before any new set is written.
- **When:** proposed at CHECKPOINT 0 on 2026-11-01 from the Phase 0 feasibility estimate, approved by the user the same day, and applied on 2026-11-02 before the first new set was written (`data/synth_work/selection.json`).
- **Why:** the estimate for the full plan was 4.6 weeks of Kaggle quota for Phase 7 answers alone, against 1.8 weeks for the floor with ablations at pool size 1 (`reports/CHECKPOINT_0.md`). It assumed 20 s per answer, not yet measured at that point.
- **How the 30 new sets were chosen:** arc quotas by largest remainder from the 60-set proportions (simple_reversal 9, external_trigger 7, no_reversal 6, partial_override 5, re_reversal 5, deferred 4; the tie for the last slot went to no_reversal because it carries the false-premise question). After subtracting one pilot per arc, the first seeds from 1013 upward in each arc were taken, with no look at content. This leaves seeds 1040, 1042 and 1044 unused, and differs from the 60-set plan only by size.
- **Consequence:** fewer sets, so wider intervals. `SCOPE_4WEEK.md`, adopted later, did not change the set count.

## 9. Exact writer of every set
For the 30 new sets, plans were written in the main session and dialogue by per-meeting subagents, both on the model shown.
- **Sets 01017-01045:** model `claude-sonnet-5-5`. The subagents were launched with an explicit Sonnet setting, and API error messages during the run name that model.
- **Sets 01013-01016:** model `claude-opus-5-5`. The subagents inherited the main session's model; this was not logged separately per call.
- **The 6 pilot sets:** **the exact model is not recorded.** The only records are "Written by Claude" (`synthgen/data/pilot/README.md`) and `generator: claude-chat` in their gold metadata. They were written earlier, outside this project's sessions, in one pass per set, so the writer knew each ending. I cannot establish the model and do not guess it.

| Set | Split | Arc | Writer | Prompt version |
|---|---|---|---|---|
| set_01000 | DEV | no_reversal | claude (earlier session, model not recorded) | PROMPT_base |
| set_01002 | DEV | external_trigger | claude (earlier session, model not recorded) | PROMPT_base |
| set_01003 | DEV | partial_override | claude (earlier session, model not recorded) | PROMPT_base |
| set_01004 | DEV | re_reversal | claude (earlier session, model not recorded) | PROMPT_base |
| set_01006 | DEV | simple_reversal | claude (earlier session, model not recorded) | PROMPT_base |
| set_01012 | DEV | deferred | claude (earlier session, model not recorded) | PROMPT_base |
| set_01013 | DEV | simple_reversal | claude-opus-5.5 | v1 |
| set_01014 | DEV | re_reversal | claude-opus-5.5 | v1 |
| set_01015 | DEV | partial_override | claude-opus-5.5 | v1 |
| set_01016 | DEV | no_reversal | claude-opus-5.5 | v1 |
| set_01017 | TEST | external_trigger | claude-sonnet-5.5 | v2 (m1-2) + v3 (rest) |
| set_01018 | TEST | re_reversal | claude-sonnet-5.5 | v2 (m1-2) + v3 (rest) |
| set_01019 | DEV | deferred | claude-sonnet-5.5 | v2 (m1-2) + v3 (rest) |
| set_01020 | TEST | simple_reversal | claude-sonnet-5.5 | v3 |
| set_01021 | TEST | simple_reversal | claude-sonnet-5.5 | v3 |
| set_01022 | TEST | external_trigger | claude-sonnet-5.5 | v3 |
| set_01023 | DEV | external_trigger | claude-sonnet-5.5 | v3 |
| set_01024 | TEST | no_reversal | claude-sonnet-5.5 | v3 |
| set_01025 | TEST | external_trigger | claude-sonnet-5.5 | v3 |
| set_01026 | TEST | no_reversal | claude-sonnet-5.5 | v3 |
| set_01027 | TEST | re_reversal | claude-sonnet-5.5 | v3 |
| set_01028 | TEST | partial_override | claude-sonnet-5.5 | v3 |
| set_01029 | TEST | partial_override | claude-sonnet-5.5 | v3 |
| set_01030 | DEV | simple_reversal | claude-sonnet-5.5 | v3 |
| set_01031 | TEST | no_reversal | claude-sonnet-5.5 | v3 |
| set_01032 | TEST | partial_override | claude-sonnet-5.5 | v3 |
| set_01033 | TEST | no_reversal | claude-sonnet-5.5 | v3 |
| set_01034 | TEST | simple_reversal | claude-sonnet-5.5 | v3 |
| set_01035 | TEST | deferred | claude-sonnet-5.5 | v3 |
| set_01036 | TEST | simple_reversal | claude-sonnet-5.5 | v3 |
| set_01037 | TEST | simple_reversal | claude-sonnet-5.5 | v3 |
| set_01038 | TEST | external_trigger | claude-sonnet-5.5 | v3 |
| set_01039 | TEST | deferred | claude-sonnet-5.5 | v3 |
| set_01041 | TEST | simple_reversal | claude-sonnet-5.5 | v3 |
| set_01043 | TEST | re_reversal | claude-sonnet-5.5 | v3 |
| set_01045 | DEV | external_trigger | claude-sonnet-5.5 | v3 |
