"""
promise_tracker_no_ai_v2
------------------------
Tracker politic 100% determinist (fără AI / LLM):
- caută surse prin Bing RSS (+ URL-uri date manual);
- prioritizează sursele oficiale;
- extrage dovezi textuale: educație, finanțare, declarații, discursuri;
- fiecare dovadă păstrează sursa, URL-ul, data, autorul și fragmentul;
- generează un raport text detaliat.

Utilizare ca bibliotecă:
    from promise_tracker_no_ai_v2 import analyze, report_text
    result = analyze("Prenume Nume", speed="normal")
    print(result["report"])

Linie de comandă:
    python promise_tracker_no_ai_v2.py "Prenume Nume" [fast|normal|deep]
    python promise_tracker_no_ai_v2.py            # pornește API-ul pe 127.0.0.1:8000
"""

import contextvars
import functools
import hashlib
import ipaddress
import itertools
import json
import re
import socket
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
import diskcache
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

__all__ = [
    "analyze",
    "report_text",
    "serve",
    "discover",
    "fetch",
    "find_speeches",
    "find_statements",
]


# ============================================================
# CONFIG
# ============================================================

_progress = contextvars.ContextVar("progress", default=lambda m: None)


def _log(msg):
    try:
        _progress.get()(msg)
    except Exception:
        pass


OFFICIAL = [
    "cdep.ro",
    "senat.ro",
    "gov.ro",
    "presidency.ro",
    "europarl.europa.eu",
    "mae.ro",
    "ccr.ro",
    "romania.europa.eu",
]

UA = "Mozilla/5.0 (compatible; promise-tracker/2.1; research)"
CORS_ORIGIN = "*"
MAX_PARALLEL_JOBS = 2
JOB_TTL_SECONDS = 6 * 3600
JOB_CACHE_SECONDS = 3600

PRESETS = {
    "fast": dict(max_queries=32, pages=1, max_sources=70, depth=1,
                 crawl_cap=40, budget=120, since_back=3),
    "normal": dict(max_queries=90, pages=2, max_sources=125, depth=2,       # înjumătățit (250 / 120): site-ul primea prea multe surse
                   crawl_cap=60, budget=360, since_back=8),
    "deep": dict(max_queries=220, pages=3, max_sources=800, depth=2,
                 crawl_cap=350, budget=1800, since_back=20),
}

BASE_TEMPLATES = [
    '"{n}"',
    '"{n}" discurs',
    '"{n}" declarații',
    '"{n}" interviu',
    '"{n}" "a spus"',
    '"{n}" "a declarat"',
    '"{n}" "a promis"',
    '"{n}" stenogramă',
    '"{n}" conferință de presă',
    '"{n}" comunicat',
    '"{n}" intervenție',
    '"{n}" dezbatere',
    '"{n}" ședință',
    '"{n}" mesaj',
    '"{n}" moțiune',
    '"{n}" campanie electorală',
    '"{n}" program de guvernare',
    '"{n}" proiect de lege',
    '"{n}" "s-a angajat"',
    '"{n}" promisiuni',
]

EDUCATION_QUERY_WORDS = [
    "studii", "facultate", "universitate", "absolvit", "biografie",
    "liceu", "diplomă", "master", "doctorat", "specializare",
    "carieră academică", "școală",
]

FUNDING_QUERY_WORDS = [
    "finanțare", "fonduri europene", "PNRR", "buget", "grant",
    "investiție", "subvenție", "bugetul de stat", "buget local",
    "împrumut", "fonduri", "taxe", "impozite", "venituri",
]

KW_URL = re.compile(
    r"steno|discurs|declar|interviu|comunicat|alocu|intervent|sedint|plen|"
    r"mesaj|conferint|educat|stud|facultat|univers|finant|buget|fondur|"
    r"pnrr|grant|investit|tax|impozit|biograf|profil",
    re.I,
)

KINDS = [
    ("stenogramă", re.compile(r"steno|sedint|plen", re.I)),
    ("discurs", re.compile(r"discurs|alocu|adresare|mesaj", re.I)),
    ("interviu", re.compile(r"interviu|invitat|emisiun", re.I)),
    ("comunicat", re.compile(r"comunicat|press", re.I)),
    ("declarație", re.compile(r"declar|intervent|conferint", re.I)),
    ("educație", re.compile(r"educat|stud|facultat|univers|liceu|scoal|biograf", re.I)),
    ("finanțare", re.compile(r"finant|buget|fondur|pnrr|grant|investit|tax|impozit", re.I)),
]

SPK = re.compile(
    r"^(?:[Dd]omnul|[Dd]oamna|D-l|D-na)?\s*"
    r"([A-ZĂÂÎȘȚŞŢ][\w\-]+(?:\s+[A-ZĂÂÎȘȚŞŢ][\w\-]+){1,4})"
    r"\s*(?:\([^)]{0,100}\))?\s*:\s*(.*)$",
    re.S,
)

QUOTE = re.compile(r'[„“"«]([^”"“„«»]{40,5000})[”"»]', re.S)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

SKIP_EXT = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".mp3", ".mp4",
    ".avi", ".mov", ".zip", ".rar", ".7z", ".gz", ".exe", ".doc", ".docx",
    ".xls", ".xlsx", ".ppt", ".pptx", ".pdf", ".css", ".js", ".xml", ".rss",
)

# Cuvinte-cheie (potrivire pe prefix de cuvânt, fără diacritice).
EDUCATION_KEYWORDS = [
    "studii", "a studiat", "studia", "facultate", "universitate",
    "liceu", "școala", "școală", "absolvent", "absolvit", "absolvă",
    "diplomă", "masterat", "master în", "master in", "masterul",
    "doctorat", "specializare", "studii superioare", "licență",
]

FUNDING_KEYWORDS = [
    "finanțare", "finanțat", "finanța", "finanțăm", "bani", "buget",
    "fonduri", "fond european", "pnrr", "grant", "împrumut", "investiție",
    "investiții", "subvenție", "subvenții", "venituri", "taxe", "impozite",
    "accize", "cofinanțare", "parteneriat public-privat",
]

PROMISE_KEYWORDS = [
    "voi ", "vom ", "va construi", "va face", "va introduce", "va investi",
    "va finanța", "va aloca", "va crea", "va crește", "va reduce",
    "va elimina", "va reforma", "ne angajăm", "mă angajez", "ne-am angajat",
    "promit", "promite", "promisiune", "planul este", "intenționăm",
    "intenționez",
]

FUNDING_CHANNELS = [
    ("buget de stat", ["bugetul de stat", "buget de stat"]),
    ("buget local", ["bugetul local", "buget local"]),
    ("fonduri europene", ["fonduri europene", "fondurile europene", "fond european"]),
    ("PNRR", ["pnrr"]),
    ("granturi", ["grant", "granturi"]),
    ("împrumuturi", ["împrumut", "împrumuturi"]),
    ("taxe și impozite", ["taxe", "impozite", "accize"]),
    ("subvenții", ["subvenție", "subvenții"]),
    ("cofinanțare", ["cofinanțare"]),
    ("investiții private", ["investitor privat", "investiții private", "capital privat"]),
    ("parteneriat public-privat", ["parteneriat public-privat"]),
]


# ============================================================
# TEXT HELPERS
# ============================================================

def strip(s):
    """Elimină diacriticele și face lowercase (pentru comparații)."""
    if not s:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", str(s))
        if unicodedata.category(c) != "Mn"
    ).lower()


def clean_text(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


@functools.lru_cache(maxsize=4096)
def _rx_word(term_norm):
    return re.compile(r"(?<!\w)" + re.escape(term_norm) + r"(?!\w)")


@functools.lru_cache(maxsize=4096)
def _rx_prefix(term_norm):
    return re.compile(r"(?<!\w)" + re.escape(term_norm))


def has_word(norm_text, term):
    """Cuvânt/expresie întreagă într-un text deja normalizat."""
    t = strip(term).strip()
    return bool(t) and _rx_word(t).search(norm_text) is not None


def has_kw(norm_text, kw):
    """Potrivire la început de cuvânt (acceptă flexiuni: finanțare/finanțarea)."""
    t = strip(kw)
    return bool(t.strip()) and _rx_prefix(t).search(norm_text) is not None


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    return list(v)


# ============================================================
# URL / HTTP (cu protecție SSRF)
# ============================================================

_TRACKING = re.compile(r"^(utm_|fbclid|gclid|mc_|ref$)", re.I)


def normalize_url(url):
    if not url:
        return ""
    try:
        p = urllib.parse.urlsplit(str(url).strip())
    except ValueError:
        return ""
    if p.scheme not in ("http", "https") or not p.netloc:
        return ""
    query = urllib.parse.urlencode(
        [(k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True)
         if not _TRACKING.match(k)]
    )
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, query, ""))


def hostname(url):
    try:
        h = (urllib.parse.urlparse(url).hostname or "").lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def is_official_domain(domain):
    domain = (domain or "").lower()
    domain = domain[4:] if domain.startswith("www.") else domain
    return any(domain == d or domain.endswith("." + d) for d in OFFICIAL)


