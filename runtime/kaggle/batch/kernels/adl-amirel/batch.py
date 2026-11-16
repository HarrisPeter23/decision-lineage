# Generic batch LLM job: runs prompts through one Ollama model on two T4s (one server each) and returns the raw model output for every item.
# The bundle carries a config (model, ctx, system prompt, think flag, num_predict, temperature) and the items (id, prompt). Parsing is done on the laptop.
# Never prints environment variables; prompts must be synthetic or public-corpus text only.
import base64, gzip, json, os, pathlib, subprocess, threading, time, urllib.request

WORK = pathlib.Path("/kaggle/working")
BUNDLE = "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"
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
