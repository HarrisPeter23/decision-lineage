"""llm.py - thin LLM wrapper: disk cache, call log, providers, and an offline mock.

Providers: "openai_compatible" (local Ollama/vLLM), "gemini_free", "anthropic", "openai", "mock".
The anthropic/openai branches are not used in the zero-cost plan. The mock lets you test the whole
pipeline (generation -> assembly -> validation) with no network or API key.
The anthropic/openai branches have NOT been exercised against live APIs in
the environment this was written in; run a 1-set smoke test first.
"""
import hashlib
import json
import pathlib
import random
import re
import os
import time


def extract_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    try:
        return json.loads(t)
    except Exception:
        pass
    starts = [i for i in (t.find("{"), t.find("[")) if i != -1]
    if not starts:
        raise ValueError("no JSON found in model output")
    start = min(starts)
    end = max(t.rfind("}"), t.rfind("]"))
    return json.loads(t[start:end + 1])


def parse_spec_block(user):
    m = re.search(r"SPEC_JSON_BEGIN\s*(.*?)\s*SPEC_JSON_END", user, re.S)
    return json.loads(m.group(1))


class LLM:
    def __init__(self, provider="anthropic", model=None, temperature=0.8, max_tokens=8000,
                 cache_dir=".llm_cache", log_path="llm_log.jsonl"):
        self.provider, self.model = provider, model
        self.temperature, self.max_tokens = temperature, max_tokens
        self.cache = pathlib.Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.log_path = pathlib.Path(log_path)
        self._client = None

    def complete(self, system, user, kind="generic", temperature=None, tag=""):
        temp = self.temperature if temperature is None else temperature
        key = hashlib.sha256(json.dumps(
            [self.provider, self.model, system, user, temp, tag]).encode()).hexdigest()
        path = self.cache / f"{key}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
        t0 = time.time()
        text, usage = self._call(system, user, temp, kind)
        path.write_text(text, encoding="utf-8")
        with self.log_path.open("a") as f:
            f.write(json.dumps(dict(ts=round(time.time(), 1), kind=kind, tag=tag, provider=self.provider, model=self.model,
                                    seconds=round(time.time() - t0, 2), usage=usage,
                                    prompt_chars=len(system) + len(user), output_chars=len(text))) + "\n")
        return text

    def _call(self, system, user, temp, kind):
        if self.provider == "mock":
            return _mock(kind, user), {}
        if self.provider == "anthropic":
            import anthropic
            self._client = self._client or anthropic.Anthropic()
            r = self._client.messages.create(model=self.model, max_tokens=self.max_tokens,
                                             temperature=temp, system=system,
                                             messages=[{"role": "user", "content": user}])
            text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
            return text, dict(input=r.usage.input_tokens, output=r.usage.output_tokens)
        if self.provider == "openai":
            from openai import OpenAI
            self._client = self._client or OpenAI()
            r = self._client.chat.completions.create(
                model=self.model, temperature=temp,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
            u = r.usage
            return r.choices[0].message.content, dict(input=u.prompt_tokens, output=u.completion_tokens)
        if self.provider == "openai_compatible":
            base = os.environ.get("OPENAI_COMPAT_BASE_URL", "http://localhost:11434/v1").rstrip("/")
            body = dict(model=self.model, temperature=temp, max_tokens=self.max_tokens,
                        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
            if os.environ.get("OPENAI_COMPAT_REASONING_EFFORT"):
                body["reasoning_effort"] = os.environ["OPENAI_COMPAT_REASONING_EFFORT"]
            if os.environ.get("OPENAI_COMPAT_EXTRA_BODY"):          # e.g. {"chat_template_kwargs": {"enable_thinking": false}} for a vLLM server
                body.update(json.loads(os.environ["OPENAI_COMPAT_EXTRA_BODY"]))
            r = _post_with_backoff(f"{base}/chat/completions", {"Content-Type": "application/json"}, body)
            u = r.get("usage") or {}
            return r["choices"][0]["message"]["content"] or "", dict(
                input=u.get("prompt_tokens"), output=u.get("completion_tokens"))
        if self.provider == "gemini_free":
            key = os.environ.get("GEMINI_API_KEY")
            if not key:
                raise RuntimeError("GEMINI_API_KEY is not set")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            r = _post_with_backoff(url, {"Content-Type": "application/json", "x-goog-api-key": key}, dict(
                systemInstruction={"parts": [{"text": system}]},
                contents=[{"role": "user", "parts": [{"text": user}]}],
                generationConfig=dict(temperature=temp, maxOutputTokens=self.max_tokens)), timeout=90)   # normal latency is about 2 s; a hung request must not block for 10 min
            parts = r["candidates"][0].get("content", {}).get("parts", [])
            u = r.get("usageMetadata") or {}
            return "".join(x.get("text", "") for x in parts if not x.get("thought")), dict(
                input=u.get("promptTokenCount"), output=u.get("candidatesTokenCount"),
                thoughts=u.get("thoughtsTokenCount"))
        raise ValueError(f"unknown provider {self.provider}")


class DailyQuotaExceeded(RuntimeError):
    pass


def _post_with_backoff(url, headers, body, max_tries=8, base_delay=2.0, timeout=600):
    """POST JSON; retry per-minute 429s, 5xx and network errors with exponential backoff; a daily-quota 429 raises at once.
    Errors never include the headers (keys)."""
    import requests
    for attempt in range(max_tries):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as e:
            r = None
            if attempt == max_tries - 1:
                raise RuntimeError(f"network failure after {max_tries} tries: {type(e).__name__}") from None
            time.sleep(min(base_delay * 2 ** attempt, 300))
            continue
        if r.status_code == 429 and "PerDay" in r.text:
            raise DailyQuotaExceeded("daily request quota exhausted for this model; retry after the reset")   # never retry a daily limit
        if r.status_code == 429 or r.status_code >= 500:
            wait = float(r.headers.get("Retry-After") or base_delay * 2 ** attempt)
            time.sleep(min(wait, 300))
            continue
        if not r.ok:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
        return r.json()
    raise RuntimeError(f"gave up after {max_tries} tries (last HTTP {r.status_code})")


# ---------------------------------------------------------------- mock
FILLERS = ["Right, so, um, where were we.", "Yeah, no, that makes sense.", "Sorry, can you repeat that?",
           "I mean, it depends, honestly.", "Okay, moving on, um.", "Did anyone check the calendar for Friday?",
           "Let me, uh, pull that up.", "Sure, sure."]


def _mock(kind, user):
    spec = parse_spec_block(user)
    if kind == "planner":
        keys = spec["option_keys"]
        opts = {k: f"option {k.lower().replace('+', ' plus ')}" for k in keys}
        out = dict(topic=f"mock topic for {spec['domain']}", options=opts,
                   beats={b["id"]: f"{b['role']} content, item {chr(97 + i)}" for i, b in enumerate(spec["beats"])},
                   distractor=None)
        if spec.get("distractor"):
            out["distractor"] = dict(topic="mock side issue", option="mock side option",
                                     beats={b["id"]: f"{b['role']} side content, item {chr(97 + i)}"
                                            for i, b in enumerate(spec["distractor"]["beats"])})
        return json.dumps(out)
    if kind == "meeting":
        rng = random.Random(spec["m"] * 7919 + len(spec["beats"]))
        people = spec["names"]
        utts, realized = [], {}

        def add(sp, tx):
            utts.append(dict(speaker=sp, text=tx))
            return len(utts) - 1
        for _ in range(rng.randint(3, 6)):
            add(rng.choice(people), rng.choice(FILLERS))
        for b in spec["beats"]:
            if rng.random() < 0.6:
                add(rng.choice(people), rng.choice(FILLERS))
            if b["role"] == "resolution" and b["implicit"]:
                tx = "Fine. Let's do that."
            else:
                tx = f"Um, so, {b['gist']}"
                if b["role"] in ("proposal", "resolution"):
                    tx += f" - that is, {b['option_text']}."
            realized[b["id"]] = [add(b["speaker"], tx)]
        while len(utts) < 50:
            add(rng.choice(people), rng.choice(FILLERS))
        return json.dumps(dict(utterances=utts, realized=realized))
    if kind == "paraphrase":
        return json.dumps([f"Could you tell me: {q}" for q in spec["questions"]])
    if kind == "judge":
        return json.dumps(dict(verdict="yes", reason="mock"))
    raise ValueError(kind)
