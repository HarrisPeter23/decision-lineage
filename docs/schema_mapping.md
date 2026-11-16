# Schema mapping: our chain roles vs decision dialogue acts (DDA) and IBIS

Draft 2026-11-03. Sources were opened and read: Fernandez, Frampton, Ehlen, Purver, Peters (2008), "Modelling and Detecting Decisions in Multi-party Dialogue", SIGdial, pp. 156-163 (`baselines/papers/fernandez2008_W08-0125.pdf`);
Anastasiou and De Liddo (2025), BCause, arXiv:2505.03584 (`baselines/papers/bcause_2505.03584.pdf`). Anastasiou and De Liddo (2024, DELITE) was downloaded but its text is not used here.
**What each source defines is quoted or paraphrased from the source. The mapping column is our interpretation and is marked as such.**

## 1. What the sources define
**Fernandez et al. 2008, Table 1.** Three main DDA classes, each applied within one decision sub-dialogue of a meeting:
- **I, issue:** utterances introducing the issue or topic under discussion.
- **R, resolution:** utterances containing the decision that is adopted. Subdivided into **RP, resolution proposal** (the decision adopted is proposed) and **RR, restatement** (the decision adopted is confirmed or restated).
- **A, agreement:** utterances explicitly signalling agreement with the decision made.
The paper describes a typical sub-dialogue as an issue raised, one or more proposals considered, and a decision adopted once agreement is reached. It names arguments for and against proposals as information worth extracting but says it does not intend to fully address this (paraphrase); the scheme has no classes for them. It is a scheme for ONE sub-dialogue; nothing links sub-dialogues across meetings.

**BCause (Anastasiou and De Liddo, 2025).** Maps discussion elements onto the IBIS schema: **Issues** (high-level topics under deliberation), **Positions** (specific stances on the issues) and **Arguments** ("evidence and reasoning provided to support or oppose positions"). Built for deliberation events, with human review of AI-proposed structures. We did not find a notion of decision versions or supersession across meetings in the part of the paper we read.

## 2. Our roles, mapped (interpretation)
| Our role | Meaning (from `synthgen/arcs.py`) | Closest DDA class | Closest IBIS element | Match |
|---|---|---|---|---|
| proposal | a participant puts forward an option for the decision | RP (resolution proposal), though RP is defined as proposing "the decision adopted"; ours also covers options later rejected | Position | partial: DDA's RP is tied to the adopted option, ours is not |
| rationale | a participant gives a reason for or against an option | none | Argument | IBIS yes; DDA has no class |
| evidence | a participant introduces new information bearing on the decision | none | Argument (the "evidence" half of "evidence and reasoning") | partial; we separate new information from reasoning, IBIS does not |
| challenge | a participant objects to the current decision or argues against it | none (A is the opposite polarity) | Argument opposing a Position | yes in IBIS |
| reconsideration | the group explicitly agrees to reopen the decision | I (an issue is raised again) | Issue re-raised | partial: I introduces a topic, ours says the topic was already decided |
| resolution | the group settles on an option (made, changed or reaffirmed) | R: RP when the option is first adopted, RR when reaffirmed; A for explicit agreement | Position chosen | yes for R; DDA's RR corresponds to our reaffirmation |

Our schema also has nodes IBIS and DDA do not: Meeting, Person, Topic, Decision, Evidence, and edges PROPOSED_BY, JUSTIFIED_BY, CHALLENGED_BY, SUPERSEDED_BY, RESOLVED_BY, DISCUSSED_IN.
Several of these distinctions are judgement calls on our side; the mapping is a reading aid, not a claim of equivalence.

## 3. What is new here (the only novelty claim)
1. **Across meetings.** DDA classes and IBIS maps describe one decision sub-dialogue or one deliberation. We link the same decision across meetings, with versions, validity windows and **supersession** edges, and we distinguish reaffirmation (no new version), partial override (a modified version) and reversal (a new version).
2. **Reasons for a change are typed and attached to versions.** Rationale, evidence and challenge links hang off the decision version they bore on, so a question such as "why did the team change its mind" has a structured answer path.
3. **Explanations are checked against the structure.** Every claim in a generated explanation cites a link, and a faithfulness checker tests the cited text.
We do **not** claim that typing decision roles within one meeting is new (Fernandez et al. 2008), that mapping speech to IBIS is new (Anastasiou and De Liddo), or that tracking state across meetings is new (EvoWiki and Graphiti track state). Our contribution is typing the reasons for a change; in the material we read, the EvoWiki paper has no rationale field, and for Graphiti we read only its README, so the claim that it does not type reasons is not yet verified against its code.

## 4. Open points
- Whether proposal should be split into "adopted" and "rejected" options is not decided; the benchmark does not make the distinction.
- The relation of our reaffirmation to RR is only approximate: RR is a restatement within a sub-dialogue, our reaffirmation is a later meeting confirming an earlier decision.
- Role typing quality is not verified by the LLM panel (planted-negative test, `reports/FREEZE.md` section 6).
