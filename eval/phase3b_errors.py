"""phase3b_errors.py - Step 2 of the Phase 3 improvement round: error taxonomy of the best valid config (single_pass_recap_roles_top4) on DEV, from
existing outputs only (no model calls). Counts for the tune half, the check half (results/phase3/p3f_split.json) and all 14 sets. tol 1, as everywhere.

False positives (each unmatched prediction gets ONE category, in this order):
  FP_role      localized on a gold utterance (one-to-one matching) but with the wrong role            [user's (b)]
  FP_dup       within tol of a gold link that another prediction already matched (duplicate/split)    [(c)]
  FP_outside   not attached to an annotated decision (decision_scope.py): a real or spurious event of some OTHER decision; gold has no label for it [(a)]
  FP_span      attached, and within 3 utterances of a gold link (boundary near-miss)
  FP_inscope   attached to an annotated decision, not near any gold link: split by hand on a sample into unannotated-real / wrong-decision / unsupported [(d), (e)]
False negatives (each unmatched gold link gets ONE category, in this order):
  FN_cap       role-matched in the UNCAPPED output, removed by the top-4 cap (D-16)                    [(d)]
  FN_span      a prediction with the right role in the same meeting within 3 utterances, not within 1  [(e)]
  FN_role      localized by a prediction with the wrong role
  FN_cross     missed entirely, in a meeting after the first meeting of its chain (a cross-meeting continuation)   [(b)]
  FN_within    missed entirely, in the first meeting of its chain                                      [(a)]
Also: WRONG_DECISION = a localized prediction whose own decision name is closer (EMBED_MODEL) to the other annotated decision of the set (sets with a
distractor only); WRONG_VERSION = a true positive that the Phase 4 graph (v4 + L2) places in a version whose option is not the gold link's version [(c)].
  HF_HUB_OFFLINE=1 python eval/phase3b_errors.py -> results/phase3/p3f_errors.json
"""
import collections
import json
import pathlib
import random
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "synthgen"), str(ROOT / "eval")]
from score import ROLES, aggregate, gold_links, match_links, score_set     # noqa: E402
from phase3_topk import div_topk, topk                                     # noqa: E402
import decision_scope as DS                                                # noqa: E402
from argdecisionlineage.linking import Embedder                            # noqa: E402
from argdecisionlineage.retrieve import LineageSystem                      # noqa: E402
from option_map import map_option                                          # noqa: E402

HEADLINE = ("why_changed", "evidence_to_reconsider", "full_lineage")
PRED = ROOT / "results/phase3/recap/merged/single_pass_recap_roles/preds"
CAP = "top4"
OUTNAME = "p3f_errors.json"
if "--args" in sys.argv:                     # after-taxonomy of recap_args_div4 (P3-F); same categories, same code
    PRED = ROOT / "results/phase3/p3f/merged/single_pass_recap_args/preds"
    CAP, OUTNAME = "div4", "p3f_errors_args_div4.json"


def dist(a, b):
    return min(abs(x - y) for x in a for y in b)


def near(p, g, t):
    return p["meeting_id"] == g["meeting_id"] and dist(p["utterance_idxs"], g["utterance_idxs"]) <= t


