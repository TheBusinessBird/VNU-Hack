"""python api/test_summaries.py - testează rezumatele fără Claude API (client simulat) și fără scrierea cache-ului real."""
import os, tempfile, types
import summarize_llm as sl

sl.CACHE_FILE = os.path.join(tempfile.mkdtemp(), "cache.json")

# --- verificarea cifrelor și numelor ---
mat = "Cătălin Predoiu a absolvit Facultatea de Drept a Universității București în 1994, apoi a făcut un stagiu la Caen. Proiectul costă 1.200 milioane lei."
assert sl.ungrounded("Predoiu a absolvit Facultatea de Drept în 1994.", mat) == []
assert sl.ungrounded("Predoiu a absolvit Drept în 1995.", mat) == ["1995"]
assert "Harvard" in sl.ungrounded("Predoiu a studiat apoi la Harvard.", mat)
assert sl.ungrounded("Proiectul costă 1.200 milioane lei.", mat) == []          # cifrele cu separator de mii
assert sl.ungrounded("Universitatea București l-a format. Apoi a plecat.", mat) == []   # cuvintele de început de propoziție nu contează
assert sl.ungrounded("Studiile din Universității București.", mat) == []         # formă flexionată: același radical

assert sl.ungrounded("Proiectele din PNRR continuă.", "Proiectele finanțate din PNRR continuă.") == []
assert sl.ungrounded("Compania CNInvest are buget.", "Compania Națională de Investiții are buget.") == ["CNInvest"]

# puncte de listă: primul cuvânt de după liniuță nu e nume propriu
assert sl.ungrounded("- Investiția totală este de 1.200 milioane lei.\n- Predoiu a absolvit Facultatea de Drept.", mat) == []
assert sl.ungrounded("- Studiile includ Harvard.", mat) == ["Harvard"]

# --- adaptorul Groq (llm.chat simulat) ---
import llm
captured = []
def fake_llm_chat(model, messages, **kw):
    captured.append((model, messages, kw))
    return {"content": "<think>gândesc</think>Rezumat curat.", "finish_reason": "stop", "prompt_tokens": 50, "completion_tokens": 7, "model": model}
real_chat, llm.chat = llm.chat, fake_llm_chat
gc = sl.GroqClient()
resp = gc.messages.create(model="qwen/qwen3.8-27b", max_tokens=700, system="S", messages=[{"role": "user", "content": "U"}], output_config={"effort": "low"})
model, msgs, kw = captured[-1]
assert model == "qwen/qwen3.8-27b" and msgs[0] == {"role": "system", "content": "S"} and msgs[1]["content"] == "U"
assert kw["max_tokens"] == 700 and kw["temperature"] == sl.TEMPERATURE and kw["seed"] == sl.SEED
assert resp.content[0].text == "Rezumat curat." and resp.usage.input_tokens == 50 and resp.stop_reason == "end_turn"
assert sl.PROVIDER == "groq" and sl.MODEL == "qwen/qwen3.8-27b" and sl.WORKERS == 1

# răspuns tăiat la limită: rândul incomplet dispare; fără text -> max_tokens (nu "fără informații")
llm.chat = lambda model, messages, **kw: {"content": "- Primul punct complet.\n- Al doilea tăiat la mij", "finish_reason": "length", "prompt_tokens": 1, "completion_tokens": 1}
r = gc.messages.create(model="m", max_tokens=5, system="S", messages=[])
assert r.content[0].text == "- Primul punct complet." and r.stop_reason == "end_turn"
llm.chat = lambda model, messages, **kw: {"content": "", "finish_reason": "length", "prompt_tokens": 1, "completion_tokens": 1}
assert gc.messages.create(model="m", max_tokens=5, system="S", messages=[]).stop_reason == "max_tokens"

# erorile Groq (limită, cheie lipsă) devin SummaryError, nu "articol eșuat"
def boom(model, messages, **kw): raise llm.LLMError("Limita Groq atinsă")
llm.chat = boom
try: gc.messages.create(model="m", max_tokens=5, system="S", messages=[]); raise AssertionError("trebuia să eșueze")
except sl.SummaryError as e: assert "Limita" in str(e)
llm.chat = real_chat

