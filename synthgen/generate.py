"""generate.py - plan -> write meetings -> assemble -> validate -> (paraphrase questions) -> save.

Examples:
  python generate.py --mock --n 6 --out data/mock          # offline smoke test, no API
  python generate.py --provider anthropic --model MODEL --n 5 --out data/pilot
  python generate.py --provider anthropic --model MODEL --n 100 --seed 1000 --paraphrase --out data/synth

Output:
  OUT/transcripts/<set>.json   <- the ONLY thing a system under test may read
  OUT/gold/<set>.json          <- chain, versions, changes, questions + gold answers
  OUT/rejected/<set>.json      <- sets that failed validation after all retries (for inspection)
"""
import argparse
import json
import pathlib
import random

from arcs import ARC_WEIGHTS, option_keys, sample_spec
from assemble import assemble
from llm import LLM, extract_json
from prompts import (MEETING_SYSTEM, PARAPHRASE_SYSTEM, PLANNER_SYSTEM, meeting_prompt,
                     paraphrase_prompt, planner_prompt)
from validate import validate_set


def plan_scenario(spec, llm, tag):
    for attempt in range(3):
        try:
            plan = extract_json(llm.complete(PLANNER_SYSTEM, planner_prompt(spec), kind="planner",
                                             tag=f"{tag}-plan{attempt}"))
            assert plan["topic"] and all(k in plan["options"] for k in option_keys(spec))
            assert all(b["id"] in plan["beats"] for b in spec["beats"])
            if spec["distractor"]:
                assert all(b["id"] in plan["distractor"]["beats"] for b in spec["distractor"]["beats"])
            else:
                plan["distractor"] = None
            return plan
        except Exception as e:
            err = e
    raise RuntimeError(f"planner failed: {err}")


def write_meeting(spec, plan, m, llm, tag):
    need = [b["id"] for b in spec["beats"] if b["meeting"] == m]
    if spec["distractor"]:
        need += [b["id"] for b in spec["distractor"]["beats"] if b["meeting"] == m]
    names = {c["name"] for c in spec["cast"]}
    for attempt in range(3):
        try:
            out = extract_json(llm.complete(MEETING_SYSTEM, meeting_prompt(spec, plan, m), kind="meeting",
                                            tag=f"{tag}-m{m}-try{attempt}"))
            utts, real = out["utterances"], out["realized"]
            assert utts and all(u["speaker"] in names and u["text"].strip() for u in utts)
            for bid in need:
                idxs = real[bid]
                assert idxs and all(isinstance(i, int) and 0 <= i < len(utts) for i in idxs)
            return dict(utterances=utts, realized={b: real[b] for b in need})
        except Exception as e:
            err = e
    raise RuntimeError(f"meeting {m} failed: {err}")


def build_set(spec, llm, tag, models):
    plan = plan_scenario(spec, llm, tag)
    meetings = [write_meeting(spec, plan, m, llm, tag) for m in range(1, spec["n_meetings"] + 1)]
    return assemble(spec, plan, meetings, models)


def paraphrase(gold, llm):
    qs = [q["question"] for q in gold["questions"]]
    try:
        out = extract_json(llm.complete(PARAPHRASE_SYSTEM, paraphrase_prompt(qs), kind="paraphrase",
                                        temperature=0.7, tag=gold["set_id"] + "-para"))
        assert isinstance(out, list) and len(out) == len(qs)
    except Exception:
        return
    for q, p in zip(gold["questions"], out):
        q["question_template"], q["question"] = q["question"], p


def arc_schedule(n, seed, only=None):
    """Balanced arc types: largest-remainder allocation of ARC_WEIGHTS, shuffled by seed."""
    if only:
        return [only] * n
    raw = {k: w * n for k, w in ARC_WEIGHTS.items()}
    counts = {k: int(v) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - counts[k], reverse=True)[: n - sum(counts.values())]:
        counts[k] += 1
    sched = [k for k, c in counts.items() for _ in range(c)]
    random.Random(seed).shuffle(sched)
    return sched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--out", default="data/synth")
    ap.add_argument("--arc", choices=list(ARC_WEIGHTS))
    ap.add_argument("--provider", default="anthropic")
    ap.add_argument("--model")
    ap.add_argument("--temperature", type=float, default=0.9)
    ap.add_argument("--paraphrase", action="store_true")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--set-retries", type=int, default=2)
    a = ap.parse_args()

    if a.mock:
        a.provider = "mock"
    llm = LLM(a.provider, a.model, temperature=a.temperature)
    out = pathlib.Path(a.out)
    for d in ("transcripts", "gold", "rejected"):
        (out / d).mkdir(parents=True, exist_ok=True)
    models = dict(generator=f"{a.provider}:{a.model}", temperature=a.temperature)

    ok = bad = 0
    sched = arc_schedule(a.n, a.seed, a.arc)
    for i in range(a.n):
        seed = a.seed + i
        spec = sample_spec(seed, sched[i])
        result, last = None, None
        for attempt in range(a.set_retries + 1):
            try:
                tr, gold = build_set(spec, llm, f"{spec['set_id']}-a{attempt}", models)
            except Exception as e:
                print(f"{spec['set_id']}: attempt {attempt} failed to build: {e}")
                continue
            errors = [m for lv, m in validate_set(tr, gold) if lv == "ERROR"]
            if not errors:
                result = (tr, gold)
                break
            print(f"{spec['set_id']}: attempt {attempt} had {len(errors)} validation errors, e.g. {errors[0]}")
            last = (tr, gold, errors)
        if result:
            tr, gold = result
            if a.paraphrase:
                paraphrase(gold, llm)
            (out / "transcripts" / f"{spec['set_id']}.json").write_text(json.dumps(tr, indent=1))
            (out / "gold" / f"{spec['set_id']}.json").write_text(json.dumps(gold, indent=1))
            ok += 1
            print(f"{spec['set_id']}: ok ({spec['arc_type']}, {spec['domain']})")
        else:
            bad += 1
            if last:
                (out / "rejected" / f"{spec['set_id']}.json").write_text(
                    json.dumps(dict(transcript=last[0], gold=last[1], errors=last[2]), indent=1))
    print(f"\ndone: {ok} accepted, {bad} rejected -> {out}")


if __name__ == "__main__":
    main()
