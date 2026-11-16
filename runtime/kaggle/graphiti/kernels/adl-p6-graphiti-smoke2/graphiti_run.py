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