@functools.lru_cache(maxsize=2048)
def _host_is_public(host):
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    if not infos:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0].split("%")[0])
        except ValueError:
            return False
        if not ip.is_global:
            return False
    return True


def is_public_url(url):
    try:
        p = urllib.parse.urlsplit(url)
        host = p.hostname
    except ValueError:
        return False
    return p.scheme in ("http", "https") and bool(host) and _host_is_public(host)


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_public_url(newurl):
            raise urllib.error.URLError("redirect către o adresă nepublică blocat")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_SafeRedirect)


def _decode(data, header_charset):
    candidates = []
    if header_charset:
        candidates.append(header_charset)
    m = re.search(rb'charset=["\']?([A-Za-z0-9_\-]+)', data[:3000], re.I)
    if m:
        candidates.append(m.group(1).decode("ascii", "ignore"))
    candidates.append("utf-8")
    for enc in candidates:
        try:
            return data.decode(enc, "replace")
        except LookupError:
            continue
    return data.decode("utf-8", "replace")


def http(url, retries=2, timeout=12, max_bytes=8_000_000):
    """GET cu retry și limită de dimensiune. Returnează (URL final, text, content-type)."""
    if not is_public_url(url):
        raise ValueError(f"URL nepublic sau invalid: {url}")

    last_error = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": UA,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "ro,en;q=0.7",
                },
            )
            with _OPENER.open(req, timeout=timeout) as r:
                data = r.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise ValueError("pagina depășește limita de dimensiune")
                text = _decode(data, r.headers.get_content_charset())
                return (
                    normalize_url(r.geturl()) or url,
                    text,
                    r.headers.get("content-type", ""),
                )
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code < 500 and exc.code != 429:
                break
        except Exception as exc:
            last_error = exc
        if attempt < retries:
            time.sleep(0.5 * (attempt + 1))
    raise last_error


def _pmap(fn, items, workers=12):
    """map paralel care propagă contextul (pentru progres) și nu aruncă excepții."""
    items = list(items)
    if not items:
        return []
    out = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [
            ex.submit(contextvars.copy_context().run, fn, it) for it in items
        ]
        for f in futures:
            try:
                out.append(f.result())
            except Exception as exc:
                _log(f"Task eșuat: {exc}")
                out.append(None)
    return out


# ============================================================
# HTML PARSER
# ============================================================

class Page(HTMLParser):
    # NU includem "form" (multe site-uri ASP învelesc toată pagina într-un <form>)
    # și nici "header" (poate conține titlul articolului).
    SKIP = {"script", "style", "nav", "footer", "aside", "noscript", "svg",
            "canvas", "select", "button", "template", "title"}
    BLOCK = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol",
             "blockquote", "td", "th", "tr", "table", "div", "section",
             "article", "main", "br", "hr", "pre", "dd", "dt", "figcaption",
             "header"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.cur = []
        self.links = []
        self.skip = 0
        self.href = None
        self.at = []

    def _flush(self):
        if self.cur:
            text = clean_text(" ".join(self.cur))
            if text:
                self.out.append(text)
            self.cur = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.BLOCK or tag in self.SKIP:
            self._flush()
        if tag in self.SKIP:
            self.skip += 1
        if tag == "a" and not self.skip:
            self.href = dict(attrs).get("href")
            self.at = []

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "a" and self.href:
            self.links.append((self.href, clean_text(" ".join(self.at))))
        if tag == "a":
            self.href = None
            self.at = []
        if tag in self.BLOCK or tag in self.SKIP:
            self._flush()
        if tag in self.SKIP and self.skip > 0:
            self.skip -= 1

    def handle_data(self, data):
        if self.skip or not data or not data.strip():
            return
        text = clean_text(data)
        if self.href:
            self.at.append(text)
        self.cur.append(text)

    def close(self):
        super().close()
        self._flush()


# ============================================================
# DISCOVERY (Bing RSS)
# ============================================================

def feed(url):
    """Returnează [(url, data_iso)] dintr-un feed RSS Bing."""
    out = []
    try:
        _, xml_text, _ = http(url, retries=1, timeout=10, max_bytes=2_000_000)
        root = ET.fromstring(xml_text.lstrip("\ufeff"))
    except ET.ParseError:
        return out  # nu e RSS (ex. pagină HTML de blocare)
    except Exception as exc:
        _log(f"RSS eșuat: {exc}")
        return out

    for item in root.iter("item"):
        link = (item.findtext("link") or "").strip()
        if not link:
            continue
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
        link = qs.get("url", [link])[0]
        link = normalize_url(link)
        if not link:
            continue

        date = ""
        pub = item.findtext("pubDate")
        if pub:
            try:
                date = parsedate_to_datetime(pub).strftime("%Y-%m-%d")
            except Exception:
                date = ""
        out.append((link, date))
    return out


def name_variants(name, aliases=()):
    """Variante ale numelui COMPLET (fără numele de familie singur)."""
    parts = clean_text(name).split()
    variants = []
    if parts:
        variants.append(" ".join(parts))
        if len(parts) >= 2:
            first, last = parts[:-1], parts[-1]
            variants.append(f"{last} {' '.join(first)}")
            variants.append(f"{parts[0]} {last}")
            variants.append(f"{last} {parts[0]}")
    variants.extend(clean_text(a) for a in aliases if clean_text(a))
    return list(dict.fromkeys(v for v in variants if v))


_DOMAIN_OK = re.compile(r"^[a-z0-9.\-]+\.[a-z]{2,}$")


def queries(name, aliases, domains, since_year):
    """
    Căutări intercalate pe categorii (general, oficial, educație, finanțare, ...),
    ca limita max_queries să acopere toate categoriile.
    """
    domains_all = list(dict.fromkeys(
        [*OFFICIAL, *[d.lower().strip() for d in domains if _DOMAIN_OK.match(d.lower().strip())]]
    ))
    variants = name_variants(name, aliases)

    core = [t.format(n=name) for t in BASE_TEMPLATES[:8]]

    official = []
    for d in domains_all:
        official.append(f'"{name}" site:{d}')
        official.append(f'"{name}" stenogramă site:{d}')
        official.append(f'"{name}" declarații site:{d}')

    education = [f'"{name}" "{w}"' for w in EDUCATION_QUERY_WORDS]
    for w in EDUCATION_QUERY_WORDS[:4]:
        for d in domains_all[:4]:
            education.append(f'"{name}" "{w}" site:{d}')

    funding = [f'"{name}" "{w}"' for w in FUNDING_QUERY_WORDS]
    for w in FUNDING_QUERY_WORDS[:4]:
        for d in domains_all[:4]:
            funding.append(f'"{name}" "{w}" site:{d}')

    more = [t.format(n=name) for t in BASE_TEMPLATES[8:]]

    variant_q = []
    for v in variants[1:]:
        variant_q.extend(t.format(n=v) for t in BASE_TEMPLATES[:5])

    years = []
    for y in range(time.localtime().tm_year, since_year - 1, -1):
        years.append(f'"{name}" discurs {y}')
        years.append(f'"{name}" declarații {y}')

    groups = [core, official, education, funding, more, variant_q, years]
    merged = [
        q for q in itertools.chain.from_iterable(itertools.zip_longest(*groups))
        if q
    ]
    return list(dict.fromkeys(merged))


def _search(q, pages=1, deadline=None):
    got = {}
    for kind in ("search", "news/search"):
        for p in range(pages):
            if deadline and time.time() > deadline:
                return got
            url = (
                f"https://www.bing.com/{kind}"
                f"?q={urllib.parse.quote(q)}"
                f"&format=rss&setlang=ro&cc=RO&count=50"
                f"&first={1 + 50 * p}"
            )
            results = feed(url)
            new = [x for x in results if x[0] not in got]
            if not new:
                break
            got.update(dict(new))
    return got


def discover(
    name,
    extra_urls=(),
    aliases=(),
    domains=(),
    since_year=2023,
    max_queries=24,
    pages=1,
    deadline=None,
):
    qs = queries(name, aliases, domains, since_year)[:max_queries]
    found = {}
    done = [0]
    lock = threading.Lock()

    def run(q):
        res = _search(q, pages, deadline)
        with lock:
            done[0] += 1
            for url, date in res.items():
                found.setdefault(url, date)
            _log(f"Căutare {done[0]}/{len(qs)} – {len(found)} URL-uri")
        return res

    _pmap(run, qs, workers=8)

    for url in extra_urls:
        u = normalize_url(url)
        if u:
            found.setdefault(u, "")
    return found


# ============================================================
# FETCH / METADATA
# ============================================================

_DATE_META = [
    re.compile(
        r'<meta[^>]+(?:property|name|itemprop)=["\'](?:article:published_time|'
        r'og:article:published_time|datepublished|date|dc\.date(?:\.issued)?|'
        r'pubdate|publishdate)["\'][^>]*content=["\'](\d{4}-\d{2}-\d{2})', re.I),
    re.compile(
        r'<meta[^>]+content=["\'](\d{4}-\d{2}-\d{2})[^"\']*["\'][^>]*'
        r'(?:property|name|itemprop)=["\'](?:article:published_time|'
        r'datepublished|date|dc\.date(?:\.issued)?|pubdate)["\']', re.I),
    re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', re.I),
    re.compile(r'<time[^>]+datetime=["\'](\d{4}-\d{2}-\d{2})', re.I),
]
_DATE_URL = re.compile(r"/(20\d{2}|19\d{2})[/\-](\d{1,2})[/\-](\d{1,2})(?:[/\-]|$)")


