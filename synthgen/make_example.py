"""make_example.py - writes a hand-authored reference set to example/ using the same
assemble() path as generated data. Utterances carry event tags; realized indexes are
computed from the tags so they cannot drift. Use it as the quality bar and as a
few-shot reference when you tune the meeting prompt."""
import json
import pathlib

from arcs import sample_spec
from assemble import assemble
from validate import validate_set

spec = sample_spec(1, "simple_reversal", set_id="example_001")
spec["cast"] = [
    dict(name="Meera", slot="manager", style="hedges a lot"),
    dict(name="Arjun", slot="proposer", style="talkative"),
    dict(name="Lena", slot="challenger", style="devil's advocate"),
    dict(name="Tomas", slot="supporter", style="quiet"),
    dict(name="Wei", slot="observer", style="detail-oriented"),
]
spec["dates"] = ["2025-03-03", "2025-03-10", "2025-03-17"]
spec["distractor"] = None
for b in spec["beats"]:
    b["implicit"] = b["id"] == "B3"   # the first resolution is an implicit "let's do that"

plan = dict(
    topic="the datastore for the order-tracking service",
    options={"A": "MongoDB (document database)", "B": "PostgreSQL with JSONB columns"},
    beats={
        "B1": "Arjun proposes using MongoDB for the order-tracking service.",
        "B2": "Arjun says the schema will keep changing for months and documents avoid a migration per change.",
        "B3": "Meera agrees to go ahead with the MongoDB plan.",
        "B4": "Wei reports a weekend load test: at about two million orders the daily report aggregation takes 38 seconds and is still climbing.",
        "B5": "Lena argues reporting is join-heavy and finance needs consistent transactions across orders and payments, so it gets worse as data grows.",
        "B6": "Meera says the load test and finance's transaction requirement mean they must reopen the datastore decision.",
        "B7": "Lena argues PostgreSQL with JSONB keeps the flexible fields while adding joins and transactions, and switching now costs about a week.",
        "B8": "Meera decides to switch the order-tracking service to PostgreSQL; Arjun redoes the schema, Lena reviews.",
    },
    distractor=None,
)

M1 = [
    ("Meera", "Okay, let's get started, um, three things today - the order-tracking datastore, sprint dates, and, Tomas, your CI thing.", []),
    ("Tomas", "Yeah the CI thing can be quick. Datastore first though, that one blocks me.", []),
    ("Arjun", "So, I've been thinking about this, and I'd say we just go with MongoDB for the order-tracking service.", ["B1"]),
    ("Lena", "Hm. Why Mongo, specifically?", []),
    ("Arjun", "Because the schema's going to keep moving for the first few months - carriers, return flows, whatever finance asks for. With documents we don't write a migration every time someone adds a field, we just ship.", ["B2"]),
    ("Wei", "I mean, that part's true, we changed the shipment object twice last quarter.", []),
    ("Lena", "Sure, but- no, okay, go on, I don't want to derail this.", []),
    ("Tomas", "Is anyone else hungry? Sorry. Ignore me.", []),
    ("Meera", "Ha, lunch after. Arjun, you're confident enough about the, the document model?", []),
    ("Arjun", "Yeah, for now. I can have a prototype by next week.", []),
    ("Meera", "Fine. Let's do that.", ["B3"]),
    ("Meera", "Sprint dates - I was thinking we start on the 17th, does that clash with anyone?", []),
    ("Wei", "I'm out on the 18th, but that's, that's fine.", []),
    ("Tomas", "Okay so the CI thing - the flaky tests are mostly the payment mocks. I'll pin them this week.", []),
    ("Meera", "Great. That's it, thanks everyone.", []),
]
M2 = [
    ("Meera", "Quick recap on the datastore - Arjun has the Mongo prototype running, right?", []),
    ("Arjun", "Running, yeah, it's on the staging box. Orders go in, shipment events attach as sub-documents.", []),
    ("Wei", "So - I ran a load test on it over the weekend, because I was curious. At about two million orders the daily report aggregation takes, I think, thirty-eight seconds, and it was still climbing.", ["B4"]),
    ("Arjun", "Thirty-eight seconds? That might be the index, I didn't tune-", []),
    ("Lena", "I don't think it's the index. This is what I was worried about last time. The report is basically joins across orders and payments, and finance is going to want consistent transactions across those, which is not what Mongo's great at. I think this gets worse, not better, as we grow.", ["B5"]),
    ("Arjun", "I mean, I could denormalize the payments in.", []),
    ("Lena", "And then you've got two copies of every payment to keep in sync.", []),
    ("Tomas", "Can I ask a dumb question - does finance actually need the transactions?", []),
    ("Wei", "They said they do. Audit thing.", []),
    ("Meera", "Okay. I don't want to decide this on the fly. Let's all think and, um, come back to it Monday.", []),
    ("Meera", "Other thing - the carrier demo is on the 20th, so...", []),
    ("Tomas", "That's tight with the sprint starting on the 17th.", []),
    ("Meera", "I know. We'll talk about it after.", []),
]
M3 = [
    ("Meera", "Right. So, the datastore again. Having sat with it - the load test numbers, and finance needing those transactions - I think we have to reopen the decision.", ["B6"]),
    ("Arjun", "Yeah. I've been poking at it all weekend and, honestly, the denormalizing thing is getting ugly.", []),
    ("Lena", "Can I make the case for Postgres? With JSONB we still get the flexible fields Arjun wanted, so the schema thing isn't lost, and we get joins and proper transactions. And we've barely written any Mongo code, so switching now costs us maybe a week.", ["B7"]),
    ("Wei", "A week is fine by me.", []),
    ("Tomas", "I can help with the, the migrations tooling, if that's the plan.", []),
    ("Arjun", "I'm, yeah. I'm okay with it. It was a fair bet but the numbers don't lie.", []),
    ("Meera", "Okay, decision: we're switching the order-tracking service to PostgreSQL. Arjun, you redo the schema this sprint, Lena reviews.", ["B8"]),
    ("Arjun", "On it.", []),
    ("Meera", "Good. Sprint planning in five minutes, grab coffee.", []),
]

meetings = []
for rows in (M1, M2, M3):
    realized = {}
    for i, (_, _, tags) in enumerate(rows):
        for t in tags:
            realized.setdefault(t, []).append(i)
    meetings.append(dict(utterances=[dict(speaker=s, text=t) for s, t, _ in rows], realized=realized))

transcript, gold = assemble(spec, plan, meetings, models=dict(generator="hand-written"))
issues = validate_set(transcript, gold)
# The example is intentionally abbreviated (real sets target 70-120 utterances per meeting),
# so only the length check is exempted; every structural check still has to pass.
errors = [m for lv, m in issues if lv == "ERROR" and " utterances" not in m]
for lv, m in issues:
    print(lv, m)
assert not errors, errors

out = pathlib.Path("example")
(out / "transcripts").mkdir(parents=True, exist_ok=True)
(out / "gold").mkdir(parents=True, exist_ok=True)
(out / "transcripts" / "example_001.json").write_text(json.dumps(transcript, indent=1))
(out / "gold" / "example_001.json").write_text(json.dumps(gold, indent=1))
print("wrote example/ with", len(gold["chain"]), "chain links and", len(gold["questions"]), "questions")
for q in gold["questions"]:
    print(f"  [{q['type']}] {q['question']}\n      -> {q['answer_text'][:150]}")
