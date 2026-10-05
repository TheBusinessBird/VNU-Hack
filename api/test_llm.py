"""python api/test_llm.py - testează clientul Groq fără rețea (transport simulat)."""
import io, json, urllib.error
import llm

assert llm.parse_duration("7.5s") == 7.5 and llm.parse_duration("1m3.2s") == 63.2 and llm.parse_duration("250ms") == 0.25
assert llm.parse_duration("2h3m1s") == 7381 and llm.parse_duration("") is None and llm.parse_duration("abc") is None

# --- strictify: required complet, additionalProperties:false, fără limite nesuportate ---
s = llm.strictify({"type": "object", "properties": {"a": {"type": "integer", "minimum": 1, "maximum": 10},
                   "b": {"type": "array", "minItems": 1, "items": {"type": "object", "properties": {"c": {"type": "string"}}, "required": []}}},
                   "required": ["a"]})
assert s["required"] == ["a", "b"] and s["additionalProperties"] is False
assert "minimum" not in s["properties"]["a"] and "minItems" not in s["properties"]["b"]
assert s["properties"]["b"]["items"]["required"] == ["c"] and s["properties"]["b"]["items"]["additionalProperties"] is False

# --- transport simulat ---
class Resp:
    def __init__(self, data, headers=None): self._d, self.headers = json.dumps(data).encode(), headers or {}
    def read(self): return self._d
    def __enter__(self): return self
    def __exit__(self, *a): return False

def ok(content="{}", prompt=10, completion=5, **hdr):
    return Resp({"choices": [{"message": {"content": content}, "finish_reason": "stop"}], "usage": {"prompt_tokens": prompt, "completion_tokens": completion}}, hdr)

def http_error(code, body=None, headers=None):
    return urllib.error.HTTPError("u", code, "x", headers or {}, io.BytesIO(json.dumps({"error": body or {}}).encode()))

sleeps, sent = [], []
def install(*responses):
    queue = list(responses)
    def fake(req, timeout=None):
        sent.append(json.loads(req.data.decode()))
        r = queue.pop(0)
        if isinstance(r, Exception): raise r
        return r
    llm._urlopen = fake
    llm._sleep = lambda s: sleeps.append(s)
    llm._state.clear(); sleeps.clear(); sent.clear()

import os, tempfile
llm.api_key = lambda: "test-key"

# 1) cerere normală: model, temperatura 0, schema strictă, parametri de raționament pentru gpt-oss
install(ok('{"a": 1}', 20, 7, **{"x-ratelimit-remaining-tokens": "7000", "x-ratelimit-reset-tokens": "5s"}))
r = llm.chat("openai/gpt-oss-20b", [{"role": "user", "content": "salut"}], temperature=0, max_tokens=300,
             schema={"type": "object", "properties": {"a": {"type": "integer"}}, "required": ["a"]}, seed=3)
b = sent[0]
assert r["content"] == '{"a": 1}' and r["prompt_tokens"] == 20 and r["completion_tokens"] == 7 and r["finish_reason"] == "stop"
assert b["temperature"] == 0 and b["max_tokens"] == 300 and b["seed"] == 3 and b["reasoning_effort"] == "low" and b["include_reasoning"] is False
assert b["response_format"]["type"] == "json_schema" and b["response_format"]["json_schema"]["strict"] is True
assert b["response_format"]["json_schema"]["schema"]["additionalProperties"] is False

# 2) qwen: fără parametri de raționament; fără schemă: fără response_format
install(ok("text"))
llm.chat("qwen/qwen3.8-27b", [{"role": "user", "content": "x"}], max_tokens=100)
assert "reasoning_effort" not in sent[0] and "response_format" not in sent[0]

# 3) cerere prea mare pentru limita pe minut: refuzată local, fără apel de rețea
install()
try: llm.chat("openai/gpt-oss-20b", [{"role": "user", "content": "x" * 20000}], max_tokens=2000); raise AssertionError("trebuia să eșueze")
except llm.LLMError as e: assert "8000" in str(e) and not sent

# 4) 429 cu retry-after: așteaptă și reîncearcă
install(http_error(429, {"message": "rate"}, {"retry-after": "12"}), ok("după așteptare"))
assert llm.chat("openai/gpt-oss-20b", [{"role": "user", "content": "x"}], max_tokens=100)["content"] == "după așteptare"
assert sleeps and 12 <= sleeps[0] <= 13

