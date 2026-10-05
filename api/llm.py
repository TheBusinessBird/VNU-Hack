"""llm - client pentru Groq (API compatibil OpenAI), folosit de toate modulele AI ale site-ului.

    import llm
    r = llm.chat("openai/gpt-oss-20b", [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}],
                 temperature=0, max_tokens=1200, schema={...})
    r["content"], r["prompt_tokens"], r["completion_tokens"], r["finish_reason"]

Cheia: variabila GROQ_API_KEY sau fișierul api/groq_key.txt (exclus din git).
Modele disponibile contului (verificate cu GET /openai/v1/models): openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.8-27b.
Planul gratuit: 8.000 tokeni/minut și 1.000 cereri/zi PE FIECARE MODEL. De aceea:
  - o cerere (prompt estimat + max_tokens) trebuie să încapă în LLM_TPM_LIMIT, altfel e refuzată de Groq (HTTP 413);
  - clientul ține socoteala tokenilor rămași (antetele x-ratelimit-*) și așteaptă resetarea înainte să trimită;
  - la HTTP 429 așteaptă `retry-after`; dacă așteptarea e foarte lungă (limita zilnică), aruncă o eroare clară.
"""
import json, os, re, threading, time, urllib.error, urllib.request

GROQ_URL = os.environ.get("GROQ_URL", "https://api.groq.com/openai/v1/chat/completions")
KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "groq_key.txt")
TPM_LIMIT = int(os.environ.get("LLM_TPM_LIMIT", "8000"))
REQUEST_TOKEN_CAP = int(os.environ.get("LLM_REQUEST_TOKEN_CAP", "7000"))    # ținta pentru prompt + max_tokens, sub limita pe minut
CHARS_PER_TOKEN = 2.6                                                        # conservator pentru română
MAX_WAIT_S = 75                                                              # cât așteptăm o resetare a limitei înainte să renunțăm
MAX_RETRIES = 6
REASONING_MODELS = ("openai/gpt-oss",)

_urlopen = urllib.request.urlopen     # înlocuite în teste
_sleep = time.sleep
_now = time.time


class LLMError(RuntimeError):
    pass


class LLMAuthError(LLMError):
    """Cheie lipsă sau invalidă: nu are rost să încercăm alt model."""


class LLMOutputError(LLMError):
    """Modelul a răspuns, dar rezultatul nu respectă schema cerută (HTTP 400 json_validate_failed). Nu e o eroare fatală:
    apelantul poate reîncerca, cu alt buget de tokeni sau cu alt model. `failed` păstrează ce a generat modelul."""

    def __init__(self, message, failed=""):
        super().__init__(message)
        self.failed = failed


def api_key():
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key and os.path.exists(KEY_FILE):
        key = open(KEY_FILE, encoding="utf-8").read().strip()
    if not key:
        raise LLMAuthError("Lipsește cheia Groq. Pune-o în api/groq_key.txt sau în variabila GROQ_API_KEY și repornește API-ul.")
    return key


def estimate_tokens(text):
    return int(len(text or "") / CHARS_PER_TOKEN) + 1


def chars_for_tokens(tokens):
    return int(max(0, tokens) * CHARS_PER_TOKEN)


def parse_duration(s):
    """'7.5s' / '1m3.2s' / '250ms' / '2h3m1s' -> secunde (None dacă nu se înțelege)."""
    if not s:
        return None
    total, found = 0.0, False
    for num, unit in re.findall(r"([\d.]+)(ms|h|m|s)", str(s)):
        found = True
        total += float(num) * {"ms": 0.001, "s": 1, "m": 60, "h": 3600}[unit]
    return total if found else None


_UNSUPPORTED_IN_STRICT = {"minimum", "maximum", "minItems", "maxItems", "minLength", "maxLength", "exclusiveMinimum", "exclusiveMaximum"}


def strictify(schema):
    """Schema pentru modul strict Groq: toate câmpurile 'required', additionalProperties:false pe fiecare obiect și fără
    cuvinte-cheie de limită, nesuportate (valorile se validează oricum în cod)."""
    if isinstance(schema, list):
        return [strictify(x) for x in schema]
    if not isinstance(schema, dict):
        return schema
    out = {k: strictify(v) for k, v in schema.items() if k not in _UNSUPPORTED_IN_STRICT}
    if out.get("type") == "object" and "properties" in out:
        out["required"] = list(out["properties"])
        out["additionalProperties"] = False
    return out


_state = {}
_state_lock = threading.Lock()


def _model_state(model):
    with _state_lock:
        return _state.setdefault(model, {"lock": threading.Lock(), "remaining": None, "reset_at": 0.0})


