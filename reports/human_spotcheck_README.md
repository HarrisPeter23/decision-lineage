# How to fill `reports/human_spotcheck.csv` (about 1 hour, 40 rows)

Open the CSV in Excel or any spreadsheet. The only columns you fill are **human_verdict** (`yes`, `partial` or `no`) and, if you like, **notes**. Save as CSV (keep the file name) and tell me.

## What each row asks
Each row is one link in a decision chain. Read `gist_to_check` (what the link is supposed to say), then `context_before`, then `marked_lines_with_star_and_after`. Lines starting with `*` are the marked lines; lines below them are the next lines, shown only to help.
Answer **yes** if the marked lines, in their context, show the named speaker (`expected_speaker`) doing what `gist_to_check` says, in the role named in `role`. Answer **partial** if part of it is right (for example the content is right but the role is arguable, or half the gist is in a neighbouring line). Answer **no** if it does not match.

## The role is the most useful thing for you to judge
The automatic judges cannot check roles reliably, so please judge the role in each row too:
- proposal: puts an option forward
- rationale: gives a reason for or against an option
- evidence: brings new information (data, a result, a constraint)
- challenge: objects to the current decision
- reconsideration: the group agrees to reopen the decision
- resolution: the group settles on an option (made, changed or kept)
`(implicit)` after a role means the speaker should settle it without naming the option (for example "fine, go ahead").
If you think the role is wrong, put the role you would choose in `notes`.

## Rows 25-40 are real meeting speech (AMI), the rest are synthetic
- `source` says which. AMI speakers are role codes: PM (project manager), ME (marketing expert), UI (user interface designer), ID (industrial designer).
- AMI text is raw transcription: lots of "um", repeated words, and acronyms written with underscores (T_V_ means TV). Expect long, messy lines.
- A few AMI decisions are phrased as a question that the team then accepts (for example "can we just put speech recognition in it as well, okay?"). Count it as **yes** if the marked line and the next two lines show the group settling on it; add a note saying it was a question.
- In AMI each marked line is only a part of a long discussion, so `partial` is a fair answer more often there.

## What happens with your answers
Links you mark `yes` or `partial` get `verification: human_spotcheck`, `no` triggers a re-read by me and, only if I agree, a logged label fix. I will report your agreement with the automatic judges and with my own hand-check. Nothing is changed in the benchmark split, and no gold label is edited silently.

## Result (2026-11-04)
34 yes, 6 partial, 0 no (see `reports/label_issues.md`; numbers in `results/human_spotcheck.json`, computed by `eval/spotcheck_apply.py`).
