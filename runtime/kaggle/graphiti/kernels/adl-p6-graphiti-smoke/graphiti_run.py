# Graphiti baseline on Kaggle (Phase 6): ingests pooled DEV corpora (one episode per meeting) with graphiti-core 0.31.2 on SYSTEM_MODEL (Ollama qwen3:14b,
# thinking off) + Ollama all-minilm embeddings + the embedded Kuzu backend, then runs graphiti.search for each question and returns the facts.
# Inputs are only what a system sees: the corpora's plain-text meetings (opaque ids, dates) and the question texts. Never prints environment variables.
import asyncio, base64, gzip, json, os, pathlib, subprocess, sys, time, traceback, urllib.request
from datetime import datetime, timezone

WORK = pathlib.Path("/kaggle/working")
BUNDLE = "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"
B = json.loads(gzip.decompress(base64.b64decode(BUNDLE)).decode())
CFG = B["config"]
OUT = WORK / "graphiti_out"
OUT.mkdir(parents=True, exist_ok=True)
LOG = open(OUT / "run.log", "a")


def log(*a):
    s = time.strftime("%H:%M:%S") + " " + " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


def sh(c, timeout=1800):
    r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=timeout)
    log("$", c[:90], "rc", r.returncode, r.stderr[-300:] if r.returncode else "")
    return r


sh(f"pip install -q graphiti-core=={CFG['graphiti_version']} kuzu=={CFG['kuzu_version']} httpx", 1200)
sh("apt-get update -qq && apt-get install -y -qq zstd", 300)
sh("curl -fsSL https://ollama.com/install.sh | sh", 600)
env = dict(os.environ, OLLAMA_CONTEXT_LENGTH=str(CFG["ctx"]), OLLAMA_MODELS="/tmp/ollama", OLLAMA_NUM_PARALLEL="4", OLLAMA_KEEP_ALIVE="120m")
srv = subprocess.Popen(["ollama", "serve"], env=env, stdout=open(WORK / "ollama.log", "w"), stderr=subprocess.STDOUT)
time.sleep(8)
for m in (CFG["model"], CFG["embed_model"]):
    sh(f"ollama pull {m}", 1800)
tags = json.load(urllib.request.urlopen("http://127.0.0.1:11434/api/tags"))
digests = {x["name"]: x["digest"] for x in tags["models"]}
log("digests", digests)

os.environ["EMBEDDING_DIM"] = str(CFG["embed_dim"])
os.environ["GRAPHITI_TELEMETRY_ENABLED"] = "false"
os.environ.setdefault("OPENAI_API_KEY", "ollama-local")      # dummy; every client below points at the local Ollama server
from openai import AsyncOpenAI                                                       # noqa: E402
from graphiti_core import Graphiti                                                   # noqa: E402
from graphiti_core.driver.kuzu_driver import KuzuDriver                              # noqa: E402
from graphiti_core.llm_client.config import LLMConfig                                # noqa: E402
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient       # noqa: E402
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig       # noqa: E402
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient  # noqa: E402
from graphiti_core.nodes import EpisodeType                                          # noqa: E402

BASE = "http://127.0.0.1:11434/v1"
STATS = dict(llm_calls=0, llm_s=0.0, llm_errors=0)


def make_client():
    c = AsyncOpenAI(api_key="ollama-local", base_url=BASE, timeout=900)
    orig = c.chat.completions.create

    async def create(*a, **kw):                     # thinking off, as for every SYSTEM_MODEL call in this project
        kw.setdefault("reasoning_effort", "none")
        t0 = time.time()
        try:
            r = await orig(*a, **kw)
            return r
        except Exception:
            STATS["llm_errors"] += 1
            raise
        finally:
            STATS["llm_calls"] += 1
            STATS["llm_s"] += time.time() - t0
    c.chat.completions.create = create
    return c


async def run_corpus(name, corpus, questions):
    cfg = LLMConfig(api_key="ollama-local", model=CFG["model"], small_model=CFG["model"], base_url=BASE, temperature=0)
    g = Graphiti(graph_driver=KuzuDriver(db=str(WORK / f"kuzu_{name}")),
                 llm_client=OpenAIGenericClient(config=cfg, client=make_client(), max_tokens=CFG["max_tokens"]),
                 embedder=OpenAIEmbedder(OpenAIEmbedderConfig(api_key="ollama-local", base_url=BASE, embedding_model=CFG["embed_model"]),
                                         client=AsyncOpenAI(api_key="ollama-local", base_url=BASE)),
                 cross_encoder=OpenAIRerankerClient(config=cfg, client=make_client()))
    await g.build_indices_and_constraints()
    episodes = []
    for m in corpus:
        t0, c0 = time.time(), STATS["llm_calls"]
        rec = dict(meeting_id=m["meeting_id"], date=m["date"])
        try:
            res = await g.add_episode(name=m["meeting_id"], episode_body=m["text"], source=EpisodeType.message, source_description="team meeting transcript",
                                      reference_time=datetime.fromisoformat(m["date"]).replace(tzinfo=timezone.utc), group_id=name)
            rec.update(ok=True, episode_uuid=res.episode.uuid, n_nodes=len(res.nodes), n_edges=len(res.edges))
        except Exception as e:
            rec.update(ok=False, error=type(e).__name__ + ": " + str(e)[:300], tb=traceback.format_exc()[-1200:])
        rec.update(seconds=round(time.time() - t0, 1), llm_calls=STATS["llm_calls"] - c0)
        episodes.append(rec)
        log(name, m["meeting_id"], "ok" if rec["ok"] else "FAILED", rec["seconds"], "s", rec["llm_calls"], "calls", rec.get("error", ""))
        (OUT / f"episodes_{name}.json").write_text(json.dumps(episodes, indent=1))
    answers = []
    for q in questions:
        try:
            edges = await g.search(q["question"], group_ids=[name], num_results=CFG["k"])
            facts = [dict(uuid=e.uuid, name=e.name, fact=e.fact, episodes=list(e.episodes or []), valid_at=e.valid_at.isoformat() if e.valid_at else None,
                          invalid_at=e.invalid_at.isoformat() if e.invalid_at else None, expired_at=e.expired_at.isoformat() if e.expired_at else None)
                     for e in edges]
            answers.append(dict(qid=q["qid"], facts=facts))
        except Exception as e:
            answers.append(dict(qid=q["qid"], facts=[], error=type(e).__name__ + ": " + str(e)[:300]))
    (OUT / f"search_{name}.json").write_text(json.dumps(answers, indent=1))
    await g.close()


t_all = time.time()
for name, item in B["corpora"].items():
    if time.time() - t_all > CFG["time_budget_s"]:
        log("time budget reached; skipping", name)
        continue
    log("corpus", name, len(item["meetings"]), "meetings", len(item["questions"]), "questions")
    try:
        asyncio.run(run_corpus(name, item["meetings"], item["questions"]))
    except Exception:
        log("CORPUS FAILED", name, traceback.format_exc()[-2000:])
(OUT / "meta.json").write_text(json.dumps(dict(config=CFG, digests=digests, wall_s=round(time.time() - t_all), **STATS), indent=1))
log("DONE", json.dumps(STATS), "wall", round(time.time() - t_all))
srv.terminate()
