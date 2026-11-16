# Label and text issues (pre-freeze edits)

- set_01014/m1.txt: real brand removed (rule 11). before: `gmail people though` after: `free-mail people though`
- set_01014/m1.txt: real brand removed (rule 11). before: `Gmail people aren't buying` after: `Free-mail people aren't buying`
- set_01014/m1.txt: real brand removed (rule 11). before: `And the gmail question` after: `And the free-mail question`
- set_01014/m2.txt: real brand removed (rule 11). before: `they're mailinator addresses` after: `they're throwaway addresses`
- set_01014/m2.txt: real brand removed (rule 11). before: `typing in the Amex to look` after: `typing in a corporate card to look`
- set_01014/m2.txt: real brand removed (rule 11). before: `That's Stripe's dunning emails` after: `That's the payment processor's dunning emails`
- set_01014/m3.txt: real brand removed (rule 11). before: `hand out the Amex so` after: `hand out the company card so`
- set_01014/m3.txt: real brand removed (rule 11). before: `without 128 mailinator addresses` after: `without 128 throwaway addresses`
- set_01014/m3.txt: real brand removed (rule 11). before: `they were mailinator addresses` after: `they were throwaway addresses`
- set_01016/m1.txt: real brand removed (rule 11). before: `the wrong Marriott, right` after: `the wrong Hartwell, right`
- set_01016/m1.txt: real brand removed (rule 11). before: `To the wrong Marriott.` after: `To the wrong Hartwell.`
- set_01019/m1.txt: real brand removed (rule 11). before: `from the Slack thread` after: `from the chat thread`
- set_01019/m3.txt: real brand removed (rule 11). before: `count the Slack thread` after: `count the chat thread`
- set_01025/m3.txt: 11 untagged tangent lines removed to meet the 120-utterance cap (now 118).
- set_01036 B7: gist named Mateo, but the arc assigns this beat to Lena; gist corrected. before: `Mateo argues for hardware keys because they resist phishing and number takeovers, cost about 28 dollars each or 6,160 for 220 people, and a 15-person pilot produced no support tickets.` after: `Lena argues for hardware keys because they resist phishing and number takeovers, cost about 28 dollars each or 6,160 for 220 people, and a 15-person pilot produced no support tickets.`
- set_01037 B7: gist named Lena, but the arc assigns this beat to Diego; gist corrected. before: `Lena argues for the regional couriers because Eastline and Southgate average 4.35 pounds, guarantee 95 percent on time with credits for misses, saving about 9,000 pounds a quarter, and have no minimum-volume clause where Parcelwise requires 15,000 parcels.` after: `Diego argues for the regional couriers because Eastline and Southgate average 4.35 pounds, guarantee 95 percent on time with credits for misses, saving about 9,000 pounds a quarter, and have no minimum-volume clause where Parcelwise requires 15,000 parcels.`
- set_01041 B7: gist named Meera, but the arc assigns this beat to Zainab; gist corrected. before: `Meera argues for three mandatory fields plus a survey link sent to the rep two days after close, since a trial with 20 reps reached 83 percent completion with real answers.` after: `Zainab argues for three mandatory fields plus a survey link sent to the rep two days after close, since a trial with 20 reps reached 83 percent completion with real answers.`
- set_01036 m3: the @B6 tag moved from Lena's reaction line to Amara's reopening line two lines earlier (the arc assigns B6 to the manager). Plumbing fix, no text change.
- Panel review (Phase 1.3): 293 links judged by gemini-3.5-flash-lite and granite4.2:8b (0 'no' from either judge). 9 links were flagged 'partial' by at least one source (judge or agent
  hand-check); each was re-read by the agent and KEPT unchanged (data/synth/verification.json). Pattern: for 5 of them the gold span marks only the key line(s) while part of the gist is
  spoken in adjacent untagged lines (set_01022 B6, 01029 B4, 01036 B4, 01037 B7, 01043 B8). This will be handled by a pre-registered span tolerance in scoring, not by editing gold.

## Human spot-check (2026-11-04, 40 links: 24 synthetic, 16 AMI; `reports/human_spotcheck.csv`, `results/human_spotcheck.json`)
- Verdicts: 34 yes, 6 partial, **0 no**. Nothing is logged as a gold error. Gold files were not edited (no approval requested or needed).
- The 6 `partial` rows are recorded for the pre-freeze panel rule; each is an observation about a span or role, not a "no". They are all kept as they are, awaiting the user's decision:
  - set_01029 B4 evidence: the gist adds the five customer complaints, which the marked line does not mention (span narrower than gist; already in the known-narrow-span list).
  - set_01021 B5 challenge: the crash-unresolved-for-a-week part sits in the previous line (span narrower than gist; new case beyond the earlier nine).
  - set_01036 B4 evidence: the 40-minute exposure of the executive mailbox is not in the marked line (span narrower than gist; already on the list).
  - ami_ES2002 B8 resolution (implicit): the PM does not clearly confirm kinetic power plus backup battery in these lines (the decision is implicit across lines).
  - ami_TS3004 B9 resolution: not clear from the marked lines that the team agreed to keep speech recognition.
  - ami_TS3012 B1 proposal: the human reads it as context/evidence ("explaining what the project is about"), not a proposal. This is the one role disagreement, 1 of 40.
