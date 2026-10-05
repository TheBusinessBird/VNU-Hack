"""diskcache - cache permanent pe disc pentru tot ce se generează pe server (analiza surselor, orientare, rezumate, erori logice, credibilitate).

Ce s-a generat o dată pentru un politician nu se mai generează: cererile următoare primesc rezultatul de pe disc, aproape instant, și după
repornirea API-ului. Nu există expirare. Un rezultat se regenerează doar dacă e cerut explicit cu `force=1`.

Fișiere: api/cache/<tip>/<nume>__<hash>.json  (tip = analysis, orientation, factcheck, credibility, summary; hash = nume + opțiunile cererii).
"""
import hashlib, json, os, re, threading, time, unicodedata

CACHE_DIR = os.environ.get("CACHE_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
_lock = threading.Lock()


def _slug(name):
    s = unicodedata.normalize("NFD", name or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "x"


def path_for(kind, name, extra=""):
    h = hashlib.sha1(f"{(name or '').lower()}\n{extra}".encode("utf-8")).hexdigest()[:10]
    return os.path.join(CACHE_DIR, kind, f"{_slug(name)}__{h}.json")


def get(kind, name, extra=""):
    """Rezultatul salvat sau None."""
    try:
        with open(path_for(kind, name, extra), encoding="utf-8") as f:
            return json.load(f).get("value")
    except (OSError, ValueError):
        return None


def put(kind, name, value, extra=""):
    if value is None:
        return
    path = path_for(kind, name, extra)
    with _lock:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"kind": kind, "name": name, "extra": extra, "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "value": value},
                      f, ensure_ascii=False)
        os.replace(tmp, path)


def delete(kind, name, extra=""):
    try:
        os.remove(path_for(kind, name, extra))
    except OSError:
        pass


def inventory():
    """{tip: număr de intrări} pentru /cache."""
    out = {}
    if os.path.isdir(CACHE_DIR):
        for kind in sorted(os.listdir(CACHE_DIR)):
            d = os.path.join(CACHE_DIR, kind)
            if os.path.isdir(d):
                out[kind] = len([f for f in os.listdir(d) if f.endswith(".json")])
    return out