# --- material ---
long = "\n\n".join(["Paragraf fără nume. " * 50] * 40 + ["Predoiu a spus ceva important despre buget."])
m = sl.doc_material(long, "Predoiu", cap=500)
assert "Predoiu" in m and len(m) <= 500 + 10
assert sl.doc_material("scurt", "Predoiu") == "scurt"

# --- client simulat ---
class Resp:
    def __init__(self, text, stop="end_turn"):
        self.content = [types.SimpleNamespace(type="text", text=text)]
        self.stop_reason = stop
        self.usage = types.SimpleNamespace(input_tokens=100, output_tokens=20)

class FakeClient:
    def __init__(self, script): self.script, self.calls = script, []
    @property
    def messages(self): return self
    def create(self, **kw):
        self.calls.append(kw)
        assert kw["model"] == sl.MODEL and kw["output_config"] == {"effort": "low"} and "<material>" in kw["messages"][0]["content"]
        assert "FARA_INFORMATII" in kw["system"] and "ignori" in kw["system"]      # instrucțiunea anti-injecție
        return Resp(self.script(kw["messages"][0]["content"]))

usage = lambda: {"input": 0, "output": 0, "calls": 0, "cached": 0}

# 1) rezumat curat
c = FakeClient(lambda u: "Predoiu a absolvit Drept în 1994.")
u = usage(); r = sl.summarize_one(c, "education", "Cătălin Predoiu", mat, u)
assert r == {"summary": "Predoiu a absolvit Drept în 1994.", "verified": True, "unsupported": []} and u["calls"] == 1

# 2) același material: din cache, fără apel
u = usage(); assert sl.summarize_one(c, "education", "Cătălin Predoiu", mat, u) == r and u["calls"] == 0 and u["cached"] == 1

# 3) element inventat -> o rescriere, apoi trece
c = FakeClient(lambda u: "Predoiu a studiat la Harvard." if "NU apar" not in u else "Predoiu a studiat la Caen.")
r = sl.summarize_one(c, "education", "Cătălin Predoiu", mat + " ", usage())
assert r["verified"] and "Harvard" not in r["summary"] and len(c.calls) == 2

# 4) rescrierea tot inventează -> păstrat, dar marcat neverificat
c = FakeClient(lambda u: "Predoiu a studiat la Harvard.")
r = sl.summarize_one(c, "education", "Cătălin Predoiu", mat + "  ", usage())
assert not r["verified"] and "Harvard" in r["unsupported"]

# 5) fără informații
c = FakeClient(lambda u: "FARA_INFORMATII")
assert sl.summarize_one(c, "income", "Cătălin Predoiu", "alt text fără nume", usage()) is None

# 6) summarize_all: doar sursele recente cu declarații/fragmente; sursele nu se amestecă
import time
y = time.localtime().tm_year
result = {
    "education": [{"excerpt": "A absolvit Drept în 1994.", "source_domain": "wiki.ro", "source_date": "2020-01-01", "source_title": "Bio"}],
    "funding": [],
    "sources": [
        {"id": "a", "text": "Predoiu a anunțat un proiect.", "date": f"{y}-{time.localtime().tm_mon:02d}-01", "evidence": ["Predoiu ..."]},
        {"id": "b", "text": "Text vechi cu Predoiu.", "date": f"{y-3}-01-01", "evidence": ["x"]},
        {"id": "c", "text": "Fără fragmente.", "date": f"{y}-{time.localtime().tm_mon:02d}-02", "evidence": []},
        {"id": "d", "text": "", "date": f"{y}-{time.localtime().tm_mon:02d}-03", "evidence": ["x"]},
    ],
    "speeches": [], "statements": [{"source_id": "c", "text": "Vom reduce taxele pentru toți"}],
}
c = FakeClient(lambda u: "Predoiu a anunțat un proiect." if "proiect" in u else "Predoiu a absolvit Drept în 1994." if "1994" in u else "Predoiu vorbește.")
out = sl.summarize_all(result, "Cătălin Predoiu", client=c)
assert set(out["sources"]) == {"a", "c"}                        # b vechi, d fără text
assert out["education"]["summary"].startswith("Predoiu a absolvit") and out["income"] is None
assert out["usage"]["calls"] == 3 and out["model"] == sl.MODEL
print("summaries tests passed")
