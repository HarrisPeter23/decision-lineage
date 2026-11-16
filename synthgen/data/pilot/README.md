# Pilot dataset: temporal decision-lineage benchmark (6 sets, all internal corporate meetings)

One set per arc type: no_reversal (control, with a distractor decision), external_trigger,
partial_override, re_reversal (4 meetings), simple_reversal, deferred.
Every set is a series of internal business meetings of one team inside a company (SaaS product, corporate events,
corporate facilities, supply chain and operations). Written by Claude to the fixed assignments for seeds 1000-1012 (see synthgen/build_prompts.py), so the
remaining 54 assignments in `assignments_all.md` continue the same design.

## Files
- `transcripts/<set>.json`   cast, meetings, utterances (idx, speaker, text, ts). The ONLY input a system may read.
- `questions.jsonl`           qid, set_id, type, question (no answers).
- `gold_answers.jsonl`        answer_text, answer_facts, supporting_links per question.
- `gold/<set>.json`           full gold: decision versions (valid_from/valid_to), typed chain links
                              (role, speaker, utterance_idxs, gist), changes, distractor, questions.
- `review_sheet.csv`          one row per chain link for human verification (fill human_verdict).
- `transcripts_txt/<set>/<meeting>.txt`  the same meetings as plain text (see ingest.py), the form a real system would ingest.
- `source_text/*.txt`         the authored text files (tags show which utterance realizes which event).

## Known limitations (state them in any write-up)
- Pilot scale: 6 sets, 19 meetings, 60 questions. Far too small for significance claims.
- Meetings are SHORT: 25-38 utterances (~9 words each), roughly 5-6 minutes of talk, versus ~30 minutes in AMI.
  The planned production target is 70-120 utterances per meeting.
- Speech is cleaner than real meetings (low filler and cut-off rates; see validate.py --stats).
- One author wrote content and labels per set in a single pass (so the writer knows the ending), which
  can make lineage easier to recover than in real data. Compare against the AMI subset.
- Gold structure comes from the arc definition; gold utterance tags were placed by the same author and
  have NOT yet been human-verified or checked by an independent judge model.
