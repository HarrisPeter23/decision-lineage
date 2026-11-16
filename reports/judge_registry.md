# Judge registry: which model judged what (one judge model per task, fixed before the task starts, never switched mid-task)

| Task | Judge model (digest / version) | Procedure | Items | Date | Output |
|---|---|---|---|---|---|
| Phase 1 link panel, all synthetic links | gemini-3.5-flash-lite (free tier) | single item per request | 293 links | 2026-11-02 | `results/panel/gemini_synth.jsonl` |
| Phase 1 link panel, all synthetic links | granite4.2:8b (f586c02f...) on Kaggle, Ollama | single item | 293 links | 2026-11-02 | `results/panel/granite_synth.jsonl` |
| Phase 1 control set_01063 links (set later rejected) | gemini-3.5-flash-lite | single item | 8 links | 2026-11-03 | `results/panel/gemini_synth.jsonl` (kept, not in dataset) |
| Phase 1 agent hand-check | agent (Sonnet 5.5), not a human | read in context | 66 links | 2026-11-02 | `results/panel/handcheck_agent.json` |
| Judge sensitivity, planted negatives (DEV) | gemini-3.5-flash-lite | single item | 113 (56 real + 57 corrupted) | 2026-11-03 | `results/judge_sensitivity/gemini.jsonl` |
| Judge sensitivity, planted negatives (DEV) | granite4.2:8b (f586c02f...) | single item | 113 | 2026-11-03 | `results/judge_sensitivity/granite.jsonl` |
| Role-blind label check | granite4.2:8b (f586c02f...) | single item | 293 links (all) | 2026-11-03 | `results/role_blind/granite.jsonl` |
| Role-blind label check | gemini-3.5-flash-lite | single item | **139 of 293** (items r000-r138, in set order; stopped by the 500/day limit) | 2026-11-03 | `results/role_blind/gemini.jsonl` |
| Batched-procedure validation | gemini-3.5-flash-lite | batches of 10 | 50 pre-drawn planted items (5 requests) | scheduled after the next quota reset | `results/gemini_batch/validation.json` |
| AMI relation pass (screening, not a judge) | qwen3:14b (bdbd181c...) SYSTEM_MODEL, thinking off | single item | 161 decision pairs | 2026-11-03 | `results/ami_screen/out/batch_out.jsonl` |
| AMI link panel (Phase 2) | granite4.2:8b (f586c02f...) | single item | 43 AMI links | 2026-11-03 | `results/panel_ami/granite.jsonl` (43 yes) |
| AMI link panel (Phase 2) | gemini-3.5-flash-lite | single item (43 < 50/day threshold in the plan) | 43 AMI links | scheduled after the 13:30 IST reset | `results/panel_ami/gemini.jsonl` |
| Phase 5 answer correctness, rubric (non-exact types), DEV pool 1 and 10, flag and drop variants | granite4.2:8b (f586c02f...) on Kaggle, Ollama, think off, temperature 0 | single item; prompt `eval/phase5_score.py` judge_prompt | ~200 per pool size | 2026-11-04 | `results/phase5/judge/<tag>/` |
| Phase 5 sentence faithfulness (all sentences) | NLI cross-encoder/nli-deberta-v3-small (fa2804872c3b), CPU, entail >= 0.5 | ALCE citation recall/precision | all DEV sentences | 2026-11-04 | `results/phase5/score/<tag>/answers.jsonl` |
| Phase 5 faithfulness-checker validation | agent (Opus 5.5), not a human | read sentence + cited items, NLI score hidden | >= 50 stratified sentences (seed 0) | 2026-11-04 | `results/phase5/agent_check.json` |
| Phase 5 NLI-vs-judge agreement | gemini-3.5-flash-lite | single item (batching not validated for this task) | ~200 pre-drawn stratified sentences | after the next quota reset | `results/phase5/gemini_faith.jsonl` |
| Phase 5 planted-negative validation (sentences: NLI; answers: granite) | NLI + granite4.2:8b; Gemini on a subset if quota allows | single item | ~60 corrupted + ~60 real each | 2026-11-04/05 | `results/phase5/planted/` |

Notes
- The role-blind Gemini result covers a subset that is **not stratified**: the first 139 items in set order (sets 01000-01019 approximately). Under the new rule
  (Gemini on pre-drawn calibration samples only) it is not extended; it is reported as n=139 with its role mix (proposal 19, rationale 37, evidence 20,
  challenge 14, reconsideration 15, resolution 34). Mixing single-item and batched verdicts in one task would change the procedure mid-task, so this is avoided.
- Only gemini-3.5-flash-lite has a documented quota known to us (500 requests/day, read from its own 429 on 2026-11-03). Other free Gemini models' limits
  are shown only in AI Studio, so no task is assigned to them.
