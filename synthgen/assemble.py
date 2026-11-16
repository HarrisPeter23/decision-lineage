"""assemble.py - turn (spec, plan, written meetings) into transcript + gold files,
and build evaluation questions whose gold answers come from the plan, not from an LLM."""
import datetime
import random

from arcs import option_key, slot_name


def _ts(date, idx):
    base = datetime.datetime.fromisoformat(date + "T10:00:00")
    return (base + datetime.timedelta(seconds=12 * idx)).isoformat()


def _link(spec, plan, b, realized, meeting_utts, is_d=False):
    idxs = sorted(set(realized[b["id"]]))
    key = None if is_d else option_key(spec, b)
    gist = plan["distractor"]["beats"][b["id"]] if is_d else plan["beats"][b["id"]]
    option = plan["distractor"]["option"] if is_d else (plan["options"].get(key) if key else None)
    return dict(link_id=b["id"], role=b["role"], meeting=b["meeting"], meeting_id=f"m{b['meeting']}",
                speaker=slot_name(spec, b["slot"]), utterance_idxs=idxs, gist=gist,
                version=b.get("version"), option_key=key, option=option,
                implicit=bool(b.get("implicit")), reaffirmation=bool(b.get("reaffirmation")))


def assemble(spec, plan, meetings, models=None):
    transcript = dict(set_id=spec["set_id"], cast=[c["name"] for c in spec["cast"]], meetings=[])
    for i, mt in enumerate(meetings):
        date = spec["dates"][i]
        transcript["meetings"].append(dict(
            meeting_id=f"m{i+1}", date=date,
            utterances=[dict(idx=j, speaker=u["speaker"], text=u["text"], ts=_ts(date, j))
                        for j, u in enumerate(mt["utterances"])]))

    realized = [mt["realized"] for mt in meetings]
    chain = [_link(spec, plan, b, realized[b["meeting"] - 1], None) for b in spec["beats"]]
    chain.sort(key=lambda l: (l["meeting"], l["utterance_idxs"][0]))
    dchain = []
    if spec.get("distractor"):
        dchain = [_link(spec, plan, b, realized[b["meeting"] - 1], None, True) for b in spec["distractor"]["beats"]]
        dchain.sort(key=lambda l: (l["meeting"], l["utterance_idxs"][0]))

    versions = [dict(v, option_text=plan["options"][v["option"]]) for v in spec["versions"]]
    changes = []
    for a, b in zip(spec["versions"], spec["versions"][1:]):
        trig = [l["link_id"] for l in chain if l["version"] == a["version"]
                and l["role"] in ("evidence", "challenge", "reconsideration")]
        newr = [l["link_id"] for l in chain if l["version"] == b["version"] and l["role"] == "rationale"]
        changes.append(dict(from_version=a["version"], to_version=b["version"], at_meeting=b["valid_from"],
                            triggered_by=trig, new_rationale=newr))

    gold = dict(set_id=spec["set_id"],
                meta=dict(arc_type=spec["arc_type"], domain=spec["domain"], seed=spec["seed"],
                          n_meetings=spec["n_meetings"], noise=spec["noise"], models=models or {}),
                topic=plan["topic"], options=plan["options"], cast=spec["cast"], versions=versions,
                chain=chain, changes=changes,
                distractor=(dict(topic=plan["distractor"]["topic"], option=plan["distractor"]["option"],
                                 chain=dchain) if dchain else None))
    gold["questions"] = build_questions(gold, random.Random(spec["seed"]))
    return transcript, gold


# ------------------------------------------------------------------ questions
def _active_version(gold, k):
    for v in gold["versions"]:
        if v["valid_from"] <= k and (v["valid_to"] is None or v["valid_to"] > k):
            return v
    return None


