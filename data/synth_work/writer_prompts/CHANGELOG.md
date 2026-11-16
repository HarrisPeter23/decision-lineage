# Writer prompt versions

- PROMPT_base.md (toolkit): not used for new sets; it shows the full arc, which breaks the anti-foreshadowing rule.
- v1 (2026-11-02): per-meeting prompt, no arc tables. Used for set_01013-01016 (claude-opus-5.5), the 4 tuning sets.
- v2 (2026-11-02): tuned after reading all 13 meetings of those sets. Changes and the reason for each:
  - Tagged lines must not copy the spec wording: key lines read almost like the gists, making extraction too easy (lesson a).
  - Hard limit of 120 utterances: set_01014 m3 reached 128.
  - No running jokes or comic set pieces: every set had them, which reads as a sitcom.
  - Imperfect arithmetic: managers did exact sums aloud.
  - Seeded off-cast names and a banned-detail list: Priya appeared in 4 of 4 sets; dentist, shoebox and Lisbon each in 2.
  - Varied meeting structure: most meetings ran admin, topic, admin.
  Sets 01013-01016 stay on v1 and are tagged as such, so any v1/v2 difference can be measured.
- v3 (2026-11-02, Sonnet 5.5): v2 plus a fictional-names rule (rule 11: no real companies). Reason: sets 01013-01016 contained real brands
  (a payment processor, a hotel chain, a card brand, free-mail providers). Those are replaced by hand before import and logged in
  reports/label_issues.md. set_01017-01019 meetings 1-2 were written with v2 and their later meetings with v3; set_01020 onward use v3 only.
- v3c (2026-11-02, procedure for the CONTROL writer only; a behavioural change, so a new name per rule 12). Same v3 prompt text and the same per-meeting
  spec as the Claude writers, but generated in chunks. Reason: in the first control run, mistral-nemo:12b given the whole-meeting prompt wrote 8-19 lines
  (60-120 required) in 8 of 8 attempts, with stage directions and misplaced tags. Differences from the Claude procedure, all to be disclosed as a deviation:
  (a) about 25 lines per call, with the dialogue so far in the meeting shown to the model; (b) the meeting's events are scheduled across the chunks and
  shown only in the chunk where they are due; (c) lines that are not 'CastName: words' (stage directions, commentary) are dropped before QC; (d) up to 3 whole-meeting
  attempts plus up to 3 tries per chunk, best attempt kept; (e) the plans (topic, options, event gists) were written by Claude, only the dialogue by the control model.
  A model that passes QC with the original whole-meeting procedure would replace this (see reports/deviations.md D-02).
- v3c2 (2026-11-02, control writer procedure revision, rule 12 new name). Same as v3c with: (a) the chunk instruction forbids writing event names (B4, D2) in speech; (b) a chunk is accepted
  only if it has >= 70 percent of the requested lines, every due tag, and no stray event ids, with up to 5 tries per chunk; (c) if stray ids remain after all tries they are stripped from
  the words (plumbing, disclosed); (d) up to 4 whole-meeting attempts. Reason: in the v3c run 10 of 19 control meetings failed QC, mostly stray tag ids and missing tags. set_01063 passed in
  v3c and is kept unchanged; the other five control sets are regenerated with v3c2.