def analyse(s, g, tr, scope, emb):
    golds = gold_links(g)
    raw = json.loads((PRED / f"{s}.json").read_text(encoding="utf-8"))["links"]
    preds = topk(raw, 4) if CAP == "top4" else div_topk(raw, 4)
    pairs = match_links(preds, golds, 1)
    tp = {(i, j) for i, j in pairs if preds[i]["role"] == golds[j]["role"]}
    tp_p, tp_g = {i for i, _ in tp}, {j for _, j in tp}
    loc_p = {i: j for i, j in pairs}
    loc_g = {j: i for i, j in pairs}
    uc = match_links(raw, golds, 1)
    uc_g = {j for i, j in uc if raw[i]["role"] == golds[j]["role"]}
    first = {}
    for gl in golds:
        first[gl["chain"]] = min(first.get(gl["chain"], 99), gl["meeting"])
    head = {lid for q in g["questions"] if q["type"] in HEADLINE for lid in q["supporting_links"]}
    ms = {m["meeting_id"]: m for m in tr["meetings"]}
    utt = lambda mid, idxs: " ".join(f"{ms[mid]['utterances'][i]['speaker']}: {ms[mid]['utterances'][i]['text']}" for i in idxs if i < len(ms[mid]["utterances"]))
    errs = []
    for i, p in enumerate(preds):
        if i in tp_p:
            continue
        if i in loc_p:
            cat, gj = "FP_role", loc_p[i]
        elif any(near(p, gl, 1) for gl in golds):
            cat, gj = "FP_dup", next(j for j, gl in enumerate(golds) if near(p, gl, 1))
        elif not scope.attached(p):
            cat, gj = "FP_outside", None
        elif any(near(p, gl, 3) for gl in golds):
            cat, gj = "FP_span", next(j for j, gl in enumerate(golds) if near(p, gl, 3))
        else:
            cat, gj = "FP_inscope", None
        errs.append(dict(set_id=s, kind="FP", cat=cat, role=p["role"], meeting_id=p["meeting_id"], idxs=p["utterance_idxs"], decision=p.get("decision", ""),
                         text=utt(p["meeting_id"], p["utterance_idxs"]), gold=None if gj is None else dict(link_id=golds[gj]["link_id"], role=golds[gj]["role"],
                         idxs=golds[gj]["utterance_idxs"], gist=golds[gj]["gist"]), headline=gj is not None and golds[gj]["link_id"] in head))
    for j, gl in enumerate(golds):
        if j in tp_g:
            continue
        if j in uc_g:
            cat = "FN_cap"
        elif any(p["role"] == gl["role"] and near(p, gl, 3) for p in preds):
            cat = "FN_span"
        elif j in loc_g:
            cat = "FN_role"
        elif gl["meeting"] > first[gl["chain"]]:
            cat = "FN_cross"
        else:
            cat = "FN_within"
        pr = preds[loc_g[j]]["role"] if j in loc_g else None
        errs.append(dict(set_id=s, kind="FN", cat=cat, role=gl["role"], predicted_role=pr, meeting_id=gl["meeting_id"], idxs=gl["utterance_idxs"], link_id=gl["link_id"],
                         gist=gl["gist"], text=utt(gl["meeting_id"], gl["utterance_idxs"]), headline=gl["link_id"] in head, implicit=gl.get("implicit", False)))
    # wrong decision attached (localized predictions, sets with a distractor)
    wrong_dec = 0
    if g.get("distractor"):
        descs = [g["topic"] + " " + " ".join(g["options"].values()), g["distractor"]["topic"] + " " + g["distractor"].get("option", "")]
        dv = emb(descs)
        for i, j in pairs:
            name = preds[i].get("decision") or ""
            if name:
                (nv,) = emb([name])
                want = 0 if golds[j]["chain"] == "main" else 1
                wrong_dec += int(np.argmax(dv @ nv)) != want
    # wrong version for true positives (Phase 4 graph, v4 + L2, as used downstream)
    S = LineageSystem(embedder=emb, fallback=False).index(tr, preds)
    by_key = {(l.meeting_id, tuple(l.idxs)): l for l in S.links}
    wrong_ver = ver_n = 0
    ver_detail = []
    for i, j in tp:
        gv = golds[j].get("version")
        if gv is None:
            continue
        l = by_key.get((preds[i]["meeting_id"], tuple(sorted(set(preds[i]["utterance_idxs"])))))
        if l is None:
            continue
        v = S._version_at(l.decision, l.pos)
        ver_n += 1
        want = g["versions"][gv - 1]["option"] if gv <= len(g["versions"]) else None
        got = map_option(v["option"], g, None, 1) if v else None
        wrong_ver += got != want
        if got != want:
            ver_detail.append(dict(role=golds[j]["role"], graph_version=None if v is None else v["n"], got=got, want=want, gold_version=gv))
    sc = score_set(preds, g, 1)
    return errs, dict(wrong_decision=wrong_dec, localized=len(pairs), wrong_version=wrong_ver, tp_with_version=ver_n, ver_detail=ver_detail), sc


