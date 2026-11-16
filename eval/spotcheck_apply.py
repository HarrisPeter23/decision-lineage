"""spotcheck_apply.py - read the filled reports/human_spotcheck.csv, compute agreement with gold and with the automatic judges (Wilson 95% CIs),
mark the checked links verification='human_spotcheck' in data/{synth,ami}/verification.json, and write results/human_spotcheck.json.
Gold files are NOT touched. Rows answered 'no' are listed for reports/label_issues.md (none was needed if the count is zero)."""
import csv, json, math, pathlib, collections

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round((c - h) / d, 3), round((c + h) / d, 3))

def kappa(a, b):
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = collections.Counter(a), collections.Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return None if pe == 1 else round((po - pe) / (1 - pe), 3)

rows = list(csv.DictReader(open("reports/human_spotcheck.csv", encoding="utf-8-sig")))
files = {"synthetic": pathlib.Path("data/synth/verification.json"), "AMI": pathlib.Path("data/ami/verification.json")}
ver = {s: json.loads(p.read_text(encoding="utf-8")) for s, p in files.items()}
rb = {}
for src, kf, gf in (("synthetic", "results/role_blind/key.json", "results/role_blind/gemini.jsonl"), ("AMI", "results/role_blind_ami/key.json", "results/role_blind_ami/gemini.jsonl")):
    key = json.load(open(kf)); got = {}
    for l in open(gf, encoding="utf-8"):
        l = l.strip()
        if l:
            try: r = json.loads(l); got.setdefault(r["item"], r["verdict"])
            except Exception: pass
    for it, k in key.items():
        if it in got: rb[(src, k["set_id"], k["link_id"])] = (got[it], k["role"])
recs = []
for x in rows:
    h = x["human_verdict"].strip().lower(); assert h in ("yes", "partial", "no"), x["row"]
    src = x["source"]; kk = f"{x['set_id']}/{x['link_id']}"; v = ver[src][kk]
    recs.append(dict(row=int(x["row"]), source=src, key=kk, role=x["role"], human=h, notes=x["notes"].strip(), gemini=v.get("gemini"), granite=v.get("granite"),
                     agent=v.get("agent_handcheck"), role_blind=rb.get((src, x["set_id"], x["link_id"]))))
def summarize(rs, label):
    n = len(rs); out = dict(group=label, n=n)
    for lvl, ok in (("strict_yes", lambda r: r["human"] == "yes"), ("yes_or_partial", lambda r: r["human"] != "no")):
        k = sum(ok(r) for r in rs); out[f"human_vs_gold_{lvl}"] = dict(k=k, n=n, rate=round(k / n, 3), ci95=wilson(k, n))
    out["human_counts"] = dict(collections.Counter(r["human"] for r in rs))
    for j in ("gemini", "granite", "agent"):
        sub = [r for r in rs if r[j]]
        if not sub: continue
        # agreement on the binary 'fully correct' question: human yes vs judge yes
        a = [r["human"] == "yes" for r in sub]; b = [r[j] == "yes" for r in sub]
        k = sum(x == y for x, y in zip(a, b)); out[f"human_vs_{j}_binary_yes"] = dict(n=len(sub), agree=k, rate=round(k / len(sub), 3), ci95=wilson(k, len(sub)), kappa=kappa(a, b),
                                                                                     judge_yes=sum(b), human_yes=sum(a))
    sub = [r for r in rs if r["role_blind"]]
    if sub:
        k = sum(r["role_blind"][0] == r["role_blind"][1] for r in sub)
        out["gemini_role_blind_vs_gold_role"] = dict(n=len(sub), agree=k, rate=round(k / len(sub), 3), ci95=wilson(k, len(sub)))
        hy = [r for r in sub if r["human"] == "yes"]; kk_ = sum(r["role_blind"][0] == r["role_blind"][1] for r in hy)
        out["gemini_role_blind_on_human_yes_links"] = dict(n=len(hy), agree=kk_, rate=round(kk_ / max(1, len(hy)), 3), ci95=wilson(kk_, len(hy)))
    return out
res = [summarize(recs, "all"), summarize([r for r in recs if r["source"] == "synthetic"], "synthetic"), summarize([r for r in recs if r["source"] == "AMI"], "AMI")]
no_rows = [r for r in recs if r["human"] == "no"]
for r in recs:                                  # mark verification (gold untouched)
    v = ver[r["source"]][r["key"]]
    if r["human"] in ("yes", "partial"):
        v["verification_before_human"] = v.get("verification"); v["verification"] = "human_spotcheck"; v["human_verdict"] = r["human"]
        v["verification_scope"] = "content_speaker_role_human"
        if r["notes"]: v["human_note"] = r["notes"]
    else:
        v["human_verdict"] = "no"
for s, p in files.items(): p.write_text(json.dumps(ver[s], indent=1), encoding="utf-8")
pathlib.Path("results/human_spotcheck.json").write_text(json.dumps(dict(summary=res, rows=recs, no_rows=[r["key"] for r in no_rows]), indent=1), encoding="utf-8")
print(json.dumps(res, indent=1)); print("no rows:", [r["key"] for r in no_rows])
