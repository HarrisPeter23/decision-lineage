# CONTROL_WRITER job: mistral-nemo:12b writes the dialogue of the 6 control sets, one meeting at a time, on two T4s (one Ollama server each).
# Chunked generation (about 25 lines per call, events scheduled across the chunks), then the same QC as the Claude-written sets.
# Never prints environment variables.
import base64, io, json, os, pathlib, re, subprocess, sys, tarfile, threading, time, urllib.request

WORK = pathlib.Path("/kaggle/working")
SRC = pathlib.Path("/kaggle/work")
MODEL = "mistral-nemo:12b"
CTX = 16384
BUNDLE = "@@BUNDLE@@"
SERVERS = [dict(port=11434, gpu="0", sets=["set_01060", "set_01062", "set_01065"]),
           dict(port=11435, gpu="1", sets=["set_01061", "set_01064"])]   # set_01063 already passed in the first chunked run


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def sh(c, timeout=900):
    r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=timeout)
    log("$", c[:80], "rc", r.returncode, r.stdout[-200:], r.stderr[-200:])
    return r


def api(port, path, body=None, timeout=1800):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


tarfile.open(fileobj=io.BytesIO(base64.b64decode(BUNDLE))).extractall(SRC, filter="data")
sys.path.insert(0, str(SRC / "synthgen"))
import phase1_specs as ps                      # noqa: E402
ps.W = SRC / "w"
import phase1_status as st                     # noqa: E402
from arcs import sample_spec                   # noqa: E402
from text_to_tagged import parse               # noqa: E402

sh("apt-get update -qq && apt-get install -y -qq zstd", 300)
sh("curl -fsSL https://ollama.com/install.sh | sh", 600)
procs = []
for s in SERVERS:
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=s["gpu"], OLLAMA_HOST=f"127.0.0.1:{s['port']}", OLLAMA_CONTEXT_LENGTH=str(CTX),
               OLLAMA_MODELS="/tmp/ollama", OLLAMA_NUM_PARALLEL="1", OLLAMA_KEEP_ALIVE="60m")
    procs.append(subprocess.Popen(["ollama", "serve"], env=env, stdout=open(WORK / f"ollama_{s['port']}.log", "w"), stderr=subprocess.STDOUT))
for s in SERVERS:
    for _ in range(90):
        try:
            api(s["port"], "/api/version"); break
        except Exception:
            time.sleep(1)
sh(f"OLLAMA_HOST=127.0.0.1:11434 ollama pull {MODEL}", 1500)
tag = [x for x in api(11434, "/api/tags")["models"] if x["name"] == MODEL][0]
meta = dict(model=MODEL, digest=tag["digest"], ctx=CTX, servers=[s["port"] for s in SERVERS], mode="chunked v3c2: about 25 lines per call, stricter per-chunk validation")

prompt = (SRC / "v3.md").read_text(encoding="utf-8")
a = 'Save the meeting to the output path you were given, then reply only "saved". The file is plain text with one utterance per line:'
assert a in prompt
prompt = prompt.replace(a, "Reply with ONLY the dialogue lines you are asked for, nothing before them and nothing after them. The text is plain text with one utterance per line:")
prompt = prompt.replace("## Output", "## Output (this is the only thing you return)")
(WORK / "control").mkdir(exist_ok=True)
(SRC / "w" / "plans").mkdir(parents=True, exist_ok=True)
for p in (SRC / "control_plans").glob("*.txt"):
    (SRC / "w" / "plans" / p.name).write_bytes(p.read_bytes())
lock = threading.Lock()
runlog = []
NL = chr(10)


def clean(t):
    t = re.sub(r"^```[a-z]*\s*|\s*```$", "", t.strip()).replace("**", "")
    return [l.strip() for l in t.splitlines() if l.strip()]


def keep_dialogue(lines, names):
    # keep only 'Name: words' lines for cast members; drop stage directions and commentary the model adds
    out = []
    for l in lines:
        sp, sep, rest = l.partition(": ")
        if sep and sp.strip() in names and rest.strip() and not rest.lstrip().startswith("("):
            out.append(sp.strip() + ": " + rest.strip())
    return out


def event_lines(spec_text):
    return {m.group(1): m.group(0)[2:] for m in re.finditer(r"^- @([A-Z]\d+) .*$", spec_text, re.M)}


def chat(port, system, user, temp, seed, n_pred):
    r = api(port, "/api/chat", dict(model=MODEL, stream=False, messages=[dict(role="system", content=system), dict(role="user", content=user)],
                                    options=dict(temperature=temp, seed=seed, num_ctx=CTX, num_predict=n_pred)))
    return r["message"]["content"], r


IDRE = re.compile(r"(?<!@)\b[BD]\d{1,2}\b")


def stray_ids(lines):
    out = []
    for l in lines:
        body = re.sub(r"\s@[A-Z0-9,]+\s*$", "", l.partition(": ")[2])
        if IDRE.search(body):
            out.append(l)
    return out


def strip_ids(lines):
    # last resort after all retries: remove stray event ids like '(B4)' or 'B4' from the words (plumbing, disclosed in v3c2)
    res = []
    for l in lines:
        sp, _, rest = l.partition(": ")
        m = re.search(r"\s@[A-Z0-9,]+\s*$", rest)
        tag = m.group(0) if m else ""
        body = rest[:len(rest) - len(tag)]
        body = re.sub(r"\s*[\(\[]?(?<!@)\b[BD]\d{1,2}\b[\)\]]?[:,]?", "", body).strip()
        res.append(sp + ": " + body + tag)
    return res


