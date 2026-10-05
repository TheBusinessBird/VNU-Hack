"""promise_tracker v2 - discursuri/articole + promisiuni + AUTOR + opiniile presei despre candidat. FĂRĂ AI, doar biblioteca standard.

Bazat pe promise_tracker.py (același API), cu adăugiri:
  * fiecare sursă are câmpul "author" (din meta/JSON-LD/byline; null dacă pagina nu îl conține)
  * "press": articole care vorbesc DESPRE candidat, cu propozițiile de opinie și un ton (positive/negative/mixed)
  * stats.press = {articles, positive, negative, mixed}

    python api/promise_tracker.py             # pornește serverul pe :8000
    curl "http://localhost:8000/analyze?name=Prenume+Nume&wait=1"
"""
import json, re, threading, hashlib, time, uuid, contextvars, html as htmlmod, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

__all__ = ["analyze", "serve", "discover", "fetch", "find_promises", "judge", "find_author", "find_opinions"]
_progress = contextvars.ContextVar("progress", default=lambda m: None)
_log = lambda m: _progress.get()(m)
OFFICIAL = ["cdep.ro", "senat.ro", "gov.ro", "presidency.ro"]
UA = "Mozilla/5.0 (research-bot)"
# ---- REGULI (editeaza liber) ----
QUERIES = ['"{n}" promisiune', '"{n}" a promis', '"{n}" discurs', '"{n}" declaratii', '"{n}" promisiuni nerespectate', '"{n}" s-a angajat']
OPINION_QUERIES = ['"{n}" critici', '"{n}" opinie', '"{n}" analiză', '"{n}" editorial', '"{n}" comentariu']
STRONG = r"promit\w*|angaj\w*|garant\w*|v[ăa] asigur|[îi]mi asum|jur c[ăa]"          # angajament explicit
WEAK = r"\bvom\s+\w+|\bvoi\s+\w+|\bo s[ăa]\s+\w+|\bam s[ăa]\s+\w+|\bnu vom\b|\bnu voi\b"  # viitor
SPEECH = r"a spus|a declarat|a afirmat|a anun[țt]at|a promis|a transmis|spune|declar[ăa]|\"|„"
KEPT = r"realizat|finalizat|implementat|inaugurat|intrat [îi]n vigoare|adoptat|votat|promulgat|dat [îi]n folosin[țt][ăa]|[îi]ndeplinit|[îi][șs]i-a [țt]inut|respectat promisiunea|aprobat"
BROKEN = r"nerespectat|ne[îi]ndeplinit|nu [îi][șs]i-a [țt]inut|nu a (fost )?(realizat|finalizat|respectat|[îi]ndeplinit|implementat|adoptat)|nu s-a (realizat|finalizat)|[îi]nc[ăa]lcat|a renun[țt]at|am[âa]nat|a e[șs]uat|neonorat|a revenit asupra"
# Opinii ale presei: cuvinte cu încărcătură evaluativă (euristică simplă)
POS = r"laud[ăa]\w*|apreci\w+|succes\w*|reu[șs]it\w*|competen\w+|onest\w*|eficien\w*|curajos\w*|credibil\w*|admir\w+|performan\w+|transparen\w+|integr\w+|salut\w*|pozitiv\w*|inspir\w+"
NEG = r"critic\w*|acuz\w*|e[șs]ec\w*|scandal\w*|minciun\w*|\bminte\b|incompeten\w*|demagog\w*|populis\w*|dezam[ăa]g\w*|contest\w*|controvers\w*|nereu[șs]\w*|gre[șs]eal\w*|gre[șs]it\w*|corup\w*|manipul\w*|ineficien\w*|ezit\w*|ambigu\w*|nem[ăa]rginit"
POS_RE = re.compile(r"\b(?:" + POS + ")", re.I)
NEG_RE = re.compile(r"\b(?:" + NEG + ")", re.I)
STOP = set("declarat afirmat anunțat anuntat promit promis promisiune ministrul președintele presedintele premierul guvernul domnul doamna aceasta aceste acesta pentru despre fiecare printre foarte trebuie anului mereu după dupa către catre există exista cadrul vorbit".split())


def http(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20) as r:
        raw = r.read()
        return r.geturl(), raw.decode(r.headers.get_content_charset() or "utf-8", "replace"), r.headers.get("content-type", "")


