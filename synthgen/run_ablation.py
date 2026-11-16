"""run_ablation.py - run every extraction configuration on a dataset, score it, write one results table.

  python run_ablation.py --data data/pilot --provider anthropic --model MODEL --out results/ablation
  python run_ablation.py --data data/pilot --provider openai --model MODEL --only single_pass,mp_p123
  python run_ablation.py --data data/pilot --provider rules --out results/rules_only      # offline

Configurations (each gets its own cache and call log, so token counts are per configuration):
  rules            keyword lower bound (NOT a reference result; see README)
  single_pass      one call per meeting, no hints            (extract_baseline.py)
  mp_p3            pass 3 only, quote field requested        (control for the passes below)
  mp_p3_verify     pass 3 only + quote verification
  mp_p13           flag decisions (1) + type roles (3)
  mp_p123          flag (1) + resolve references (2) + type (3)
  mp_p123_verify   all three passes + quote verification

Outputs: OUT/summary.md (tables), OUT/results.json, OUT/<config>/preds/*.json, OUT/<config>/llm_log.jsonl.
Exit code 1 if any configuration had failed LLM calls (its row is marked FAILED, never silently zero).
"""
import argparse
import json
import pathlib
import sys

import extract_baseline as eb
import extract_multipass as mp
import extract_recap as er
import extract_args as ea
from llm import LLM
from score import ROLES, score_dir

CONFIGS = [
    dict(name="rules", kind="rules"),
    dict(name="single_pass", kind="single"),
    dict(name="mp_p3", kind="mp", passes=(3,), verify=False),
    dict(name="mp_p3_verify", kind="mp", passes=(3,), verify=True),
    dict(name="mp_p13", kind="mp", passes=(1, 3), verify=False),
    dict(name="mp_p123", kind="mp", passes=(1, 2, 3), verify=False),
    dict(name="mp_p123_verify", kind="mp", passes=(1, 2, 3), verify=True),
    dict(name="single_pass_recap_roles", kind="recap"),
    dict(name="single_pass_recap_args", kind="args"),
    dict(name="single_pass_recap_args_v2", kind="args2"),   # P3-F: the one allowed revision (args_v2)       # P3-F: recap output + argument-completion pass (extract_args.py); div4 cap applied afterwards      # D-17: single_pass + own-output recap + contrastive role definitions (extract_recap.py)
]


def _usage(log_path):
    calls = tin = tout = 0
    p = pathlib.Path(log_path) if log_path else None
    if p and p.exists():
        for line in p.read_text().splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            calls += 1
            u = r.get("usage") or {}
            tin += u.get("input", 0)
            tout += u.get("output", 0)
    return dict(calls=calls, input_tokens=tin, output_tokens=tout)


def run_config(cfg, data, out, make_llm, tol, n_boot):
    d = pathlib.Path(out) / cfg["name"]
    preds = d / "preds"
    row = dict(name=cfg["name"], status="ok", extra={})
    llm = None if cfg["kind"] == "rules" else make_llm(cfg["name"], d)
    if cfg["kind"] == "rules":
        eb.run_dir(data, preds, None)
    elif cfg["kind"] in ("single", "recap", "args", "args2"):
        fn = {"single": eb.run_dir, "recap": er.run_dir, "args": ea.run_dir, "args2": lambda d, p, l: ea.run_dir(d, p, l, version="v2")}[cfg["kind"]]
        total, failed = fn(data, preds, llm)
        row["extra"] = dict(meetings=total, failed=failed)
        if failed:
            row["status"] = f"FAILED ({failed}/{total} meeting calls failed)"
    else:
        tot = mp.run_dir(data, preds, llm, cfg["passes"], cfg["verify"])
        row["extra"] = tot
        if tot["p3_failed"]:
            row["status"] = f"FAILED ({tot['p3_failed']}/{tot['meetings']} pass-3 calls failed)"
        elif tot["p1_failed"] or tot["p2_failed"]:
            row["status"] = f"degraded (pass1 failed {tot['p1_failed']}, pass2 failed {tot['p2_failed']})"
    row["score"] = score_dir(preds, data, tol, n_boot)
    row["usage"] = _usage(getattr(llm, "log_path", None))
    return row


