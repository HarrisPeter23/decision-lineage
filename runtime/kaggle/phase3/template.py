# Phase 3 extraction runs on DEV: starts one model server (vLLM or Ollama, per config), splits the DEV sets across parallel worker processes,
# and runs synthgen/run_ablation.py on each part. Raw outputs, per-config caches and call logs are returned for merging and scoring on the laptop.
# DEV data only. Never prints environment variables.
import base64, gzip, io, json, os, pathlib, shutil, subprocess, sys, tarfile, time, urllib.request

WORK = pathlib.Path("/kaggle/working")
SRC = pathlib.Path("/kaggle/src_bundle")
BUNDLE = "@@BUNDLE@@"
CFG = json.loads(gzip.decompress(base64.b64decode(BUNDLE)).decode()) if False else None


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def sh(c, timeout=1800, check=False):
    r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=timeout)
    log("$", c[:110], "rc", r.returncode)
    if r.returncode:
        log("STDERR TAIL:", r.stderr[-1200:])
    return r


raw = base64.b64decode(BUNDLE)
tar_len = int.from_bytes(raw[:8], "big")
CFG = json.loads(raw[8:8 + tar_len].decode())
tarfile.open(fileobj=io.BytesIO(raw[8 + tar_len:]), mode="r:gz").extractall(SRC, filter="data")
KIND, MODEL, WORKERS, CONFIGS = CFG["server"], CFG["model"], CFG["workers"], CFG["configs"]
PORT = 8000 if KIND == "vllm" else 11434
base_env = dict(os.environ, OPENAI_COMPAT_BASE_URL=f"http://127.0.0.1:{PORT}/v1")
if CFG.get("chunk_budget"):
    base_env["ADL_CHUNK_BUDGET"] = str(CFG["chunk_budget"])
meta = dict(cfg={k: v for k, v in CFG.items() if k != "note"}, t0=time.time())
procs = []


def wait_ready(timeout=1500):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/v1/models", timeout=5)
            return True
        except Exception:
            time.sleep(5)
    return False


if KIND == "vllm":
    ENV = WORK / "venv"
    sh("pip -q install uv", 600)
    sh(f"uv venv {ENV} --python 3.11", 900)
    r = sh(f"uv pip install --python {ENV}/bin/python vllm", 1800)
    meta["install_rc"] = r.returncode
    meta["versions"] = subprocess.run(f"{ENV}/bin/python -c 'import vllm,torch;print(vllm.__version__,torch.__version__)'", shell=True, capture_output=True, text=True).stdout.strip()
    srv = subprocess.Popen(f"{ENV}/bin/vllm serve {MODEL} --quantization awq --dtype float16 --tensor-parallel-size 2 --max-model-len 12288 --port {PORT} --seed 7 --max-num-seqs {CFG.get('max_num_seqs', 16)}",
                           shell=True, stdout=open(WORK / "server.log", "w"), stderr=subprocess.STDOUT)
    base_env["OPENAI_COMPAT_EXTRA_BODY"] = json.dumps({"chat_template_kwargs": {"enable_thinking": False}})
else:
    sh("apt-get update -qq && apt-get install -y -qq zstd", 300)
    sh("curl -fsSL https://ollama.com/install.sh | sh", 600)
    env = dict(os.environ, OLLAMA_CONTEXT_LENGTH="16384", OLLAMA_MODELS="/tmp/ollama", OLLAMA_NUM_PARALLEL=str(CFG.get("parallel", 4)), OLLAMA_KEEP_ALIVE="60m")
    srv = subprocess.Popen(["ollama", "serve"], env=env, stdout=open(WORK / "server.log", "w"), stderr=subprocess.STDOUT)
    time.sleep(8)
    sh(f"ollama pull {MODEL}", 1800)
    base_env["OPENAI_COMPAT_REASONING_EFFORT"] = "none"
ok = wait_ready()
meta["server_ready"] = ok
meta["ready_s"] = round(time.time() - meta["t0"])
log("server ready:", ok, "after", meta["ready_s"], "s")
if not ok:
    (WORK / "phase3_meta.json").write_text(json.dumps(meta))
    log("SERVER FAILED; tail:", (WORK / "server.log").read_text(errors="replace")[-2000:])
    sys.exit(0)

dev = CFG["dev_sets"]
parts = [dev[i::WORKERS] for i in range(WORKERS)]
sg = SRC / "synthgen"
for i, sets in enumerate(parts):
    d = WORK / f"parts/w{i}"
    for sub in ("transcripts", "gold", "base_preds"):                 # base_preds: the config's own pass-1 outputs (P3-F argument pass)
        (d / sub).mkdir(parents=True, exist_ok=True)
        for s in sets:
            if (SRC / "data" / sub / f"{s}.json").exists():          # pooled corpora carry no gold (Phase 5)
                shutil.copy(SRC / "data" / sub / f"{s}.json", d / sub / f"{s}.json")
t_run = time.time()
for i, sets in enumerate(parts):
    cmd = [sys.executable, "run_ablation.py", "--data", str(WORK / f"parts/w{i}"), "--provider", "openai_compatible", "--model", MODEL,
           "--only", ",".join(CONFIGS), "--out", str(WORK / f"out/w{i}"), "--bootstrap", "0"]
    procs.append(subprocess.Popen(cmd, cwd=str(sg), env=base_env, stdout=open(WORK / f"worker{i}.log", "w"), stderr=subprocess.STDOUT))
for p in procs:
    p.wait()
meta["run_s"] = round(time.time() - t_run)
meta["worker_rc"] = [p.returncode for p in procs]
calls = tin = tout = 0
for f in (WORK / "out").glob("w*/*/llm_log.jsonl"):
    for line in f.read_text().splitlines():
        try:
            u = json.loads(line).get("usage") or {}
        except Exception:
            continue
        calls += 1
        tin += u.get("input") or 0
        tout += u.get("output") or 0
meta.update(calls=calls, input_tokens=tin, output_tokens=tout, out_tok_per_s=round(tout / max(meta["run_s"], 1), 1))
(WORK / "phase3_meta.json").write_text(json.dumps(meta))
log("DONE", json.dumps({k: v for k, v in meta.items() if k != "cfg"}))
srv.terminate()
