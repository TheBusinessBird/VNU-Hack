"""python api/test_diskcache.py - cache-ul permanent pe disc: tot ce e generat o dată se citește de pe disc, nu se mai generează."""
import json, os, tempfile
os.environ["CACHE_DIR"] = tempfile.mkdtemp()
import diskcache as dc
import promise_tracker_no_ai_v2 as pt

# --- get / put / delete / inventar ---
assert dc.get("factcheck", "Ion Exemplu", "normal") is None
dc.put("factcheck", "Ion Exemplu", {"findings": [1, 2]}, "normal")
assert dc.get("factcheck", "Ion Exemplu", "normal") == {"findings": [1, 2]}
assert dc.get("factcheck", "ion exemplu", "normal") == {"findings": [1, 2]}            # numele nu ține cont de majuscule
assert dc.get("factcheck", "Ion Exemplu", "fast") is None                              # alte opțiuni = altă intrare
assert dc.get("factcheck", "Alt Politician", "normal") is None
dc.put("credibility", "Ion Exemplu", None)                                              # None nu se salvează
assert dc.inventory() == {"factcheck": 1}
assert "ion-exemplu__" in os.path.basename(dc.path_for("factcheck", "Ion Exemplu", "normal"))
dc.delete("factcheck", "Ion Exemplu", "normal"); assert dc.get("factcheck", "Ion Exemplu", "normal") is None
assert not [f for d in os.walk(dc.CACHE_DIR) for f in d[2] if f.endswith(".tmp")]       # scriere atomică: fără fișiere temporare

# --- joburile răspund imediat de pe disc, fără să pornească vreo generare ---
name = "Ion Exemplu"
cases = {
  "analysis":    (lambda: pt.start_job(name, {"include_text": True, "speed": "normal"}),
                  json.dumps(pt._clean_opts({"include_text": True, "speed": "normal"}), sort_keys=True, ensure_ascii=False)),
  "orientation": (lambda: pt.start_orientation_job(name), "normal|{}"),
  "credibility": (lambda: pt.start_credibility_job(name), "normal"),
  "factcheck":   (lambda: pt.start_factcheck_job(name), f"normal|{pt.FACTCHECK_MAX_NEWS * pt.FACTCHECK_PER_NEWS}|0"),
}
started = []
real_thread = pt.threading.Thread
pt.threading.Thread = lambda *a, **k: started.append(1) or real_thread(*a, **k)
try:
    for kind, (call, extra) in cases.items():
        assert call is not None
        dc.put(kind, name, {"kind": kind, "ok": True}, extra)
        job = call()
        assert job["status"] == "done" and job["result"] == {"kind": kind, "ok": True} and job["done"].is_set(), kind
        assert job["progress"].startswith("Din cache"), kind
        assert pt.public(job)["result"]["ok"] is True
    # rezumat la cerere: cheia = tip + url normalizat
    pt.is_public_url = lambda u: True        # domeniul de test nu se rezolvă prin DNS
    url = "https://exemplu.ro/articol-1"
    ident = pt.normalize_url(url)
    dc.put("summary", name, {"kind": "article", "summary": {"summary": "- punct", "verified": True}}, f"article|{ident}")
    job = pt.start_summary_one_job(name, {"kind": "article", "url": url})
    assert job["status"] == "done" and job["result"]["summary"]["summary"] == "- punct"
finally:
    pt.threading.Thread = real_thread
assert started == [], "nu trebuia pornit niciun fir de generare"
print("diskcache tests passed")
