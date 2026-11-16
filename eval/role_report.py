"""role_report.py - role-blind agreement with gold (per role recall with Wilson CIs, confusion matrix, Cohen's kappa) and the full judge-sensitivity table.
Writes reports/role_verification.md. Judges: gemini-3.5-flash-lite (single-item for items r000-r138, batched-10 for the rest and for AMI; validated) and granite4.2:8b.
  python eval/role_report.py"""
import collections
import json
import math
import pathlib

ROLES = ["proposal", "rationale", "evidence", "challenge", "reconsideration", "resolution"]
R = pathlib.Path("results")


def wilson(k, n):
    if not n:
        return (None, None)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def load(p):
    p = pathlib.Path(p)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    pe = sum(ca[c] * cb[c] for c in set(ca) | set(cb)) / (n * n)
    return po, (None if pe == 1 else (po - pe) / (1 - pe))


def block(title, V, key):
    ids = [i for i in V if i in key]
    pairs = [(key[i]["role"], V[i] if V[i] in ROLES else "invalid") for i in ids]
    acc, kap = kappa(pairs)
    lines = [f"### {title}", f"n = {len(ids)}; accuracy {acc:.3f}; Cohen's kappa {kap:.3f}" if kap is not None else f"n = {len(ids)}; accuracy {acc:.3f}", "",
             "| gold role | n | recall (judge names the gold role) | 95% Wilson CI |", "|---|---|---|---|"]
    for r in ROLES:
        g = [p for p in pairs if p[0] == r]
        k = sum(a == b for a, b in g)
        lo, hi = wilson(k, len(g))
        lines.append(f"| {r} | {len(g)} | {k}/{len(g)} = {k / max(1, len(g)):.2f} | {lo:.2f}-{hi:.2f} |" if g else f"| {r} | 0 | - | - |")
    cm = collections.Counter(pairs)
    cols = ROLES + (["invalid"] if any(b == "invalid" for _, b in pairs) else [])
    lines += ["", "Confusion matrix (rows = gold role, columns = judge's role):", "", "| gold \\ judge | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for r in ROLES:
        lines.append(f"| **{r}** | " + " | ".join(str(cm[(r, c)]) for c in cols) + " |")
    return lines


def main():
    syn_key = json.loads((R / "role_blind/key.json").read_text(encoding="utf-8"))
    ami_key = json.loads((R / "role_blind_ami/key.json").read_text(encoding="utf-8")) if (R / "role_blind_ami/key.json").exists() else {}
    gem = {r["item"]: r["verdict"] for r in load(R / "role_blind/gemini.jsonl")}
    gem.update({r["item"]: r["verdict"] for r in load(R / "role_blind/gemini_batched.jsonl")})
    gem_ami = {r["item"]: r["verdict"] for r in load(R / "role_blind_ami/gemini.jsonl")}
    gran = {r["item"]: r["verdict"] for r in load(R / "role_blind/granite.jsonl")}
    gran_ami = {r["item"]: r["verdict"] for r in load(R / "role_blind_ami/granite.jsonl")}
    val = json.loads((R / "role_blind/batched_validation.json").read_text(encoding="utf-8")) if (R / "role_blind/batched_validation.json").exists() else None
    out = ["# Role verification (role-blind) and judge sensitivity", "",
           "**What the link-level `llm_consensus` label means: content and speaker only.** The panel judges were told the intended role and could not detect wrong roles "
           "(see section 2). Roles are verified only by (a) this role-blind agreement, in which the judge does not see the gold role, and (b) the human spot-check if it is returned.", ""]
    out += ["## 1. Role-blind agreement with gold", "",
            "The judge sees the context and the target lines and picks one of six roles; it is never told the gold role, the speaker or the gist. A low recall means the judge and the "
            "gold disagree; it does not say which one is right, because the judges themselves are weak at argumentative roles.", ""]
    if val:
        out += [f"Batched procedure (10 per request) validated on {val['n']} links that also have single-item verdicts: exact agreement {val['exact_agreement']}, kappa {val['kappa']}, "
                f"threshold {val['threshold']}, passed = {val['passed']}. Gemini verdicts: items r000-r138 single-item, the rest batched.", ""]
    if gem:
        out += block(f"Gemini, synthetic links ({len(gem)} of {len(syn_key)})", gem, syn_key) + [""]
    if gem_ami:
        out += block(f"Gemini, AMI links ({len(gem_ami)} of {len(ami_key)})", gem_ami, ami_key) + [""]
    out += block("granite4.2:8b, synthetic links", gran, syn_key) + [""]
    if gran_ami:
        out += block("granite4.2:8b, AMI links", gran_ami, ami_key) + [""]
    # sensitivity
    key = json.loads((R / "judge_sensitivity/key.json").read_text(encoding="utf-8"))
    out += ["## 2. Judge sensitivity on planted corruptions (DEV, 56 real + 57 corrupted links)", "",
            "A corrupted link counts as detected when the judge says partial or no. Real links not judged yes are false alarms. 95% Wilson intervals.", "",
            "| judge | corruption | n | detected (partial or no) | rate | 95% CI | judged no | rate |", "|---|---|---|---|---|---|---|---|"]
    for judge in ("gemini", "granite"):
        V = {r["item"]: r["verdict"] for r in load(R / f"judge_sensitivity/{judge}.jsonl")}
        for kind, label in (("wrong_role", "wrong role"), ("wrong_speaker", "wrong speaker"), ("shifted_utt", "shifted utterance"), ("unsupportive", "unsupportive quote"), ("ALL", "all corrupted"), ("real", "real links (false alarms)")):
            ids = [i for i in V if (key[i]["kind"] != "real" if kind == "ALL" else key[i]["kind"] == kind)]
            f = sum(V[i] in ("partial", "no") for i in ids)
            no = sum(V[i] == "no" for i in ids)
            lo, hi = wilson(f, len(ids))
            out.append(f"| {judge} | {label} | {len(ids)} | {f} | {f / max(1, len(ids)):.2f} | {lo:.2f}-{hi:.2f} | {no} | {no / max(1, len(ids)):.2f} |")
    out += ["", "Both judges see the intended role in the prompt, so for wrong-role items a flag means the judge disagreed with a stated role; neither did so reliably."]
    pathlib.Path("reports/role_verification.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
