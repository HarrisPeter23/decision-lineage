# synthgen - synthetic multi-meeting decision-lineage benchmark

Generates sets of 3-4 related meeting transcripts in which a team decides, challenges, and
sometimes reverses a decision, together with gold causal chains and evaluation questions.

**Scope: every scenario is an internal corporate meeting** (a team inside a company: engineering, product, marketing,
finance, IT/security, supply chain, facilities, events, sales ops, data, HR). Domains for seeds from 1013 on are balanced
across these twelve functions (`arcs.BALANCED_FROM_SEED`); the six pilot seeds keep their original assignment.

## Design principle: plan first, then write

1. **`arcs.py` fixes the gold structure in code**: which roles occur, in which meeting, spoken by
   which participant, which option is valid when. Six arc types: simple reversal, re-reversal,
   partial override, **no reversal (control)**, deferred decision, external trigger. A distractor
   decision is added to ~40% of sets.
2. **The LLM only supplies content**: a planner call fills in topic, options and one concrete sentence
   per event; one writer call per meeting turns the events into messy spoken dialogue and reports
   which utterances realize each event.
3. **Gold labels therefore come from the plan, not from re-reading the transcript**. Humans verify
   them instead of annotating from scratch.
4. **Questions and gold answers are built deterministically** from the plan (`assemble.py`).
   An optional LLM pass paraphrases question wording to reduce template leakage.

## Quick start

```bash
python generate.py --mock --n 10 --out data/mock      # offline smoke test, no API key
python selftest.py                                     # proves the validator catches corruptions
python make_example.py                                 # hand-written reference set in example/

pip install anthropic            # or: pip install openai
export ANTHROPIC_API_KEY=...     # (or OPENAI_API_KEY)
python generate.py --provider anthropic --model <GENERATOR_MODEL> --n 5 --out data/pilot
python validate.py data/pilot --stats
```

**Read the pilot sets yourself before scaling.** Then run, e.g.
`--n 100 --seed 1000 --paraphrase --out data/synth`. Arc types are balanced automatically.

NOTE: the anthropic/openai branches in `llm.py` were written without network access and are
untested against live APIs. The mock path and every non-LLM component are tested.


## Alternative path: another Claude writes the content (no API calls from you)

`build_prompts.py` generates `prompts_out/batch_01.md ... batch_12.md` (60 sets, 5 per batch) plus
`PROMPT_base.md` and `assignments_all.md`. Each batch file is a complete prompt: paste it into a
fresh Claude chat (or give it to Claude Code, which can save files directly).

1. The other Claude writes ONE plain-text file per set (the same format as `pilot/*.txt`): header lines (topic, options,
   one gist per event), then `== m1` ... and one `Name: words` line per utterance with ` @B4` tags on the key utterances.
   It never types indexes or structure and never writes JSON.
2. Save each reply as `inbox/<set_id>.txt` (JSON files are still accepted).
3. `python import_tagged.py inbox/ --out data/synth` (reads .txt and .json) rebuilds the exact transcript + gold files from
   `arcs.sample_spec(seed, arc_type)` (so roles, cast, dates, versions, questions and gold answers
   always match the arc) and runs `validate.py`. Problems are reported per file with the reason;
   paste them back to Claude and ask it to fix that set.
4. Then run the same QC protocol (`validate.py --stats`, judge, human review sheet).

Change size or seed with `python build_prompts.py --n 100 --seed 2000 --per-batch 5`. The assignments
(arc, cast, distractor, implicit resolutions, noise) come from the same seed the importer uses, so
keep `--seed`/`--n` identical between building prompts and importing.

## Scoring and the first baselines

```bash
python selftest_score.py                                         # 18 checks: corrupt oracle predictions, scorer must react exactly
python extract_baseline.py --data data/pilot --out preds/rules --provider rules      # keyword lower bound (offline)
python extract_baseline.py --data data/pilot --out preds/single_pass --provider anthropic --model <MODEL>
python score.py --pred preds/single_pass --data data/pilot --bootstrap 1000 --out results/single_pass.json
```
`score.py` reports localization and role-typed P/R/F1 (micro, per role, macro), role and speaker accuracy,
chain completeness and chain-exact rate, implicit-resolution recall, a gold-to-predicted role confusion
matrix, a per-arc table and bootstrap 95% CIs resampled over SETS. Precision is a lower bound because gold
labels only the annotated decisions. `extract_baseline.py` aborts if every LLM call fails, so a broken API
setup cannot masquerade as a zero score.

