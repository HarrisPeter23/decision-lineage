"""phase7_gemini_sample.py - draws the Gemini calibration sample for Phase 7 (FREEZE section 20), fixed by seed BEFORE any Gemini call.
Per system at pool size 1 (lineage, vector_rag, evowiki_style, graphiti): 150 generated sentences with at least one citation, and 150 answers of ANY
question type (TEST has about 140 rubric-judged answers per system, too few for 150; for exact-match types Gemini calibrates the exact-match scoring),
uniformly at random with seed 0
(random.Random(seed) over the run's items in qid order). If a system has fewer eligible items, all are taken and the shortfall is reported.
600 sentences + 600 answers on TEST.
  python eval/phase7_gemini_sample.py --tags k1,vector_rag_k1,evowiki_style_k1,graphiti_k1 --out results/phase5/gemini_sample_dryrun.json   (DEV dry run)
On TEST the same command takes the TEST run tags (written in Phase 7); nothing else changes.
"""
import argparse
import json
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXACT = ("who_proposed", "as_of", "lookup_final")
N_SENT, N_ANS, SEED = 150, 150, 0


def draw(tags, out, seed=SEED, score_root="results/phase5/score"):
    sample = dict(seed=seed, per_system=dict(sentences=N_SENT, answers=N_ANS), systems={}, shortfall={})
    for tag in tags:
        A = sorted((json.loads(l) for l in (ROOT / score_root / tag / "answers.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()),
                   key=lambda a: a["qid"])
        sents = [dict(qid=a["qid"], set_id=a["set_id"], sent_index=i, text=s["text"], cites=s["cites"]) for a in A for i, s in enumerate(a["sentences"]) if s["cites"]]
        ans = [dict(qid=a["qid"], set_id=a["set_id"], type=a["type"], exact_type=a["type"] in EXACT) for a in A]
        rng = random.Random(f"{seed}:{tag}")
        S = rng.sample(sents, min(N_SENT, len(sents)))
        Q = rng.sample(ans, min(N_ANS, len(ans)))
        sample["systems"][tag] = dict(sentences=S, answers=Q)
        sample["shortfall"][tag] = dict(sentences=max(0, N_SENT - len(sents)), answers=max(0, N_ANS - len(ans)), eligible_sentences=len(sents), eligible_answers=len(ans))
    pathlib.Path(out).write_text(json.dumps(sample, indent=1), encoding="utf-8")
    return sample


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--score-root", default="results/phase5/score")   # Phase 7: results/phase7/score (path plumbing only; sampling unchanged)
    a = ap.parse_args()
    s = draw(a.tags.split(","), ROOT / a.out, score_root=a.score_root)
    print({t: (len(v["sentences"]), len(v["answers"])) for t, v in s["systems"].items()}, "shortfall", s["shortfall"])
