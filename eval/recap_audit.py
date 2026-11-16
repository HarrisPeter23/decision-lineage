"""recap_audit.py - leakage audit of single_pass_recap_roles (CHECKPOINT 4 review, item 1). DEV only; TEST is never read.
(a) Recap uses only the system's own prior outputs: rebuild every prompt from the config's OWN merged predictions + the DEV transcript, and compare its length
    with prompt_chars logged by the kernel for that call (the kernel prompt cannot be re-read: caches stay on Kaggle). Also rebuild the prompts with gold links
    injected instead, to show the check would catch a gold recap. Static check: extract_recap.py never opens a gold path.
(b) Role-guide examples invented: longest shared word n-gram between each example sentence and every DEV utterance and DEV gold gist; nearest DEV utterance by
    EMBED_MODEL cosine; DEV transcript occurrences of the example's proper names.
(c) Structure hints: the guide text is listed for manual review in the report; this script only greps for counts/positions.
  HF_HUB_OFFLINE=1 python eval/recap_audit.py   -> results/phase3/recap_audit.json
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "synthgen"))
sys.path.insert(0, str(ROOT))
import extract_recap as er                                   # noqa: E402
from argdecisionlineage.linking import Embedder              # noqa: E402
from score import gold_links                                 # noqa: E402


def words(t):
    return re.findall(r"[a-z0-9']+", t.lower())


def longest_shared_ngram(a, b):
    A, B = words(a), words(b)
    best, best_s = 0, ""
    for n in range(min(len(A), 12), 0, -1):
        grams = {tuple(A[i:i + n]) for i in range(len(A) - n + 1)}
        for i in range(len(B) - n + 1):
            if tuple(B[i:i + n]) in grams:
                return n, " ".join(B[i:i + n])
    return best, best_s


def rebuild(tr, links_by_meeting):
    prompts, prior = [], []
    for k, m in enumerate(tr["meetings"], 1):
        prompts.append(er.prompt(m, er.recap_text(prior)))
        text = {u["idx"]: u["text"] for u in m["utterances"]}
        for l in links_by_meeting.get(m["meeting_id"], []):
            prior.append((k, dict(l, text=" ".join(text.get(i, "") for i in l["utterance_idxs"]))))
    return prompts


def main():
    dev = json.loads((ROOT / "data/synth/split.json").read_text(encoding="utf-8"))["dev"]
    logs = {}
    for f in (ROOT / "results/phase3/recap/raw/out").glob("w*/single_pass_recap_roles/llm_log.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            logs[d["tag"]] = d["prompt_chars"]
    pred_dir = ROOT / "results/phase3/recap/merged/single_pass_recap_roles/preds"
    rows, n_ok, n_gold_ok = [], 0, 0
    for s in dev:
        tr = json.loads((ROOT / "data/synth/transcripts" / f"{s}.json").read_text(encoding="utf-8"))
        g = json.loads((ROOT / "data/synth/gold" / f"{s}.json").read_text(encoding="utf-8"))
        own = {}
        for l in json.loads((pred_dir / f"{s}.json").read_text(encoding="utf-8"))["links"]:
            own.setdefault(l["meeting_id"], []).append(l)
        gl = {}
        for l in gold_links(g):
            gl.setdefault(l["meeting_id"], []).append(dict(l, decision=g["topic"] if l["chain"] == "main" else g["distractor"]["topic"], option=l.get("option") or ""))
        for m, p_own, p_gold in zip(tr["meetings"], rebuild(tr, own), rebuild(tr, gl)):
            tag = f"{s}-{m['meeting_id']}-recap"
            ok, gok = len(er.SYSTEM) + len(p_own) == logs.get(tag), len(er.SYSTEM) + len(p_gold) == logs.get(tag)   # llm.py logs len(system) + len(user)
            n_ok += ok
            n_gold_ok += gok
            rows.append(dict(tag=tag, logged=logs.get(tag), rebuilt_own=len(er.SYSTEM) + len(p_own), rebuilt_gold=len(er.SYSTEM) + len(p_gold), own_match=ok, gold_match=gok))
    src = (ROOT / "synthgen/extract_recap.py").read_text(encoding="utf-8")
    static = dict(mentions_gold_path=bool(re.search(r"[\"'/]gold[\"'/]|gold_links|\"gold\"", src)), reads_only=re.findall(r"\(pathlib\.Path\(data\) / \"(\w+)\"\)", src))
    # (b)
    ex = [line.split("->")[0].strip(" -\"") for line in er.ROLE_GUIDE.splitlines() if "->" in line]
    ex = [re.sub(r'"\s*(said|by|with).*$', "", e).strip('" ') for e in ex]
    utts, gists = [], []
    for s in dev:
        tr = json.loads((ROOT / "data/synth/transcripts" / f"{s}.json").read_text(encoding="utf-8"))
        utts += [(s, m["meeting_id"], u["idx"], u["text"]) for m in tr["meetings"] for u in m["utterances"]]
        g = json.loads((ROOT / "data/synth/gold" / f"{s}.json").read_text(encoding="utf-8"))
        gists += [(s, l["link_id"], l["gist"]) for l in gold_links(g)]
    emb = Embedder()
    U = emb([u[3] for u in utts])
    E = emb(ex)
    dev_text = " ".join(u[3] for u in utts).lower()
    exrows = []
    for i, e in enumerate(ex):
        n_u, s_u, _ = max((longest_shared_ngram(e, u[3]) + (u[:3],) for u in utts), key=lambda x: x[0])
        n_g, s_g, _ = max((longest_shared_ngram(e, g_[2]) + (g_[:2],) for g_ in gists), key=lambda x: x[0])
        sims = U @ E[i]
        j = int(sims.argmax())
        exrows.append(dict(example=e, longest_ngram_utterance=n_u, ngram_u=s_u, longest_ngram_gist=n_g, ngram_g=s_g, nearest_cos=round(float(sims[j]), 3),
                           nearest=dict(set=utts[j][0], meeting=utts[j][1], idx=utts[j][2], text=utts[j][3][:200])))
    names = {n: sorted({u[0] for u in utts if re.search(rf"\b{n}\b", u[3])}) for n in ("Brightway", "Clearline", "Priya", "Sam")}   # DEV sets whose utterances name it
    # (c)
    hints = re.findall(r"(meeting \d|first meeting|last meeting|final meeting|\b\d+ (links|events|resolutions|proposals)\b|exactly \w+ |at most|at least)", er.ROLE_GUIDE, re.I)
    out = dict(a=dict(calls=len(rows), own_rebuild_matches=n_ok, gold_rebuild_matches=n_gold_ok, static=static, rows=rows),
               b=dict(examples=exrows, name_counts_in_dev=names), c=dict(structure_phrases_in_guide=hints))
    (ROOT / "results/phase3/recap_audit.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("a:", n_ok, "/", len(rows), "own-rebuild matches;", n_gold_ok, "gold-rebuild matches; static", static)
    for r in exrows:
        print(f"b: ngram_u {r['longest_ngram_utterance']} '{r['ngram_u']}' | ngram_gist {r['longest_ngram_gist']} | cos {r['nearest_cos']} | {r['example'][:60]}")
    print("b names:", names, "c:", hints)


if __name__ == "__main__":
    main()
