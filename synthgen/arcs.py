"""arcs.py - decision-arc skeletons and the spec sampler.

Design rule: the GOLD STRUCTURE (who plays which role, in which meeting, which
option is valid when) is fixed here, in code. The LLM only supplies natural-
language content (topic, option names, what each beat says) and the dialogue
that realizes it. That is what makes the gold labels trustworthy.
"""
import copy
import datetime
import random

ROLE_DEFS = {
    "proposal": "a participant puts forward an option for the decision",
    "rationale": "a participant gives a reason for or against an option",
    "evidence": "a participant introduces new information (data, a test result, an outside constraint) bearing on the decision",
    "challenge": "a participant objects to the current decision or argues against it",
    "reconsideration": "the group (usually the lead) explicitly agrees to reopen or re-examine the decision",
    "resolution": "the group settles on an option (decision made, changed, or reaffirmed)",
}

SLOTS = ["manager", "proposer", "challenger", "supporter", "observer"]
SLOT_DESC = {
    "manager": "leads the meeting and makes the final call",
    "proposer": "brings the first proposal and defends it",
    "challenger": "tends to push back and ask hard questions",
    "supporter": "usually backs the proposer and adds practical detail",
    "observer": "less involved in the debate; often brings data or outside information",
}

NAMES = [
    "Meera", "Arjun", "Lena", "Tomas", "Wei", "Amara", "Diego", "Sana", "Ivan", "Noor",
    "Kofi", "Hana", "Marco", "Priya", "Elif", "Jonas", "Yuki", "Fatima", "Oscar", "Ravi",
    "Chloe", "Bashir", "Ingrid", "Mateo", "Zainab", "Henrik", "Lakshmi", "Pavel", "Aisha", "Sven",
    "Camila", "Dmitri", "Nadia", "Kwame", "Sofia", "Tariq", "Mei", "Rohan", "Greta", "Omar",
]

STYLES = [
    "hedges a lot (\"I think maybe...\")",
    "blunt and brief",
    "talkative, drifts into tangents",
    "quiet, speaks up rarely",
    "tends to interrupt others",
    "likes to play devil's advocate",
    "detail-oriented, quotes numbers",
    "big-picture, vague on details",
]

DOMAINS = [   # all are teams inside a company; keep the list length (12) stable: seeds index into it
    {"domain": "backend engineering team", "hint": "choice of a database or data store for a service"},
    {"domain": "mobile app team", "hint": "native vs cross-platform framework, or an app release policy"},
    {"domain": "marketing team", "hint": "which channel gets the quarterly campaign budget"},
    {"domain": "finance team", "hint": "which expense, billing or planning tool to adopt, or how to handle a budget cut"},
    {"domain": "IT and security team", "hint": "which security tool, identity provider or device policy to adopt"},
    {"domain": "supply chain and operations team", "hint": "which logistics vendor to use, or how stock is replenished"},
    {"domain": "SaaS product team", "hint": "pricing model or trial policy for a new subscription"},
    {"domain": "corporate facilities team", "hint": "office fit-out materials, space planning or a workplace vendor"},
    {"domain": "corporate events team", "hint": "format of the annual customer or sales conference"},
    {"domain": "sales operations team", "hint": "which CRM workflow, territory model or sales tool to adopt"},
    {"domain": "data and analytics team", "hint": "which model or evaluation metric to ship, or which BI tool to adopt"},
    {"domain": "HR team", "hint": "remote vs hybrid policy, or a change to the hiring process"},
]

BALANCED_FROM_SEED = 1013   # seeds below this (the six pilot sets) keep their original random domain; later seeds cycle through all domains evenly

ARC_WEIGHTS = {
    "simple_reversal": 0.25,
    "re_reversal": 0.15,
    "partial_override": 0.15,
    "no_reversal": 0.15,
    "deferred": 0.10,
    "external_trigger": 0.20,
}


