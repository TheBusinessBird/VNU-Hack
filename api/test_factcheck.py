"""python api/test_factcheck.py - testează detectorul de erori logice cu Groq simulat (fără rețea)."""
import json, threading
import llm, fact_checker_api as fc

assert fc.MODELS == ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]

# --- cererea încape în limita Groq: prompt de sistem + antet + pasaje + răspuns < REQUEST_TOKEN_CAP < TPM ---
sys_tokens = int(len(fc.SYSTEM_FINDINGS("ro")) / fc.SYSTEM_CHARS_PER_TOKEN)
budget = fc.batch_char_budget(fc.SYSTEM_FINDINGS("ro"))
worst = sys_tokens + 160 + int(budget / fc.CHARS_PER_TOKEN) + fc.NUM_PREDICT_FINDINGS + fc.SAFETY_TOKENS
assert worst <= llm.REQUEST_TOKEN_CAP < llm.TPM_LIMIT, (worst, sys_tokens, budget)
assert sys_tokens < 2000, sys_tokens                      # promptul de sistem compact

# --- date: 6 articole, câte 2 declarații ---
def src(i): return {"id": f"s{i}", "url": f"https://x.ro/{i}", "title": f"Articol {i}", "domain": "x.ro", "date": f"2026-09-{10+i:02d}", "kind": "articol", "source_score": 50, "author": "-"}
texts = {i: [f"Am redus șomajul la zero în doar o lună, numărul {i}, și nimeni nu mai este fără job în România.",
             f"Opoziția a votat împotriva legii {i}, deci vrea ca oamenii să rămână săraci și să plece din țară."] for i in range(1, 7)}
scraped = {"sources": [src(i) for i in range(1, 7)],
           "speeches": [],
           "statements": [{"source_id": f"s{i}", "text": t, "context": "", "attributed_same_paragraph": True, "date": f"2026-09-{10+i:02d}"}
                          for i in range(1, 7) for t in texts[i]]}

calls, lock = [], threading.Lock()
def fake_chat(model, messages, **kw):
    with lock: calls.append((model, kw))
    assert kw["temperature"] == fc.SAMPLING["temperature"] and kw["max_tokens"] == fc.NUM_PREDICT_FINDINGS
    assert kw["schema"]["properties"]["findings"]["items"]["properties"]["passage_id"]["enum"]
    user = messages[1]["content"]
    if model == "openai/gpt-oss-20b" and "numărul 2" in user:
        raise llm.LLMError("Limita Groq pentru openai/gpt-oss-20b este atinsă")          # acest model cade: preia altul
    pid = "P1"
    quote = [t for t in sum(texts.values(), []) if t in user][0]
    f = [{"passage_id": pid, "quote": quote, "category": "implausible", "problem": "Rezultat extrem.", "reasoning": "Testul e.", "severity": "high",
          "confidence": "high", "how_to_verify": "INS."},
         {"passage_id": pid, "quote": "citat inventat care nu există în text", "category": "logical_fallacy", "problem": "x", "reasoning": "y",
          "severity": "low", "confidence": "low", "how_to_verify": "z"}]
    return {"content": json.dumps({"findings": f}), "finish_reason": "stop", "prompt_tokens": 800, "completion_tokens": 120, "model": model}

real = llm.chat; llm.chat = fake_chat
try:
    out = fc.fact_check("Ion Exemplu", scraped=scraped, language="ro", max_passages=20, max_pairs=0, contradictions=False)
finally:
    llm.chat = real

used = {m for m, _ in calls}
assert used == set(fc.MODELS), used                                      # toate cele 3 modele au primit lucru
assert out["summary"]["flags"] >= 1 and all(f["quote"] in sum(texts.values(), [])[0] + "".join(sum(texts.values(), [])) for f in out["findings"])
assert not any("inventat" in f["quote"] for f in out["findings"])        # citatele inventate sunt aruncate
assert out["stats"]["quotes_dropped_not_found"] >= 1
assert len(out["passages"]) == 12 and out["model"] == ", ".join(fc.MODELS)
# batch-ul care a eșuat pe gpt-oss-20b a fost refăcut pe alt model: nu lipsește nicio sursă
assert {f["source"]["id"] for f in out["findings"]} == {f"s{i}" for i in range(1, 7)}, {f["source"]["id"] for f in out["findings"]}

# --- fără cheie: eroare clară, nu așteptare ---
llm.api_key, real_key = (lambda: (_ for _ in ()).throw(llm.LLMError("Lipsește cheia Groq."))), llm.api_key
try: fc.preflight(); raise AssertionError("trebuia să eșueze")
except llm.LLMError: pass
print("factcheck tests passed")