# 5) 429 cu așteptare foarte lungă (limita zilnică): eroare clară
install(http_error(429, {"message": "daily"}, {"retry-after": "3600"}))
try: llm.chat("openai/gpt-oss-20b", [{"role": "user", "content": "x"}], max_tokens=100); raise AssertionError("trebuia să eșueze")
except llm.LLMError as e: assert "limita" in str(e).lower() and not sleeps

# 6) ritmare: dacă tokenii rămași în minutul curent nu ajung, așteaptă resetarea înainte să trimită
install(ok("1", **{"x-ratelimit-remaining-tokens": "500", "x-ratelimit-reset-tokens": "20s"}), ok("2"))
llm.chat("openai/gpt-oss-120b", [{"role": "user", "content": "x"}], max_tokens=800)
assert not sleeps
llm.chat("openai/gpt-oss-120b", [{"role": "user", "content": "x"}], max_tokens=800)
assert sleeps and 19 <= sleeps[0] <= 21, sleeps
# alt model = altă limită: nu așteaptă
install(ok("1", **{"x-ratelimit-remaining-tokens": "10", "x-ratelimit-reset-tokens": "30s"}), ok("2"))
llm.chat("openai/gpt-oss-120b", [{"role": "user", "content": "x"}], max_tokens=800)
llm.chat("qwen/qwen3.8-27b", [{"role": "user", "content": "x"}], max_tokens=800)
assert not sleeps

# 7) JSON invalid de la model: a doua încercare cu alt seed; 401 -> mesaj despre cheie; 500 -> reîncercare
install(http_error(400, {"code": "json_validate_failed", "message": "bad json"}), ok('{"a": 2}'))
assert llm.chat("openai/gpt-oss-20b", [{"role": "user", "content": "x"}], max_tokens=100, seed=1)["content"] == '{"a": 2}'
assert sent[1]["seed"] == 2
install(http_error(401, {"message": "invalid"}))
try: llm.chat("openai/gpt-oss-20b", [{"role": "user", "content": "x"}], max_tokens=100); raise AssertionError("trebuia să eșueze")
except llm.LLMError as e: assert "cheia" in str(e).lower()
install(http_error(503, {"message": "busy"}), ok("revenit"))
assert llm.chat("openai/gpt-oss-20b", [{"role": "user", "content": "x"}], max_tokens=100)["content"] == "revenit"

# 8) cheia lipsă
llm.api_key = lambda: (_ for _ in ()).throw(llm.LLMError("Lipsește cheia Groq."))
try: llm.chat("openai/gpt-oss-20b", [{"role": "user", "content": "x"}], max_tokens=100); raise AssertionError
except llm.LLMError as e: assert "cheia" in str(e).lower()
print("llm tests passed")

# --- fallback între modele ---
llm.api_key = lambda: "test-key"
install(http_error(400, {"code": "json_validate_failed", "message": "bad"}), http_error(400, {"code": "json_validate_failed", "message": "bad"}),
        http_error(400, {"code": "json_validate_failed", "message": "bad", "failed_generation": "{broken"}), ok("de la al doilea model"))
r = llm.chat("openai/gpt-oss-20b", [{"role": "user", "content": "x"}], max_tokens=100, fallbacks=["openai/gpt-oss-120b"])
assert r["content"] == "de la al doilea model" and r["model"] == "openai/gpt-oss-120b" and sent[-1]["model"] == "openai/gpt-oss-120b"
# fără fallback: eroarea de ieșire invalidă păstrează ce a generat modelul
install(*[http_error(400, {"code": "json_validate_failed", "message": "bad", "failed_generation": "{broken"}) for _ in range(3)])
try: llm.chat("openai/gpt-oss-20b", [{"role": "user", "content": "x"}], max_tokens=100); raise AssertionError("trebuia să eșueze")
except llm.LLMOutputError as e: assert e.failed == "{broken"
# limita zilnică a primului model -> trece pe următorul
install(http_error(429, {"message": "daily"}, {"retry-after": "7200"}), ok("din rezervă"))
assert llm.chat("openai/gpt-oss-20b", [{"role": "user", "content": "x"}], max_tokens=100, fallbacks=["qwen/qwen3.8-27b"])["content"] == "din rezervă"
# cheie invalidă -> nu încearcă alt model
install(http_error(401, {"message": "invalid"}))
try: llm.chat("openai/gpt-oss-20b", [{"role": "user", "content": "x"}], max_tokens=100, fallbacks=["qwen/qwen3.8-27b"]); raise AssertionError
except llm.LLMAuthError: assert len(sent) == 1
print("llm fallback tests passed")