def build_questions(gold, rng):
    topic, chain, versions = gold["topic"], gold["chain"], gold["versions"]
    n = gold["meta"]["n_meetings"]
    arc = gold["meta"]["arc_type"]
    qs = []

    def link(role, **kw):
        return [l for l in chain if l["role"] == role and all(l.get(k) == v for k, v in kw.items())]

    def add(t, q, text, facts, links):
        qs.append(dict(qid=f"{gold['set_id']}-q{len(qs)+1:02d}", type=t, question=q, answer_text=text,
                       answer_facts=facts, supporting_links=[l["link_id"] for l in links]))

    resolutions = link("resolution")
    final = versions[-1]
    last_res = [l for l in resolutions if l["version"] == final["version"]][-1]

    add("lookup_final", f"What did the team finally decide about {topic}?", final["option_text"],
        dict(option=final["option_text"]), [last_res])

    desc = "; ".join(f"meeting {l['meeting']}: {l['speaker']} - {l['gist']}" for l in resolutions)
    add("decisions_about", f"What decisions were made about {topic}?", desc,
        dict(decisions=[dict(meeting=l["meeting"], option=l["option"],
                             reaffirmation=l["reaffirmation"]) for l in resolutions]), resolutions)

    for k in sorted(rng.sample(range(1, n + 1), min(2, n))):
        v = _active_version(gold, k)
        if v:
            first = [l for l in resolutions if l["version"] == v["version"] and l["meeting"] <= k][0]
            add("as_of", f"What was the decision about {topic} as of the end of meeting {k}?",
                v["option_text"], dict(as_of=k, option=v["option_text"]), [first])
        else:
            add("as_of", f"What was the decision about {topic} as of the end of meeting {k}?",
                "No decision had been made yet.", dict(as_of=k, option=None), [])

    if len(versions) > 1:
        seq = " -> ".join(f"{v['option_text']} (from meeting {v['valid_from']})" for v in versions)
        trig = [l for l in chain if l["link_id"] in {t for c in gold["changes"] for t in c["triggered_by"]}]
        add("change_over_time", f"How did the decision about {topic} change over time?", seq,
            dict(sequence=[v["option_text"] for v in versions]), resolutions + trig)
    elif arc == "no_reversal":
        add("change_over_time", f"How did the decision about {topic} change over time?",
            f"It did not change: {final['option_text']} was decided in meeting 1 and reaffirmed later.",
            dict(changed=False), resolutions)
    else:
        add("change_over_time", f"How did the decision about {topic} change over time?",
            f"Nothing was decided until meeting {final['valid_from']}, when the team chose {final['option_text']}.",
            dict(first_decision_meeting=final["valid_from"]), resolutions)

    if gold["changes"]:
        multi = len(gold["changes"]) > 1
        for c in gold["changes"]:
            vfrom, vto = c["from_version"], c["to_version"]
            rat0 = [l for l in link("rationale", version=vfrom) if not l["reaffirmation"]][:1]
            trig = [l for l in chain if l["link_id"] in c["triggered_by"]]
            newr = [l for l in chain if l["link_id"] in c["new_rationale"]]
            newres = [l for l in resolutions if l["version"] == vto][:1]
            text = (f"Before: {versions[vfrom-1]['option_text']}, because {rat0[0]['gist']} "
                    f"Triggered by: " + " ".join(f"{l['speaker']} ({l['role']}): {l['gist']}" for l in trig) +
                    f" After: {versions[vto-1]['option_text']}, because "
                    + " ".join(l["gist"] for l in newr))
            q = (f"Why did the decision about {topic} change at meeting {c['at_meeting']}?" if multi
                 else f"Why was the original decision about {topic} changed?")
            add("why_changed", q, text, dict(from_version=vfrom, to_version=vto,
                                             triggers=[l["link_id"] for l in trig]),
                rat0 + trig + newr + newres)
    elif arc == "no_reversal":
        ch = link("challenge") + link("evidence") + link("rationale", reaffirmation=True)
        text = (f"It did not change. The team kept {final['option_text']}. Concerns raised: "
                + " ".join(l["gist"] for l in link("challenge") + link("evidence"))
                + " Why it stayed: " + " ".join(l["gist"] for l in link("rationale", reaffirmation=True)))
        add("why_changed", f"Why did the team change its decision about {topic}?", text,
            dict(false_premise=True), ch + link("resolution", reaffirmation=True))

    props = link("proposal")
    if arc == "deferred":
        p = [l for l in props if l["option_key"] == "B"][0]
        add("who_proposed", f"Who proposed {final['option_text']}?", p["speaker"],
            dict(speaker=p["speaker"]), [p])
    else:
        add("who_proposed", f"Who proposed the original decision about {topic}?", props[0]["speaker"],
            dict(speaker=props[0]["speaker"]), props[:1])

    recon = link("reconsideration")
    if recon:
        ev = [l for l in chain if l["role"] in ("evidence", "challenge")]
        text = " ".join(f"{l['speaker']} ({l['role']}): {l['gist']}" for l in ev)
        add("evidence_to_reconsider", f"What evidence caused the team to reconsider its decision about {topic}?",
            text, dict(evidence=[l["link_id"] for l in ev]), ev + recon)

    meetings = sorted({l["meeting"] for l in chain})
    add("meetings_contributed", f"Which meetings contributed to the final decision about {topic}?",
        ", ".join(f"meeting {m}" for m in meetings), dict(meetings=meetings), chain)

    text = " | ".join(f"meeting {l['meeting']} - {l['speaker']} [{l['role']}]: {l['gist']}" for l in chain)
    add("full_lineage", f"Show the complete lineage of the decision about {topic} from proposal to final outcome.",
        text, dict(order=[l["link_id"] for l in chain]), chain)

    d = gold.get("distractor")
    if d:
        res = [l for l in d["chain"] if l["role"] == "resolution"]
        add("distractor", f"What was decided about {d['topic']}?", d["option"], dict(option=d["option"]), res)
    return qs