def has_tag(lines, t):
    return any(l.endswith(" @" + t) or (" @" in l and t in re.findall(r"@([A-Z0-9,]+)\s*$", l)[0].split(",") if re.findall(r"@([A-Z0-9,]+)\s*$", l) else False) for l in lines)


def write_meeting(port, sid, m, spec, user, attempt):
    names = {c["name"] for c in spec["cast"]}
    target = max(70, min(110, spec["noise"][m - 1]["target_utterances"]))
    n_chunks = -(-target // 25)
    ev = event_lines(user)
    tags = list(ev)
    sched = {}
    for i, t in enumerate(tags):
        sched.setdefault(min(n_chunks - 1, (1 if n_chunks > 1 else 0) + (i * (n_chunks - 1)) // max(len(tags), 1)), []).append(t)
    lines, toks, secs = [], 0, 0.0
    for c in range(n_chunks):
        last = c == n_chunks - 1
        want = sched.get(c, [])
        n_lines = 25 if not last else max(12, target - len(lines))
        task = NL + NL + "## Dialogue so far in this meeting" + NL + (NL.join(lines) if lines else "(the meeting is just starting)")
        task += NL + NL + "## Your task now" + NL + "Write the NEXT " + str(n_lines) + " lines of the meeting, continuing naturally from the last line. Output only new lines in the form 'Name: words', one per line, no stage directions, no brackets, nothing else. Never write event names such as B4 or D2 inside the words; a tag appears only as the very last token of a key line, written like ' @B4'."
        if want:
            task += " In these lines the following must happen, in this order, and the key line for each must end with its tag (a space and the tag, like ' @B4'):" + NL + NL.join(ev[t] for t in want)
        task += NL + ("This is the end of the meeting, so wrap up the way these people would." if last else "Do not end the meeting yet.")
        got = []
        for k in range(5):
            t0 = time.time()
            text, r = chat(port, prompt, user + task, 0.6 + 0.08 * k, 1000 * m + 10 * c + k + attempt, 1500)
            secs += time.time() - t0
            toks += r.get("eval_count") or 0
            got = keep_dialogue(clean(text), names)
            if len(got) >= max(10, int(n_lines * 0.7)) and all(has_tag(got, t) for t in want) and not stray_ids(got):
                break
        got = strip_ids(got)
        lines += got
    return NL.join(lines), toks, secs


def work(server):
    port = server["port"]
    t_server = time.time()
    for sid in server["sets"]:
        plan = parse(SRC / "w" / "plans" / (sid + ".txt"))
        spec = sample_spec(int(sid.split("_")[1]), plan["arc_type"], sid)
        (WORK / "control" / sid).mkdir(exist_ok=True)
        (SRC / "w" / "meetings" / sid).mkdir(parents=True, exist_ok=True)
        for m in range(1, spec["n_meetings"] + 1):
            ps.build(sid, m)
            user = (SRC / "w" / "specs" / sid / ("m" + str(m) + ".md")).read_text(encoding="utf-8")
            best = None
            for attempt in range(1, 5):
                t0 = time.time()
                try:
                    text, toks, gen_s = write_meeting(port, sid, m, spec, user, attempt)
                    probs = st.qc(sid, m, spec, text)
                    info = dict(out_tok=toks, gen_s=round(gen_s, 1), tok_s=round(toks / max(gen_s, 1e-6), 1))
                except Exception as e:
                    text, probs, info = "", ["call failed: " + type(e).__name__ + ": " + str(e)[:80]], {}
                rec = dict(set=sid, m=m, attempt=attempt, port=port, secs=round(time.time() - t0, 1), problems=probs[:6], **info)
                with lock:
                    runlog.append(rec)
                    (WORK / "run_log.json").write_text(json.dumps(dict(meta=meta, runlog=runlog), indent=1))
                log(sid, "m" + str(m), "try" + str(attempt), len(probs), "problems", rec["secs"], "s")
                if best is None or len(probs) < best[0]:
                    best = (len(probs), text, probs)
                if not probs:
                    break
            for d in (WORK / "control" / sid, SRC / "w" / "meetings" / sid):
                (d / ("m" + str(m) + ".txt")).write_text(best[1] + NL, encoding="utf-8")
            (WORK / "control" / sid / ("m" + str(m) + ".status.json")).write_text(json.dumps(dict(problems=best[2], tries=attempt)))
    server["wall_s"] = round(time.time() - t_server)


# warm both models first so load time is not counted as writing time
for s in SERVERS:
    api(s["port"], "/api/generate", dict(model=MODEL, prompt="hi", stream=False, options=dict(num_predict=1, num_ctx=CTX)))
t_all = time.time()
threads = [threading.Thread(target=work, args=(s,)) for s in SERVERS]
[t.start() for t in threads]
[t.join() for t in threads]
meta["wall_s_total"] = round(time.time() - t_all)
meta["per_server"] = [dict(port=s["port"], wall_s=s.get("wall_s")) for s in SERVERS]
(WORK / "run_log.json").write_text(json.dumps(dict(meta=meta, runlog=runlog), indent=1))
log("DONE", meta)
for p in procs:
    p.terminate()
