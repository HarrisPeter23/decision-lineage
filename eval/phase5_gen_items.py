"""phase5_gen_items.py - turns retrieved subgraphs (eval/phase5_retrieval.py output) into generation items for the generic batch kernel.
  python eval/phase5_gen_items.py --retrieval results/phase5/retrieval_rf1/single_pass_recap_roles_top4@k1.jsonl --tag k1 --kernel adl-p5-gen-k1
Writes results/phase5/gen/<tag>/{items.jsonl,config.json} and builds runtime/kaggle/batch/kernels/<kernel>. DEV only (qids are checked against split.json).
"""
import argparse
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from argdecisionlineage import explain   # noqa: E402

CONFIG = dict(model="qwen3:14b", ctx=8192, think=False, num_predict=700, temperature=0, seed=7, system=explain.SYSTEM)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--retrieval", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--kernel", required=True)
    ap.add_argument("--no-kernel", action="store_true", help="only write items (Phase 6 combines several systems into one kernel)")
    a = ap.parse_args()
    dev = set(json.loads((ROOT / "data/synth/split.json").read_text(encoding="utf-8"))["dev"])
    rows = [json.loads(l) for l in (ROOT / a.retrieval).read_text(encoding="utf-8").splitlines() if l.strip()]
    gold = {}
    out = ROOT / "results/phase5/gen" / a.tag
    out.mkdir(parents=True, exist_ok=True)
    items = []
    for r in rows:
        assert r["set_id"] in dev
        if r["set_id"] not in gold:
            gold[r["set_id"]] = {q["qid"]: q["question"] for q in json.loads((ROOT / "data/synth/gold" / f"{r['set_id']}.json").read_text(encoding="utf-8"))["questions"]}
        system, user, _ = explain.prompt(gold[r["set_id"]][r["qid"]], r["retrieval"])
        assert system == CONFIG["system"]
        items.append(dict(id=f"{r['qid']}@{a.tag}", prompt=user))
    (out / "items.jsonl").write_text("\n".join(json.dumps(i) for i in items) + "\n", encoding="utf-8")
    (out / "config.json").write_text(json.dumps(CONFIG, indent=1), encoding="utf-8")
    if not a.no_kernel:
        subprocess.run([sys.executable, "runtime/kaggle/batch/build.py", a.kernel, str(out / "config.json"), str(out / "items.jsonl")], cwd=ROOT, check=True)
    print(len(items), "items; mean prompt chars", sum(len(i["prompt"]) for i in items) // len(items))


if __name__ == "__main__":
    main()