def _valid_date(d):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", d or "")
    if not m:
        return False
    y, mo, da = map(int, m.groups())
    return 1990 <= y <= time.localtime().tm_year + 1 and 1 <= mo <= 12 and 1 <= da <= 31


def extract_date(html, fallback="", url=""):
    head = html[:200_000]
    for rx in _DATE_META:
        m = rx.search(head)
        if m and _valid_date(m.group(1)):
            return m.group(1)
    m = _DATE_URL.search(url or "")
    if m:
        d = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        if _valid_date(d):
            return d
    return fallback if _valid_date(fallback) else ""


def extract_title(html):
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if not m:
        return ""
    return clean_text(unescape(re.sub(r"<[^>]+>", " ", m.group(1))))


_AUTHOR_PATTERNS = [
    re.compile(r'<meta[^>]+(?:name|property)=["\'](?:author|article:author|dc\.creator)["\'][^>]*content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:name|property)=["\'](?:author|article:author|dc\.creator)["\']', re.I),
    re.compile(r'"author"\s*:\s*\{[^}]*?"name"\s*:\s*"([^"]+)"', re.I),
    re.compile(r'(?:class|rel)=["\'][^"\']*author[^"\']*["\'][^>]*>\s*([^<]{3,80})<', re.I),
]


def extract_author(html):
    head = html[:200_000]
    for rx in _AUTHOR_PATTERNS:
        m = rx.search(head)
        if m:
            raw = re.sub(r"\\u([0-9a-fA-F]{4})", lambda u: chr(int(u.group(1), 16)), m.group(1))   # JSON-LD: ş -> ş
            author = clean_text(unescape(raw))
            if author and len(author) <= 120 and not author.lower().startswith("http"):
                return author
    return "Necunoscut"


def fetch(url, rss_date=""):
    try:
        url = normalize_url(url)
        if not url or urllib.parse.urlsplit(url).path.lower().endswith(SKIP_EXT):
            return None

        real, html, ctype = http(url)
        if "html" not in (ctype or "").lower() and "<html" not in html[:2000].lower():
            return None

        parser = Page()
        parser.feed(html)
        parser.close()

        paragraphs, norms, seen = [], [], set()
        for item in parser.out:
            if len(item) < 20:
                continue
            key = strip(item)
            if key in seen:
                continue
            seen.add(key)
            paragraphs.append(item)
            norms.append(key)

        links = []
        for href, tx in parser.links:
            href = (href or "").strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            absolute = normalize_url(urllib.parse.urljoin(real, href))
            if absolute:
                links.append((absolute, clean_text(tx)))

        return {
            "id": hashlib.sha256(real.encode("utf-8")).hexdigest()[:12],
            "url": real,
            "domain": hostname(real),
            "title": extract_title(html),
            "date": extract_date(html, rss_date, real),
            "author": extract_author(html),
            "paras": paragraphs,
            "norm": norms,
            "links": links,
        }
    except Exception as exc:
        return None     # pagina nu răspunde (timeout, 403...): se sare peste ea, fără să apară ca mesaj de progres


# ============================================================
# SCORING / RELEVANCE
# ============================================================

def source_score(doc):
    """Scor determinist 0..100: cât de utilă este sursa (nu cât de adevărată)."""
    if not doc:
        return 0
    score = 20
    title_url = strip(doc.get("title", "") + " " + doc.get("url", ""))

    if is_official_domain(doc.get("domain", "")):
        score += 45
    if re.search(r"steno|discurs|declar|interviu|comunicat|conferint|plen|sedint", title_url):
        score += 15
    if re.search(r"educat|stud|univers|facultat|liceu|finant|buget|fondur|pnrr|grant|investit|biograf", title_url):
        score += 8

    text_len = sum(len(p) for p in doc.get("paras", []))
    if text_len > 2500:
        score += 5
    if text_len > 7000:
        score += 5
    return min(score, 100)


def document_text(doc):
    return "\n\n".join(doc.get("paras", []))


def contains_person(doc, variants):
    blob = "\n".join(doc.get("norm", []))
    return any(has_word(blob, v) for v in variants if v)


def relevant_document(doc, variants, min_chars=300):
    if not doc:
        return False
    if sum(len(p) for p in doc.get("paras", [])) < min_chars:
        return False
    return contains_person(doc, variants)


def article_kind(doc):
    blob = strip(doc.get("title", "") + " " + doc.get("url", ""))
    for kind, regex in KINDS:
        if regex.search(blob):
            return kind
    return "articol"


# ============================================================
# EVIDENCE EXTRACTION
# ============================================================

def _window_sentences(paragraph, match, limit):
    """Pentru paragrafe lungi: fereastră de propoziții în jurul primei potriviri."""
    sents = [s for s in SENTENCE_SPLIT.split(paragraph) if s]
    if not sents:
        return paragraph[:limit]
    idx = next((i for i, s in enumerate(sents) if match(strip(s))), 0)
    out = [sents[idx]]
    size = len(sents[idx])
    lo, hi = idx - 1, idx + 1
    while True:
        grew = False
        if hi < len(sents) and size + 1 + len(sents[hi]) <= limit:
            out.append(sents[hi]); size += 1 + len(sents[hi]); hi += 1; grew = True
        if lo >= 0 and size + 1 + len(sents[lo]) <= limit:
            out.insert(0, sents[lo]); size += 1 + len(sents[lo]); lo -= 1; grew = True
        if not grew:
            break
    text = " ".join(out)
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip() + "…"
    return text


def make_excerpt(paragraphs, index, match, limit=700):
    """Paragraful potrivit + vecini, fără să taie fragmentul relevant."""
    main = paragraphs[index]
    if len(main) > limit:
        return _window_sentences(main, match, limit)

    if len(main) >= 120:
        return main  # suficient de lung; vecinii ar adăuga doar zgomot
    parts = [main]
    size = len(main)
    lo, hi = index - 1, index + 1
    while len(parts) < 3:
        grew = False
        if hi < len(paragraphs) and size + 1 + len(paragraphs[hi]) <= limit:
            parts.append(paragraphs[hi]); size += 1 + len(paragraphs[hi]); hi += 1; grew = True
        if lo >= 0 and size + 1 + len(paragraphs[lo]) <= limit:
            parts.insert(0, paragraphs[lo]); size += 1 + len(paragraphs[lo]); lo -= 1; grew = True
        if not grew:
            break
    return " ".join(parts)


def detect_funding_channels(text):
    """Surse de finanțare menționate EXPLICIT în text."""
    norm = strip(text)
    return [
        label for label, words in FUNDING_CHANNELS
        if any(has_kw(norm, w) for w in words)
    ]


def _fp(text, n=300):
    return re.sub(r"\W+", " ", strip(text)).strip()[:n]


def extract_evidence(doc, keywords, category, variants=(), person_terms=(),
                     max_items=8, min_excerpt=100, require_person=True):
    """
    Dovezi extrase DOAR din textul sursei. Pentru educație/finanțare,
    fragmentul trebuie să menționeze persoana (nume complet sau nume de familie).
    """
    paragraphs = doc.get("paras", [])
    norms = doc.get("norm") or [strip(p) for p in paragraphs]
    terms = [t for t in list(variants) + list(person_terms) if t]
    result, seen = [], set()

    for i, p_norm in enumerate(norms):
        matched = [kw for kw in keywords if has_kw(p_norm, kw)]
        if not matched:
            continue

        def match(s_norm, _kws=matched):
            return any(has_kw(s_norm, k) for k in _kws)

        context = make_excerpt(paragraphs, i, match)
        if len(context) < min_excerpt:
            continue

        ctx_norm = strip(context)
        mentions_person = any(has_word(ctx_norm, t) for t in terms)
        if require_person and not mentions_person:
            continue

        channels = detect_funding_channels(paragraphs[i]) if category == "finanțare" else []
        if category == "finanțare" and len(matched) < 2 and not channels:
            continue  # "buget"/"bani" singur e prea generic

        key = _fp(context)
        if key in seen:
            continue
        seen.add(key)

        item = {
            "category": category,
            "keyword": matched[0],
            "excerpt": context,
            "mentions_politician_in_excerpt": mentions_person,
            "source_id": doc.get("id"),
            "source_url": doc.get("url"),
            "source_title": doc.get("title"),
            "source_domain": doc.get("domain"),
            "source_date": doc.get("date"),
            "source_author": doc.get("author", "Necunoscut"),
            "source_score": source_score(doc),
        }
        if category == "finanțare":
            item["funding_channels"] = channels
        result.append(item)

    result.sort(key=lambda x: (len(x.get("funding_channels", [])), len(x["excerpt"])), reverse=True)
    return result[:max_items]


