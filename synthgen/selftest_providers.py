"""selftest_providers.py - offline checks for the HTTP providers against a local fake server."""
import http.server
import json
import os
import shutil
import tempfile
import threading

import llm as L

hits = []


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        hits.append(body)
        code = 429 if len(hits) == 1 else 200
        out = json.dumps(dict(choices=[dict(message=dict(content="hello"))],
                              usage=dict(prompt_tokens=3, completion_tokens=1))).encode()
        self.send_response(code)
        if code == 429:
            self.send_header("Retry-After", "0")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ["OPENAI_COMPAT_BASE_URL"] = f"http://127.0.0.1:{srv.server_port}/v1"
tmp = tempfile.mkdtemp()
ok = 0


def check(name, cond):
    global ok
    print("PASS" if cond else "FAIL", name)
    ok += bool(cond)


m = L.LLM("openai_compatible", "fake", 0, 50, cache_dir=tmp + "/c", log_path=tmp + "/l.jsonl")
check("returns text after 429 retry", m.complete("s", "u", temperature=0) == "hello")
check("retried exactly once", len(hits) == 2)
check("temperature passed", hits[-1]["temperature"] == 0)
check("cache hit makes no call", m.complete("s", "u", temperature=0) == "hello" and len(hits) == 2)
rec = json.loads(open(tmp + "/l.jsonl").read().splitlines()[0])
check("tokens and provider logged", rec["usage"]["input"] == 3 and rec["provider"] == "openai_compatible")
os.environ.pop("GEMINI_API_KEY", None)
try:
    L.LLM("gemini_free", "x", cache_dir=tmp + "/c", log_path=tmp + "/l.jsonl").complete("s", "u")
    check("missing key raises", False)
except RuntimeError:
    check("missing key raises", True)
# OPENAI_COMPAT_EXTRA_BODY is merged into the request (vLLM chat_template_kwargs)
hits.clear()
os.environ["OPENAI_COMPAT_BASE_URL"] = f"http://127.0.0.1:{srv.server_port}/v1"
os.environ["OPENAI_COMPAT_EXTRA_BODY"] = '{"chat_template_kwargs": {"enable_thinking": false}}'
m3 = L.LLM("openai_compatible", "fake3", 0, 50, cache_dir=tmp + "/c3", log_path=tmp + "/l3.jsonl")
m3.complete("s", "u3", temperature=0)
check("extra body reaches the server", hits and hits[-1].get("chat_template_kwargs") == {"enable_thinking": False})
os.environ.pop("OPENAI_COMPAT_EXTRA_BODY")

# a daily-quota 429 must raise at once, not retry
hits.clear()


class Q(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        hits.append(1)
        out = b'{"error":{"details":[{"quotaId":"GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}}'
        self.send_response(429)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


q = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Q)
threading.Thread(target=q.serve_forever, daemon=True).start()
os.environ["OPENAI_COMPAT_BASE_URL"] = f"http://127.0.0.1:{q.server_port}/v1"
m2 = L.LLM("openai_compatible", "fake2", 0, 50, cache_dir=tmp + "/c2", log_path=tmp + "/l2.jsonl")
try:
    m2.complete("s", "u2", temperature=0)
    check("daily-quota 429 raises at once", False)
except L.DailyQuotaExceeded:
    check("daily-quota 429 raises at once", len(hits) == 1)
q.shutdown()
srv.shutdown()
shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{ok}/8 provider checks passed")
raise SystemExit(0 if ok == 8 else 1)
