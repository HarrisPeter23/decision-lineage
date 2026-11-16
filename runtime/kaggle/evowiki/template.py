# evowiki_style Build on Kaggle (Phase 6): builds the Wiki of each pooled DEV corpus meeting by meeting on SYSTEM_MODEL (Ollama qwen3:14b, thinking off,
# temperature 0), applying the FREEZE section 9 chunking rule to the extraction call. Corpora run in parallel threads; each corpus is sequential (W_t needs W_{t-1}).
# Inputs: only the corpora's meetings (opaque ids, dates, utterances). Never prints environment variables.
import base64, io, json, os, pathlib, subprocess, sys, tarfile, threading, time, traceback, urllib.request

WORK = pathlib.Path("/kaggle/working")
SRC = pathlib.Path("/kaggle/src_bundle")
BUNDLE = "@@BUNDLE@@"
raw = base64.b64decode(BUNDLE)
n = int.from_bytes(raw[:8], "big")
CFG = json.loads(raw[8:8 + n].decode())
tarfile.open(fileobj=io.BytesIO(raw[8 + n:]), mode="r:gz").extractall(SRC, filter="data")
OUT = WORK / "evowiki_out"
OUT.mkdir(parents=True, exist_ok=True)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def sh(c, timeout=1800):
    r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=timeout)
    log("$", c[:90], "rc", r.returncode, r.stderr[-300:] if r.returncode else "")


sh("apt-get update -qq && apt-get install -y -qq zstd", 300)
sh("curl -fsSL https://ollama.com/install.sh | sh", 600)
env = dict(os.environ, OLLAMA_CONTEXT_LENGTH=str(CFG["ctx"]), OLLAMA_MODELS="/tmp/ollama", OLLAMA_NUM_PARALLEL=str(CFG["workers"]), OLLAMA_KEEP_ALIVE="120m")
srv = subprocess.Popen(["ollama", "serve"], env=env, stdout=open(WORK / "ollama.log", "w"), stderr=subprocess.STDOUT)
time.sleep(8)
sh(f"ollama pull {CFG['model']}", 1800)
digest = [x["digest"] for x in json.load(urllib.request.urlopen("http://127.0.0.1:11434/api/tags"))["models"] if x["name"] == CFG["model"]]
log("digest", digest)
os.environ["OPENAI_COMPAT_BASE_URL"] = "http://127.0.0.1:11434/v1"
os.environ["OPENAI_COMPAT_REASONING_EFFORT"] = "none"
sys.path[:0] = [str(SRC), str(SRC / "synthgen")]
from llm import LLM                                     # noqa: E402
from baselines.evowiki_style import evowiki as E        # noqa: E402
import chunking as C                                    # noqa: E402

corpora = json.loads((SRC / "corpora.json").read_text())
todo = sorted(corpora, key=lambda c: -len(corpora[c]["meetings"]))
lock = threading.Lock()
meta = dict(model=CFG["model"], digest=digest, corpora={})


def worker():
    while True:
        with lock:
            if not todo:
                return
            name = todo.pop(0)
        t0 = time.time()
        d = OUT / name
        d.mkdir(exist_ok=True)
        llm = LLM("openai_compatible", CFG["model"], temperature=0, max_tokens=CFG["max_tokens"], cache_dir=str(d / "cache"), log_path=str(d / "llm_log.jsonl"))
        try:
            w, st = E.build(corpora[name], llm, chunk_windows=lambda m: C.make_windows(m["utterances"]), tag=name)
            (d / "wiki.json").write_text(json.dumps(w.to_json(), indent=1))
            st["seconds"] = round(time.time() - t0)
        except Exception:
            st = dict(error=traceback.format_exc()[-1500:])
        with lock:
            meta["corpora"][name] = st
            (OUT / "meta.json").write_text(json.dumps(meta, indent=1))
        log(name, json.dumps(st)[:300])


t_all = time.time()
ts = [threading.Thread(target=worker) for _ in range(CFG["workers"])]
[t.start() for t in ts]
[t.join() for t in ts]
meta["wall_s"] = round(time.time() - t_all)
(OUT / "meta.json").write_text(json.dumps(meta, indent=1))
log("DONE wall", meta["wall_s"])
srv.terminate()
