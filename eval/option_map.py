"""option_map.py - evaluation-side mapping of a free-text answer to a gold option key of a set (used by every system's exact-match scoring).

v1 (Phase 4/5 as first run): the option with the most DISTINCTIVE content tokens (tokens of that option's text not in any other option) present in the text,
    embedding fallback on no hit or a tie.
v3 = v1 + only the question/topic-word ban (no splitting). v2 was REJECTED: on the 4 answers where v1 and v2 disagree, v2 was right 1/4 and v1 3/4
    (agent-checked); splitting "14-day" drops the "14" (tokens under 3 characters are discarded).
v2 (fix attempt of 2026-11-06, found while inspecting Phase 6 answers; applied to EVERY system and re-scored everywhere, both versions reported):
    * tokens that occur in the question or the set's topic are removed from the distinctive sets (an answer echoing the question's words, e.g. "regional
      store replenishment", no longer counts as evidence for the option whose text happens to contain them);
    * hyphenated tokens and number-unit tokens are split ("14-day" -> "14", "day"), so "14 days" matches "a 14-day free trial".
Validated on gold, not on system output: the mapper must return the gold key for every gold option text and for every lookup_final / as_of gold answer text
(`python eval/option_map.py` reports both versions).
"""
import json
import pathlib
import re
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from argdecisionlineage.graph import tokens    # noqa: E402

_EMB = None


def _emb():
    global _EMB
    if _EMB is None:
        from argdecisionlineage.linking import Embedder
        _EMB = Embedder()
    return _EMB


def toks2(text):
    out = set()
    for t in tokens(re.sub(r"(\d)([a-z])", r"\1 \2", text.lower().replace("-", " "))):
        out.add(t)
    return out


def map_option(text, g, question=None, version=2):
    keys = list(g["options"])
    if text is None:
        return None
    if len(keys) > 1:
        tk = toks2 if version == 2 else (lambda s: set(tokens(s)))
        toks = {k: tk(g["options"][k]) for k in keys}
        ban = (tk(question or "") | tk(g.get("topic", ""))) if version in (2, 3) else set()
        t = tk(text)
        sc = {k: len(((toks[k] - set().union(*(toks[j] for j in keys if j != k))) - ban) & t) for k in keys}
        top = max(sc.values())
        if top > 0 and list(sc.values()).count(top) == 1:
            return max(sc, key=sc.get)
    emb = _emb()
    vecs = emb([g["options"][k] for k in keys])
    (v,) = emb([text])
    return keys[int(np.argmax(vecs @ v))]


def gold_key(g, k):
    for v in g["versions"]:
        if v["valid_from"] <= k and (v["valid_to"] is None or k < v["valid_to"]):
            return v["option"]
    return None


def validate():
    dev = json.loads((ROOT / "data/synth/split.json").read_text(encoding="utf-8"))["dev"]
    res = {}
    for ver in (1, 2):
        n = ok = n2 = ok2 = 0
        bad = []
        for s in dev:
            g = json.loads((ROOT / "data/synth/gold" / f"{s}.json").read_text(encoding="utf-8"))
            for k, txt in g["options"].items():
                n += 1
                ok += map_option(txt, g, None, ver) == k
            for q in g["questions"]:
                if q["type"] in ("lookup_final", "as_of") and q["answer_facts"].get("option"):
                    want = gold_key(g, q["answer_facts"].get("as_of") or g["meta"]["n_meetings"])
                    got = map_option(q["answer_text"], g, q["question"], ver)
                    n2 += 1
                    ok2 += got == want
                    if got != want:
                        bad.append(q["qid"])
        res[f"v{ver}"] = dict(option_texts=f"{ok}/{n}", gold_answers=f"{ok2}/{n2}", failures=bad)
    print(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    validate()
