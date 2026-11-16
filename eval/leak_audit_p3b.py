"""leak_audit_p3b.py - Step 1 of the Phase 3 improvement round (2026-11-06): leakage audit of single_pass_recap_roles on its CACHED OUTPUTS. DEV only.
Extends reports/recap_audit.md (prompts) to the model outputs:
  (1) gold link ids (B1.., D1..) or arc names inside any output field (decision, option);
  (2) wording shared with gold annotations (gists, option texts, topics) that does NOT occur in the set's transcript: any shared word 5-gram that is absent from
      the transcript is a leak signal (the model can only know annotation wording from the annotations);
  (3) the logged prompts: prompt_chars of all 44 calls vs prompts rebuilt from the config's own outputs (repeated from recap_audit.md).
  python eval/leak_audit_p3b.py -> results/phase3/leak_audit_p3b.json
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "synthgen")]
from score import gold_links   # noqa: E402

ARCS = ["simple_reversal", "re_reversal", "partial_override", "no_reversal", "deferred", "external_trigger"]


def words(t):
    return re.findall(r"[a-z0-9']+", t.lower())


def grams(ws, n):
    return {tuple(ws[i:i + n]) for i in range(len(ws) - n + 1)}


def main():
    dev = json.loads((ROOT / "data/synth/split.json").read_text(encoding="utf-8"))["dev"]
    pred_dir = ROOT / "results/phase3/recap/merged/single_pass_recap_roles/preds"
    res = dict(sets=len(dev), fields=0, id_hits=[], arc_hits=[], annotation_only_5grams=[])
    for s in dev:
        g = json.loads((ROOT / "data/synth/gold" / f"{s}.json").read_text(encoding="utf-8"))
        tr = json.loads((ROOT / "data/synth/transcripts" / f"{s}.json").read_text(encoding="utf-8"))
        tgrams = grams(words(" ".join(u["text"] for m in tr["meetings"] for u in m["utterances"])), 5)
        ann = [l["gist"] for l in gold_links(g)] + list(g["options"].values()) + [g["topic"]]
        if g.get("distractor"):
            ann += [g["distractor"]["topic"], g["distractor"].get("option", "")]
        agrams = set().union(*(grams(words(a), 5) for a in ann))
        ann_only = agrams - tgrams
        for l in json.loads((pred_dir / f"{s}.json").read_text(encoding="utf-8"))["links"]:
            for field in ("decision", "option"):
                t = l.get(field) or ""
                if not t:
                    continue
                res["fields"] += 1
                if re.search(r"\b[BD]\d{1,2}\b", t):
                    res["id_hits"].append((s, field, t))
                if any(a.replace("_", " ") in t.lower() or a in t.lower() for a in ARCS):
                    res["arc_hits"].append((s, field, t))
                hit = grams(words(t), 5) & ann_only
                if hit:
                    res["annotation_only_5grams"].append((s, field, t, [" ".join(h) for h in hit]))
    audit = json.loads((ROOT / "results/phase3/recap_audit.json").read_text(encoding="utf-8"))["a"]
    res["prompt_rebuild"] = dict(own_matches=audit["own_rebuild_matches"], gold_matches=audit["gold_rebuild_matches"], calls=audit["calls"])
    res["verdict"] = "PASS" if not (res["id_hits"] or res["arc_hits"] or res["annotation_only_5grams"]) and audit["own_rebuild_matches"] == audit["calls"] else "CHECK"
    (ROOT / "results/phase3/leak_audit_p3b.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in res.items()}))
    for x in res["annotation_only_5grams"][:10]:
        print(x)


if __name__ == "__main__":
    main()
