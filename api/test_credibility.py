"""python api/test_credibility.py - testează scorul de credibilitate fără rețea (model simulat)."""
import json
import credibility_llm as cl
import llm

# --- formula: x*0.2 + y*0.2 + z*0.4 + w*0.2 ---
assert cl.credibility(7, 7, 7, 7) == 7.0
assert cl.credibility(10, 10, 10, 10) == 10.0 and cl.credibility(1, 1, 1, 1) == 1.0
assert cl.credibility(5, 6, 9, 4) == round(5 * .2 + 6 * .2 + 9 * .4 + 4 * .2, 1) == 6.6
assert abs(sum(cl.WEIGHTS.values()) - 1.0) < 1e-9 and cl.WEIGHTS["history"] == 0.4
assert cl.OPTIONS["temperature"] == 0                        # cerință: temperatura 0
assert cl._clamp(15) == 10 and cl._clamp(0) == 1 and cl._clamp("7.4") == 7 and cl._clamp(None) is None and cl._clamp("x") is None

# --- bugetul cererii: prompt + răspuns încap sub limita Groq de tokeni pe minut ---
for system, predict in ((cl.SYSTEM_HISTORY, cl.PREDICT_HISTORY), (cl.SYSTEM_ARTICLES, cl.PREDICT_BATCH)):
    b = cl.data_budget_chars(system, predict)
    tokens_used = int(len(system) / cl.SYSTEM_CHARS_PER_TOKEN) + predict + cl.SAFETY_TOKENS + int(b / cl.CHARS_PER_TOKEN)
    assert tokens_used <= llm.REQUEST_TOKEN_CAP < llm.TPM_LIMIT, (tokens_used, llm.REQUEST_TOKEN_CAP)
assert cl.MODEL == "openai/gpt-oss-120b"
lines, dropped = cl.fit(["a" * 100] * 10, 450)
assert len(lines) == 4 and dropped == 6

# --- date: 70 de semnalări, 12 articole ---
def src(i): return {"id": f"s{i}", "title": f"Articol {i}", "domain": "x.ro", "date": f"2026-09-{i:02d}", "url": f"https://x.ro/{i}"}
findings = [{"category": "likely_false" if i % 2 else "logical_fallacy", "severity": "high" if i < 10 else "low", "confidence": "medium",
             "quote": "citat " + "lung " * 80, "problem": "problemă " * 50, "source": src(1 + i % 12)} for i in range(70)]
fc = {"findings": findings, "passages": [{"kind": "quote", "text": f"declarație {i} " * 20, "source": src(1 + i % 12)} for i in range(36)]}

seen = {"history_prompt": None, "calls": []}
def fake_chat(system, user, schema, predict, model=None):
    assert model == cl.MODEL
    seen["calls"].append((predict, len(user)))
    if "history" in schema["properties"]:
        seen["history_prompt"] = user
        return {"obj": {"reason": "Mai multe semnalări grave repetate.", "history": 4}, "done_reason": "stop", "prompt_tokens": 100, "output_tokens": 50}
    ids = schema["properties"]["items"]["items"]["properties"]["id"]["enum"]
    items = [{"id": i, "feasibility": 8, "precision": 6, "manipulation": 5} for i in ids]
    items.append({"id": "A99", "feasibility": 1, "precision": 1, "manipulation": 1})            # id inexistent: ignorat
    return {"obj": {"items": items}, "done_reason": "stop", "prompt_tokens": 100, "output_tokens": 50}

out = cl.score_credibility(fc, "Ion Exemplu", chat=fake_chat)
prompt = seen["history_prompt"]
assert prompt.count("[F") <= cl.MAX_FINDINGS and "[F51]" not in prompt                          # cel mult 50 de erori în prompt
assert out["basis"]["findings_total"] == 70 and out["basis"]["findings_used"] <= 50 and out["basis"]["findings_cap"] == 50
assert len(prompt) <= cl.data_budget_chars(cl.SYSTEM_HISTORY, cl.PREDICT_HISTORY) + 900        # + antet
assert out["components"] == {"feasibility": 8.0, "precision": 6.0, "history": 4, "manipulation": 5.0}
assert out["score"] == cl.credibility(8, 6, 4, 5) == 5.4
assert out["basis"]["articles"] == 12 and out["basis"]["articles_scored"] == 12
assert len(seen["calls"]) == 1 + 2                                                              # istoric + 2 loturi (8 + 4 articole)
assert all(v["history"] == 4 and v["score"] == 5.4 for v in out["articles"].values())          # scorul articolului folosește z-ul politicianului
assert out["run"]["temperature"] == 0 and out["run"]["calls"] == 3 and len(out["top_flags"]) == 5
a1 = out["articles"]["s1"]
assert a1["flags"] == len([f for f in findings if f["source"]["id"] == "s1"]) and a1["statements"] == 3

# --- fără semnalări, dar cu declarații: se calculează oricum (un istoric curat contează) ---
clean = {"findings": [], "passages": fc["passages"][:5]}
out2 = cl.score_credibility(clean, "Ion Exemplu", chat=fake_chat)
assert out2["basis"]["findings_used"] == 0 and "(nicio semnalare)" in seen["history_prompt"]

# --- fără declarații: eroare clară ---
try: cl.score_credibility({"findings": [], "passages": []}, "Ion Exemplu", chat=fake_chat); raise AssertionError("trebuia să eșueze")
except cl.CredibilityError as e: assert "erori logice" in str(e)

# --- răspuns invalid de la model ---
try: cl.score_credibility(fc, "Ion Exemplu", chat=lambda *a, **k: {"obj": None}); raise AssertionError("trebuia să eșueze")
except cl.CredibilityError: pass
def partial(system, user, schema, predict, **kw):
    if "history" in schema["properties"]: return fake_chat(system, user, schema, predict, **kw)
    return {"obj": {"items": [{"id": "A1", "feasibility": 99, "precision": 0, "manipulation": "x"}, {"id": "A2", "feasibility": 7, "precision": 7, "manipulation": 7}]}}
out3 = cl.score_credibility(fc, "Ion Exemplu", chat=partial)
assert out3["basis"]["articles_scored"] == 2 and cl._clamp(99) == 10                           # A1 are "manipulation": "x" -> sărit; A2 ok
print("credibility tests passed")
