# CONTROL_WRITER job: mistral-nemo:12b writes the dialogue of the 6 control sets, one meeting at a time, on two T4s (one Ollama server each).
# Chunked generation (about 25 lines per call, events scheduled across the chunks), then the same QC as the Claude-written sets.
# Never prints environment variables.
import base64, io, json, os, pathlib, re, subprocess, sys, tarfile, threading, time, urllib.request

WORK = pathlib.Path("/kaggle/working")
SRC = pathlib.Path("/kaggle/work")
MODEL = "mistral-nemo:12b"
CTX = 16384
BUNDLE = "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"
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