def _b(id, role, meeting, slot, version=None, option=None, can_implicit=False, reaffirmation=False):
    return dict(id=id, role=role, meeting=meeting, slot=slot, version=version,
                option=option, can_implicit=can_implicit, reaffirmation=reaffirmation)


def _v(version, option, valid_from, valid_to):
    # valid_to = meeting in which this version was replaced (None = still valid at the end)
    return dict(version=version, option=option, valid_from=valid_from, valid_to=valid_to)


ARCS = {
    "simple_reversal": dict(
        description="A is decided, new evidence and a challenge arrive, the group reopens it and switches to B.",
        n_meetings=3,
        versions=[_v(1, "A", 1, 3), _v(2, "B", 3, None)],
        beats=[
            _b("B1", "proposal", 1, "proposer", 1),
            _b("B2", "rationale", 1, "proposer", 1),
            _b("B3", "resolution", 1, "manager", 1, can_implicit=True),
            _b("B4", "evidence", 2, "observer", 1),
            _b("B5", "challenge", 2, "challenger", 1),
            _b("B6", "reconsideration", 3, "manager", 1),
            _b("B7", "rationale", 3, "challenger", 2),
            _b("B8", "resolution", 3, "manager", 2, can_implicit=True),
        ],
    ),
    "re_reversal": dict(
        description="A, then B after a challenge, then back to A after new problems with B.",
        n_meetings=4,
        versions=[_v(1, "A", 1, 2), _v(2, "B", 2, 4), _v(3, "A", 4, None)],
        beats=[
            _b("B1", "proposal", 1, "proposer", 1),
            _b("B2", "rationale", 1, "proposer", 1),
            _b("B3", "resolution", 1, "manager", 1, can_implicit=True),
            _b("B4", "evidence", 2, "observer", 1),
            _b("B5", "challenge", 2, "challenger", 1),
            _b("B6", "rationale", 2, "challenger", 2),
            _b("B7", "resolution", 2, "manager", 2),
            _b("B8", "evidence", 3, "supporter", 2),
            _b("B9", "challenge", 3, "proposer", 2),
            _b("B10", "reconsideration", 4, "manager", 2),
            _b("B11", "rationale", 4, "proposer", 3),
            _b("B12", "resolution", 4, "manager", 3, can_implicit=True),
        ],
    ),
    "partial_override": dict(
        description="A stays, but a modification M is added after a challenge (final option is A+M).",
        n_meetings=3,
        versions=[_v(1, "A", 1, 3), _v(2, "A+M", 3, None)],
        beats=[
            _b("B1", "proposal", 1, "proposer", 1),
            _b("B2", "rationale", 1, "proposer", 1),
            _b("B3", "resolution", 1, "manager", 1, can_implicit=True),
            _b("B4", "evidence", 2, "observer", 1),
            _b("B5", "challenge", 2, "challenger", 1),
            _b("B6", "reconsideration", 3, "manager", 1),
            _b("B7", "rationale", 3, "supporter", 2),
            _b("B8", "resolution", 3, "manager", 2),
        ],
    ),
    "no_reversal": dict(
        description="CONTROL: challenged and reconsidered, but the group reaffirms A. The decision never changes.",
        n_meetings=3,
        versions=[_v(1, "A", 1, None)],
        beats=[
            _b("B1", "proposal", 1, "proposer", 1),
            _b("B2", "rationale", 1, "proposer", 1),
            _b("B3", "resolution", 1, "manager", 1, can_implicit=True),
            _b("B4", "evidence", 2, "observer", 1),
            _b("B5", "challenge", 2, "challenger", 1),
            _b("B6", "reconsideration", 3, "manager", 1),
            _b("B7", "rationale", 3, "proposer", 1, reaffirmation=True),
            _b("B8", "resolution", 3, "manager", 1, reaffirmation=True),
        ],
    ),
    "deferred": dict(
        description="Nothing is decided at first; a competing option appears; the group chooses B in meeting 3.",
        n_meetings=3,
        versions=[_v(1, "B", 3, None)],
        beats=[
            _b("B1", "proposal", 1, "proposer", None, "A"),
            _b("B2", "rationale", 1, "proposer", None, "A"),
            _b("B3", "evidence", 2, "observer", None, "A"),
            _b("B4", "proposal", 2, "challenger", None, "B"),
            _b("B5", "rationale", 2, "challenger", None, "B"),
            _b("B6", "resolution", 3, "manager", 1, can_implicit=False),
        ],
    ),
    "external_trigger": dict(
        description="A is decided; an outside constraint (not a debate) forces a switch to B within a meeting.",
        n_meetings=3,
        versions=[_v(1, "A", 1, 2), _v(2, "B", 2, None)],
        beats=[
            _b("B1", "proposal", 1, "proposer", 1),
            _b("B2", "rationale", 1, "proposer", 1),
            _b("B3", "resolution", 1, "manager", 1, can_implicit=True),
            _b("B4", "evidence", 2, "manager", 1),
            _b("B5", "reconsideration", 2, "manager", 1),
            _b("B6", "rationale", 2, "supporter", 2),
            _b("B7", "resolution", 2, "manager", 2),
        ],
    ),
}

