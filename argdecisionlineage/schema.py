"""schema.py - the typed chain schema (see docs/schema_mapping.md). Roles, node kinds, edge kinds."""

ROLES = ("proposal", "rationale", "evidence", "challenge", "reconsideration", "resolution")

# node kinds
MEETING, PERSON, DECISION, VERSION, LINK = "meeting", "person", "decision", "version", "link"

# edge kinds (all carry: meeting, date, confidence, refs, and for version edges valid_from / valid_to as meeting indexes)
PROPOSED_BY = "PROPOSED_BY"        # decision -> person
JUSTIFIED_BY = "JUSTIFIED_BY"      # version -> link (rationale or evidence)
CHALLENGED_BY = "CHALLENGED_BY"    # version -> link (challenge)
SUPERSEDED_BY = "SUPERSEDED_BY"    # version -> next version
RESOLVED_BY = "RESOLVED_BY"        # version -> link (resolution that created or reaffirmed it)
DISCUSSED_IN = "DISCUSSED_IN"      # decision -> meeting
REOPENED_BY = "REOPENED_BY"        # version -> link (reconsideration)

# how a version came about
INITIAL, CHANGED, MODIFIED, RESTORED = "initial", "changed", "modified", "restored"
