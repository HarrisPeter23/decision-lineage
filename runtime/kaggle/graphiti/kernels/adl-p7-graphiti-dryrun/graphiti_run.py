# Graphiti baseline on Kaggle (Phase 6): ingests pooled DEV corpora (one episode per meeting) with graphiti-core 0.31.2 on SYSTEM_MODEL (Ollama qwen3:14b,
# thinking off) + Ollama all-minilm embeddings + a local Neo4j Community server, then runs graphiti.search for each question and returns the facts.
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