def main():
    split = json.loads((ROOT / "results/phase3/p3f_split.json").read_text(encoding="utf-8"))
    dev = split["tune"] + split["check"]
    emb = Embedder()
    tau, _ = DS.calibrate(ROOT / "data/synth/gold", ROOT / "data/synth/transcripts", dev)
    E, X, SC = [], {}, {}
    for s in dev:
        g = json.loads((ROOT / "data/synth/gold" / f"{s}.json").read_text(encoding="utf-8"))
        tr = json.loads((ROOT / "data/synth/transcripts" / f"{s}.json").read_text(encoding="utf-8"))
        e, x, sc = analyse(s, g, tr, DS.Scope(g, tr, tau, 1), emb)
        E += e
        X[s], SC[s] = x, sc
    out = {}
    for name, sets in (("tune", split["tune"]), ("check", split["check"]), ("all", dev)):
        es = [e for e in E if e["set_id"] in sets]
        c = collections.Counter(e["cat"] for e in es)
        ch = collections.Counter(e["cat"] for e in es if e["headline"])
        a = aggregate([SC[s] for s in sets])
        out[name] = dict(counts=dict(sorted(c.items())), headline_counts=dict(sorted(ch.items())),
                         wrong_decision=sum(X[s]["wrong_decision"] for s in sets), localized=sum(X[s]["localized"] for s in sets),
                         wrong_version=sum(X[s]["wrong_version"] for s in sets), tp_with_version=sum(X[s]["tp_with_version"] for s in sets),
                         wrong_version_by=dict(collections.Counter(f"{d['role']}:{'no version yet' if d['graph_version'] is None else 'other version'}" for s in sets for d in X[s]["ver_detail"])),
                         f1=round(a["role_typed"]["f1"], 3), p=round(a["role_typed"]["p"], 3), r=round(a["role_typed"]["r"], 3),
                         per_role={r: dict(p=round(a["per_role"][r]["p"], 3), r=round(a["per_role"][r]["r"], 3), f1=round(a["per_role"][r]["f1"], 3),
                                           support=a["per_role"][r]["support"]) for r in ROLES},
                         fn_role_confusions=dict(collections.Counter(f"{e['role']}->{e['predicted_role']}" for e in es if e["cat"] == "FN_role")),
                         fn_by_role=dict(collections.Counter(f"{e['cat']}:{e['role']}" for e in es if e["kind"] == "FN")))
    out["per_set"] = {s: dict(f1=round(aggregate([SC[s]])["role_typed"]["f1"], 3), half="tune" if s in split["tune"] else "check", arc=SC[s]["arc"],
                              n_gold=SC[s]["n_gold"], n_pred=SC[s]["n_pred"], tp=SC[s]["role_tp"]) for s in dev}
    rng = random.Random(0)
    samples = {}
    for cat in sorted({e["cat"] for e in E}):
        xs = [e for e in E if e["cat"] == cat]
        rng.shuffle(xs)
        samples[cat] = xs[:6]
    out["samples"] = samples
    out["inscope_all"] = [e for e in E if e["cat"] == "FP_inscope"]
    (ROOT / "results/phase3" / OUTNAME).write_text(json.dumps(out, indent=1), encoding="utf-8")
    for name in ("tune", "check", "all"):
        o = out[name]
        print(name, "F1", o["f1"], "counts", o["counts"], "| headline", o["headline_counts"], "| wrong_dec", o["wrong_decision"], "/", o["localized"],
              "| wrong_ver", o["wrong_version"], "/", o["tp_with_version"])
        print("   FN role confusions", o["fn_role_confusions"])


if __name__ == "__main__":
    main()
