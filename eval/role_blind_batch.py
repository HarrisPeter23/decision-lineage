"""role_blind_batch.py - finish the Gemini role-blind check (judge assigns one of the six roles without seeing the gold role), batched 10 per request.

Procedure (fixed before running):
  1. VALIDATE the batched procedure on 50 links that already have single-item Gemini verdicts (stratified by gold role, seed 20261104): proceed to step 2 only if
     exact agreement between batched and single verdicts is at least 0.90. Otherwise the remaining items are judged single-item (budget allows it).
  2. RUN the remaining synthetic links (items r139-r292) and all 43 AMI links, 10 per request.
One judge model (gemini-3.5-flash-lite) for the whole task; which procedure judged which item is recorded in the output (field `procedure`).
  python eval/role_blind_batch.py validate
  python eval/role_blind_batch.py run
"""
import collections
import json
import pathlib
import random
import sys

sys.path.insert(0, "eval")
sys.path.insert(0, "synthgen")
import gemini_batch as gb         # noqa: E402
import panel                      # noqa: E402
import role_blind as rb           # noqa: E402

ROLES = rb.ROLES
CHOICES = " | ".join(f'"{r}"' for r in ROLES)
RUBRIC = "Choose exactly ONE role for each item, using only the role definitions given in that item."
OUT = pathlib.Path("results/role_blind")
AMI = pathlib.Path("results/role_blind_ami")
CACHE = "runtime/cache/gemini_batch_role"


def build_ami():
    AMI.mkdir(parents=True, exist_ok=True)
    items, key = [], {}
    for sid, tr, gold, l in panel.iter_links("data/ami"):
        item = f"a{len(items):03d}"
        items.append(dict(item=item, set_id=sid, link_id=item, mode="role", prompt=rb.prompt(tr, l)))
        key[item] = dict(set_id=sid, link_id=l["link_id"], role=l["role"], implicit=bool(l.get("implicit")))
    (AMI / "items.jsonl").write_text("\n".join(json.dumps(i) for i in items) + "\n", encoding="utf-8")
    (AMI / "key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    return items, key


def load(p):
    return [json.loads(l) for l in pathlib.Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def run(items, tag):
    return gb.run_batches([dict(id=i["item"], prompt=i["prompt"]) for i in items], size=10, field="role", allowed=tuple(ROLES), choices=CHOICES,
                          rubric=RUBRIC, cache=CACHE, tag=tag)


def validate():
    key = json.loads((OUT / "key.json").read_text(encoding="utf-8"))
    single = {r["item"]: r["verdict"] for r in load(OUT / "gemini.jsonl")}
    items = {i["item"]: i for i in load(OUT / "items.jsonl")}
    rng = random.Random(20261104)
    by = collections.defaultdict(list)
    for i in single:
        by[key[i]["role"]].append(i)
    pick = []
    for role, ids in sorted(by.items()):
        rng.shuffle(ids)
        pick += ids[:max(5, round(50 * len(ids) / len(single)))]
    rng.shuffle(pick)
    pick = pick[:50]
    got = run([items[i] for i in pick], "role_validate")
    pairs = [(single[i], got[i]) for i in pick]
    agree, kap = gb.kappa(pairs)
    gold_single = sum(single[i] == key[i]["role"] for i in pick) / len(pick)
    gold_batched = sum(got[i] == key[i]["role"] for i in pick) / len(pick)
    res = dict(n=len(pick), exact_agreement=agree, kappa=kap, accuracy_vs_gold_single=round(gold_single, 3), accuracy_vs_gold_batched=round(gold_batched, 3),
               missing=sum(v == "missing" for v in got.values()), invalid=sum(v == "invalid" for v in got.values()), threshold=0.90, passed=agree >= 0.90,
               changed=[dict(item=i, gold=key[i]["role"], single=single[i], batched=got[i]) for i in pick if single[i] != got[i]])
    (OUT / "batched_validation.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "changed"}), "\nchanged:", res["changed"])


def do_run():
    val = json.loads((OUT / "batched_validation.json").read_text(encoding="utf-8"))
    batched_ok = val["passed"]
    syn = [i for i in load(OUT / "items.jsonl")]
    done = {r["item"] for r in load(OUT / "gemini.jsonl")}
    rest = [i for i in syn if i["item"] not in done]
    ami = load(AMI / "items.jsonl") if (AMI / "items.jsonl").exists() else build_ami()[0]
    if not batched_ok:
        raise SystemExit("batched validation below threshold; run these items single-item instead (not implemented here on purpose)")
    for name, items, path in (("synthetic_rest", rest, OUT / "gemini_batched.jsonl"), ("ami", ami, AMI / "gemini.jsonl")):
        got_done = {r["item"] for r in load(path)} if path.exists() else set()
        todo = [i for i in items if i["item"] not in got_done]
        for k in range(0, len(todo), 40):                        # write after every 4 requests so an interruption loses little
            res = run(todo[k:k + 40], "role_" + name)
            with path.open("a", encoding="utf-8") as f:
                for i, v in res.items():
                    f.write(json.dumps(dict(item=i, verdict=v, procedure="batched10")) + "\n")
            print(name, k + len(res), "of", len(todo), flush=True)
    print("done")


def do_run_single():
    """Fallback fixed in advance for a failed batched validation: single-item requests for all remaining items, same prompt and model as the first 139."""
    import time
    from llm import LLM, DailyQuotaExceeded, extract_json
    llm = LLM("gemini_free", gb.MODEL, temperature=0, max_tokens=300, cache_dir="runtime/cache/role_blind_gemini", log_path="runtime/role_blind_gemini_log.jsonl")
    ami = load(AMI / "items.jsonl") if (AMI / "items.jsonl").exists() else build_ami()[0]
    jobs = [(i, OUT / "gemini.jsonl") for i in load(OUT / "items.jsonl")] + [(i, AMI / "gemini.jsonl") for i in ami]
    mode = sys.argv[2] if len(sys.argv) > 2 else ""
    if mode == "ami":                                          # parallel worker: AMI items only
        jobs = [j for j in jobs if j[1] == AMI / "gemini.jsonl"]
    elif mode == "rev":                                        # parallel worker: synthetic items from the end (the cache makes any overlap free)
        jobs = [j for j in jobs if j[1] == OUT / "gemini.jsonl"][::-1]
    done = {}
    for _, p in jobs:
        done.setdefault(p, {r["item"] for r in load(p)} if p.exists() else set())
    last = 0.0
    n = 0
    for it, path in jobs:
        if it["item"] in done[path]:
            continue
        if gb.used_today() >= gb.BUDGET:
            raise SystemExit("daily budget reached; resume after the reset")
        time.sleep(max(0.0, 5.0 - (time.time() - last)))
        last = time.time()
        try:
            r = extract_json(llm.complete(rb.SYSTEM, it["prompt"], kind="judge", temperature=0))
            v, why = str(r.get("role", "")).lower().strip(), str(r.get("reason", ""))[:200]
            v = v if v in ROLES else "invalid"
        except DailyQuotaExceeded as e:
            raise SystemExit(str(e))
        except Exception as e:
            v, why = "error", type(e).__name__
        if v == "error":
            continue                                           # leave it for the next resume; never record errors as verdicts
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(dict(item=it["item"], verdict=v, reason=why, procedure="single")) + "\n")
        n += 1
        if n % 10 == 0:
            print(n, "done", flush=True)
    print("done", n)


if __name__ == "__main__":
    {"validate": validate, "run": do_run, "run_single": do_run_single, "build_ami": build_ami}[sys.argv[1]]()
