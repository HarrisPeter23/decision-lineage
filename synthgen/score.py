"""score.py - score extracted chain links against gold.

Prediction file per set (preds_dir/<set_id>.json):
  {"set_id": "...", "links": [{"meeting_id": "m1", "role": "proposal",
                               "utterance_idxs": [4], "speaker": "Henrik", "confidence": 0.8}, ...]}

Matching (one-to-one, greedy): a prediction can match a gold link when it is in the same meeting
and one of its utterance indexes is within --tol indexes of one of the gold link's indexes.
Role-agreeing candidates are matched first, then closer ones. Reported:
  * localization P/R/F1  - did we find the right utterance (role ignored)?
  * role-typed P/R/F1    - right utterance AND right role (the headline number), micro + per role
  * role accuracy        - of localized links, how many got the right role
  * speaker accuracy     - of localized links, how many have the right speaker
  * chain completeness   - per set, share of the main decision chain recovered with the right role
  * chain-exact rate     - share of sets whose main chain was recovered completely
  * implicit-resolution recall - the hard case ("yeah, let's do that")
  * confusion matrix, per-arc breakdown, bootstrap 95% CI over SETS (questions/links are clustered in sets)

CAVEAT on precision: gold labels only the annotated decision(s) of each set (main chain + distractor).
A system that correctly labels some other decision in the transcript (an onboarding checklist, a rota)
is counted as a false positive, so precision is a LOWER BOUND. Lead with recall and role-typed F1.

Usage: python score.py --pred preds/single_pass --data data/pilot [--tol 0] [--bootstrap 1000] [--out res.json]
"""
import argparse
import json
import pathlib
import random
from collections import Counter, defaultdict

ROLES = ["proposal", "rationale", "evidence", "challenge", "reconsideration", "resolution"]


def gold_links(gold):
    out = [dict(l, chain="main") for l in gold["chain"]]
    if gold.get("distractor"):
        out += [dict(l, chain="distractor") for l in gold["distractor"]["chain"]]
    return out


def _dist(a, b):
    return min(abs(x - y) for x in a for y in b)


def match_links(preds, golds, tol=0):
    cands = []
    for i, p in enumerate(preds):
        pi = p.get("utterance_idxs") or []
        if not pi:
            continue
        for j, g in enumerate(golds):
            if p.get("meeting_id") != g["meeting_id"]:
                continue
            d = _dist(pi, g["utterance_idxs"])
            if d <= tol:
                cands.append(((p.get("role") != g["role"], d, i, j), i, j))
    cands.sort()
    used_p, used_g, pairs = set(), set(), []
    for _, i, j in cands:
        if i in used_p or j in used_g:
            continue
        used_p.add(i)
        used_g.add(j)
        pairs.append((i, j))
    return pairs


def score_set(preds, gold, tol=0):
    golds = gold_links(gold)
    pairs = match_links(preds, golds, tol)
    role_ok = [(i, j) for i, j in pairs if preds[i].get("role") == golds[j]["role"]]
    ok_p = {i for i, _ in role_ok}
    ok_g = {j for _, j in role_ok}
    per_role = {r: dict(tp=0, fp=0, fn=0) for r in ROLES}
    for i, j in role_ok:
        per_role[golds[j]["role"]]["tp"] += 1
    for i, p in enumerate(preds):
        if i not in ok_p and p.get("role") in per_role:
            per_role[p["role"]]["fp"] += 1
    for j, g in enumerate(golds):
        if j not in ok_g:
            per_role[g["role"]]["fn"] += 1
    conf = Counter()
    matched_g = {j: i for i, j in pairs}
    for j, g in enumerate(golds):
        conf[(g["role"], preds[matched_g[j]].get("role") if j in matched_g else "MISSED")] += 1
    spk = sum(1 for i, j in pairs
              if str(preds[i].get("speaker", "")).strip().lower() == golds[j]["speaker"].strip().lower())
    main = [j for j, g in enumerate(golds) if g["chain"] == "main"]
    dis = [j for j, g in enumerate(golds) if g["chain"] == "distractor"]
    imp = [j for j, g in enumerate(golds) if g.get("implicit")]
    return dict(set_id=gold["set_id"], arc=gold["meta"]["arc_type"], n_pred=len(preds), n_gold=len(golds),
                loc_tp=len(pairs), role_tp=len(role_ok), speaker_ok=spk, per_role=per_role, conf=conf,
                main_n=len(main), main_found=sum(j in ok_g for j in main),
                dis_n=len(dis), dis_found=sum(j in ok_g for j in dis),
                imp_n=len(imp), imp_found=sum(j in ok_g for j in imp))