class Text(HTMLParser):
    SKIP = {"script", "style", "nav", "footer", "header", "aside", "form", "noscript"}
    KEEP = {"p", "h1", "h2", "h3", "li", "blockquote"}

    def __init__(s):
        super().__init__(); s.out, s.skip, s.keep, s.cur = [], 0, 0, []

    def handle_starttag(s, t, a):
        s.skip += t in s.SKIP; s.keep += t in s.KEEP

    def handle_endtag(s, t):
        if t in s.KEEP and s.cur: s.out.append(" ".join(s.cur)); s.cur = []
        s.skip -= (t in s.SKIP and s.skip > 0); s.keep -= (t in s.KEEP and s.keep > 0)

    def handle_data(s, d):
        if s.keep and not s.skip and d.strip(): s.cur.append(d.strip())


# ------------------------------- AUTOR -------------------------------
META_RE = re.compile(r"<meta\b([^>]*)>", re.I)
ATTR_RE = re.compile(r'([\w:.-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')')
AUTHOR_META = {"author", "article:author", "dc.creator", "twitter:creator", "parsely-author", "sailthru.author"}


def _clean_author(s):
    s = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), s or "")   # escape-uri JSON din JSON-LD
    s = htmlmod.unescape(re.sub(r"<[^>]+>", " ", s))
    s = re.sub(r"\s+", " ", s).strip(" ,;-|·•")
    s = re.sub(r"^(de|by|autor(ul)?|redactor|text|scris de|publicat de)\s*:?\s+", "", s, flags=re.I).strip()
    s = re.split(r"\s+[|·•]\s+|\s+-\s+|\s+(?:Publicat|Actualizat|Data)\b", s)[0].strip()
    if not (3 <= len(s) <= 80) or len(s.split()) > 6 or re.search(r"https?:|www\.|@|\d{4}", s): return None
    return s


def find_author(page):
    """Autorul articolului din meta-taguri, JSON-LD sau byline; None dacă nu se găsește."""
    for m in META_RE.finditer(page):
        a = {k.lower(): (v1 or v2) for k, v1, v2 in ATTR_RE.findall(m.group(1))}
        if (a.get("name") or a.get("property") or "").lower() in AUTHOR_META:
            c = _clean_author(a.get("content"))
            if c: return c
    for m in re.finditer(r'"author"\s*:\s*(.{0,400})', page, re.S):          # JSON-LD
        chunk = m.group(1)
        n = re.search(r'"name"\s*:\s*"([^"]+)"', chunk) if chunk.lstrip()[:1] in "{[" else re.match(r'\s*"([^"]+)"', chunk)
        c = _clean_author(n.group(1)) if n else None
        if c: return c
    for m in re.finditer(r'<[^>]+(?:itemprop=["\']author["\']|rel=["\']author["\']|class=["\'][^"\']*(?:author|autor|byline)[^"\']*["\'])[^>]*>(.{0,200}?)</', page, re.S | re.I):
        c = _clean_author(m.group(1))
        if c: return c
    return None