def extract_relevant_article_evidence(doc, variants, max_items=6):
    """Fragmente generale din sursă care menționează politicianul."""
    paragraphs = doc.get("paras", [])
    norms = doc.get("norm") or [strip(p) for p in paragraphs]
    result, seen = [], set()

    for i, p_norm in enumerate(norms):
        if not any(has_word(p_norm, v) for v in variants if v):
            continue

        def match(s_norm):
            return any(has_word(s_norm, v) for v in variants if v)

        excerpt = make_excerpt(paragraphs, i, match, limit=900)
        if len(excerpt) < 120:
            continue
        key = _fp(excerpt, 250)
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "excerpt": excerpt,
            "source_id": doc.get("id"),
            "source_url": doc.get("url"),
            "source_title": doc.get("title"),
            "source_domain": doc.get("domain"),
            "source_date": doc.get("date"),
            "source_author": doc.get("author", "Necunoscut"),
            "source_score": source_score(doc),
        })
        if len(result) >= max_items:
            break
    return result


# ============================================================
# SPEECHES / STATEMENTS
# ============================================================

def find_speeches(doc, surname):
    """Stenograme: replica politicianului integral, până la următorul vorbitor."""
    result = []
    current = None
    target = strip(surname)

    def flush():
        if current:
            text = "\n".join(x for x in current["text"] if x).strip()
            if len(text) >= 150:
                result.append({"speaker": current["speaker"], "text": text})

    for paragraph in doc.get("paras", []):
        match = SPK.match(paragraph)
        if match:
            flush()
            speaker = match.group(1)
            if has_word(strip(speaker), target):
                current = {"speaker": speaker, "text": [match.group(2)]}
            else:
                current = None
        elif current:
            current["text"].append(paragraph)

    flush()
    return result


def find_statements(doc, surname):
    """
    Citate candidate: citat între ghilimele cu politicianul în proximitate.
    Nu pretinde verificare semantică a atribuirii.
    """
    paragraphs = doc.get("paras", [])
    norms = doc.get("norm") or [strip(p) for p in paragraphs]
    target = strip(surname)
    out, seen = [], set()

    for i, paragraph in enumerate(paragraphs):
        if not QUOTE.search(paragraph):
            continue
        window = " ".join(norms[max(0, i - 1): i + 2])
        if not has_word(window, target):
            continue
        same_paragraph = has_word(norms[i], target)

        for m in QUOTE.finditer(paragraph):
            quote = clean_text(m.group(1))
            if len(quote) < 40:
                continue
            key = _fp(quote, 400)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "text": quote,
                "context": paragraph,
                "attributed_same_paragraph": same_paragraph,
            })
    return out


def statement_is_promise(statement):
    norm = strip(statement)
    return any(has_kw(norm, k) for k in PROMISE_KEYWORDS)


# ============================================================
# DEDUP
# ============================================================

def dedupe_evidence(items):
    seen, result = set(), []
    for item in items:
        key = _fp(item.get("excerpt") or item.get("text") or item.get("source_url") or "", 400)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def dedupe_statements(items):
    seen, result = set(), []
    for item in items:
        key = _fp(item.get("text", ""), 400)
        if len(key) < 20 or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


# ============================================================
# REPORT
# ============================================================

def source_block(item):
    return (
        f"Sursă: {item.get('source_title') or 'Fără titlu'}\n"
        f"Site: {item.get('source_domain') or 'domeniu necunoscut'}\n"
        f"URL: {item.get('source_url') or 'URL necunoscut'}\n"
        f"Data: {item.get('source_date') or 'dată necunoscută'}\n"
        f"Autor: {item.get('source_author') or 'autor necunoscut'}"
    )


def report_text(result):
    politician = result.get("politician", "Politician necunoscut")
    stats = result.get("stats", {})
    L = []

    L.append(f"PROFIL POLITIC: {politician}")
    L.append("=" * 80)
    L.append("Raport generat automat din surse web și dovezi textuale, fără AI.")
    L.append(
        f"Surse analizate: {stats.get('sources', 0)} | "
        f"Discursuri: {stats.get('speeches', 0)} | "
        f"Declarații: {stats.get('statements', 0)}"
    )
    if stats.get("truncated"):
        L.append("ATENȚIE: analiza a atins limita de timp; rezultatele pot fi incomplete.")
    L.append("")

    L.append("1. EDUCAȚIA / STUDIILE POLITICIANULUI")
    L.append("-" * 80)
    education = result.get("education", [])
    if not education:
        L.append("Nu a fost găsită în sursele analizate o dovadă textuală suficient de clară despre educație.")
        L.append("Nu este completată din memorie sau presupuneri.")
    for idx, item in enumerate(education, 1):
        L.append(f"[{idx}]")
        L.append(source_block(item))
        L.append(f"Fragment relevant:\n„{item['excerpt']}”")
        L.append("")

    L.append("2. DE UNDE VIN BANII / CUM SE FINANȚEAZĂ")
    L.append("-" * 80)
    funding = result.get("funding", [])
    if not funding:
        L.append("Nu a fost găsită o dovadă textuală suficient de clară despre sursa finanțării.")
        L.append("Nu presupunem sursa unei finanțări fără un fragment care să o susțină.")
    for idx, item in enumerate(funding, 1):
        L.append(f"[{idx}]")
        L.append(source_block(item))
        channels = item.get("funding_channels", [])
        if channels:
            L.append("Sursa banilor menționată explicit: " + ", ".join(channels))
        L.append(f"Fragment relevant:\n„{item['excerpt']}”")
        L.append("")

    L.append("3. DECLARAȚII / PROMISIUNI")
    L.append("-" * 80)
    statements = result.get("statements", [])
    if not statements:
        L.append("Nu au fost identificate citate candidate suficient de clare.")
    for idx, item in enumerate(statements[:30], 1):
        L.append(f"[{idx}]")
        L.append(source_block(item))
        L.append(f"Declarație: „{item.get('text', '')}”")
        if item.get("is_promise"):
            L.append("Indicator keyword: posibilă promisiune/angajament")
        if not item.get("attributed_same_paragraph", True):
            L.append("Notă: numele apare în paragraful vecin, nu în același paragraf; atribuire de verificat.")
        L.append("")

    L.append("4. DISCURSURI / STENOGRAME")
    L.append("-" * 80)
    speeches = result.get("speeches", [])
    if not speeches:
        L.append("Nu au fost identificate discursuri/replici suficient de clare.")
    for idx, item in enumerate(speeches[:20], 1):
        L.append(f"[{idx}]")
        L.append(source_block(item))
        excerpt = item.get("text", "")
        if len(excerpt) > 2500:
            excerpt = excerpt[:2500].rstrip() + "…"
        L.append(f"Text:\n{excerpt}")
        L.append("")

    L.append("5. SURSE RELEVANTE")
    L.append("-" * 80)
    for idx, item in enumerate(result.get("sources", [])[:30], 1):
        L.append(f"[{idx}] {item.get('title') or 'Fără titlu'} ({item.get('domain') or 'domeniu necunoscut'})")
        L.append(f"URL: {item.get('url')}")
        L.append(f"Data: {item.get('date') or 'necunoscută'}")
        L.append(f"Autor: {item.get('author') or 'necunoscut'}")
        L.append(f"Tip: {item.get('kind')}")
        L.append(f"Scor sursă: {item.get('source_score', 0)}/100")
        for ev in item.get("evidence", [])[:2]:
            L.append(f"  • {ev}")
        L.append("")

    return "\n".join(L).strip()


# ============================================================
# MAIN ANALYSIS
# ============================================================

def _year_of(date):
    try:
        return int(str(date)[:4])
    except (TypeError, ValueError):
        return None


def _date_of(item):
    return item.get("date") or item.get("source_date") or ""