def _prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def aggregate(rs):
    S = lambda k: sum(r[k] for r in rs)
    npred, ngold = S("n_pred"), S("n_gold")
    lp, lr, lf = _prf(S("loc_tp"), npred - S("loc_tp"), ngold - S("loc_tp"))
    tp = S("role_tp")
    p, r, f = _prf(tp, npred - tp, ngold - tp)
    per_role = {}
    for role in ROLES:
        t = sum(x["per_role"][role]["tp"] for x in rs)
        fp = sum(x["per_role"][role]["fp"] for x in rs)
        fn = sum(x["per_role"][role]["fn"] for x in rs)
        pr, rc, f1 = _prf(t, fp, fn)
        per_role[role] = dict(p=pr, r=rc, f1=f1, support=t + fn)
    comp = [x["main_found"] / x["main_n"] for x in rs if x["main_n"]]
    conf = Counter()
    for x in rs:
        conf.update(x["conf"])
    by_arc = {}
    for arc in sorted({x["arc"] for x in rs}):
        sub = [x for x in rs if x["arc"] == arc]
        t = sum(x["role_tp"] for x in sub)
        npr, ngd = sum(x["n_pred"] for x in sub), sum(x["n_gold"] for x in sub)
        pa, ra, fa = _prf(t, npr - t, ngd - t)
        by_arc[arc] = dict(sets=len(sub), p=pa, r=ra, f1=fa)
    return dict(
        sets=len(rs), links_gold=ngold, links_pred=npred,
        localization=dict(p=lp, r=lr, f1=lf),
        role_typed=dict(p=p, r=r, f1=f),
        macro_f1=sum(v["f1"] for v in per_role.values()) / len(ROLES),
        role_accuracy_given_localized=(tp / S("loc_tp")) if S("loc_tp") else 0.0,
        speaker_accuracy_given_localized=(S("speaker_ok") / S("loc_tp")) if S("loc_tp") else 0.0,
        chain_completeness=sum(comp) / len(comp) if comp else 0.0,
        chain_exact_rate=sum(1 for x in rs if x["main_n"] and x["main_found"] == x["main_n"]) / max(len(rs), 1),
        implicit_resolution_recall=(S("imp_found") / S("imp_n")) if S("imp_n") else None,
        implicit_n=S("imp_n"), per_role=per_role, by_arc=by_arc,
        confusion={f"{g}->{p_}": c for (g, p_), c in sorted(conf.items())})


def bootstrap(rs, n=1000, seed=0):
    rng = random.Random(seed)
    f1s, comps = [], []
    for _ in range(n):
        samp = [rs[rng.randrange(len(rs))] for _ in rs]
        a = aggregate(samp)
        f1s.append(a["role_typed"]["f1"])
        comps.append(a["chain_completeness"])
    q = lambda xs: (sorted(xs)[int(0.025 * len(xs))], sorted(xs)[min(int(0.975 * len(xs)), len(xs) - 1)])
    return dict(role_typed_f1_ci=q(f1s), chain_completeness_ci=q(comps))


def load_preds(pred_dir, set_id):
    p = pathlib.Path(pred_dir) / f"{set_id}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text()).get("links", [])


def score_dir(pred_dir, data_dir, tol=0, n_boot=0):
    rs, missing = [], []
    for gp in sorted((pathlib.Path(data_dir) / "gold").glob("*.json")):
        gold = json.loads(gp.read_text())
        preds = load_preds(pred_dir, gold["set_id"])
        if preds is None:
            missing.append(gold["set_id"])
            preds = []
        rs.append(score_set(preds, gold, tol))
    res = aggregate(rs)
    res["missing_prediction_files"] = missing
    res["tol"] = tol
    if n_boot and len(rs) > 1:
        res["bootstrap_95ci"] = bootstrap(rs, n_boot)
    return res


def print_report(res):
    L, R = res["localization"], res["role_typed"]
    print(f"\nsets={res['sets']}  gold links={res['links_gold']}  predicted links={res['links_pred']}  tol={res['tol']}")
    if res["missing_prediction_files"]:
        print("WARNING no predictions for:", res["missing_prediction_files"])
    print(f"localization : P {L['p']:.3f}  R {L['r']:.3f}  F1 {L['f1']:.3f}")
    print(f"role-typed   : P {R['p']:.3f}  R {R['r']:.3f}  F1 {R['f1']:.3f}   (macro-F1 over roles {res['macro_f1']:.3f})")
    print(f"role accuracy given localized   : {res['role_accuracy_given_localized']:.3f}")
    print(f"speaker accuracy given localized: {res['speaker_accuracy_given_localized']:.3f}")
    print(f"chain completeness (main chain) : {res['chain_completeness']:.3f}   chain-exact rate {res['chain_exact_rate']:.3f}")
    ir = res["implicit_resolution_recall"]
    print(f"implicit-resolution recall      : {'n/a' if ir is None else f'{ir:.3f}'} (n={res['implicit_n']})")
    if "bootstrap_95ci" in res:
        b = res["bootstrap_95ci"]
        print(f"bootstrap 95% CI over sets      : role-typed F1 [{b['role_typed_f1_ci'][0]:.3f}, {b['role_typed_f1_ci'][1]:.3f}]"
              f"  chain completeness [{b['chain_completeness_ci'][0]:.3f}, {b['chain_completeness_ci'][1]:.3f}]")
    print("\nper role          P      R      F1    support")
    for r, v in res["per_role"].items():
        print(f"  {r:<16}{v['p']:.3f}  {v['r']:.3f}  {v['f1']:.3f}  {v['support']}")
    print("\nper arc           sets   P      R      F1")
    for a, v in res["by_arc"].items():
        print(f"  {a:<17}{v['sets']:<6} {v['p']:.3f}  {v['r']:.3f}  {v['f1']:.3f}")
    print("\nconfusion (gold->predicted role; MISSED = no prediction on that utterance):")
    for k, c in res["confusion"].items():
        g, p = k.split("->")
        if g != p:
            print(f"  {k:<36}{c}")
    print("\nNote: precision is a lower bound (gold labels only the annotated decisions); see score.py docstring.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--tol", type=int, default=0)
    ap.add_argument("--bootstrap", type=int, default=0)
    ap.add_argument("--out")
    a = ap.parse_args()
    res = score_dir(a.pred, a.data, a.tol, a.bootstrap)
    print_report(res)
    if a.out:
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
