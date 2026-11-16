"""evowiki_style - re-implementation of EvoWiki (Chen, Wang, Que, arXiv 2608.23265) from the paper; no code was released. See SIMPLIFICATIONS.md.

Build, one meeting at a time, W_t = F(W_{t-1}, M_t)  (paper eq. 3-5):
  call 1  Resolve + Extract : timeline normalization, intra-meeting proposal -> discussion -> decision parsing, candidate state updates with evidence spans
  call 2  Coref + Route     : bind each candidate to an existing entity-attribute slot of W_{t-1} (by its index) or open a new slot; classify the relation
  Overwrite (deterministic) : at most one Active state per slot (eq. 8); replace / revise / revoke close the old state's interval, label it Overturned and add a
                              version edge; non-conflicting facts stay; every state keeps its provenance anchor (meeting, utterance span)
Read: the complete serialized Wiki is the only context (no top-k, no raw-meeting fallback), capped at READ_BUDGET estimated tokens (phase6.md section 0).
Only *decided* updates become states ("preventing candidate plans from being written as final states"). No rationale fields: the paper has none.
The LLM is any object with complete(system, user, kind=..., temperature=..., tag=...) -> str (synthgen/llm.py); nothing here reads gold.
"""
import json
import math
import re

SYSTEM = "You maintain a structured project wiki from workplace meeting transcripts. Output ONLY valid JSON, no commentary, no code fences."
READ_BUDGET = 6000
RELATIONS = ("same", "replace", "revise", "revoke", "add")


def _json(raw):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        return json.loads(t)
    except Exception:
        a, b = t.find("{"), t.rfind("}")
        return json.loads(t[a:b + 1])


def extract_prompt(meeting, k):
    lines = "\n".join(f"[{u['idx']}] {u['speaker']}: {u['text']}" for u in meeting["utterances"])
    return f"""Meeting {k} of a series, held on {meeting.get('date', 'unknown date')}. Each line is [index] speaker: text.

Step 1 (timeline): resolve relative time expressions ("next Thursday", "from the 26th") against the meeting date.
Step 2 (micro-evolution): for every topic where the team discusses a course of action, a choice between options, an owner, a deadline, a budget, a risk or
another project fact, trace how it develops within this meeting: proposed -> discussed -> decided (or left open).
Step 3 (extraction): list the resulting state updates. One update per entity-attribute, e.g. entity "Level 4 fit-out", attribute "flooring", value "luxury vinyl
plank from Norvik". stage = "decided" only if the team settled it in this meeting (including implicit agreement such as "fine, go ahead" or instructions that
presuppose the decision); "proposed" or "discussed" otherwise. Give the utterance indexes that state or settle it (most important first).

Return JSON: {{"updates": [{{"entity": "...", "attribute": "...", "value": "...", "stage": "decided|proposed|discussed", "effective": "date or meeting",
"evidence": [int, ...]}}]}}

TRANSCRIPT:
{lines}"""


def route_prompt(index_lines, updates):
    ups = "\n".join(f"U{i}: {u['entity']} | {u['attribute']} = {u['value']}" for i, u in enumerate(updates))
    return f"""The project wiki currently has these entity-attribute slots (id: entity | attribute = current ACTIVE value):
{index_lines or '(empty wiki)'}

New decided updates from the latest meeting:
{ups}

For each update, resolve references ("the vendor", "that plan", role titles) against the wiki and decide:
- slot: the id of the existing slot it is about, or "NEW" if no slot matches;
- for NEW slots, the canonical entity and attribute names;
- relation to the slot's active value: "same" (restates or reaffirms it), "replace" (a different value now holds), "revise" (the value is modified or extended),
  "revoke" (it is cancelled and nothing replaces it), "add" (new slot, or a fact that does not conflict).

Return JSON: {{"routes": [{{"update": "U0", "slot": "S3" or "NEW", "entity": "...", "attribute": "...", "relation": "same|replace|revise|revoke|add"}}]}}"""


class Wiki:
    def __init__(self):
        self.slots = []        # dict(id, entity, attribute, states=[dict(value, label, valid_from, valid_to, meeting_id, evidence, date)])
        self.edges = []        # version-replacement edges (slot id, from state index, to state index, meeting)

    def index_lines(self):
        out = []
        for s in self.slots:
            act = [st for st in s["states"] if st["label"] == "Active"]
            out.append(f"{s['id']}: {s['entity']} | {s['attribute']} = {act[-1]['value'] if act else '(none active)'}")
        return "\n".join(out)

    def new_slot(self, entity, attribute):
        s = dict(id=f"S{len(self.slots)}", entity=entity, attribute=attribute, states=[])
        self.slots.append(s)
        return s

    def overwrite(self, slot, update, relation, k, meeting):
        """State-Overwrite Protocol (paper section 'State Overwriting and the Structured Wiki')."""
        act = [i for i, st in enumerate(slot["states"]) if st["label"] == "Active"]
        anchor = dict(meeting_id=meeting["meeting_id"], meeting=k, date=meeting.get("date", ""), evidence=update["evidence"])
        if relation == "same" and act:
            slot["states"][act[-1]].setdefault("reaffirmed", []).append(anchor)          # no new version; provenance of the reaffirmation kept
            return
        if act and relation in ("replace", "revise", "revoke"):
            for i in act:
                slot["states"][i].update(label="Overturned", valid_to=k)
        value = "(revoked: no value holds)" if relation == "revoke" else update["value"]
        if act and relation == "add":                    # a non-conflicting fact in an occupied slot: keep both, the newest is Active
            for i in act:
                slot["states"][i].update(label="Overturned", valid_to=k)
        slot["states"].append(dict(value=value, label="Active", valid_from=k, valid_to=None, **anchor))
        if act:
            self.edges.append((slot["id"], act[-1], len(slot["states"]) - 1, k))

    def to_json(self):
        return dict(slots=self.slots, edges=self.edges)

    @staticmethod
    def from_json(d):
        w = Wiki()
        w.slots, w.edges = d["slots"], [tuple(e) for e in d["edges"]]
        return w