def analyze(
    name,
    extra_urls=(),
    on_progress=None,
    include_text=False,
    aliases=(),
    domains=(),
    speed="fast",
    since_year=None,
    depth=None,
    max_sources=None,
    budget=None,
    term=None,
):
    """
    Returnează dict cu: politician, generated_at, stats, education[], funding[],
    sources[], speeches[], statements[], report.

    Educația și finanțarea apar doar cu dovezi textuale; fiecare dovadă
    păstrează sursa și URL-ul. Documentele mai vechi decât `since_year` sunt
    folosite doar pentru educație (o biografie rămâne valabilă).
    """
    name = clean_text(name)
    if len(name.split()) < 2:
        raise ValueError("Dă numele complet (prenume + nume).")
    if speed not in PRESETS:
        raise ValueError("speed trebuie să fie fast, normal sau deep.")

    extra_urls = [u for u in (normalize_url(x) for x in _as_list(extra_urls)) if u]
    aliases = [clean_text(a) for a in _as_list(aliases) if clean_text(a)]
    domains = [clean_text(d).lower() for d in _as_list(domains) if clean_text(d)]

    token = _progress.set(on_progress or (lambda m: None))
    try:
        P = dict(PRESETS[speed])
        for k, v in (("max_sources", max_sources), ("depth", depth), ("budget", budget)):
            if v is not None:
                P[k] = v

        cutoff_year = since_year if since_year is not None else time.localtime().tm_year - P["since_back"]
        start = time.time()
        deadline = start + P["budget"]

        # termenul după care se atribuie declarațiile: implicit numele de familie; pentru partide, sigla (ex. "PSD")
        surname = clean_text(term) if term else name.split()[-1]
        full_variants = name_variants(name, aliases)
        person_terms = [surname]

        # ---------------- DISCOVERY ----------------
        found = discover(
            name,
            extra_urls=extra_urls,
            aliases=aliases,
            domains=domains,
            since_year=cutoff_year,
            max_queries=P["max_queries"],
            pages=P["pages"],
            deadline=start + 0.45 * P["budget"],
        )

        extra_set = set(extra_urls)

        def initial_rank(item):
            url = item[0]
            if url in extra_set:
                return -100
            if is_official_domain(hostname(url)):
                return 0
            if KW_URL.search(strip(url)):
                return 1
            return 2

        ranked = sorted(found.items(), key=initial_rank)
        limit = max(P["max_sources"], len(extra_set))
        ranked = ranked[:limit]

        _log(f"Descarc {len(ranked)} pagini...")

        def fetch_task(item, _deadline=deadline):
            if time.time() >= _deadline:
                return None
            return fetch(item[0], item[1])

        downloaded = _pmap(fetch_task, ranked, 12)

        docs, seen_urls = [], set(found)
        for doc in downloaded:
            if not doc:
                continue
            seen_urls.add(doc["url"])
            if relevant_document(doc, full_variants):
                docs.append(doc)

        # ---------------- CRAWL INTERN ----------------
        for rnd in range(P["depth"]):
            if time.time() >= deadline:
                break
            candidates = {}
            for doc in docs:
                for href, text in doc.get("links", []):
                    if href in seen_urls or href in candidates:
                        continue
                    if hostname(href) != doc.get("domain"):
                        continue
                    if urllib.parse.urlsplit(href).path.lower().endswith(SKIP_EXT):
                        continue
                    clue = strip(text + " " + href)
                    if any(has_word(clue, v) for v in full_variants) or KW_URL.search(clue):
                        candidates[href] = ""

            batch = list(candidates.items())[: P["crawl_cap"]]
            if not batch:
                break
            seen_urls.update(u for u, _ in batch)
            _log(f"Crawl runda {rnd + 1}: {len(batch)} linkuri")

            for doc in _pmap(fetch_task, batch, 12):
                if doc and doc["url"] not in {d["url"] for d in docs}:
                    seen_urls.add(doc["url"])
                    if relevant_document(doc, full_variants):
                        docs.append(doc)

        docs = list({d["url"]: d for d in docs}.values())

        # ---------------- ANALYSIS ----------------
        speeches, statements, education, funding, kept = [], [], [], [], []

        for i, doc in enumerate(docs, 1):
            _log(f"Analizez {i}/{len(docs)}")

            year = _year_of(doc.get("date"))
            old = year is not None and year < cutoff_year

            doc["kind"] = article_kind(doc)
            doc["source_score"] = source_score(doc)
            blob = "\n".join(doc["norm"])
            doc["mentions"] = sum(
                len(_rx_word(strip(v)).findall(blob)) for v in full_variants
            )
            doc["evidence"] = [
                x["excerpt"]
                for x in extract_relevant_article_evidence(doc, full_variants, max_items=4)
            ]

            edu = extract_evidence(
                doc, EDUCATION_KEYWORDS, "educație",
                variants=full_variants, person_terms=person_terms, max_items=4,
            )
            if old and not edu:
                continue

            education.extend(edu)
            speech_items = [] if old else find_speeches(doc, surname)
            doc["primary"] = bool(speech_items) or is_official_domain(doc.get("domain", ""))
            kept.append(doc)

            if old:
                continue

            funding.extend(
                extract_evidence(
                    doc, FUNDING_KEYWORDS, "finanțare",
                    variants=full_variants, person_terms=person_terms, max_items=5,
                )
            )

            meta = {
                "source_id": doc["id"],
                "source_url": doc["url"],
                "source_title": doc["title"],
                "source_domain": doc["domain"],
                "source_date": doc["date"],
                "source_author": doc.get("author", "Necunoscut"),
                "source_score": doc["source_score"],
                "date": doc["date"],
                "author": doc.get("author", "Necunoscut"),
            }

            for speech in speech_items:
                speeches.append({
                    "id": hashlib.sha256((doc["id"] + speech["text"][:400]).encode("utf-8")).hexdigest()[:12],
                    **meta,
                    "speaker": speech["speaker"],
                    "text": speech["text"],
                })

            for st in find_statements(doc, surname):
                statements.append({
                    "id": hashlib.sha256((doc["id"] + st["text"]).encode("utf-8")).hexdigest()[:12],
                    **meta,
                    "text": st["text"],
                    "context": st["context"],
                    "attributed_same_paragraph": st["attributed_same_paragraph"],
                    "is_promise": statement_is_promise(st["text"]),
                })

        # ---------------- DEDUPE + SORT ----------------
        education = dedupe_evidence(education)
        funding = dedupe_evidence(funding)
        statements = dedupe_statements(statements)

        education.sort(key=lambda x: (x.get("source_score", 0), _date_of(x)), reverse=True)
        for lst in (funding, speeches, statements):
            lst.sort(key=lambda x: (_date_of(x), x.get("source_score", 0)), reverse=True)
        statements.sort(key=lambda x: x.get("attributed_same_paragraph", False), reverse=True)

        sources = []
        for doc in kept:
            source = {
                "id": doc["id"],
                "url": doc["url"],
                "domain": doc["domain"],
                "title": doc["title"],
                "date": doc["date"],
                "author": doc.get("author", "Necunoscut"),
                "kind": doc["kind"],
                "primary": doc["primary"],
                "mentions": doc["mentions"],
                "source_score": doc["source_score"],
                "evidence": doc.get("evidence", []),
            }
            if include_text:
                source["text"] = document_text(doc)
            sources.append(source)
        sources.sort(key=lambda x: (x.get("source_score", 0), x.get("date") or ""), reverse=True)

        result = {
            "politician": name,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "stats": {
                "sources": len(kept),
                "speeches": len(speeches),
                "statements": len(statements),
                "education_evidence": len(education),
                "funding_evidence": len(funding),
                "elapsed_s": round(time.time() - start, 1),
                "truncated": time.time() >= deadline,
                "speed": speed,
                "ai_enabled": False,
            },
            "education": education[:30],
            "funding": funding[:40],
            "sources": sources,
            "speeches": speeches[:100],
            "statements": statements[:100],
        }
        result["report"] = report_text(result)
        _log("Gata")
        return result
    finally:
        _progress.reset(token)


# ============================================================
# HTTP API
# ============================================================

JOBS = {}       # job_id -> job
JOB_KEYS = {}   # (nume, opțiuni) -> job
JLOCK = threading.Lock()


def _finished_job(result, key):
    """Un job deja terminat, cu rezultatul citit de pe disc: răspunde imediat, fără să genereze nimic."""
    job = {"job_id": uuid.uuid4().hex[:12], "status": "done", "progress": "Din cache (disc)", "result": result,
           "error": None, "done": threading.Event(), "t": time.time()}
    job["done"].set()
    with JLOCK:
        JOBS[job["job_id"]] = job
        JOB_KEYS[key] = job
    return job
_SLOTS = threading.BoundedSemaphore(MAX_PARALLEL_JOBS)


def _to_int(v, lo, hi, label):
    if isinstance(v, bool):
        raise ValueError(f"{label} invalid")
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise ValueError(f"{label} invalid")
    if not lo <= n <= hi:
        raise ValueError(f"{label} trebuie să fie între {lo} și {hi}")
    return n


def _clean_opts(raw):
    """Validează opțiunile primite prin API (GET/POST)."""
    opts = {}
    for key in ("extra_urls", "aliases", "domains"):
        if key in raw and raw[key] not in (None, ""):
            values = _as_list(raw[key])
            if not all(isinstance(x, str) for x in values) or len(values) > 100:
                raise ValueError(f"{key} trebuie să fie listă de texte")
            opts[key] = values
    if "speed" in raw and raw["speed"] not in (None, ""):
        if raw["speed"] not in PRESETS:
            raise ValueError("speed trebuie să fie fast, normal sau deep.")
        opts["speed"] = raw["speed"]
    if raw.get("term") not in (None, ""):
        if not isinstance(raw["term"], str) or len(raw["term"]) > 60:
            raise ValueError("term trebuie să fie un text scurt")
        opts["term"] = clean_text(raw["term"])
    if raw.get("include_text") in (True, 1, "1", "true"):
        opts["include_text"] = True
    ranges = {
        "since_year": (1990, time.localtime().tm_year),
        "depth": (0, 4),
        "max_sources": (1, 2000),
        "budget": (10, 7200),
    }
    for key, (lo, hi) in ranges.items():
        if key in raw and raw[key] not in (None, ""):
            opts[key] = _to_int(raw[key], lo, hi, key)
    return opts


