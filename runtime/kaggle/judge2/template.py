# JUDGE_SECONDARY job: granite4.2:8b answers the same per-link judge prompts as the Gemini judge, on two T4s (one Ollama server each).
# Input is a bundle of prompts only (synthetic text). Never prints environment variables.
import base64, gzip, json, os, pathlib, re, subprocess, sys, threading, time, urllib.request

WORK = pathlib.Path("/kaggle/working")
MODEL = "granite4.2:8b"
CTX = 8192
BUNDLE = "@@BUNDLE@@"
PORTS = [(11434, "0"), (11435, "1")]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def sh(c, timeout=900):
    r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=timeout)
    log("$", c[:80], "rc", r.returncode, r.stdout[-150:], r.stderr[-150:])


def api(port, path, body=None, timeout=900):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


items = [json.loads(l) for l in gzip.decompress(base64.b64decode(BUNDLE)).decode().splitlines()]
log("prompts", len(items))
sh("apt-get update -qq && apt-get install -y -qq zstd", 300)
sh("curl -fsSL https://ollama.com/install.sh | sh", 600)
procs = []
for port, gpu in PORTS:
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=gpu, OLLAMA_HOST=f"127.0.0.1:{port}", OLLAMA_CONTEXT_LENGTH=str(CTX),
               OLLAMA_MODELS="/tmp/ollama", OLLAMA_NUM_PARALLEL="1", OLLAMA_KEEP_ALIVE="60m")
    procs.append(subprocess.Popen(["ollama", "serve"], env=env, stdout=open(WORK / f"ollama_{port}.log", "w"), stderr=subprocess.STDOUT))
for port, _ in PORTS:
    for _ in range(90):
        try:
            api(port, "/api/version"); break
        except Exception:
            time.sleep(1)
sh(f"OLLAMA_HOST=127.0.0.1:11434 ollama pull {MODEL}", 1500)
tag = [x for x in api(11434, "/api/tags")["models"] if x["name"] == MODEL][0]
for port, _ in PORTS:
    api(port, "/api/generate", dict(model=MODEL, prompt="hi", stream=False, options=dict(num_predict=1, num_ctx=CTX)))
SYSTEM = "You are a strict annotation checker. Output ONLY valid JSON."
SYSTEM_ROLE = "You are a careful annotator of workplace meetings. Output ONLY valid JSON."
ROLES = ("proposal", "rationale", "evidence", "challenge", "reconsideration", "resolution")
out_path = WORK / "judge2.jsonl"
lock = threading.Lock()
done = [0]


def parse(t):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t.strip())
    try:
        return json.loads(t)
    except Exception:
        m = re.search(r"\{.*\}", t, re.S)
        return json.loads(m.group(0)) if m else {}


def worker(port, chunk):
    for it in chunk:
        t0 = time.time()
        try:
            role_mode = it.get("mode") == "role"
            r = api(port, "/api/chat", dict(model=MODEL, stream=False, think=False, messages=[
                dict(role="system", content=SYSTEM_ROLE if role_mode else SYSTEM), dict(role="user", content=it["prompt"])],
                options=dict(temperature=0, seed=7, num_ctx=CTX, num_predict=200)))
            raw = r["message"]["content"]
            j = parse(raw)
            v = str(j.get("role" if role_mode else "verdict", "")).lower().strip()
            allowed = ROLES if role_mode else ("yes", "partial", "no")
            rec = dict(item=it.get("item"), set_id=it["set_id"], link_id=it["link_id"], judge="granite", model=MODEL,
                       verdict=v if v in allowed else "invalid", reason=str(j.get("reason", raw))[:300],
                       secs=round(time.time() - t0, 2), out_tok=r.get("eval_count"))
        except Exception as e:
            rec = dict(item=it.get("item"), set_id=it["set_id"], link_id=it["link_id"], judge="granite", model=MODEL, verdict="error", reason=type(e).__name__)
        with lock:
            with out_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
            done[0] += 1
            if done[0] % 25 == 0:
                log(done[0], "judged")


t_all = time.time()
threads = [threading.Thread(target=worker, args=(PORTS[i][0], items[i::2])) for i in range(2)]
[t.start() for t in threads]
[t.join() for t in threads]
(WORK / "judge2_meta.json").write_text(json.dumps(dict(model=MODEL, digest=tag["digest"], n=len(items), wall_s=round(time.time() - t_all))))
log("DONE", len(items), "in", round(time.time() - t_all), "s")
for p in procs:
    p.terminate()
