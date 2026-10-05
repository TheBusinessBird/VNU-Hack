"""python api/test_orientation.py - testează logica fără rețea (model simulat)."""
import json, re, orientation_llm as ol

for a in ol.AXES: re.compile(a[4], re.I)       # toate regex-urile compilează
assert len(ol.AXES) == 10 and ol.MODEL == "openai/gpt-oss-20b"

desc = "Dan a spus că „vom accelera descentralizarea fondurilor către primării și vom reduce cheltuielile statului central”. " * 3
result = {"sources": [
    {"id": "a", "url": "https://cdep.ro/x", "domain": "cdep.ro", "title": "Discurs", "date": "2026-09-01", "author": None,
     "text": desc + "\n\nParagraf fără relevanță, despre vreme și alte lucruri care nu îl privesc pe nimeni, în nicio axă." * 2},
    {"id": "b", "url": "https://ziar.ro/y", "domain": "ziar.ro", "title": "Articol", "date": "2026-09-02", "author": "Ana Pop",
     "text": "Bogdan Ivan acuză guvernul de lipsa descentralizării. Nimic despre candidat aici, doar alt om cu numele Bogdan.\n\n" + desc},
    {"id": "c", "url": "https://x.ro/z", "domain": "x.ro", "title": "Fără text", "date": "", "author": None, "text": ""}]}

structure = next(a for a in ol.AXES if a[0] == "structure")
ctx, refs = ol.build_context(result, "dan", 4000, re.compile(structure[4], re.I))
assert "[S1] cdep.ro" in ctx                       # sursa oficială e prima
assert "vreme" not in ctx                          # paragraful irelevant e omis
assert "Bogdan Ivan acuză" not in ctx              # "Bogdan" nu e "Dan"
assert set(refs) == {"S1", "S2"} and refs["S2"]["author"] == "Ana Pop"
assert len(ctx) <= 4000 + 400

# o axă fără fragmente relevante nu apelează modelul
labor = next(a for a in ol.AXES if a[0] == "labor")
assert ol.build_context(result, "dan", 4000, re.compile(labor[4], re.I)) == ("", {})

quote_ok = "vom accelera descentralizarea fondurilor către primării"
calls = []
def fake_chat(messages, schema, model=None, **kw):
    calls.append(messages[1]["content"])
    assert list(schema["properties"])[:3] == ["evidence", "rationale", "pole"]   # dovezile înaintea verdictului
    assert "Politician: Nicusor Dan" in messages[1]["content"] and "EXCERPTS" in messages[1]["content"]
    if "Centralism" in messages[1]["content"]:     # axa 'structure': citat real + unul inventat + unul cu sursă inexistentă
        r = {"evidence": [{"source": "S1", "quote": quote_ok}, {"source": "S1", "quote": "citat inventat de model"}, {"source": "S9", "quote": quote_ok}],
             "rationale": "se apropie de polul Descentralizare", "pole": "right", "strength": "clear", "confidence": "high"}
    elif "Free Market" in messages[1]["content"]:  # verdict fără niciun citat verificabil
        r = {"evidence": [{"source": "S1", "quote": "alt citat inventat"}], "rationale": "x", "pole": "left", "strength": "slight", "confidence": "high"}
    else:
        return {"message": {"content": "nu e json"}, "prompt_eval_count": 10, "eval_count": 1}
    return {"message": {"content": json.dumps(r)}, "prompt_eval_count": 100, "eval_count": 20}

out = ol.score_orientation(result, "Nicusor Dan", chat=fake_chat)
ax = {a["id"]: a for a in out["axes"]}
assert [a["id"] for a in out["axes"]] == ol.AXIS_IDS
assert ax["structure"]["score"] == 5 and len(ax["structure"]["evidence"]) == 1       # right+clear=5; doar citatul verificat rămâne
assert ax["structure"]["evidence"][0]["url"] == "https://cdep.ro/x"
assert ax["labor"]["score"] is None and "Niciun fragment" in ax["labor"]["rationale"]
assert all(ax[i]["score"] is None for i in ol.AXIS_IDS if i != "structure")          # restul: fără suport sau fără JSON valid
assert all("Labor Liberalization" not in c for c in calls)                            # axa fără fragmente nu a ajuns la model
assert [ol.to_score(p, s) for p, s in [("left", "clear"), ("left", "slight"), ("balanced", "clear"), ("right", "slight"), ("right", "clear"), ("none", "clear")]] == [1, 2, 3, 4, 5, None]
assert out["run"]["llm_calls"] == len(calls) and out["model"] == "openai/gpt-oss-20b"

# răspuns tăiat / JSON stricat nu mai oprește scorarea (regresie: "Unterminated string starting at...")
truncated = '{"evidence": [{"source": "S1", "quote": "vom accelera descentralizarea fondurilor către primării"}], "rationale": "Se apropie de polul Descentralizare", "pole": "right", "strength": "clear", "confidence": "hi'
assert ol._parse(truncated)["pole"] == "right" and len(ol._parse(truncated)["evidence"]) == 1
broken_mid_string = '{"evidence": [{"source": "S1", "quote": "text tăiat la mijloc'
try: ol._parse(broken_mid_string); raise AssertionError("trebuia să eșueze")
except ol.BadJSON: pass
attempts = []
def flaky_chat(messages, schema, model=None, **kw):
    attempts.append(kw)
    ok = '{"evidence": [{"source": "S1", "quote": "%s"}], "rationale": "ok", "pole": "right", "strength": "clear", "confidence": "high"}' % quote_ok
    content = broken_mid_string if (len(attempts) % 2 == 1) else ok     # prima încercare pe fiecare axă e stricată, a doua bună
    return {"message": {"content": content}, "prompt_eval_count": 1, "eval_count": 1}
out2 = ol.score_orientation(result, "Nicusor Dan", chat=flaky_chat)
assert any(k.get("num_predict") == ol.OUTPUT_TOKENS * 2 for k in attempts)           # reîncercarea folosește buget dublu
assert {a["id"]: a for a in out2["axes"]}["structure"]["score"] == 5
def always_broken(messages, schema, model=None, **kw):
    return {"message": {"content": broken_mid_string}}
out3 = ol.score_orientation(result, "Nicusor Dan", chat=always_broken)              # nu aruncă: axele rămân fără scor
assert all(a["score"] is None for a in out3["axes"]) and len(out3["axes"]) == 10
print("orientation tests passed")