def feed(url):
    """RSS Bing (fara cheie API). Returneaza [(url_real, data)]."""
    out = []
    try:
        for it in ET.fromstring(http(url)[1]).iter("item"):
            link = it.findtext("link") or ""
            link = urllib.parse.parse_qs(urllib.parse.urlparse(link).query).get("url", [link])[0]
            d = it.findtext("pubDate") or ""
            m = re.search(r"(\d{1,2}) (\w{3}) (\d{4})", d)
            mon = {k: i + 1 for i, k in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
            out.append((link, f"{m.group(3)}-{mon.get(m.group(2), 1):02d}-{int(m.group(1)):02d}" if m else ""))
    except Exception as e:
        _log(f"Feed error: {e}")
    return out


def _search(queries, kinds=("search", "news/search")):
    found = {}
    for q in queries:
        for kind in kinds:
            for u, d in feed(f"https://www.bing.com/{kind}?q={urllib.parse.quote(q)}&format=rss&setlang=ro&cc=RO"): found.setdefault(u, d)
        time.sleep(0.6)
    return found


def discover(name, extra_urls=()):
    found = _search([q.format(n=name) for q in QUERIES] + [f'"{name}" site:{d}' for d in OFFICIAL])
    for u in extra_urls: found.setdefault(u, "")
    return found


def discover_opinions(name):
    return _search([q.format(n=name) for q in OPINION_QUERIES])


def fetch(url, rss_date):
    try:
        real, html, ctype = http(url)
        if "html" not in ctype: return None
        p = Text(); p.feed(html)
        t = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        d = re.search(r'(?:published_time|datePublished)["\']?[^0-9]{0,20}(\d{4}-\d{2}-\d{2})', html)
        return dict(id=hashlib.md5(real.encode()).hexdigest()[:10], url=real, domain=urllib.parse.urlparse(real).netloc.replace("www.", ""),
                    title=re.sub(r"\s+", " ", htmlmod.unescape(t.group(1))).strip() if t else "", date=(d.group(1) if d else rss_date),
                    author=find_author(html), paras=p.out)
    except Exception:
        return None


def mentions(text, surname):
    return re.search(r"(?<![\wăâîșț])" + re.escape(surname) + r"(?![\wăâîșț])", text, re.I) is not None


def sents(par):
    return [s.strip() for s in re.split(r'(?<=[.!?…])\s+(?=[A-ZĂÂÎȘȚ„"])', par) if len(s.strip()) > 25]


def words(s):
    return {w[:6] for w in re.findall(r"[a-zăâîșțşţ]{6,}", s.lower()) if w not in STOP}  # prefix 6 = stemming simplu


def find_promises(doc, surname):
    res, P = [], doc["paras"]
    for i, par in enumerate(P):
        near = mentions(" ".join(P[max(0, i - 1):i + 2]), surname)
        if not near: continue
        S = sents(par)
        for j, s in enumerate(S):
            strong, weak = re.search(STRONG, s, re.I), re.search(WEAK, s, re.I)
            if strong or (weak and re.search(SPEECH, par, re.I)):
                ctx = " ".join(S[max(0, j - 1):j + 2])
                res.append(dict(promise=s, quote=s, context=ctx, topic=", ".join(sorted({w for w in re.findall(r"[a-zăâîșț]{6,}", s.lower()) if w not in STOP}, key=len, reverse=True)[:4])))
    return res


def find_opinions(doc, surname):
    """Propoziții care menționează candidatul și conțin limbaj evaluativ. Euristică pe cuvinte-cheie."""
    out, seen = [], set()
    for par in doc["paras"]:
        for s in sents(par):
            if not mentions(s, surname) or s in seen: continue
            pos, neg = len(POS_RE.findall(s)), len(NEG_RE.findall(s))
            if not (pos or neg): continue
            seen.add(s)
            out.append({"quote": s, "tone": "positive" if pos > neg else "negative" if neg > pos else "mixed"})
    return out[:8]


def judge(p, others):
    kw = words(p["promise"]); need = 3 if len(kw) >= 6 else 2; ev, k, b = [], 0, 0
    for d in others:
        for par in d["paras"]:
            for s in sents(par):
                if len(kw & words(s)) < need: continue
                if re.search(BROKEN, s, re.I): b += 1; ev.append({"doc_id": d["id"], "quote": s})
                elif re.search(KEPT, s, re.I): k += 1; ev.append({"doc_id": d["id"], "quote": s})
    status = "partial" if k and b else "kept" if k else "broken" if b else "unverifiable"
    why = {"partial": "Surse ulterioare conțin atât indicii de îndeplinire, cât și de neîndeplinire.", "kept": "Surse ulterioare conțin cuvinte-cheie de îndeplinire pe același subiect.",
           "broken": "Surse ulterioare conțin cuvinte-cheie de neîndeplinire pe același subiect.", "unverifiable": "Nu s-au găsit propoziții ulterioare relevante cu indicii de rezultat."}[status]
    return status, why + " (Euristică pe cuvinte-cheie: verifică manual.)", ev[:6]


def _tone(ops):
    pos, neg = sum(o["tone"] == "positive" for o in ops), sum(o["tone"] == "negative" for o in ops)
    return "positive" if pos > neg else "negative" if neg > pos else "mixed"


# ======================= FUNCȚIA PUBLICĂ (import) =======================
def analyze(name, extra_urls=(), on_progress=None, include_text=True, max_sources=40, max_press=25):
    """Rulează tot pipeline-ul și întoarce:
    {politician, generated_at, stats, sources[] (cu author), promises[], press[] (opinii despre candidat)}.
    Fără AI. Blocant (poate dura câteva minute); pentru progres dă on_progress=lambda msg: ..."""
    name = " ".join(str(name).split())
    if len(name.split()) < 2:
        raise ValueError("Dă numele complet (prenume + nume).")
    tok = _progress.set(on_progress or (lambda m: None))
    try:
        surname = name.split()[-1].lower()
        _log("Caut surse...")
        found = list(discover(name, extra_urls).items())[:max_sources]
        main_urls = {u for u, _ in found}
        _log("Caut opinii din presă...")
        extra = [(u, d) for u, d in discover_opinions(name).items() if u not in main_urls][:max_press]
        docs, press_docs = [], []
        for i, (u, d) in enumerate(found + extra):
            _log(f"Descarc sursa {i+1}/{len(found) + len(extra)}")
            doc = fetch(u, d)
            if doc:
                txt = " ".join(doc["paras"])
                if mentions(txt, surname) and len(txt) > 400: (docs if u in main_urls else press_docs).append(doc)
        by = {d["id"]: d for d in docs}
        proms = {}
        for d in docs:
            for x in find_promises(d, surname):
                x.update(id=hashlib.md5((d["id"] + x["quote"]).encode()).hexdigest()[:8], source_id=d["id"], source_url=d["url"], date=d["date"])
                proms[x["id"]] = x
        for i, x in enumerate(proms.values()):
            _log(f"Verific rezultatul {i+1}/{len(proms)}")
            others = [d for d in docs if d["id"] != x["source_id"] and (d["date"] or "") >= (x["date"] or "")]
            st, why, ev = judge(x, others)
            x.update(status=st, rationale=why, evidence=[{"source_id": e["doc_id"], "url": by[e["doc_id"]]["url"], "quote": e["quote"]} for e in ev])
        plist = list(proms.values())
        _log("Extrag opiniile presei...")
        press = []
        for d in docs + press_docs:
            if any(d["domain"].endswith(o) for o in OFFICIAL): continue      # sursele oficiale nu sunt presă
            ops = find_opinions(d, surname)
            if ops:
                press.append({"id": d["id"], "url": d["url"], "domain": d["domain"], "title": d["title"], "date": d["date"], "author": d["author"],
                              "tone": _tone(ops), "opinions": ops})
        sources = [{"id": d["id"], "url": d["url"], "domain": d["domain"], "title": d["title"], "date": d["date"], "author": d["author"],
                    **({"text": "\n\n".join(d["paras"])} if include_text else {})} for d in docs]
        stats = {s: sum(p["status"] == s for p in plist) for s in ("kept", "partial", "broken", "unverifiable")}
        pstats = {"articles": len(press), **{t: sum(a["tone"] == t for a in press) for t in ("positive", "negative", "mixed")}}
        _log("Gata")
        return {"politician": name, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "stats": {"sources": len(docs), "promises": len(plist), **stats, "press": pstats},
                "sources": sources, "promises": plist, "press": press}
    finally:
        _progress.reset(tok)


# ============================ SERVER API (JSON) ============================
JOBS, JLOCK = {}, threading.Lock()


def start_job(name, urls=(), include_text=True, refresh=False):
    name = " ".join(str(name).split())
    if len(name.split()) < 2: raise ValueError("Parametrul 'name' trebuie să conțină numele complet.")
    key = (name.lower(), include_text, tuple(urls))
    with JLOCK:
        j = JOBS.get(key)
        if j and not refresh and (j["status"] == "running" or time.time() - j["t"] < 3600): return j
        jid = uuid.uuid4().hex[:12]
        j = JOBS[key] = JOBS[jid] = {"job_id": jid, "status": "running", "progress": "Pornit", "result": None, "error": None,
                                     "done": threading.Event(), "t": time.time()}
    def work():
        try:
            j["result"] = analyze(name, urls, lambda m: j.__setitem__("progress", m), include_text); j["status"] = "done"
        except Exception as e:
            j["error"], j["status"] = str(e), "error"
        j["done"].set()
    threading.Thread(target=work, daemon=True).start()
    return j


def start_orientation_job(name, refresh=False, num_ctx=None):
    """Scorurile 1..5 pe 10 axe, calculate de Ollama din textele surselor. Refolosește analiza deja făcută pentru același nume
    (altfel o rulează întâi). Rezultatul se citește tot din /jobs/<id>."""
    name = " ".join(str(name).split())
    if len(name.split()) < 2: raise ValueError("Parametrul 'name' trebuie să conțină numele complet.")
    key = ("orientation", name.lower(), num_ctx)
    with JLOCK:
        j = JOBS.get(key)
        if j and not refresh and (j["status"] == "running" or (j["status"] == "done" and time.time() - j["t"] < 3600)): return j
        jid = uuid.uuid4().hex[:12]
        j = JOBS[key] = JOBS[jid] = {"job_id": jid, "status": "running", "progress": "Pornit", "result": None, "error": None,
                                     "done": threading.Event(), "t": time.time()}
    def work():
        try:
            import importlib, orientation_llm as ol
            importlib.reload(ol)            # preia modificările prompt-ului fără restart
            prog = lambda m: j.__setitem__("progress", m)
            src = start_job(name, (), True, False)      # refolosește analiza din memorie (sau o pornește) ca să nu scrapuim de două ori
            while not src["done"].wait(2):
                prog("Analiza surselor: " + str(src["progress"]))
            if src["status"] == "error": raise RuntimeError(src["error"])
            analysis = src["result"]
            prog("Ollama evaluează axele...")
            j["result"] = ol.score_orientation(analysis, name, on_progress=prog, **({"num_ctx": num_ctx} if num_ctx else {})); j["status"] = "done"
        except Exception as e:
            j["error"], j["status"] = str(e), "error"
        j["done"].set()
    threading.Thread(target=work, daemon=True).start()
    return j


def public(j):
    return {k: j[k] for k in ("job_id", "status", "progress", "error", "result")} | {"status_url": f"/jobs/{j['job_id']}"}


class H(BaseHTTPRequestHandler):
    def log_message(s, *a): pass

    def _h(s, code, n=0):
        s.send_response(code)
        for k, v in (("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(n)), ("Access-Control-Allow-Origin", "*"),
                     ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"), ("Access-Control-Allow-Headers", "Content-Type")): s.send_header(k, v)
        s.end_headers()

    def reply(s, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode(); s._h(code, len(b)); s.wfile.write(b)

    def do_OPTIONS(s): s._h(204)

    def go(s, name, urls, inc, refresh, wait):
        try: j = start_job(name, urls, inc, refresh)
        except ValueError as e: return s.reply(400, {"error": str(e)})
        if wait: j["done"].wait()
        s.reply(200 if j["status"] == "done" else 500 if j["status"] == "error" else 202, public(j))

    def do_GET(s):
        u = urllib.parse.urlparse(s.path); q = urllib.parse.parse_qs(u.query)
        if u.path == "/health": s.reply(200, {"ok": True})
        elif u.path.startswith("/jobs/"):
            j = JOBS.get(u.path[6:])
            s.reply(200, public(j)) if j else s.reply(404, {"error": "job inexistent"})
        elif u.path == "/orientation":
            try:
                n = q.get("num_ctx", [""])[0]
                j = start_orientation_job(q.get("name", [""])[0], q.get("refresh") == ["1"], int(n) if n.isdigit() else None)
            except ValueError as e: return s.reply(400, {"error": str(e)})
            if q.get("wait") == ["1"]: j["done"].wait()
            s.reply(200 if j["status"] == "done" else 500 if j["status"] == "error" else 202, public(j))
        elif u.path == "/analyze":
            s.go(q.get("name", [""])[0], q.get("url", []), q.get("include_text", ["1"])[0] != "0", q.get("refresh") == ["1"], q.get("wait") == ["1"])
        else:
            s.reply(200, {"endpoints": {"GET /analyze?name=Prenume+Nume[&wait=1][&url=...][&include_text=0][&refresh=1]": "pornește (sau așteaptă) analiza",
                                        "POST /analyze  {name, urls?, include_text?, refresh?, wait?}": "idem, cu JSON", "GET /jobs/<job_id>": "status + rezultat",
                                        "GET /orientation?name=Prenume+Nume[&refresh=1][&num_ctx=8192][&wait=1]": "scoruri 1..5 pe 10 axe, calculate de Ollama (llama3.2:1b) din textele surselor", "GET /health": "ok"}})

    def do_POST(s):
        try: b = json.loads(s.rfile.read(int(s.headers.get("Content-Length") or 0)) or b"{}")
        except Exception: return s.reply(400, {"error": "JSON invalid"})
        s.go(b.get("name", ""), b.get("urls", []), b.get("include_text", True), b.get("refresh", False), b.get("wait", False))


def serve(host="127.0.0.1", port=8000):
    print(f"API pe http://{host}:{port}  (GET / pentru lista de endpoint-uri)")
    ThreadingHTTPServer((host, port), H).serve_forever()


if __name__ == "__main__":
    serve()