DISTRACTOR_BEATS = [
    _b("D1", "proposal", 2, "supporter"),
    _b("D2", "rationale", 2, "supporter"),
    _b("D3", "resolution", 2, "manager"),
]


def sample_spec(seed, arc_type=None, set_id=None):
    """Return a JSON-serializable spec. Everything structural is decided here."""
    rng = random.Random(seed)
    if arc_type is None:
        arc_type = rng.choices(list(ARC_WEIGHTS), weights=list(ARC_WEIGHTS.values()))[0]
    arc = copy.deepcopy(ARCS[arc_type])
    dom = rng.choice(DOMAINS)          # always consume this draw so casts/noise/dates stay identical
    if seed >= BALANCED_FROM_SEED:
        dom = DOMAINS[seed % len(DOMAINS)]
    names = rng.sample(NAMES, len(SLOTS))
    styles = rng.sample(STYLES, len(SLOTS))
    cast = [dict(name=n, slot=s, style=st) for n, s, st in zip(names, SLOTS, styles)]

    for b in arc["beats"]:
        b["implicit"] = bool(b["can_implicit"] and rng.random() < 0.5)

    distractor = None
    if rng.random() < 0.4:
        distractor = dict(beats=[dict(b, implicit=False) for b in copy.deepcopy(DISTRACTOR_BEATS)])

    start = datetime.date(2025, 1, 6) + datetime.timedelta(days=rng.randint(0, 300))
    dates = [(start + datetime.timedelta(days=7 * i)).isoformat() for i in range(arc["n_meetings"])]

    noise = []
    for _ in range(arc["n_meetings"]):
        noise.append(dict(
            interruptions=rng.choice(["few", "some", "many"]),
            filler_talk_pct=rng.choice([15, 25, 35]),
            false_starts=rng.choice(["rare", "common"]),
            pronoun_heavy=rng.random() < 0.6,
            digression=rng.random() < 0.5,
            target_utterances=rng.randint(70, 120),
        ))

    return dict(
        set_id=set_id or f"set_{seed:05d}",
        seed=seed,
        arc_type=arc_type,
        arc_description=arc["description"],
        domain=dom["domain"],
        decision_hint=dom["hint"],
        cast=cast,
        n_meetings=arc["n_meetings"],
        dates=dates,
        versions=arc["versions"],
        beats=arc["beats"],
        distractor=distractor,
        noise=noise,
    )


def slot_name(spec, slot):
    return next(c["name"] for c in spec["cast"] if c["slot"] == slot)


def option_key(spec, beat):
    if beat.get("option"):
        return beat["option"]
    v = beat.get("version")
    if v is None:
        return None
    return spec["versions"][v - 1]["option"]


def option_keys(spec):
    keys = {v["option"] for v in spec["versions"]}
    keys |= {b["option"] for b in spec["beats"] if b.get("option")}
    return sorted(keys)
