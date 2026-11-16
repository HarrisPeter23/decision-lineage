"""phase3_score.py - merge the per-worker outputs of a Phase 3 kernel and score every config on DEV.

  python eval/phase3_score.py --workers results/phase3/<tag>/raw/out --tag <tag> [--sets set_a,set_b]   # raw/out contains w0/, w1/, ... each with <config>/preds, <config>/llm_log.jsonl
Primary scoring uses span tolerance 1 (pre-registered, reports/FREEZE.md section 7); tolerance 0 is written as the stricter secondary. Bootstrap over SETS, 1000 resamples, seed 0.
Writes results/phase3/<tag>/summary_tol1.md, summary_tol0.md, results.json. DEV data only (the sets present in the worker outputs must all be DEV; checked here).
"""
import argparse
import json
import pathlib
import shutil
import sys

sys.path.insert(0, "synthgen")
import run_ablation as ra        # noqa: E402
from score import score_dir      # noqa: E402


def usage(logs):
    calls = tin = tout = 0
    for f in logs:
        for line in pathlib.Path(f).read_text(encoding="utf-8").splitlines():
            try:
                u = json.loads(line).get("usage") or {}
            except Exception:
                continue
            calls += 1
            tin += u.get("input") or 0
            tout += u.get("output") or 0
    return dict(calls=calls, input_tokens=tin, output_tokens=tout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--data", default="data/synth")
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--meta", help="phase3_meta.json of the kernel: a non-zero worker exit code marks every config of that run as degraded (D-18)")
    a = ap.parse_args()
    out = pathlib.Path("results/phase3") / a.tag
    wdirs = sorted(pathlib.Path(a.workers).glob("w*"))
    assert wdirs, "no worker directories found"
    split = json.loads(pathlib.Path(a.data, "split.json").read_text(encoding="utf-8"))
    dev = set(split["dev"])
    configs = sorted({c.name for w in wdirs for c in w.iterdir() if c.is_dir()})
    dd = out / "devdata"
    shutil.rmtree(dd, ignore_errors=True)
    for sub in ("transcripts", "gold"):
        (dd / sub).mkdir(parents=True)
        for s in dev:
            shutil.copy(pathlib.Path(a.data, sub, f"{s}.json"), dd / sub / f"{s}.json")
    rc = json.loads(pathlib.Path(a.meta).read_text(encoding="utf-8")).get("worker_rc") if a.meta else None
    bad_rc = bool(rc and any(rc))
    results = {}
    for tol in (1, 0):
        rows = []
        for cfg in configs:
            merged = out / "merged" / cfg / "preds"
            if tol == 1:
                shutil.rmtree(merged.parent, ignore_errors=True)
                merged.mkdir(parents=True)
                seen = []
                for w in wdirs:
                    for f in sorted((w / cfg / "preds").glob("set_*.json")):
                        assert f.stem in dev, f"{f.stem} is not a DEV set"
                        shutil.copy(f, merged / f.name)
                        seen.append(f.stem)
                missing = sorted(dev - set(seen))
                assert not missing, f"{cfg}: no predictions for {missing}"
            logs = [w / cfg / "llm_log.jsonl" for w in wdirs if (w / cfg / "llm_log.jsonl").exists()]
            stats = {}
            for w in wdirs:
                sf = w / cfg / "preds" / "_stats.json"
                if sf.exists():
                    for k, v in json.loads(sf.read_text(encoding="utf-8")).items():
                        stats[k] = stats.get(k, 0) + v
            empty = []                                   # meetings with no links at all: the signature of a failed call (D-18)
            for s in sorted(dev):
                pr = json.loads((merged / f"{s}.json").read_text(encoding="utf-8"))["links"]
                mids = {m["meeting_id"] for m in json.loads(pathlib.Path(a.data, "transcripts", f"{s}.json").read_text(encoding="utf-8"))["meetings"]}
                empty += [f"{s}-{m}" for m in sorted(mids - {l["meeting_id"] for l in pr})]
            status = "ok"
            if empty or bad_rc:
                status = f"degraded (meetings with no links: {empty or 'none'}; worker exit codes: {rc})"
            stats["meetings_without_links"] = empty
            rows.append(dict(name=cfg, status=status, extra=stats, score=score_dir(merged, dd, tol, a.n_boot), usage=usage(logs)))
        (out / f"summary_tol{tol}.md").parent.mkdir(parents=True, exist_ok=True)
        ra.write_summary(rows, out, f"data/synth DEV ({len(dev)} sets)", tol)
        (out / "summary.md").replace(out / f"summary_tol{tol}.md")
        results[f"tol{tol}"] = [dict(name=r["name"], status=r["status"], role_typed=r["score"]["role_typed"], localization=r["score"]["localization"], usage=r["usage"],
                                     ci=r["score"].get("bootstrap_95ci")) for r in rows]
    (out / "results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    print("configs:", configs, "->", out)


if __name__ == "__main__":
    main()
