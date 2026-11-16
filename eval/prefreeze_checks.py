"""prefreeze_checks.py - CPU-only consistency checks before FREEZE (2026-11-08). DEV only; no model calls.
 (1) Rebuild every lineage-system generation prompt (pool 1 and pool 10) from the CURRENT frozen code (extractor outputs single_pass_recap_roles_top4,
     graph v4, linker L2, router RF1, retrieve.py, explain.py) and compare byte-for-byte with the prompts that were actually sent (results/phase5/gen/k*/items.jsonl).
 (2) The exact-match option mapper inside eval/phase5_score.py vs eval/option_map.py v1, on every exact-type answer of every system.
 (3) Same question ids, gold files and scoring code for all systems (qid sets per run; sha256 of the gold files and scoring modules).
 (4) Diagnostic: for the version-creating resolutions that the final extractor misses (CHECKPOINT_4b), were they in the pre-cap candidates?
  HF_HUB_OFFLINE=1 python eval/prefreeze_checks.py -> results/prefreeze_checks.json
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "eval"), str(ROOT / "synthgen")]
from argdecisionlineage import explain                  # noqa: E402
from argdecisionlineage.linking import Embedder         # noqa: E402
import phase5_retrieval as PR                           # noqa: E402
import phase5_score as PS                               # noqa: E402
import option_map as OM                                 # noqa: E402


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]


def main():
    out = {}
    dev = json.loads((ROOT / "data/synth/split.json").read_text(encoding="utf-8"))["dev"]
    gold = {s: json.loads((ROOT / "data/synth/gold" / f"{s}.json").read_text(encoding="utf-8")) for s in dev}
    qtext = {q["qid"]: q["question"] for g in gold.values() for q in g["questions"]}
    index = json.loads((ROOT / "data/synth/pools/dev/index.json").read_text(encoding="utf-8"))
    emb = Embedder()
    # (1)
    for size, src, tag in (("1", "single_pass_recap_roles_top4", "k1"), ("10", "single_pass_recap_roles_top4_pooled", "k10")):
        sent = {json.loads(l)["id"]: json.loads(l)["prompt"] for l in (ROOT / f"results/phase5/gen/{tag}/items.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
        rows = []
        for p in [p for p in index if p.startswith(f"dev_k{size}_")]:
            rows += PR.run_pool(ROOT / "data/synth/pools/dev" / p, src, emb, gold)
        same = diff = 0
        bad = []
        for r in rows:
            _, user, _ = explain.prompt(qtext[r["qid"]], r["retrieval"])
            if sent.get(f"{r['qid']}@{tag}") == user:
                same += 1
            else:
                diff += 1
                bad.append(r["qid"])
        out[f"prompts_{tag}"] = dict(identical=same, different=diff, total=len(rows), different_qids=bad[:20])
        print(tag, out[f"prompts_{tag}"])
    # (2)
    n = agree = 0
    for t in ("k1", "k10", "vector_rag_k1", "vector_rag_k10", "evowiki_style_k1", "evowiki_style_k10", "graphiti_k1", "graphiti_k10"):
        for l in (ROOT / f"results/phase5/score/{t}/answers.jsonl").read_text(encoding="utf-8").splitlines():
            a = json.loads(l)
            if a["type"] in ("lookup_final", "as_of") and a["answer"] and not PS.NO_DECISION.search(a["answer"]):
                n += 1
                agree += PS.map_option(a["answer"], gold[a["set_id"]]) == OM.map_option(a["answer"], gold[a["set_id"]], None, 1)
    out["mapper_phase5_vs_option_map_v1"] = dict(answers=n, identical=agree)
    print("mapper", out["mapper_phase5_vs_option_map_v1"])
    # (3)
    qsets = {}
    for t in ("k1", "k10", "vector_rag_k1", "vector_rag_k10", "evowiki_style_k1", "evowiki_style_k10", "graphiti_k1", "graphiti_k10"):
        qsets[t] = sorted(json.loads(l)["qid"] for l in (ROOT / f"results/phase5/score/{t}/answers.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())
    ref = qsets["k1"]
    out["same_questions"] = {t: (q == ref) for t, q in qsets.items()}
    out["n_questions"] = len(ref)
    out["hashes"] = dict(gold=hashlib.sha256("".join(sha(ROOT / "data/synth/gold" / f"{s}.json") for s in sorted(dev)).encode()).hexdigest()[:16],
                         split=sha(ROOT / "data/synth/split.json"), phase5_score=sha(ROOT / "eval/phase5_score.py"), phase5_final=sha(ROOT / "eval/phase5_final.py"),
                         faithfulness=sha(ROOT / "argdecisionlineage/faithfulness.py"), explain=sha(ROOT / "argdecisionlineage/explain.py"),
                         retrieve=sha(ROOT / "argdecisionlineage/retrieve.py"), graph=sha(ROOT / "argdecisionlineage/graph.py"), linking=sha(ROOT / "argdecisionlineage/linking.py"))
    print("same questions", out["same_questions"])
    # (4)
    from phase3_topk import topk
    raw_dir = ROOT / "results/phase3/recap/merged/single_pass_recap_roles/preds"
    diag = []
    for s, lid in (("set_01014", "B3"), ("set_01023", "B3"), ("set_01045", "B7")):
        g = gold[s]
        gl = next(l for l in g["chain"] if l["link_id"] == lid)
        raw = json.loads((raw_dir / f"{s}.json").read_text(encoding="utf-8"))["links"]
        near = lambda p, tol: p["meeting_id"] == gl["meeting_id"] and min(abs(a - b) for a in p["utterance_idxs"] for b in gl["utterance_idxs"]) <= tol
        pre = [p for p in raw if near(p, 1)]
        pre_res = [p for p in pre if p["role"] == "resolution"]
        capped = topk(raw, 4)
        diag.append(dict(set_id=s, link=lid, implicit=gl.get("implicit"), pre_cap_any_role=[(p["role"], p["confidence"]) for p in pre],
                         pre_cap_resolution=bool(pre_res), in_top4=any(near(p, 1) and p["role"] == "resolution" for p in capped),
                         meeting_links_pre_cap=sum(p["meeting_id"] == gl["meeting_id"] for p in raw)))
    out["missed_resolution_diag"] = diag
    for d in diag:
        print(d)
    (ROOT / "results/prefreeze_checks.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
