# Generic batch LLM job: runs prompts through one Ollama model on two T4s (one server each) and returns the raw model output for every item.
# The bundle carries a config (model, ctx, system prompt, think flag, num_predict, temperature) and the items (id, prompt). Parsing is done on the laptop.
# Never prints environment variables; prompts must be synthetic or public-corpus text only.
import base64, gzip, json, os, pathlib, subprocess, threading, time, urllib.request

WORK = pathlib.Path("/kaggle/working")
BUNDLE = "@@BUNDLE@@"
PORTS = [(11434, "0"), (11435, "1")]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def sh(c, timeout=900):
    r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=timeout)
    log("$", c[:80], "rc", r.returncode, r.stdout[-150:], r.stderr[-150:])


def api(port, path, body=None, timeout=1800):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request("http://127.0.0.1:" + str(port) + path, data=data, headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


blob = json.loads(gzip.decompress(base64.b64decode(BUNDLE)).decode())
CFG, ITEMS = blob["config"], blob["items"]
MODEL, CTX = CFG["model"], CFG["ctx"]
log("model", MODEL, "items", len(ITEMS))
sh("apt-get update -qq && apt-get install -y -qq zstd", 300)
sh("curl -fsSL https://ollama.com/install.sh | sh", 600)
procs = []
for port, gpu in PORTS:
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=gpu, OLLAMA_HOST="127.0.0.1:" + str(port), OLLAMA_CONTEXT_LENGTH=str(CTX),
               OLLAMA_MODELS="/tmp/ollama", OLLAMA_NUM_PARALLEL="1", OLLAMA_KEEP_ALIVE="60m")
    procs.append(subprocess.Popen(["ollama", "serve"], env=env, stdout=open(WORK / ("ollama_" + str(port) + ".log"), "w"), stderr=subprocess.STDOUT))
for port, _ in PORTS:
    for _ in range(90):
        try:
            api(port, "/api/version"); break
        except Exception:
            time.sleep(1)
sh("OLLAMA_HOST=127.0.0.1:11434 ollama pull " + MODEL, 1800)
tag = [x for x in api(11434, "/api/tags")["models"] if x["name"] == MODEL][0]
for port, _ in PORTS:
    api(port, "/api/generate", dict(model=MODEL, prompt="hi", stream=False, options=dict(num_predict=1, num_ctx=CTX)))
out_path = WORK / "batch_out.jsonl"
lock = threading.Lock()
done = [0]


def worker(port, chunk):
    for it in chunk:
        t0 = time.time()
        try:
            body = dict(model=MODEL, stream=False, messages=[dict(role="system", content=CFG.get("system", "")), dict(role="user", content=it["prompt"])],
                        options=dict(temperature=CFG.get("temperature", 0), seed=CFG.get("seed", 7), num_ctx=CTX, num_predict=CFG.get("num_predict", 300)))
            if CFG.get("think") is not None:
                body["think"] = CFG["think"]
            r = api(port, "/api/chat", body)
            rec = dict(id=it["id"], raw=r["message"]["content"], secs=round(time.time() - t0, 2), in_tok=r.get("prompt_eval_count"), out_tok=r.get("eval_count"))
        except Exception as e:
            rec = dict(id=it["id"], raw="", error=type(e).__name__ + ": " + str(e)[:100])
        with lock:
            with out_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
            done[0] += 1
            if done[0] % 25 == 0:
                log(done[0], "done")


t_all = time.time()
threads = [threading.Thread(target=worker, args=(PORTS[i][0], ITEMS[i::2])) for i in range(2)]
[t.start() for t in threads]
[t.join() for t in threads]
(WORK / "batch_meta.json").write_text(json.dumps(dict(model=MODEL, digest=tag["digest"], config={k: v for k, v in CFG.items() if k != "system"}, n=len(ITEMS), wall_s=round(time.time() - t_all))))
log("DONE", len(ITEMS), "in", round(time.time() - t_all), "s")
for p in procs:
    p.terminate()