Lesson from the first run (results/): a keyword baseline I wrote after seeing the pilot got role-typed F1
0.55 and 100% implicit-resolution recall, because the pilot used stock phrases ("let's go with that").
After rewording two implicit decisions naturally, implicit recall fell to 0 and F1 to 0.52. So: (1) never
treat a rule baseline written with knowledge of the data as a reference result, (2) the benchmark is only
hard if phrasing varies. The batch prompts now forbid stock phrases and require varied implicit agreements.

## Plain-text transcripts and ingestion

`python ingest.py export data/pilot transcripts_txt` writes each meeting as a plain-text file (header, blank line, one
`Speaker: text` line per utterance); `python ingest.py roundtrip data/pilot` proves the text parses back to identical
speakers, text and indexes. Utterance index = zero-based position among the utterance lines, which is what scoring uses.
Systems under test should be given the text files; the JSON `gold/` files are for scoring only.

## Multi-pass extraction and the one-command ablation

```bash
python selftest_multipass.py                      # 14 checks with a gold-informed fake model (no API)
python run_ablation.py --data data/pilot --provider anthropic --model <MODEL> --out results/ablation
python error_dump.py --pred results/ablation/mp_p123/preds --data data/pilot --out errors.md
```
`run_ablation.py` runs rules, single_pass, mp_p3 (control), mp_p3_verify, mp_p13, mp_p123 and mp_p123_verify, scores each
with bootstrap CIs over sets, logs tokens per configuration, and writes `summary.md`. Failed LLM calls make a row FAILED
instead of a quiet zero. `antigravity_prompt_run_baselines.md` is a ready prompt for an autonomous coding agent that has
network access and API keys.

## Output

```
OUT/transcripts/<set>.json   cast, meetings, utterances (idx, speaker, text, ts)  <- system input
OUT/gold/<set>.json          meta, topic, options, versions (valid_from/valid_to), chain links
                             (role, speaker, utterance_idxs, gist), changes, questions + gold answers
OUT/rejected/<set>.json      sets that failed validation after retries
llm_log.jsonl                every call: model, tokens, seconds (use for the cost/latency numbers)
```

Systems under test must read **only** `transcripts/`. Question `supporting_links` let you score
retrieval and chain completeness; `answer_facts` support exact-match checks.

## Quality-control protocol (do all four; report them in the paper)

1. **Automatic checks** (`validate.py`): speakers in cast, indexes in range, key utterance spoken by
   the intended person, ordering rules (evidence after the decision it challenges, resolution after
   proposal, ...), no leaked event IDs or meta words, implicit/explicit resolution heuristics.
2. **Independent LLM judge**: `python validate.py OUT --review-csv rev.csv --judge --provider P --model M`
   Use a model from a *different family* than the generator. It pre-fills `auto_judge`.
3. **Human verification of every chain link** in `rev.csv` (fill `human_verdict`). Double-annotate
   ~20% with a second person and report agreement (Cohen's kappa). Remove or regenerate failures.
4. **Diversity audit**: `python validate.py OUT --stats` (arc/domain balance, near-duplicate sets,
   filler and cut-off rates). Compare these against the AMI subset to see how clean the synthetic
   speech is.

Freeze a test split BEFORE tuning any prompt or system.

## Things to tune on the pilot

- Dialogue too clean/formulaic: raise `noise` ranges in `sample_spec`, add few-shot excerpts from
  AMI or from `example/` to `MEETING_SYSTEM`.
- Implicit resolutions that actually name the option (warning in validate): tighten the IMPLICIT note.
- Meetings shorter than 50 utterances: raise the target or request two passes.
- Same-sounding evidence across sets: add more domains / decision hints in `arcs.DOMAINS`.
- Questions: spot-check paraphrases did not change meaning (`question_template` keeps the original).

## Rough cost

About 5-6 LLM calls per set (1 plan, 3-4 meetings, 1 paraphrase). A meeting is roughly 3-5k
output tokens, so 100 sets is on the order of 1-1.5M output tokens plus prompt tokens. This is a
rough estimate; read the real numbers from `llm_log.jsonl` after the pilot and price them with your provider.

## What to disclose in the paper

Generation method and prompts (`prompts.py`), generator and judge models, that gold structure is
specified by the plan, validation and human-verification results (including agreement), known
limitations (cleaner than real speech, limited domains, LLM-written dialogue), and that real-speech
results come from a separate annotated AMI subset.
