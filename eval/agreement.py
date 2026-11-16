"""agreement.py - judge reliability (Phase 1.3): raw agreement and Cohen's kappa between two verdict sources over the links both labelled."""
import collections, json, pathlib, sys

def load_jsonl(p):
    return {(r["set_id"], r["link_id"]): r["verdict"] for r in map(json.loads, pathlib.Path(p).read_text(encoding="utf-8").splitlines())}

def load_hand(p):
    return {(r["set_id"], r["link_id"]): r["verdict"] for r in json.loads(pathlib.Path(p).read_text(encoding="utf-8"))}

def kappa(a, b):
    keys = sorted(set(a) & set(b))
    if not keys: return None
    cats = sorted({a[k] for k in keys} | {b[k] for k in keys})
    n = len(keys); po = sum(a[k] == b[k] for k in keys) / n
    pa = collections.Counter(a[k] for k in keys); pb = collections.Counter(b[k] for k in keys)
    pe = sum(pa[c] * pb[c] for c in cats) / (n * n)
    return dict(n=n, agree=round(po, 3), kappa=None if pe == 1 else round((po - pe) / (1 - pe), 3), a=dict(pa), b=dict(pb))

if __name__ == "__main__":
    loaders = {"hand": load_hand}
    def get(x): return load_hand(x) if x.endswith(".json") else load_jsonl(x)
    print(kappa(get(sys.argv[1]), get(sys.argv[2])))