def _update_limits(st, headers):
    try:
        rem = headers.get("x-ratelimit-remaining-tokens")
        reset = parse_duration(headers.get("x-ratelimit-reset-tokens"))
        if rem is not None:
            st["remaining"] = int(float(rem))
            st["reset_at"] = _now() + (reset if reset is not None else 60)
    except (TypeError, ValueError):
        pass


def _retry_after(headers):
    """Antetul retry-after: secunde ('12') sau durată ('1m3s'); 20 s dacă lipsește."""
    raw = (headers.get("retry-after") or "").strip()
    try:
        return float(raw)
    except ValueError:
        return parse_duration(raw) or 20


def chat(model, messages, temperature=0, max_tokens=1000, schema=None, seed=None, reasoning_effort="low", timeout=120, fallbacks=()):
    """O cerere de completare. Întoarce {content, finish_reason, prompt_tokens, completion_tokens, model}.
    Dacă modelul eșuează (ieșire care nu respectă schema, limită atinsă, eroare de server), încearcă pe rând modelele din `fallbacks`;
    cheia lipsă sau invalidă oprește totul imediat."""
    last = None
    for m in [model, *[f for f in fallbacks if f != model]]:
        try:
            return _chat_one(m, messages, temperature, max_tokens, schema, seed, reasoning_effort, timeout)
        except LLMAuthError:
            raise
        except LLMError as e:
            last = e
    raise last


def _chat_one(model, messages, temperature, max_tokens, schema, seed, reasoning_effort, timeout):
    key = api_key()
    prompt_est = estimate_tokens(json.dumps(messages, ensure_ascii=False))
    need = prompt_est + max_tokens
    if need > TPM_LIMIT:
        raise LLMError(f"Cererea (~{need} tokeni: prompt + răspuns) depășește limita de {TPM_LIMIT} tokeni/minut a modelului {model}.")

    body = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    if seed is not None:
        body["seed"] = seed
    if model.startswith(REASONING_MODELS):
        body["reasoning_effort"] = reasoning_effort
        body["include_reasoning"] = False
    if schema is not None:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "raspuns", "strict": True, "schema": strictify(schema)}}
    payload = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + key, "User-Agent": "politics-mvp/1.0"}

    st = _model_state(model)
    with st["lock"]:                                  # o singură cerere pe model odată: limita pe minut e comună
        net_errors = 0
        for attempt in range(MAX_RETRIES + 1):
            wait = st["reset_at"] - _now()
            if st["remaining"] is not None and st["remaining"] < need and wait > 0:
                _sleep(min(wait + 0.3, MAX_WAIT_S))   # așteptăm resetarea ferestrei de un minut
                st["remaining"] = None
            req = urllib.request.Request(GROQ_URL, data=payload, headers=headers)
            try:
                with _urlopen(req, timeout=timeout) as r:
                    data = json.loads(r.read().decode("utf-8"))
                    _update_limits(st, r.headers)
                choice = data["choices"][0]
                usage = data.get("usage") or {}
                return {"content": (choice.get("message") or {}).get("content") or "", "finish_reason": choice.get("finish_reason"),
                        "prompt_tokens": usage.get("prompt_tokens", 0), "completion_tokens": usage.get("completion_tokens", 0), "model": model}
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")
                try:
                    err = json.loads(detail).get("error", {})
                except ValueError:
                    err = {}
                if e.code == 429:
                    retry = _retry_after(e.headers)
                    if retry > MAX_WAIT_S or attempt == MAX_RETRIES:
                        raise LLMError(f"Limita Groq pentru {model} este atinsă (de obicei cea zilnică); reîncearcă peste ~{int(retry // 60) + 1} min. {err.get('message', '')[:160]}")
                    _sleep(retry + 0.5)
                    st["remaining"] = None
                    continue
                if e.code == 413:
                    raise LLMError(f"Cerere prea mare pentru limita Groq a modelului {model}: {err.get('message', detail)[:200]}")
                if e.code in (401, 403):
                    raise LLMAuthError("Cheia Groq este invalidă sau nu are acces la acest model.")
                if e.code == 400 and err.get("code") == "json_validate_failed":
                    if attempt < 2:
                        body["seed"] = (body.get("seed") or 0) + 1                  # modelul a produs JSON invalid: alte încercări, cu alt seed
                        payload = json.dumps(body).encode("utf-8")
                        continue
                    raise LLMOutputError(f"{model} a întors un răspuns care nu respectă schema: {err.get('message', '')[:160]}", err.get("failed_generation") or "")
                if e.code >= 500 and attempt < MAX_RETRIES:
                    _sleep(min(2 ** attempt, 10))
                    continue
                raise LLMError(f"Groq a răspuns {e.code}: {err.get('message', detail)[:240]}")
            except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
                net_errors += 1
                if net_errors > 3:
                    raise LLMError(f"Nu mă pot conecta la Groq ({e}).")
                _sleep(2 * net_errors)
        raise LLMError("Groq nu a răspuns după mai multe încercări.")
