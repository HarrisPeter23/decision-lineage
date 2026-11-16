"""explain.py - Layer 5: grounded explanation from the retrieved subgraph ONLY (no transcript, no gold).

prompt(question, subgraph) -> (system, user, idmap): every retrieved item gets a local id L1..Ln (chronological). The generator must answer in JSON:
    {"answer": "<one-sentence direct answer>", "sentences": [{"text": "...", "cites": ["L1", ...]}, ...]}
with sentences in chronological order and at least one citation each. Graph facts the generator may need (whether the decision changed, the versions and when
they held, "no decision yet", the as-of meeting) are given as a header derived from the graph, not from gold.
parse(raw, idmap) -> dict(answer, sentences=[{text, cites=[item dicts]}], parse_ok, unknown_cites)
"""
import json
import re

SYSTEM = ("You answer questions about how a team's decisions developed across meetings. You may use ONLY the numbered evidence given. "
          "Output ONLY valid JSON, no commentary, no code fences.")


def _ordinals(sub):
    """Meeting numbers as the ordinal among the meetings in which the anchored decision was discussed (the same reading of 'meeting k' as retrieval)."""
    ms = sub.get("meetings") or sorted({it["meeting"] for it in sub["items"]} | {v["valid_from"] for v in sub["versions"]})
    return {m: i for i, m in enumerate(ms, 1)}


def prompt(question, sub):
    items = sorted(sub["items"], key=lambda it: (it["meeting"], it["idxs"][0]))
    idmap = {f"L{i}": it for i, it in enumerate(items, 1)}
    ordn = _ordinals(sub)
    ev = []
    for lid, it in idmap.items():
        role = it["role"] or "transcript excerpt"
        where = f"meeting {ordn[it['meeting']]} ({it['date']})" if it["meeting"] in ordn else f"another meeting ({it['date']})"
        ev.append(f"[{lid}] {where}, {it['speaker']} ({role}): {it['text']}")
    head = []
    if sub.get("system", "lineage") != "lineage":                          # baselines: same instructions, no lineage-graph header (phase6.md section 0)
        head.append(sub.get("header") or "The evidence below was retrieved for this question.")
    elif sub["versions"]:
        head.append("Decision versions recorded in the graph (in time order):")
        for v in sub["versions"]:
            until = f"until meeting {ordn.get(v['valid_to'], '?')}" if v["valid_to"] else "still in force"
            head.append(f"- version {v['n']} ({v['kind']}), from meeting {ordn.get(v['valid_from'], '?')}, {until}: {v['option'][:220]}")
    else:
        head.append("The graph records no decision (no version) for this topic.")
    if sub.get("changed") is False and sub["intent"] == "why_changed":
        head.append("Note: the graph records NO change of this decision. If the question assumes a change, say that it did not change and explain why it stayed.")
    if sub.get("as_of"):
        head.append(f"The question asks about the state at the end of meeting {sub['as_of']['ordinal']}.")
    if sub.get("no_decision_yet"):
        head.append("Note: at the asked point no decision had been made yet; say so.")
    user = f"""QUESTION: {question}

{chr(10).join(head)}

EVIDENCE (numbered; each line is one statement from a meeting):
{chr(10).join(ev) if ev else '(none)'}

Instructions:
- Answer the question using only the evidence above. Do not add facts that are not in the evidence.
- "answer": one sentence that directly answers the question (a name, an option, a list of meetings, or "it did not change" / "no decision had been made yet").
- "sentences": the explanation, in chronological order, 1-8 short sentences. Every sentence must cite the evidence ids it relies on, e.g. ["L2", "L5"].
- Say who said what and in which meeting when it matters.

Return JSON: {{"answer": "...", "sentences": [{{"text": "...", "cites": ["L1"]}}]}}"""
    return SYSTEM, user, idmap


def _json(raw):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        return json.loads(t)
    except Exception:
        a, b = t.find("{"), t.rfind("}")
        return json.loads(t[a:b + 1])


def parse(raw, idmap):
    try:
        d = _json(raw)
        sents, unknown = [], 0
        for s in d.get("sentences") or []:
            cites = []
            for c in s.get("cites") or []:
                c = str(c).strip().strip("[]")
                if c in idmap:
                    cites.append(idmap[c])
                else:
                    unknown += 1
            if str(s.get("text", "")).strip():
                sents.append(dict(text=str(s["text"]).strip(), cites=cites))
        return dict(answer=str(d.get("answer", "")).strip(), sentences=sents, parse_ok=True, unknown_cites=unknown)
    except Exception:
        return dict(answer=raw.strip()[:500], sentences=[], parse_ok=False, unknown_cites=0)
