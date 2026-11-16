"""phase7_gen_items.py - generation items for Phase 7 from results/phase7/retrieval/<system>@<scope>.jsonl, with the FROZEN generator settings
(FREEZE section 13): qwen3:14b, thinking off, temperature 0, seed 7, num_predict 700; num_ctx 8192 for my system and its ablations, 12288 for baselines.
Item id = "<qid>@<system>@<scope>". Kernels are split so that each script stays under about 0.9 MB (Kaggle's limit is about 1 MB).
  python eval/phase7_gen_items.py --runs lineage@test_k1,no_typing@test_k1,... --kernel adl-p7-gen-lin
"""
import argparse
import base64
import gzip
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from argdecisionlineage import explain   # noqa: E402

MINE = {"lineage", "no_typing", "no_conflict_resolution", "static_graph"}
GOLD = {"test_k1": "data/synth/gold", "test_k10": "data/synth/gold", "ami": "data/ami/gold"}
LIMIT = 900_000


def config(ctx):
    return dict(model="qwen3:14b", ctx=ctx, think=False, num_predict=700, temperature=0, seed=7, system=explain.SYSTEM)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--kernel", required=True)
    a = ap.parse_args()
    runs = a.runs.split(",")
    ctxs = {8192 if r.split("@")[0] in MINE else 12288 for r in runs}
    assert len(ctxs) == 1, "my system (8192) and baselines (12288) go into separate kernels"
    ctx = ctxs.pop()
    qtext, items = {}, []
    for run in runs:
        system, scope = run.split("@")
        for l in (ROOT / f"results/phase7/retrieval/{run}.jsonl").read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            r = json.loads(l)
            if r["set_id"] not in qtext:
                qtext[r["set_id"]] = {q["qid"]: q["question"] for q in json.loads((ROOT / GOLD[scope] / f"{r['set_id']}.json").read_text(encoding="utf-8"))["questions"]}
            _, user, _ = explain.prompt(qtext[r["set_id"]][r["qid"]], r["retrieval"])
            items.append(dict(id=f"{r['qid']}@{system}@{scope}", prompt=user))
    out = ROOT / "results/phase7/gen" / a.kernel
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(config(ctx), indent=1), encoding="utf-8")
    parts, cur = [], []
    for it in items:
        cur.append(it)
        if len(base64.b64encode(gzip.compress(json.dumps(cur).encode()))) > LIMIT:
            parts.append(cur[:-1])
            cur = [it]
    parts.append(cur)
    for i, part in enumerate(parts):
        name = f"{a.kernel}-{i}"
        f = out / f"items_{i}.jsonl"
        f.write_text("\n".join(json.dumps(x) for x in part) + "\n", encoding="utf-8")
        subprocess.run([sys.executable, "runtime/kaggle/batch/build.py", name, str(out / "config.json"), str(f)], cwd=ROOT, check=True)
    print(len(items), "items in", len(parts), "kernel(s); ctx", ctx)


if __name__ == "__main__":
    main()