def fmt_ci(r):
    b = r["score"].get("bootstrap_95ci")
    return f"[{b['role_typed_f1_ci'][0]:.2f}, {b['role_typed_f1_ci'][1]:.2f}]" if b else "n/a"


def write_summary(rows, out, data, tol):
    L = []
    L.append(f"# Extraction ablation on `{data}` (tol={tol})\n")
    L.append("Role-typed = right utterance AND right role. CI = bootstrap 95% over SETS. "
             "Precision is a lower bound (gold labels only annotated decisions).\n")
    L.append("| config | status | role-typed P | R | F1 | F1 95% CI | localization F1 | chain completeness | chain-exact | "
             "implicit recall (n) | speaker acc | calls | in tok | out tok | quote drops |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        s = r["score"]
        ir = s["implicit_resolution_recall"]
        L.append(f"| {r['name']} | {r['status']} | {s['role_typed']['p']:.3f} | {s['role_typed']['r']:.3f} | "
                 f"{s['role_typed']['f1']:.3f} | {fmt_ci(r)} | {s['localization']['f1']:.3f} | "
                 f"{s['chain_completeness']:.3f} | {s['chain_exact_rate']:.2f} | "
                 f"{'n/a' if ir is None else f'{ir:.2f}'} ({s['implicit_n']}) | "
                 f"{s['speaker_accuracy_given_localized']:.3f} | {r['usage']['calls']} | "
                 f"{r['usage']['input_tokens']} | {r['usage']['output_tokens']} | "
                 f"{r['extra'].get('dropped_quote', '-')} |")
    L.append("\n## Per-role F1\n")
    L.append("| config | " + " | ".join(ROLES) + " |")
    L.append("|---|" + "---|" * len(ROLES))
    for r in rows:
        L.append(f"| {r['name']} | " + " | ".join(f"{r['score']['per_role'][x]['f1']:.2f}" for x in ROLES) + " |")
    L.append("\n## Reading this table honestly\n")
    L.append("- The pilot is small (see `sets` in results.json); differences between configurations inside each other's "
             "confidence intervals are not evidence of improvement.")
    L.append("- `rules` was written with knowledge of the pilot phrasing; it is a sanity floor, not a reference baseline.")
    L.append("- Implicit-resolution recall rests on very few examples; do not over-read it.")
    L.append("- Compare `mp_p3` with `single_pass` to see the effect of the prompt change alone, and `mp_p13`, `mp_p123` "
             "against `mp_p3` to see what each added pass contributes.")
    (pathlib.Path(out) / "summary.md").write_text("\n".join(L) + "\n")


def run_all(data, out, make_llm, tol=0, n_boot=1000, only=None):
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)
    cfgs = [c for c in CONFIGS if not only or c["name"] in only]
    rows = []
    for cfg in cfgs:
        print(f"\n=== {cfg['name']} ===")
        rows.append(run_config(cfg, data, out, make_llm, tol, n_boot))
        s = rows[-1]["score"]["role_typed"]
        print(f"{cfg['name']}: status={rows[-1]['status']}  role-typed P {s['p']:.3f} R {s['r']:.3f} F1 {s['f1']:.3f}")
    write_summary(rows, out, data, tol)
    (pathlib.Path(out) / "results.json").write_text(json.dumps(rows, indent=1, default=str))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default="results/ablation")
    ap.add_argument("--provider", default="anthropic", help="anthropic | openai | rules")
    ap.add_argument("--model")
    ap.add_argument("--only", help="comma-separated config names")
    ap.add_argument("--tol", type=int, default=0)
    ap.add_argument("--bootstrap", type=int, default=1000)
    a = ap.parse_args()
    only = a.only.split(",") if a.only else None
    if a.provider == "rules":
        only = ["rules"]

    def make_llm(name, d):
        d.mkdir(parents=True, exist_ok=True)
        return LLM(a.provider, a.model, temperature=0, cache_dir=str(d / "cache"), log_path=str(d / "llm_log.jsonl"))

    rows = run_all(a.data, a.out, make_llm, a.tol, a.bootstrap, only)
    print(f"\nwrote {a.out}/summary.md")
    sys.exit(1 if any(r["status"].startswith("FAILED") for r in rows) else 0)


if __name__ == "__main__":
    main()
