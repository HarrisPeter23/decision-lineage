"""Builds the Graphiti kernel for DEV pooled corpora.
  python runtime/kaggle/graphiti/build.py <kernel-name> --pools dev_k1_00,dev_k1_01 [--time-budget-h 10]
Bundles, per pool: the plain-text meetings in corpus order (opaque ids, dates, text) and the question texts of its sets (qid + question only).
DEV only (asserted). Gold answers, set ids and the private map are NOT bundled; the qid -> pool assignment is done here, on the harness side."""
import argparse, base64, gzip, json, pathlib, sys
sys.path.insert(0, ".")
from baselines.graphiti.episodes import episodes_for   # FREEZE section 9 / 18: one episode per chunk window when a meeting exceeds the budget

ap = argparse.ArgumentParser()
ap.add_argument("name")
ap.add_argument("--pools", required=True)
ap.add_argument("--time-budget-h", type=float, default=10)
ap.add_argument("--concurrency", type=int, default=4)
ap.add_argument("--chunk-budget", type=int, default=6000, help="FREEZE section 9 BUDGET (6000); smaller values only for the DEV dry-run")
ap.add_argument("--source", default="dev", choices=["dev", "test", "ami"], help="ami: data/ami series as pool-1 corpora (Phase 7, after FREEZE)")
ap.add_argument("--hardened-install", action="store_true", help="Phase 7 D-36: checked Ollama install + frozen-digest assert (infrastructure only)")
a = ap.parse_args()
dev = set(json.loads(pathlib.Path("data/synth/split.json").read_text(encoding="utf-8"))["dev"])
import fnmatch
# Inputs come from the SHARED pools only: synthetic DEV pools, or the shared AMI pools written by eval/ami_pools.py (dates normalised there, once, for
# every system; FREEZE section 18). This builder does no date handling of its own.
P = {"ami": pathlib.Path("data/ami/pools"), "test": pathlib.Path("data/synth/pools/test"), "dev": pathlib.Path("data/synth/pools/dev")}[a.source]   # test: Phase 7 only
GOLD_Q = pathlib.Path("data/ami/gold") if a.source == "ami" else pathlib.Path("data/synth/gold")
corpora = {}
pats = ["*"] if a.source == "ami" else a.pools.split(",")
names = sorted({p.name for pat in pats for p in P.iterdir() if p.is_dir() and fnmatch.fnmatch(p.name, pat)})
for name in names:
    assert name.startswith(f"{a.source}_") or a.source == "ami", "pools of the chosen source only"
    ids = json.loads((P / name / "corpus.json").read_text(encoding="utf-8"))["meetings"]
    meetings = []
    for m in ids:
        text = (P / name / "meetings" / f"{m}.txt").read_text(encoding="utf-8")
        head, _, body = text.partition("\n\n")
        date = [l.split(":", 1)[1].strip() for l in head.splitlines() if l.lower().startswith("date:")][0]
        meetings.append(dict(meeting_id=m, date=date, text=body.strip(), episodes=episodes_for(m, body, a.chunk_budget)))
    sets = json.loads((P / name / "private_map.json").read_text(encoding="utf-8"))["_sets"]
    assert a.source != "dev" or all(s in dev for s in sets)
    qs = []
    for s in sets:
        for q in json.loads((GOLD_Q / f"{s}.json").read_text(encoding="utf-8"))["questions"]:
            qs.append(dict(qid=q["qid"], question=q["question"]))
    corpora[name] = dict(meetings=meetings, questions=qs)
cfg = dict(model="qwen3:14b", embed_model="all-minilm", embed_dim=384, ctx=16384, max_tokens=4096, k=12, graphiti_version="0.31.2", neo4j_version="5.26.17",
           time_budget_s=int(a.time_budget_h * 3600), concurrency=a.concurrency)
blob = base64.b64encode(gzip.compress(json.dumps(dict(config=cfg, corpora=corpora)).encode())).decode()
out = pathlib.Path("runtime/kaggle/graphiti/kernels") / a.name
out.mkdir(parents=True, exist_ok=True)
src = pathlib.Path("runtime/kaggle/graphiti/template.py").read_text(encoding="utf8")
if a.hardened_install:
    # Phase 7, D-36 (infrastructure only, user-approved): the one-line `curl | sh` install can return rc 0 with no binary when a download fails inside the
    # pipes. Download the script to a file, run it, check the binary, retry up to 3 times, abort before any model call if still missing; then assert the
    # pulled model digests equal the frozen ones before any episode. Model, config, seed and Graphiti code are unchanged.
    old_i = 'sh("curl -fsSL https://ollama.com/install.sh | sh", 600)\n'
    new_i = ('for _try in range(3):\n'
             '    sh("curl -fsSL --retry 3 https://ollama.com/install.sh -o /tmp/install.sh && sh /tmp/install.sh", 600)\n'
             '    if os.path.exists("/usr/local/bin/ollama"):\n'
             '        break\n'
             '    log("ollama binary missing after install attempt", _try + 1)\n'
             '    time.sleep(30)\n'
             'else:\n'
             '    raise SystemExit("ollama install failed 3 times; no model call made")\n')
    old_d = 'log("digests", digests)\n'
    new_d = (old_d + 'FROZEN = {"bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8", "1b226e2802dbb772b5fc32a58f103ca1804ef7501331012de126ab22f67475ef"}\n'
             'assert FROZEN <= set(digests.values()), ("model digests differ from the frozen ones", digests)\n'
             'log("frozen digests confirmed")\n')
    # launch 4 (user-approved exception, 2026-11-09): launch 3 failed because the apt mirror was unreachable, so zstd (needed to unpack the Ollama
    # .tar.zst) was missing. Retry apt up to 3 times and require zstd and java before continuing; abort before any model call otherwise.
    old_a = 'sh("apt-get update -qq && apt-get install -y -qq zstd openjdk-17-jre-headless", 600)\n'
    new_a = ('for _try in range(3):\n'
             '    sh("apt-get update -qq && apt-get install -y -qq --fix-missing zstd openjdk-17-jre-headless", 600)\n'
             '    if sh("command -v zstd && command -v java", 30).returncode == 0:\n'
             '        break\n'
             '    log("zstd or java missing after apt attempt", _try + 1)\n'
             '    time.sleep(60)\n'
             'else:\n'
             '    raise SystemExit("apt install failed 3 times; no model call made")\n')
    assert src.count(old_i) == 1 and src.count(old_d) == 1 and src.count(old_a) == 1
    src = src.replace(old_a, new_a).replace(old_i, new_i).replace(old_d, new_d)
(out / "graphiti_run.py").write_text(src.replace("@@BUNDLE@@", blob), encoding="utf8", newline="\n")
(out / "kernel-metadata.json").write_text(json.dumps(dict(id="KAGGLE_USER/" + a.name, title=a.name, code_file="graphiti_run.py", language="python", kernel_type="script",
    is_private=True, enable_gpu=True, enable_internet=True, dataset_sources=[], competition_sources=[], kernel_sources=[])))
print(a.name, {k: (len(v["meetings"]), len(v["questions"])) for k, v in corpora.items()}, "->", out)