def start_job(name, opts=None, refresh=False):
    name = clean_text(name)
    if len(name.split()) < 2:
        raise ValueError("Parametrul 'name' trebuie să conțină numele complet.")
    opts = _clean_opts(opts or {})

    key = (name.lower(), json.dumps(opts, sort_keys=True, ensure_ascii=False))
    cache_extra = key[1]
    if not refresh:
        hit = diskcache.get("analysis", name, cache_extra)
        if hit is not None:
            return _finished_job(hit, key)

    with JLOCK:
        now = time.time()
        for jid in [j for j, v in JOBS.items()
                    if v["status"] != "running" and now - v["t"] > JOB_TTL_SECONDS]:
            JOBS.pop(jid, None)
        for k in [k for k, v in JOB_KEYS.items() if v["job_id"] not in JOBS]:
            JOB_KEYS.pop(k, None)

        existing = JOB_KEYS.get(key)
        if (
            existing
            and not refresh
            and existing["status"] != "error"
            and (existing["status"] == "running" or now - existing["t"] < JOB_CACHE_SECONDS)
        ):
            return existing

        job = {
            "job_id": uuid.uuid4().hex[:12],
            "status": "running",
            "progress": "Pornit",
            "result": None,
            "error": None,
            "done": threading.Event(),
            "t": now,
        }
        JOBS[job["job_id"]] = job
        JOB_KEYS[key] = job

    def work():
        try:
            job["progress"] = "În coadă"
            with _SLOTS:
                job["progress"] = "Pornit"
                job["result"] = analyze(
                    name,
                    on_progress=lambda msg: job.__setitem__("progress", msg),
                    **opts,
                )
            job["status"] = "done"
            diskcache.put("analysis", name, job["result"], cache_extra)
        except Exception as exc:
            job["error"] = str(exc)
            job["status"] = "error"
        finally:
            job["t"] = time.time()
            job["done"].set()

    threading.Thread(target=work, daemon=True).start()
    return job


def who_opts(query_or_data):
    """aliases + term din cererea site-ului (GET query sau JSON), ca joburile să refolosească aceeași analiză."""
    aliases = query_or_data.get("alias") or query_or_data.get("aliases") or []
    if isinstance(aliases, str):
        aliases = [aliases]
    term = query_or_data.get("term") or ""
    if isinstance(term, list):
        term = term[0] if term else ""
    out = {}
    if aliases:
        out["aliases"] = [a for a in aliases if isinstance(a, str)]
    if term:
        out["term"] = term
    return out


def start_orientation_job(name, refresh=False, num_ctx=None, speed="normal", who=None):
    """Scoruri 1..5 pe 10 axe, calculate prin Groq din textele surselor (vezi orientation_llm.py).
    Refolosește aceeași analiză ca /analyze?include_text=1, ca să nu se scrapuiască de două ori."""
    name = clean_text(name)
    if len(name.split()) < 2:
        raise ValueError("Parametrul 'name' trebuie să conțină numele complet.")
    who = who or {}
    key = ("orientation", name.lower(), num_ctx, speed, json.dumps(who, sort_keys=True))
    cache_extra = f"{speed}|{json.dumps(who, sort_keys=True)}"
    if not refresh:
        hit = diskcache.get("orientation", name, cache_extra)
        if hit is not None:
            return _finished_job(hit, key)
    with JLOCK:
        existing = JOB_KEYS.get(key)
        if existing and not refresh and (existing["status"] == "running" or (
                existing["status"] == "done" and time.time() - existing["t"] < JOB_CACHE_SECONDS)):
            return existing
        job = {"job_id": uuid.uuid4().hex[:12], "status": "running", "progress": "Pornit",
               "result": None, "error": None, "done": threading.Event(), "t": time.time()}
        JOBS[job["job_id"]] = job
        JOB_KEYS[key] = job

    def work():
        try:
            import importlib
            import orientation_llm as ol
            importlib.reload(ol)
            src = start_job(name, {"include_text": True, "speed": speed, **who}, refresh=refresh)
            while not src["done"].wait(2):
                job["progress"] = "Analiza surselor: " + str(src["progress"])
            if src["status"] == "error":
                raise RuntimeError(src["error"])
            job["progress"] = "Modelul evaluează axele..."
            job["result"] = ol.score_orientation(
                src["result"], name, on_progress=lambda m: job.__setitem__("progress", m), term=who.get("term"))
            job["status"] = "done"
            diskcache.put("orientation", name, job["result"], cache_extra)
        except Exception as exc:
            job["error"], job["status"] = str(exc), "error"
        finally:
            job["t"] = time.time()
            job["done"].set()

    threading.Thread(target=work, daemon=True).start()
    return job


def start_summary_job(name, refresh=False, speed="normal"):
    """Rezumate în română prin Groq / Claude API (vezi summarize_llm.py): educație, declarație de venit și fiecare sursă recentă.
    Refolosește aceeași analiză ca /analyze?include_text=1. Costă: se pornește doar la cerere explicită."""
    name = clean_text(name)
    if len(name.split()) < 2:
        raise ValueError("Parametrul 'name' trebuie să conțină numele complet.")
    key = ("summaries", name.lower(), speed)
    with JLOCK:
        existing = JOB_KEYS.get(key)
        if existing and not refresh and (existing["status"] == "running" or (
                existing["status"] == "done" and time.time() - existing["t"] < JOB_CACHE_SECONDS)):
            return existing
        job = {"job_id": uuid.uuid4().hex[:12], "status": "running", "progress": "Pornit",
               "result": None, "error": None, "done": threading.Event(), "t": time.time()}
        JOBS[job["job_id"]] = job
        JOB_KEYS[key] = job

    def work():
        try:
            import importlib
            import summarize_llm as sm
            importlib.reload(sm)
            sm.check_access(sm.make_client())      # eșuează devreme (fără cheie), înainte de minutele de scraping
            src = start_job(name, {"include_text": True, "speed": speed}, refresh=refresh)
            while not src["done"].wait(2):
                job["progress"] = "Analiza surselor: " + str(src["progress"])
            if src["status"] == "error":
                raise RuntimeError(src["error"])
            job["progress"] = f"{sm.MODEL} scrie rezumatele..."
            job["result"] = sm.summarize_all(
                src["result"], name, on_progress=lambda m: job.__setitem__("progress", m))
            job["status"] = "done"
        except Exception as exc:
            job["error"], job["status"] = str(exc), "error"
        finally:
            job["t"] = time.time()
            job["done"].set()

    threading.Thread(target=work, daemon=True).start()
    return job