def build(corpus, llm, chunk_windows=None, tag="evo"):
    """chunk_windows(meeting) -> [(start, end)] (the FREEZE section 9 rule; synthetic meetings always fit in one window). Returns (wiki, stats)."""
    w = Wiki()
    st = dict(meetings=0, extract_failed=0, route_failed=0, updates=0, decided=0, states=0)
    for k, m in enumerate(corpus["meetings"], 1):
        st["meetings"] += 1
        wins = chunk_windows(m) if chunk_windows else [(0, len(m["utterances"]))]
        ups = []
        for n, (a, b) in enumerate(wins):
            win = dict(m, utterances=[dict(u, idx=i) for i, u in enumerate(m["utterances"][a:b])])
            try:
                d = _json(llm.complete(SYSTEM, extract_prompt(win, k), kind="evo_extract", temperature=0, tag=f"{tag}-{m['meeting_id']}-x{n}"))
                for u in d.get("updates") or []:
                    ev = [int(i) + a for i in (u.get("evidence") or []) if str(i).lstrip("-").isdigit() and 0 <= int(i) < b - a]
                    if u.get("entity") and u.get("attribute") and u.get("value"):
                        ups.append(dict(entity=str(u["entity"])[:120], attribute=str(u["attribute"])[:120], value=str(u["value"])[:300],
                                        stage=str(u.get("stage", "")).lower(), evidence=ev[:6]))
            except Exception:
                st["extract_failed"] += 1
        st["updates"] += len(ups)
        dec = [u for u in ups if u["stage"] == "decided"]
        st["decided"] += len(dec)
        if not dec:
            continue
        try:
            r = _json(llm.complete(SYSTEM, route_prompt(w.index_lines(), dec), kind="evo_route", temperature=0, tag=f"{tag}-{m['meeting_id']}-route"))
            routes = {str(x.get("update")): x for x in r.get("routes") or []}
        except Exception:
            st["route_failed"] += 1
            routes = {}
        ids = {s["id"]: s for s in w.slots}
        for i, u in enumerate(dec):
            x = routes.get(f"U{i}", {})
            rel = x.get("relation") if x.get("relation") in RELATIONS else "add"
            slot = ids.get(str(x.get("slot")))
            if slot is None:                                 # NEW slot, or an unparseable route: write-time fallback = exact name match, else a new slot
                ent, att = str(x.get("entity") or u["entity"]), str(x.get("attribute") or u["attribute"])
                slot = next((s for s in w.slots if s["entity"].lower() == ent.lower() and s["attribute"].lower() == att.lower()), None) or w.new_slot(ent, att)
                ids[slot["id"]] = slot
                if not slot["states"]:
                    rel = "add"
            w.overwrite(slot, u, rel, k, m)
    st["states"] = sum(len(s["states"]) for s in w.slots)
    st["slots"] = len(w.slots)
    return w, st


def _tok(t):
    return math.ceil(1.4 * len(t.split())) + 6


def read(wiki, corpus, question, budget=READ_BUDGET):
    """Wiki-only Read: every state is an evidence item (entity, attribute, value, lifecycle label, validity, provenance). Returns the subgraph-like dict."""
    ms = {m["meeting_id"]: m for m in corpus["meetings"]}
    items = []
    for s in wiki.slots:
        for j, stt in enumerate(s["states"]):
            m = ms.get(stt["meeting_id"])
            ev = [i for i in stt.get("evidence") or [] if m and i < len(m["utterances"])] or ([0] if m else [])
            until = f"until meeting {stt['valid_to']}" if stt["valid_to"] else "still active"
            items.append(dict(link_id=f"{s['id']}.{j}", meeting_id=stt["meeting_id"], meeting=stt["meeting"], date=stt.get("date", ""), idxs=ev,
                              speaker=m["utterances"][ev[0]]["speaker"] if m and ev else "", role=None, version=j + 1, source="wiki",
                              text=f"[{stt['label']}] {s['entity']} | {s['attribute']}: {stt['value']} (from meeting {stt['valid_from']}, {until})",
                              source_text=" ".join(f"{m['utterances'][i]['speaker']}: {m['utterances'][i]['text']}" for i in ev) if m else "",
                              label=stt["label"], last=max([stt["valid_from"]] + [a["meeting"] for a in stt.get("reaffirmed", [])])))
    total, truncated = sum(_tok(i["text"]) for i in items), False
    if total > budget:                                       # pre-declared truncation: Overturned oldest first, then Active of the least recently updated slots
        truncated = True
        order = sorted(items, key=lambda i: (i["label"] == "Active", i["last"]))
        drop = set()
        for i in order:
            if total <= budget:
                break
            drop.add(i["link_id"])
            total -= _tok(i["text"])
        items = [i for i in items if i["link_id"] not in drop]
    for i in items:
        i.pop("label", None)
        i.pop("last", None)
    return dict(system="evowiki_style", intent=None, items=items, versions=[], meetings=list(range(1, len(corpus["meetings"]) + 1)), truncated=truncated,
                header="The evidence below is the complete project wiki: one line per state, labelled Active (currently valid) or Overturned (superseded), "
                       "with the meeting where it took effect.")
