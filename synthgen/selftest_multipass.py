"""selftest_multipass.py - test extract_multipass.py and run_ablation.py without any API.

A FakeLLM answers each prompt kind from the gold labels, so we can check: hints reach pass 3 only when
passes 1-2 ran, quote verification drops hallucinated links (and only when enabled), failures are
reported rather than scored as zeros, and the ablation runner produces correctly scored rows.
Run: python selftest_multipass.py [data_dir]"""
import json
import pathlib
import re
import shutil
import sys
import tempfile

import run_ablation as ra
from score import gold_links

DATA = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "data/pilot")
GOLD = {g["set_id"]: g for g in (json.loads(p.read_text()) for p in (DATA / "gold").glob("*.json"))}
TR = {t["set_id"]: t for t in (json.loads(p.read_text()) for p in (DATA / "transcripts").glob("*.json"))}


class FakeLLM:
    def __init__(self, hallucinate=False, fail_kinds=()):
        self.hallucinate, self.fail_kinds = hallucinate, set(fail_kinds)
        self.prompts = []   # (kind, user)

    def complete(self, system, user, kind="generic", temperature=None, tag=""):
        self.prompts.append((kind, user))
        if kind in self.fail_kinds:
            raise RuntimeError("simulated API failure")
        m = re.match(r"(set_\d+)-(m\d+)-", tag)
        sid, mid = m.group(1), m.group(2)
        meeting = next(x for x in TR[sid]["meetings"] if x["meeting_id"] == mid)
        links = [l for l in gold_links(GOLD[sid]) if l["meeting_id"] == mid]
        text = {u["idx"]: u["text"] for u in meeting["utterances"]}
        if kind == "mp_flag":
            return json.dumps({"flagged": sorted({l["utterance_idxs"][0] for l in links
                                                  if l["role"] in ("proposal", "resolution", "reconsideration")})})
        if kind == "mp_resolve":
            idxs = [int(i) for i in re.findall(r"FLAGGED \[(\d+)\]", user)]
            return json.dumps({"resolved": [dict(idx=i, resolved_text="resolved " + text[i], refers_to="the decision",
                                                 speech_act="resolution") for i in idxs]})
        out = []
        for l in links:
            q = " ".join(text[l["utterance_idxs"][0]].split()[:6])
            out.append(dict(role=l["role"], utterance_idxs=l["utterance_idxs"], speaker=l["speaker"],
                            quote=q, confidence=0.9))
        if kind == "mp_type" and self.hallucinate:
            out.append(dict(role="evidence", utterance_idxs=[0], speaker="X",
                            quote="words that never appear in this meeting at all", confidence=0.9))
        return json.dumps({"links": out})


def make_factory(**kw):
    made = {}

    def make(name, d):
        made[name] = FakeLLM(**kw)
        return made[name]
    make.made = made
    return make


results = []


def check(name, cond, detail=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"   {detail}"))


def rows_by_name(rows):
    return {r["name"]: r for r in rows}


tmp = pathlib.Path(tempfile.mkdtemp())
try:
    # 1) clean run of every config with a perfect fake model
    f = make_factory()
    rows = rows_by_name(ra.run_all(str(DATA), str(tmp / "a"), f, n_boot=0, only=[c["name"] for c in ra.CONFIGS if c["name"] != "rules"]))
    for name in ("single_pass", "mp_p3", "mp_p13", "mp_p123", "mp_p123_verify"):
        s = rows[name]["score"]["role_typed"]
        check(f"{name}: perfect model -> F1 1.0, status ok", abs(s["f1"] - 1) < 1e-9 and rows[name]["status"] == "ok", (s, rows[name]["status"]))
    check("mp_p3 sends no hints; mp_p13 and mp_p123 do",
          all("HINTS" not in u for k, u in f.made["mp_p3"].prompts if k == "mp_type")
          and any("HINTS" in u for k, u in f.made["mp_p13"].prompts if k == "mp_type")
          and any("resolved meaning" in u for k, u in f.made["mp_p123"].prompts if k == "mp_type"))
    check("mp_p13 never calls pass 2; mp_p3 never calls pass 1 or 2",
          not any(k == "mp_resolve" for k, _ in f.made["mp_p13"].prompts)
          and {k for k, _ in f.made["mp_p3"].prompts} == {"mp_type"})
    check("pass 2 prompt carries preceding lines for each flagged item",
          all("PRECEDING LINES" in u for k, u in f.made["mp_p123"].prompts if k == "mp_resolve"))

    # 2) hallucinated link: hurts precision unless quote verification is on
    f2 = make_factory(hallucinate=True)
    rows = rows_by_name(ra.run_all(str(DATA), str(tmp / "b"), f2, n_boot=0, only=["mp_p3", "mp_p3_verify"]))
    check("hallucination without verification: precision < 1", rows["mp_p3"]["score"]["role_typed"]["p"] < 1)
    check("hallucination with verification: precision 1, drops counted",
          abs(rows["mp_p3_verify"]["score"]["role_typed"]["p"] - 1) < 1e-9
          and rows["mp_p3_verify"]["extra"]["dropped_quote"] == 19, rows["mp_p3_verify"]["extra"])

    # 3) failures are reported, never scored as a quiet zero
    f3 = make_factory(fail_kinds=("mp_type",))
    rows = rows_by_name(ra.run_all(str(DATA), str(tmp / "c"), f3, n_boot=0, only=["mp_p123"]))
    check("pass-3 failures -> status FAILED", rows["mp_p123"]["status"].startswith("FAILED"), rows["mp_p123"]["status"])
    f4 = make_factory(fail_kinds=("mp_flag", "mp_resolve"))
    rows = rows_by_name(ra.run_all(str(DATA), str(tmp / "d"), f4, n_boot=0, only=["mp_p123"]))
    check("pass-1 failures -> degraded (still produces pass-3 links), not FAILED",
          rows["mp_p123"]["status"].startswith("degraded") and rows["mp_p123"]["score"]["role_typed"]["f1"] > 0.99,
          rows["mp_p123"]["status"])
    f5 = make_factory(fail_kinds=("extract",))
    rows = rows_by_name(ra.run_all(str(DATA), str(tmp / "e"), f5, n_boot=0, only=["single_pass"]))
    check("single-pass failures -> status FAILED", rows["single_pass"]["status"].startswith("FAILED"))

    # 4) summary file exists and mentions every config
    summ = (tmp / "a" / "summary.md").read_text()
    check("summary.md written with all configs", all(n in summ for n in ("single_pass", "mp_p123_verify")))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{sum(results)}/{len(results)} multipass/ablation checks passed")
sys.exit(0 if all(results) else 1)
