# Role verification (role-blind) and judge sensitivity

**What the link-level `llm_consensus` label means: content and speaker only.** The panel judges were told the intended role and could not detect wrong roles (see section 2). Roles are verified only by (a) this role-blind agreement, in which the judge does not see the gold role, and (b) the human spot-check if it is returned.

## 1. Role-blind agreement with gold

The judge sees the context and the target lines and picks one of six roles; it is never told the gold role, the speaker or the gist. A low recall means the judge and the gold disagree; it does not say which one is right, because the judges themselves are weak at argumentative roles.

Batched procedure (10 per request) validated on 49 links that also have single-item verdicts: exact agreement 0.837, kappa 0.79, threshold 0.9, passed = False. Gemini verdicts: items r000-r138 single-item, the rest batched.

### Gemini, synthetic links (293 of 293)
n = 293; accuracy 0.689; Cohen's kappa 0.623

| gold role | n | recall (judge names the gold role) | 95% Wilson CI |
|---|---|---|---|
| proposal | 40 | 40/40 = 1.00 | 0.91-1.00 |
| rationale | 77 | 16/77 = 0.21 | 0.13-0.31 |
| evidence | 41 | 41/41 = 1.00 | 0.91-1.00 |
| challenge | 30 | 3/30 = 0.10 | 0.03-0.26 |
| reconsideration | 32 | 31/32 = 0.97 | 0.84-0.99 |
| resolution | 73 | 71/73 = 0.97 | 0.91-0.99 |

Confusion matrix (rows = gold role, columns = judge's role):

| gold \ judge | proposal | rationale | evidence | challenge | reconsideration | resolution |
|---|---|---|---|---|---|---|
| **proposal** | 40 | 0 | 0 | 0 | 0 | 0 |
| **rationale** | 14 | 16 | 47 | 0 | 0 | 0 |
| **evidence** | 0 | 0 | 41 | 0 | 0 | 0 |
| **challenge** | 2 | 18 | 7 | 3 | 0 | 0 |
| **reconsideration** | 0 | 0 | 1 | 0 | 31 | 0 |
| **resolution** | 2 | 0 | 0 | 0 | 0 | 71 |

### Gemini, AMI links (43 of 43)
n = 43; accuracy 0.442; Cohen's kappa 0.306

| gold role | n | recall (judge names the gold role) | 95% Wilson CI |
|---|---|---|---|
| proposal | 8 | 6/8 = 0.75 | 0.41-0.93 |
| rationale | 13 | 5/13 = 0.38 | 0.18-0.64 |
| evidence | 4 | 3/4 = 0.75 | 0.30-0.95 |
| challenge | 1 | 0/1 = 0.00 | 0.00-0.79 |
| reconsideration | 5 | 0/5 = 0.00 | 0.00-0.43 |
| resolution | 12 | 5/12 = 0.42 | 0.19-0.68 |

Confusion matrix (rows = gold role, columns = judge's role):

| gold \ judge | proposal | rationale | evidence | challenge | reconsideration | resolution |
|---|---|---|---|---|---|---|
| **proposal** | 6 | 0 | 1 | 0 | 0 | 1 |
| **rationale** | 3 | 5 | 3 | 1 | 1 | 0 |
| **evidence** | 1 | 0 | 3 | 0 | 0 | 0 |
| **challenge** | 0 | 1 | 0 | 0 | 0 | 0 |
| **reconsideration** | 4 | 0 | 1 | 0 | 0 | 0 |
| **resolution** | 4 | 2 | 0 | 0 | 1 | 5 |

### granite4.2:8b, synthetic links
n = 293; accuracy 0.444; Cohen's kappa 0.350

| gold role | n | recall (judge names the gold role) | 95% Wilson CI |
|---|---|---|---|
| proposal | 40 | 40/40 = 1.00 | 0.91-1.00 |
| rationale | 77 | 5/77 = 0.06 | 0.03-0.14 |
| evidence | 41 | 40/41 = 0.98 | 0.87-1.00 |
| challenge | 30 | 14/30 = 0.47 | 0.30-0.64 |
| reconsideration | 32 | 13/32 = 0.41 | 0.26-0.58 |
| resolution | 73 | 18/73 = 0.25 | 0.16-0.36 |

Confusion matrix (rows = gold role, columns = judge's role):

| gold \ judge | proposal | rationale | evidence | challenge | reconsideration | resolution | invalid |
|---|---|---|---|---|---|---|---|
| **proposal** | 40 | 0 | 0 | 0 | 0 | 0 | 0 |
| **rationale** | 39 | 5 | 32 | 0 | 0 | 0 | 1 |
| **evidence** | 1 | 0 | 40 | 0 | 0 | 0 | 0 |
| **challenge** | 7 | 2 | 7 | 14 | 0 | 0 | 0 |
| **reconsideration** | 17 | 1 | 1 | 0 | 13 | 0 | 0 |
| **resolution** | 55 | 0 | 0 | 0 | 0 | 18 | 0 |

## 2. Judge sensitivity on planted corruptions (DEV, 56 real + 57 corrupted links)

A corrupted link counts as detected when the judge says partial or no. Real links not judged yes are false alarms. 95% Wilson intervals.

| judge | corruption | n | detected (partial or no) | rate | 95% CI | judged no | rate |
|---|---|---|---|---|---|---|---|
| gemini | wrong role | 15 | 1 | 0.07 | 0.01-0.30 | 0 | 0.00 |
| gemini | wrong speaker | 14 | 14 | 1.00 | 0.78-1.00 | 13 | 0.93 |
| gemini | shifted utterance | 14 | 11 | 0.79 | 0.52-0.92 | 11 | 0.79 |
| gemini | unsupportive quote | 14 | 14 | 1.00 | 0.78-1.00 | 14 | 1.00 |
| gemini | all corrupted | 57 | 40 | 0.70 | 0.57-0.80 | 38 | 0.67 |
| gemini | real links (false alarms) | 56 | 0 | 0.00 | 0.00-0.06 | 0 | 0.00 |
| granite | wrong role | 15 | 0 | 0.00 | 0.00-0.20 | 0 | 0.00 |
| granite | wrong speaker | 14 | 10 | 0.71 | 0.45-0.88 | 4 | 0.29 |
| granite | shifted utterance | 14 | 12 | 0.86 | 0.60-0.96 | 9 | 0.64 |
| granite | unsupportive quote | 14 | 14 | 1.00 | 0.78-1.00 | 13 | 0.93 |
| granite | all corrupted | 57 | 36 | 0.63 | 0.50-0.74 | 26 | 0.46 |
| granite | real links (false alarms) | 56 | 0 | 0.00 | 0.00-0.06 | 0 | 0.00 |

Both judges see the intended role in the prompt, so for wrong-role items a flag means the judge disagreed with a stated role; neither did so reliably.