def start_summary_one_job(name, data):
    """Un singur rezumat, la cerere: kind=article (pornind de la url-ul articolului, descărcat acum) sau
    kind=education / income (pornind de la fragmentele trimise de site). Nu depinde de analiza din memorie."""
    name = clean_text(name)
    if len(name.split()) < 2:
        raise ValueError("Parametrul 'name' trebuie să conțină numele complet.")
    kind = data.get("kind")
    if kind not in ("article", "education", "income"):
        raise ValueError("kind trebuie să fie article, education sau income.")
    url = None
    if kind == "article":
        url = normalize_url(data.get("url") or "")
        if not url or not is_public_url(url):
            raise ValueError("url invalid.")
        ident = url
    else:
        items = data.get("items")
        if not isinstance(items, list) or not items or len(items) > 60 or not all(isinstance(x, dict) for x in items):
            raise ValueError("items trebuie să fie o listă nevidă de fragmente.")
        ident = hashlib.sha256(json.dumps(items, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    key = ("summary-one", name.lower(), kind, ident)
    cache_extra = f"{kind}|{ident}"
    if not data.get("force"):
        hit = diskcache.get("summary", name, cache_extra)
        if hit is not None:
            return _finished_job(hit, key)
    with JLOCK:
        existing = JOB_KEYS.get(key)
        if existing and not data.get("force") and (existing["status"] == "running" or (
                existing["status"] == "done" and time.time() - existing["t"] < JOB_CACHE_SECONDS)):
            return existing
        job = {"job_id": uuid.uuid4().hex[:12], "status": "running", "progress": "Pornit",
               "result": None, "error": None, "done": threading.Event(), "t": time.time()}
        JOBS[job["job_id"]] = job
        JOB_KEYS[key] = job

    def work():
        try:
            import importlib
            import summarize_llm as sm
            importlib.reload(sm)
            client = sm.make_client()
            sm.check_access(client)
            if kind == "article":
                job["progress"] = "Descarc articolul..."
                doc = fetch(url)
                if not doc:
                    raise RuntimeError("Nu am putut descărca articolul.")
                material = sm.doc_material(document_text(doc), data.get("term") or name.split()[-1])
            else:
                material = sm.evidence_material(items)
            job["progress"] = f"{sm.MODEL} scrie rezumatul..."
            usage = {"input": 0, "output": 0, "calls": 0, "cached": 0}
            res = sm.summarize_one(client, "article" if kind == "article" else kind, name, material, usage)
            job["result"] = {"kind": kind, "model": sm.MODEL, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                             "summary": res, "usage": usage}      # summary=None: materialul nu spune nimic despre politician
            job["status"] = "done"
            diskcache.put("summary", name, job["result"], cache_extra)
        except Exception as exc:
            job["error"], job["status"] = str(exc), "error"
        finally:
            job["t"] = time.time()
            job["done"].set()

    threading.Thread(target=work, daemon=True).start()
    return job


FACTCHECK_MAX_NEWS = 20           # MVP: erori logice doar în ultimele 20 de știri din „Discursuri și promisiuni”, pentru viteză
FACTCHECK_PER_NEWS = 3            # și cel mult 3 declarații pe știre (un apel al modelului pe știre, ~1 minut fiecare)


def latest_speech_news(scraped, limit=FACTCHECK_MAX_NEWS, per_news=FACTCHECK_PER_NEWS, since=""):
    """Rezultatul scraper-ului restrâns la cele mai recente `limit` surse cu discursuri sau citate (cele din „Discursuri și promisiuni”),
    cu cel mult `per_news` declarații din fiecare (discursurile primele)."""
    with_stmt = {x.get("source_id") for k in ("speeches", "statements") for x in scraped.get(k, [])}
    dated = [s for s in scraped.get("sources", []) if s["id"] in with_stmt and s.get("date") and s["date"] >= since]
    keep = {s["id"] for s in sorted(dated, key=lambda s: s["date"], reverse=True)[:limit]}
    taken = {}

    def first_n(items):
        out = []
        for x in items:
            sid = x.get("source_id")
            if sid in keep and taken.get(sid, 0) < per_news:
                taken[sid] = taken.get(sid, 0) + 1
                out.append(x)
        return out

    speeches = first_n(scraped.get("speeches", []))
    statements = first_n(scraped.get("statements", []))
    return {**scraped, "sources": [s for s in scraped.get("sources", []) if s["id"] in keep],
            "speeches": speeches, "statements": statements}


def start_credibility_job(name, refresh=False, speed="normal"):
    """Scorul de credibilitate (1..10), calculat prin Groq din erorile logice (vezi credibility_llm.py).
    Rulează întâi (sau refolosește) analiza erorilor logice a aceluiași politician."""
    name = clean_text(name)
    if len(name.split()) < 2:
        raise ValueError("Parametrul 'name' trebuie să conțină numele complet.")
    key = ("credibility", name.lower(), speed)
    cache_extra = speed
    if not refresh:
        hit = diskcache.get("credibility", name, cache_extra)
        if hit is not None:
            return _finished_job(hit, key)
    with JLOCK:
        existing = JOB_KEYS.get(key)
        if existing and not refresh and (existing["status"] == "running" or (
                existing["status"] == "done" and time.time() - existing["t"] < JOB_CACHE_SECONDS)):
            return existing
        job = {"job_id": uuid.uuid4().hex[:12], "status": "running", "progress": "Pornit",
               "result": None, "error": None, "done": threading.Event(), "t": time.time()}
        JOBS[job["job_id"]] = job
        JOB_KEYS[key] = job

    def work():
        try:
            import importlib
            import credibility_llm as cl
            importlib.reload(cl)
            fcjob = start_factcheck_job(name, refresh, speed)
            while not fcjob["done"].wait(2):
                job["progress"] = "Erori logice: " + str(fcjob["progress"])
            if fcjob["status"] == "error":
                raise RuntimeError(fcjob["error"])
            job["progress"] = "Calculez scorul de credibilitate..."
            job["result"] = cl.score_credibility(fcjob["result"], name, on_progress=lambda m: job.__setitem__("progress", m))
            job["status"] = "done"
            diskcache.put("credibility", name, job["result"], cache_extra)
        except Exception as exc:
            job["error"], job["status"] = str(exc), "error"
        finally:
            job["t"] = time.time()
            job["done"].set()

    threading.Thread(target=work, daemon=True).start()
    return job


def start_factcheck_job(name, refresh=False, speed="normal", max_passages=FACTCHECK_MAX_NEWS * FACTCHECK_PER_NEWS, max_pairs=0):
    """Erori logice / contradicții / afirmații suspecte, prin Groq (pool de modele), la cerere (vezi fact_checker_api.py).
    Refolosește aceeași analiză ca /analyze?include_text=1, ca să nu se scrapuiască de două ori."""
    name = clean_text(name)
    if len(name.split()) < 2:
        raise ValueError("Parametrul 'name' trebuie să conțină numele complet.")
    key = ("factcheck", name.lower(), speed, max_passages, max_pairs)
    cache_extra = f"{speed}|{max_passages}|{max_pairs}"
    if not refresh:
        hit = diskcache.get("factcheck", name, cache_extra)
        if hit is not None:
            return _finished_job(hit, key)
    with JLOCK:
        existing = JOB_KEYS.get(key)
        if existing and not refresh and (existing["status"] == "running" or (
                existing["status"] == "done" and time.time() - existing["t"] < JOB_CACHE_SECONDS)):
            return existing
        job = {"job_id": uuid.uuid4().hex[:12], "status": "running", "progress": "Pornit",
               "result": None, "error": None, "done": threading.Event(), "t": time.time()}
        JOBS[job["job_id"]] = job
        JOB_KEYS[key] = job

    def work():
        try:
            import importlib
            import fact_checker_api as fc
            importlib.reload(fc)
            fc.preflight()
            src = start_job(name, {"include_text": True, "speed": speed}, refresh=refresh)
            while not src["done"].wait(2):
                job["progress"] = "Analiza surselor: " + str(src["progress"])
            if src["status"] == "error":
                raise RuntimeError(src["error"])
            since = time.strftime("%Y-%m-%d", time.localtime(time.time() - 365 * 86400))
            scraped = latest_speech_news(src["result"], since=since)
            job["progress"] = f"{len(scraped['sources'])} știri ({len(scraped['speeches']) + len(scraped['statements'])} declarații) de analizat..."
            job["result"] = fc.fact_check(
                name, language="ro", max_passages=max_passages, max_pairs=max_pairs, scraped=scraped,
                include_reported=False,            # doar „Discursuri și promisiuni”: stenograme și citate, nu articolele din presă
                since_date=since,                  # aceeași fereastră de 12 luni ca în site
                on_progress=lambda m: job.__setitem__("progress", m))
            job["status"] = "done"
            diskcache.put("factcheck", name, job["result"], cache_extra)
        except Exception as exc:
            job["error"], job["status"] = str(exc), "error"
        finally:
            job["t"] = time.time()
            job["done"].set()

    threading.Thread(target=work, daemon=True).start()
    return job


_METH = {"sig": None, "data": None}


def methodology_data():
    """Tot ce arată pagina „Metodologie”, citit din cod și din ce s-a salvat efectiv: nimic nu e scris de mână, deci nu se poate desprinde de realitate."""
    import glob, os
    from collections import Counter
    import credibility_llm as cl
    import fact_checker_api as fc
    import orientation_llm as ol
    import summarize_llm as sm
    import llm

    files = sorted(glob.glob(os.path.join(diskcache.CACHE_DIR, "analysis", "*.json")))
    sig = [(f, os.path.getmtime(f)) for f in files]
    if sig != _METH["sig"]:
        domains, politicians = {}, []
        for f in files:
            try:
                entry = json.load(open(f, encoding="utf-8"))
                res = entry["value"]
            except (OSError, ValueError, KeyError):
                continue
            with_stmt = Counter(x.get("source_id") for k in ("speeches", "statements") for x in res.get(k, []))
            politicians.append({"name": entry.get("name"), "sources": len(res.get("sources", [])), "speeches": len(res.get("speeches", [])),
                                "statements": len(res.get("statements", [])), "education_fragments": len(res.get("education", [])),
                                "funding_fragments": len(res.get("funding", [])), "generated_at": res.get("generated_at")})
            for s in res.get("sources", []):
                d = domains.setdefault(s.get("domain"), {"domain": s.get("domain"), "sources": 0, "with_statements": 0,
                                                         "official": is_official_domain(s.get("domain")), "politicians": set()})
                d["sources"] += 1
                d["with_statements"] += 1 if with_stmt.get(s.get("id")) else 0
                d["politicians"].add(entry.get("name"))
        rows = sorted(({**d, "politicians": sorted(d["politicians"])} for d in domains.values() if d["domain"]),
                      key=lambda d: (-d["sources"], d["domain"]))
        _METH["sig"], _METH["data"] = sig, {"domains": rows, "politicians": politicians}
    cached = _METH["data"]
    preset = PRESETS["normal"]
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "domains": cached["domains"], "politicians": cached["politicians"],
        "cache": diskcache.inventory(),
        "search": {"engine": "Bing (flux RSS: căutare web + Bing News)", "locale": "ro-RO", "pages_per_query": preset["pages"],
                   "results_per_page": 50, "max_queries": preset["max_queries"], "query_templates": BASE_TEMPLATES,
                   "education_words": EDUCATION_QUERY_WORDS, "funding_words": FUNDING_QUERY_WORDS},
        "fetch": {"max_sources": preset["max_sources"], "crawl_depth": preset["depth"], "crawl_cap": preset["crawl_cap"],
                  "time_budget_s": preset["budget"], "years_back": preset["since_back"], "user_agent": UA, "min_chars": 300,
                  "skipped_extensions": list(SKIP_EXT)},
        "official_domains": OFFICIAL,
        "promise_keywords": PROMISE_KEYWORDS, "education_keywords": EDUCATION_KEYWORDS, "funding_keywords": FUNDING_KEYWORDS,
        "factcheck": {"max_news": FACTCHECK_MAX_NEWS, "per_news": FACTCHECK_PER_NEWS, "window_days": 365, "models": fc.MODELS,
                      "temperature": fc.SAMPLING["temperature"], "categories": fc.CATEGORIES, "max_findings_per_call": fc.MAX_FINDINGS_PER_CALL},
        "credibility": {"weights": cl.WEIGHTS, "model": cl.MODEL, "fallbacks": cl.FALLBACKS, "temperature": cl.OPTIONS["temperature"],
                        "max_findings": cl.MAX_FINDINGS, "articles_per_batch": cl.ARTICLES_PER_BATCH},
        "orientation": {"model": ol.MODEL, "fallbacks": ol.FALLBACKS, "temperature": ol.OPTIONS["temperature"], "axes": [a[0] for a in ol.AXES],
                        "max_context_chars": ol.MAX_CONTEXT_CHARS},
        "summaries": {"model": sm.MODEL, "fallbacks": sm.FALLBACKS, "temperature": sm.TEMPERATURE, "max_doc_chars": sm.MAX_DOC_CHARS},
        "provider": {"name": "Groq", "tpm_limit": llm.TPM_LIMIT, "request_token_cap": llm.REQUEST_TOKEN_CAP},
    }


def public(job):
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "progress": job["progress"],
        "error": job["error"],
        "result": job["result"],
        "status_url": f"/jobs/{job['job_id']}",
    }


