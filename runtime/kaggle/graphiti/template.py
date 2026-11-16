# Graphiti baseline on Kaggle (Phase 6): ingests pooled DEV corpora (one episode per meeting) with graphiti-core 0.31.2 on SYSTEM_MODEL (Ollama qwen3:14b,
# thinking off) + Ollama all-minilm embeddings + a local Neo4j Community server, then runs graphiti.search for each question and returns the facts.
# Inputs are only what a system sees: the corpora's plain-text meetings (opaque ids, dates) and the question texts. Never prints environment variables.
import asyncio, base64, gzip, json, os, pathlib, subprocess, sys, time, traceback, urllib.request
from datetime import datetime, timezone

WORK = pathlib.Path("/kaggle/working")
BUNDLE = "@@BUNDLE@@"
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


sh(f"pip install -q graphiti-core=={CFG['graphiti_version']} httpx", 1200)
sh("apt-get update -qq && apt-get install -y -qq zstd openjdk-17-jre-headless", 600)
# Graph backend: Neo4j Community (GPL-3.0), Graphiti's primary backend, run locally in this session only (the Kuzu driver of graphiti-core 0.31.2 fails, D-24)
NEO = f"/kaggle/neo4j-community-{CFG['neo4j_version']}"
sh(f"curl -fsSL https://dist.neo4j.org/neo4j-community-{CFG['neo4j_version']}-unix.tar.gz | tar -xz -C /kaggle", 900)
sh(f"{NEO}/bin/neo4j-admin dbms set-initial-password graphiti-local-pw", 300)
sh(f"{NEO}/bin/neo4j start", 300)
for _ in range(90):
    try:
        import socket
        socket.create_connection(("127.0.0.1", 7687), timeout=2).close()
        break
    except Exception:
        time.sleep(2)
time.sleep(10)
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
    g = Graphiti("bolt://127.0.0.1:7687", "neo4j", "graphiti-local-pw",
                 llm_client=OpenAIGenericClient(config=cfg, client=make_client(), max_tokens=CFG["max_tokens"]),
                 embedder=OpenAIEmbedder(OpenAIEmbedderConfig(api_key="ollama-local", base_url=BASE, embedding_model=CFG["embed_model"]),
                                         client=AsyncOpenAI(api_key="ollama-local", base_url=BASE)),
                 cross_encoder=OpenAIRerankerClient(config=cfg, client=make_client()))
    await g.build_indices_and_constraints()
    episodes = []
    for m, ep in ((m, ep) for m in corpus for ep in (m.get("episodes") or [dict(name=m["meeting_id"], text=m["text"])])):   # chunked episodes (FREEZE 18)
        t0, c0 = time.time(), STATS["llm_calls"]
        rec = dict(meeting_id=m["meeting_id"], episode=ep["name"], date=m["date"])
        try:
            res = await g.add_episode(name=ep["name"], episode_body=ep["text"], source=EpisodeType.message, source_description="team meeting transcript",
                                      reference_time=datetime.fromisoformat(m["date"]).replace(tzinfo=timezone.utc), group_id=name)
            rec.update(ok=True, episode_uuid=res.episode.uuid, n_nodes=len(res.nodes), n_edges=len(res.edges))
        except Exception as e:
            rec.update(ok=False, error=type(e).__name__ + ": " + str(e)[:300], tb=traceback.format_exc()[-1200:])
        rec.update(seconds=round(time.time() - t0, 1), llm_calls=STATS["llm_calls"] - c0)
        episodes.append(rec)
        log(name, ep["name"], "ok" if rec["ok"] else "FAILED", rec["seconds"], "s", rec["llm_calls"], "calls", rec.get("error", ""))
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


async def main():
    sem = asyncio.Semaphore(CFG.get("concurrency", 1))          # corpora in parallel; each corpus is ingested meeting by meeting, in time order

    async def one(name, item):
        async with sem:
            if time.time() - t_all > CFG["time_budget_s"]:
                log("time budget reached; skipping", name)
                return
            log("corpus", name, len(item["meetings"]), "meetings", len(item["questions"]), "questions")
            try:
                await run_corpus(name, item["meetings"], item["questions"])
            except Exception:
                log("CORPUS FAILED", name, traceback.format_exc()[-2000:])
    order = sorted(B["corpora"].items(), key=lambda kv: -len(kv[1]["meetings"]))   # longest first
    await asyncio.gather(*(one(n, it) for n, it in order))

asyncio.run(main())
(OUT / "meta.json").write_text(json.dumps(dict(config=CFG, digests=digests, wall_s=round(time.time() - t_all), **STATS), indent=1))
log("DONE", json.dumps(STATS), "wall", round(time.time() - t_all))
srv.terminate()