class H(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _headers(self, code, length=0):
        self.send_response(code)
        for key, value in (
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(length)),
            ("Access-Control-Allow-Origin", CORS_ORIGIN),
            ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type"),
        ):
            self.send_header(key, value)
        self.end_headers()

    def reply(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        try:
            self._headers(code, len(body))
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_OPTIONS(self):
        self._headers(204)

    def go(self, name, opts, refresh, wait):
        try:
            job = start_job(name, opts, refresh=refresh)
        except (ValueError, TypeError) as exc:
            return self.reply(400, {"error": str(exc)})

        if wait:
            job["done"].wait()

        status = {"done": 200, "error": 500}.get(job["status"], 202)
        self.reply(status, public(job))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        path = parsed.path.rstrip("/") or "/"

        if path == "/methodology":
            try:
                return self.reply(200, methodology_data())
            except Exception as exc:
                return self.reply(500, {"error": f"{type(exc).__name__}: {exc}"})

        if path == "/cached":
            # doar citește de pe disc ce a fost generat deja; nu pornește niciodată o generare
            kind = (query.get("kind") or [""])[0]
            name = clean_text((query.get("name") or [""])[0])
            speed = (query.get("speed") or ["normal"])[0]
            extras = {"credibility": speed, "factcheck": f"{speed}|{FACTCHECK_MAX_NEWS * FACTCHECK_PER_NEWS}|0",
                      "orientation": f"{speed}|{json.dumps(who_opts(query), sort_keys=True)}"}
            if kind not in extras or len(name.split()) < 2:
                return self.reply(400, {"error": "kind trebuie să fie credibility, factcheck sau orientation, iar name numele complet."})
            hit = diskcache.get(kind, name, extras[kind])
            return self.reply(200, {"found": hit is not None, "result": hit})

        if path == "/cache":
            return self.reply(200, {"dir": diskcache.CACHE_DIR, "entries": diskcache.inventory()})

        if path == "/health":
            return self.reply(200, {"ok": True})

        if path.startswith("/jobs/"):
            job = JOBS.get(path[6:])
            if not job:
                return self.reply(404, {"error": "job inexistent"})
            return self.reply(200, public(job))

        if path == "/summaries":
            try:
                job = start_summary_job((query.get("name") or [""])[0], query.get("force") == ["1"],
                                        (query.get("speed") or ["normal"])[0])
            except (ValueError, TypeError) as exc:
                return self.reply(400, {"error": str(exc)})
            if query.get("wait") == ["1"]:
                job["done"].wait()
            return self.reply({"done": 200, "error": 500}.get(job["status"], 202), public(job))

        if path == "/credibility":
            try:
                job = start_credibility_job((query.get("name") or [""])[0], query.get("force") == ["1"],
                                            (query.get("speed") or ["normal"])[0])
            except (ValueError, TypeError) as exc:
                return self.reply(400, {"error": str(exc)})
            if query.get("wait") == ["1"]:
                job["done"].wait()
            return self.reply({"done": 200, "error": 500}.get(job["status"], 202), public(job))

        if path == "/factcheck":
            try:
                job = start_factcheck_job((query.get("name") or [""])[0], query.get("force") == ["1"],
                                          (query.get("speed") or ["normal"])[0])
            except (ValueError, TypeError) as exc:
                return self.reply(400, {"error": str(exc)})
            if query.get("wait") == ["1"]:
                job["done"].wait()
            return self.reply({"done": 200, "error": 500}.get(job["status"], 202), public(job))

        if path == "/orientation":
            try:
                n = (query.get("num_ctx") or [""])[0]
                job = start_orientation_job(
                    (query.get("name") or [""])[0], query.get("force") == ["1"],
                    int(n) if n.isdigit() else None, (query.get("speed") or ["normal"])[0], who_opts(query))
            except (ValueError, TypeError) as exc:
                return self.reply(400, {"error": str(exc)})
            if query.get("wait") == ["1"]:
                job["done"].wait()
            return self.reply({"done": 200, "error": 500}.get(job["status"], 202), public(job))

        if path == "/analyze":
            raw = {
                "extra_urls": query.get("url"),
                "aliases": query.get("alias"),
                "domains": query.get("domain"),
                "include_text": (query.get("include_text") or [""])[0],
                "term": (query.get("term") or [""])[0],
            }
            for key in ("speed", "depth", "since_year", "max_sources", "budget"):
                if query.get(key):
                    raw[key] = query[key][0]
            return self.go(
                query.get("name", [""])[0],
                raw,
                query.get("force") == ["1"],
                query.get("wait") == ["1"],
            )

        if path == "/":
            return self.reply(200, {"endpoints": {
                "GET /analyze?name=Prenume+Nume": "caută surse și extrage automat informații",
                "GET /analyze?name=...&wait=1": "așteaptă până la final",
                "POST /analyze": "aceleași opțiuni prin JSON",
                "GET /jobs/<job_id>": "status + rezultat",
                "GET /orientation?name=...[&speed=normal][&refresh=1][&wait=1]": "scoruri 1..5 pe 10 axe, calculate prin Groq (openai/gpt-oss-20b)",
                "GET /summaries?name=...[&speed=normal][&refresh=1][&wait=1]": "rezumate în română prin Groq (qwen/qwen3.8-27b) sau Claude API (SUMMARY_PROVIDER=claude)",
                "POST /summary {name, kind: article|education|income, url | items:[{excerpt,source_domain,source_date,source_title}]}": "un rezumat, la cerere (Groq qwen/qwen3.8-27b)",
                "GET /factcheck?name=...[&refresh=1][&wait=1]": "erori logice, contradicții, afirmații suspecte, doar din ultimele 20 de știri cu discursuri și citate, max. 3 declarații pe știre, prin Groq (gpt-oss-120b, gpt-oss-20b, qwen3.8-27b), la cerere",
                "GET /credibility?name=...[&refresh=1][&wait=1]": "scor de credibilitate 1..10 (fezabilitate, precizie, istoric, manipulare), din erorile logice, prin Groq (openai/gpt-oss-120b, temperatura 0)",
                "GET /cached?kind=credibility|factcheck|orientation&name=...": "citește de pe disc ce a fost generat deja (nu generează niciodată)",
                "GET /methodology": "datele paginii „Metodologie”: site-urile folosite, modelele, limitele, ponderile",
                "GET /cache": "ce e salvat pe disc (tot ce se generează se păstrează; se regenerează doar cu &force=1)",
                "GET /health": "ok",
            }})

        return self.reply(404, {"error": "endpoint inexistent"})

    def do_POST(self):
        route = self.path.split("?")[0].rstrip("/")
        if route not in ("/analyze", "/summary"):
            return self.reply(404, {"error": "endpoint inexistent"})
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > 2_000_000:
                return self.reply(413, {"error": "request prea mare"})
            data = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(data, dict):
                raise ValueError
        except Exception:
            return self.reply(400, {"error": "JSON invalid"})

        if route == "/summary":
            try:
                job = start_summary_one_job(data.get("name", ""), data)
            except (ValueError, TypeError) as exc:
                return self.reply(400, {"error": str(exc)})
            if data.get("wait"):
                job["done"].wait()
            return self.reply({"done": 200, "error": 500}.get(job["status"], 202), public(job))

        return self.go(
            data.get("name", ""),
            data,
            bool(data.get("force", False)),
            bool(data.get("wait", False)),
        )


def serve(host="127.0.0.1", port=8000):
    print(f"API pe http://{host}:{port} (GET / pentru lista endpoint-urilor)")
    ThreadingHTTPServer((host, port), H).serve_forever()


if __name__ == "__main__":
    args = sys.argv[1:]
    if args:
        res = analyze(
            args[0],
            on_progress=lambda m: print(m, file=sys.stderr),
            speed=args[1] if len(args) > 1 else "fast",
        )
        print(res["report"])
    else:
        serve()
