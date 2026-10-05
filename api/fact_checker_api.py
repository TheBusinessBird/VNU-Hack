#!/usr/bin/env python3
"""
fact_checker_api
================
Politician statement fact-check API.

    name  ->  scraper (promise_tracker_no_ai_v2)  ->  Groq models (gpt-oss-120b / gpt-oss-20b / qwen3.8-27b)  ->  flagged statements

Pipeline
--------
1. SCRAPE      Runs the existing scraper for the politician's name (or reuses a result passed in `scraped`).
2. PASSAGES    Turns its output into attributed passages: verbatim speeches, direct quotes, and reported speech.
3. PASS 1      Per-passage review. The model flags statements that may be false, self-contradictory, conspiratorial,
               unverifiable, implausible, fallacious, misleading or otherwise suspicious. Batches are spread round-robin over a
               pool of Groq models: on the free plan every model has its own 8,000 tokens/minute limit, so the pool multiplies throughput.
4. PASS 2      Cross-statement review (optional): candidate pairs of statements on the same topic are checked for contradictions.
5. VERIFY      Every quote the model returns is checked against the source text. Quotes that cannot be found are dropped.

IMPORTANT HONESTY NOTE
----------------------
A language model with no internet access CANNOT verify facts. The output is a list of *flags for a human fact-checker*, not
verdicts. Every finding carries a "how_to_verify" field and a confidence level for that reason.

Requirements
------------
    * Python 3.9+ (standard library only), llm.py (Groq client) and a Groq key in api/groq_key.txt or GROQ_API_KEY
    * promise_tracker_no_ai_v2.py in the same directory

Run
---
    python fact_checker_api.py                       # API on http://127.0.0.1:8100
    python fact_checker_api.py --check "Nume Prenume" --speed fast   # CLI, prints JSON (progress goes to stderr)

Environment overrides
---------------------
    FACTCHECK_MODELS     default openai/gpt-oss-120b,openai/gpt-oss-20b,qwen/qwen3.8-27b
    FACTCHECK_PORT       default 8100
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import llm
import promise_tracker_no_ai_v2 as scraper
from llm import LLMError

__all__ = ["fact_check", "report_text", "serve", "preflight", "LLMError"]


# ============================================================
# CONFIG  (context size, sampling, budgets)
# ============================================================

def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except ValueError:
        return default


# ---- Models (Groq) ----------------------------------------------------------
# Free plan: 8,000 tokens/minute and 1,000 requests/day PER MODEL, so pass-1 batches rotate over a pool of models.
MODELS = [m.strip() for m in os.environ.get("FACTCHECK_MODELS", "openai/gpt-oss-120b,openai/gpt-oss-20b,qwen/qwen3.8-27b").split(",") if m.strip()]
MODEL = MODELS[0]
STATS_LOCK = threading.Lock()

# ---- Request budget ---------------------------------------------------------
# One request = system prompt + header + passages + the answer budget, and it has to stay under llm.REQUEST_TOKEN_CAP:
#     REQUEST_TOKEN_CAP >= system prompt + header + passages + NUM_PREDICT + SAFETY
# gpt-oss reasons briefly (low effort) before answering and those tokens count towards NUM_PREDICT.
NUM_PREDICT_FINDINGS = 1800      # output cap, pass 1 (reasoning + up to MAX_FINDINGS_PER_CALL findings)
NUM_PREDICT_PAIR = 900           # output cap, pass 2
SAFETY_TOKENS = 300              # slack for chat-template tokens + estimate error
CHARS_PER_TOKEN = llm.CHARS_PER_TOKEN          # conservative for Romanian passages (diacritics split into more tokens)
SYSTEM_CHARS_PER_TOKEN = 3.4     # conservative for the English system prompt
MAX_BATCH_CHARS = 5000           # hard cap on passage text per request (quality > packing)
MAX_UNIT_CHARS = 3200            # long speeches are split into pieces of at most this size
MAX_PASSAGES_PER_BATCH = 8
MAX_FINDINGS_PER_CALL = 6

# ---- Sampling ---------------------------------------------------------------
# Low temperature: this is analysis, not creative writing. A fixed seed makes runs reproducible.
SAMPLING = {"temperature": 0, "seed": 1337}

LEVELS = ["low", "medium", "high"]
CATEGORIES = [
    "likely_false",
    "contradiction",
    "conspiratorial",
    "unverifiable",
    "implausible",
    "logical_fallacy",
    "misleading",
    "other_suspicious",
]
PAIR_RELATIONS = ["direct_contradiction", "reversal", "tension", "consistent", "unrelated"]
LANGUAGES = {"en": "English", "ro": "Romanian"}

SEV_W = {"low": 1, "medium": 2, "high": 3}
CONF_W = {"low": 1, "medium": 2, "high": 3}

I18N = {
    "en": {
        "disclaimer": (
            "These are automated FLAGS produced by a small local language model without internet "
            "access. They are leads for a human fact-checker, not verdicts. Verify every item "
            "against primary sources before relying on it."
        ),
        "pair_verify": "Compare the two original documents (dates and full context) and check whether circumstances changed in between.",
        "pair_problem": "Statements appear inconsistent.",
        "no_units": (
            "The scraper found no attributable statements (speeches, direct quotes or reported "
            "speech) for this name. Try speed=normal/deep, add aliases, or pass extra_urls."
        ),
        "category": {
            "likely_false": "Probabil fals", "contradiction": "Contradicție", "conspiratorial": "Conspiraționist",
            "unverifiable": "Neverificabil", "implausible": "Improbabil", "logical_fallacy": "Eroare logică",
            "misleading": "Înșelător", "other_suspicious": "Altfel suspect",
        },
        "level": {"low": "scăzută", "medium": "medie", "high": "ridicată"},
        "relationship": {"direct_contradiction": "Contradicție directă", "reversal": "Schimbare de poziție", "tension": "Tensiune"},
    },
}
# Romanian is the default language of the API; labels and fixed texts are Romanian in both cases
I18N["ro"] = {
    "disclaimer": (
        "Acestea sunt SEMNALĂRI automate generate de un model de limbaj local de mici dimensiuni, fără "
        "acces la internet. Sunt piste pentru un verificator uman, nu verdicte. Verificați fiecare "
        "element în surse primare înainte de a-l folosi."
    ),
    "pair_verify": "Comparați cele două documente originale (date și context complet) și verificați dacă circumstanțele s-au schimbat între timp.",
    "pair_problem": "Declarațiile par inconsistente.",
    "no_units": (
        "Scraper-ul nu a găsit declarații atribuibile (discursuri, citate directe sau vorbire "
        "indirectă) pentru acest nume. Încercați speed=normal/deep, adăugați alias-uri sau transmiteți extra_urls."
    ),
    "category": I18N["en"]["category"],
    "level": I18N["en"]["level"],
    "relationship": I18N["en"]["relationship"],
}


def tr(language: str) -> dict:
    return I18N.get(language, I18N["ro"])


# ============================================================
# PROMPTS
# ============================================================
# The system prompt is IDENTICAL for every call in a job (the politician's name and the
# passages go in the user message). That keeps every request identical in its first part, so only
# the first call pays the cost of reading this long prompt.

EXAMPLE_OUTPUT = {
    "en": r"""{"findings": [
{"passage_id": "P1", "quote": "Am redus șomajul la zero în doar o lună și nimeni nu mai este fără job în România.", "category": "implausible", "problem": "Claims unemployment fell to zero within a month, which is an extreme and absolute result.", "reasoning": "Test e: no economy reaches 0% unemployment, and structural unemployment cannot disappear in one month. Based on general knowledge.", "severity": "high", "confidence": "high", "how_to_verify": "Monthly unemployment rate published by INS and Eurostat for the period."},
{"passage_id": "P3", "quote": "Prețurile cresc pentru că o rețea secretă de bancheri controlează tot și nimeni nu are voie să vorbească despre asta.", "category": "conspiratorial", "problem": "Attributes price rises to a secret network of bankers and a ban on discussing it, with no evidence.", "reasoning": "Test c: a hidden coordinated group and a cover-up are asserted. Inflation has documented economic causes that are not mentioned.", "severity": "high", "confidence": "high", "how_to_verify": "Central bank and INS inflation reports; ask the speaker to name the people or documents."},
{"passage_id": "P5", "quote": "Deficitul bugetar a scăzut anul acesta, iar acum este cel mai mare din ultimii zece ani.", "category": "contradiction", "problem": "The sentence says the deficit fell and also that it is the highest in ten years.", "reasoning": "Test a: both halves can only be true if the deficit was even higher before, which the statement does not say, so as written it contradicts itself.", "severity": "medium", "confidence": "medium", "how_to_verify": "Annual budget deficit as a percentage of GDP from the Ministry of Finance and Eurostat."},
{"passage_id": "P6", "quote": "Opoziția a votat împotriva legii mele, deci vrea ca oamenii să rămână săraci.", "category": "logical_fallacy", "problem": "Treats a vote against one law as proof of a wish to keep people poor.", "reasoning": "Test f: attributing a motive as proof; people can oppose a law for many other reasons.", "severity": "low", "confidence": "high", "how_to_verify": "The opposition's stated reasons in the plenary transcript on cdep.ro."}
]}""",
    "ro": r"""{"findings": [
{"passage_id": "P1", "quote": "Am redus șomajul la zero în doar o lună și nimeni nu mai este fără job în România.", "category": "implausible", "problem": "Afirmă că șomajul a scăzut la zero într-o singură lună, un rezultat extrem și absolut.", "reasoning": "Testul e: nicio economie nu ajunge la șomaj de 0%, iar șomajul structural nu dispare într-o lună. Pe baza cunoștințelor generale.", "severity": "high", "confidence": "high", "how_to_verify": "Rata lunară a șomajului publicată de INS și Eurostat pentru perioada respectivă."},
{"passage_id": "P3", "quote": "Prețurile cresc pentru că o rețea secretă de bancheri controlează tot și nimeni nu are voie să vorbească despre asta.", "category": "conspiratorial", "problem": "Atribuie creșterea prețurilor unei rețele secrete de bancheri și unei interdicții de a discuta, fără nicio dovadă.", "reasoning": "Testul c: sunt afirmate un grup ascuns, coordonat, și o mușamalizare. Inflația are cauze economice documentate care nu sunt menționate.", "severity": "high", "confidence": "high", "how_to_verify": "Rapoartele de inflație ale băncii centrale și ale INS; solicitarea numelor persoanelor sau a documentelor invocate."},
{"passage_id": "P5", "quote": "Deficitul bugetar a scăzut anul acesta, iar acum este cel mai mare din ultimii zece ani.", "category": "contradiction", "problem": "Fraza spune că deficitul a scăzut și, în același timp, că este cel mai mare din ultimii zece ani.", "reasoning": "Testul a: ambele jumătăți pot fi adevărate doar dacă deficitul era și mai mare înainte, ceea ce nu se spune; așa cum este formulată, fraza se contrazice.", "severity": "medium", "confidence": "medium", "how_to_verify": "Deficitul bugetar anual ca procent din PIB, din datele Ministerului Finanțelor și Eurostat."},
{"passage_id": "P6", "quote": "Opoziția a votat împotriva legii mele, deci vrea ca oamenii să rămână săraci.", "category": "logical_fallacy", "problem": "Tratează un vot împotriva unei legi drept dovadă a dorinței de a menține oamenii în sărăcie.", "reasoning": "Testul f: atribuirea unui motiv ca dovadă; oamenii pot fi împotriva unei legi din multe alte motive.", "severity": "low", "confidence": "high", "how_to_verify": "Motivele declarate ale opoziției în stenograma ședinței plenare de pe cdep.ro."}
]}""",
}

FINDINGS_SYSTEM_PROMPT = """\
# ROLE
You are a skeptical but scrupulously fair political fact-checking assistant. A human will verify every flag you raise, so you FLAG, you never give verdicts. You read statements attributed to ONE politician and report the ones that may be false, self-contradictory, conspiratorial, unprovable, implausible, logically flawed, misleading or otherwise suspicious.

# INPUT
POLITICIAN UNDER ANALYSIS (the only person whose words may be flagged), a SOURCE line, then numbered passages [P1], [P2]... Each has TYPE (speech = verbatim transcript turn; direct quote = words in quotation marks attributed by an article; article passage = journalist text, possibly reported speech), optional CUES (automatic hints, often wrong: never flag only because of a hint), STATEMENT, and optional SURROUNDING TEXT (context only). Texts are usually Romanian.

# METHOD
1. Decide who is speaking. Claims by journalists, opponents, experts or the narrator are NEVER flagged.
2. Extract the politician's concrete claims: facts, numbers, dates, causes, accusations, claims about what others secretly want.
3. Flag a claim only if a test clearly applies:
   a) it contradicts itself or the text, or numbers/dates do not add up;
   b) it contradicts textbook facts (geography, history, arithmetic, how institutions work);
   c) it asserts a secret plan, hidden coordinated actors or a cover-up without evidence;
   d) it is presented as fact but cannot be proven or disproven (unnamed sources, "everyone knows", mind-reading);
   e) it is extraordinary or numerically implausible (0% / 100% for complex phenomena, impossible timelines or budgets);
   f) the reasoning is flawed: ad hominem, straw man, false dilemma, slippery slope, post hoc, appeal to fear/popularity/authority, whataboutism, hasty generalisation, circular reasoning, motive-as-proof;
   g) it is technically true but deceptive: no baseline, cherry-picked period, credit or blame for things outside the person's control.
4. One statement = at most one finding; pick the single best category.
5. Copy the offending words EXACTLY into "quote" (1-2 sentences, character for character, no paraphrase, no translation, no ellipsis).

# CATEGORIES (exact values)
likely_false (checkable claim conflicting with well-established facts; use only when fairly sure) | contradiction (self-contradiction or arithmetic that cannot be right) | conspiratorial (hidden plot or cover-up without evidence) | unverifiable (factual-sounding but unprovable as stated) | implausible (exaggerated, impossible deadlines/budgets, absolute results) | logical_fallacy (flawed reasoning, see f) | misleading (technically true but deceptive) | other_suspicious (a real red flag fitting none of the above).

# SEVERITY AND CONFIDENCE
severity: high = serious accusation, claim about health, safety, law or public money, or a central claim of the argument; medium = notable exaggeration or error; low = minor imprecision.
confidence: high = the problem is visible in the text itself or concerns a textbook fact; medium = plausible problem that needs checking; low = hunch (use this instead of dropping a doubtful but reasonable flag).

# DO NOT FLAG
Opinions, values and slogans; ordinary ambitious promises (flag a promise only if its deadline, budget or effect is impossible or it contradicts itself); words of anyone but the politician; neutral, plausible, consistent facts; greetings, procedural remarks. Over-flagging wastes the researcher's time: precision first, then recall.

# HONESTY RULES
1. You have NO internet and NO database. Never say you checked or confirmed anything.
2. Never invent statistics, laws, dates, names or sources. If you rely on general knowledge say "based on general knowledge" and do not use confidence "high" unless it is textbook-level.
3. If unsure whether a claim is false, use "unverifiable" or a lower confidence, never "likely_false". Your knowledge may be outdated: for recent events use "unverifiable".
4. "passage_id" is the id (for example "P3") of the passage that contains the quote.
5. If nothing qualifies return {"findings": []}: an empty list is a correct answer. Never invent a finding. Report at most <<MAX_FINDINGS>> findings, the most serious first.

# OUTPUT
Return ONLY one JSON object {"findings": [ ... ]}. Each finding has: passage_id, quote, category, problem (1-2 sentences: what exactly is wrong), reasoning (2-3 short sentences naming the test a-g that applied), severity, confidence, how_to_verify (which kind of source would settle it, for example INS or Eurostat statistics, Monitorul Oficial, the parliament transcript on cdep.ro, the original video). Keys and category values stay in English; write the free-text fields in <<LANGUAGE>>.
"""

PAIR_SYSTEM_PROMPT = """\
# ROLE
You are a careful political fact-checking analyst. You compare TWO statements made by the SAME politician, possibly on different dates and in different documents, and decide whether they are inconsistent with each other. A human will review your answer.

# INPUT FORMAT
POLITICIAN, then STATEMENT A and STATEMENT B, each with its date and source title. The texts are usually in Romanian.

# RELATIONS (use these exact values)
- direct_contradiction: both statements are about the SAME subject and the SAME time frame, and they cannot both be true. Example: A "The tax will never be raised." B "We raised the tax as planned." Or A says the figure is 5% and B says 15% for the same thing and period.
- reversal: the politician took one position or made one promise and later took the opposite position or abandoned it. It may be legitimate (new facts, new circumstances) but is worth noting. Dates matter: use the earlier date as the first position.
- tension: partial inconsistency: different figures for similar things, a changed scope or deadline, or claims that are hard to reconcile without extra explanation.
- consistent: same subject, no conflict.
- unrelated: different subjects, or too vague to compare. This is the most common correct answer.

# RULES
1. Be conservative. When in doubt choose "unrelated" or "consistent", or at most "tension".
2. Different periods are not a contradiction ("unemployment rose in 2020" and "unemployment fell in 2023" are compatible).
3. A general statement and a specific example are not a contradiction unless the example violates the generalisation.
4. Opinions that evolve are at most a "reversal", never a "direct_contradiction".
5. Do not use outside knowledge to decide which statement is true. You only judge whether A and B are consistent with EACH OTHER.
6. You have no internet access. Do not claim to have checked anything.
7. Never invent numbers, dates or quotes. Refer only to what is written in A and B.

# OUTPUT FORMAT
Return ONLY one JSON object, no markdown. Keep keys and enum values in English; write the free text in <<LANGUAGE>>.
{"relationship": "direct_contradiction | reversal | tension | consistent | unrelated",
 "key_conflict": "short phrase naming the subject on which they differ, or empty if none",
 "explanation": "2-3 sentences explaining precisely what conflicts, mentioning the dates",
 "confidence": "low | medium | high"}
"""


# ============================================================
# LLM CLIENT (Groq, see llm.py)
# ============================================================

def preflight() -> dict:
    """Raises LLMError if there is no Groq key."""
    llm.api_key()
    return {"provider": "groq", "models": MODELS}


THINK_RE = re.compile(r"<think>.*?(?:</think>|$)", re.S | re.I)


def parse_json_lenient(text: str):
    """Parse model output; salvage complete findings from a truncated array."""
    text = THINK_RE.sub("", text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except ValueError:
        pass

    pos = text.find("[")
    if '"findings"' in text and pos != -1:
        dec = json.JSONDecoder()
        items, i = [], pos + 1
        while i < len(text):
            while i < len(text) and text[i] in " \n\r\t,":
                i += 1
            try:
                obj, i = dec.raw_decode(text, i)
            except ValueError:
                break
            if isinstance(obj, dict):
                items.append(obj)
        return {"findings": items, "_salvaged": True}
    return None


def new_stats() -> dict:
    return {
        "llm_calls": 0,
        "retries": 0,
        "prompt_tokens": 0,
        "output_tokens": 0,
        "truncated_outputs": 0,
        "possible_prompt_truncation": 0,
        "unparseable_outputs": 0,
        "quotes_dropped_not_found": 0,
        "quotes_repaired": 0,
        "batches": 0,
        "batches_skipped_time_budget": 0,
        "pairs_checked": 0,
        "llm_seconds": 0.0,
    }


def chat_json(system: str, user: str, schema: dict, num_predict: int, stats: dict, model: str | None = None):
    """One structured Groq call. Returns (parsed_or_None, done_reason). Rate limits and retries are handled in llm.py."""
    t0 = time.time()
    r = llm.chat(model or MODEL, [{"role": "system", "content": system}, {"role": "user", "content": user}],
                 temperature=SAMPLING["temperature"], seed=SAMPLING["seed"], max_tokens=num_predict, schema=schema)
    reason = "length" if r["finish_reason"] == "length" else ""
    obj = parse_json_lenient(r["content"])
    with STATS_LOCK:
        stats["llm_calls"] += 1
        stats["llm_seconds"] += time.time() - t0
        stats["prompt_tokens"] += r["prompt_tokens"]
        stats["output_tokens"] += r["completion_tokens"]
        if reason == "length":
            stats["truncated_outputs"] += 1
        if obj is None:
            stats["unparseable_outputs"] += 1
    return obj, reason


# ============================================================
# SCHEMAS
# ============================================================

def findings_schema(passage_ids: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "maxItems": MAX_FINDINGS_PER_CALL,
                "items": {
                    "type": "object",
                    # Field order matters for constrained decoding: the model writes the
                    # quote and the reasoning BEFORE it commits to severity/confidence.
                    "properties": {
                        "passage_id": {"type": "string", "enum": passage_ids},
                        "quote": {"type": "string", "maxLength": 320},
                        "category": {"type": "string", "enum": CATEGORIES},
                        "problem": {"type": "string", "maxLength": 260},
                        "reasoning": {"type": "string", "maxLength": 420},
                        "severity": {"type": "string", "enum": LEVELS},
                        "confidence": {"type": "string", "enum": LEVELS},
                        "how_to_verify": {"type": "string", "maxLength": 200},
                    },
                    "required": [
                        "passage_id", "quote", "category", "problem",
                        "reasoning", "severity", "confidence", "how_to_verify",
                    ],
                },
            }
        },
        "required": ["findings"],
    }


PAIR_SCHEMA = {
    "type": "object",
    "properties": {
        "relationship": {"type": "string", "enum": PAIR_RELATIONS},
        "key_conflict": {"type": "string", "maxLength": 120},
        "explanation": {"type": "string", "maxLength": 450},
        "confidence": {"type": "string", "enum": LEVELS},
    },
    "required": ["relationship", "key_conflict", "explanation", "confidence"],
}


# ============================================================
# TEXT HELPERS
# ============================================================

def norm_words(text: str) -> str:
    """Diacritic-free, lowercase, punctuation-free word string for robust matching."""
    return " ".join(re.findall(r"[a-z0-9]+", scraper.strip(text)))


def split_text(text: str, limit: int) -> list[str]:
    """Split long text on sentence boundaries into pieces of at most `limit` chars."""
    text = text.strip()
    if len(text) <= limit:
        return [text]
    parts, cur = [], ""
    for sent in scraper.SENTENCE_SPLIT.split(text):
        while len(sent) > limit:               # pathological: no punctuation
            if cur:
                parts.append(cur)
                cur = ""
            parts.append(sent[:limit])
            sent = sent[limit:]
        if cur and len(cur) + 1 + len(sent) > limit:
            parts.append(cur)
            cur = sent
        else:
            cur = f"{cur} {sent}".strip()
    if cur:
        parts.append(cur)
    return parts


CUE_PATTERNS = [
    ("absolute language", re.compile(
        r"\b(niciodata|intotdeauna|mereu|toti|toate|nimeni|nimic|absolut|complet|total|"
        r"fara exceptie|oricand|nicio|niciun|zero|100 ?%|100 la suta)\b")),
    ("numeric claim", re.compile(r"\d")),
    ("conspiracy vocabulary", re.compile(
        r"complot|conspirati|agenda ascunsa|retea secreta|guvern(?:ul)? din umbra|stat paralel|"
        r"globalis|mondialis|marele reset|plandemi|cabala|ne ascund|ni se ascunde|ne manipulez|"
        r"puteri oculte|new world order|ordine de la|controlat[ae]? din afara")),
    ("unnamed authority", re.compile(
        r"studii (?:arata|spun|dovedesc)|specialistii (?:spun|arata)|toata lumea stie|se stie ca|"
        r"este evident ca|oamenii spun|expertii (?:spun|arata)|multi spun")),
    ("sweeping causal claim", re.compile(r"din cauza|din vina|vina (?:este|e) a|datorita faptului")),
    ("accusation", re.compile(r"\b(?:minte|mint|hoti|hot|tradator|corup|vandut|infractor|trada)\w*")),
]


def heuristic_cues(text: str) -> list[str]:
    n = scraper.strip(text)
    cues = [label for label, rx in CUE_PATTERNS if rx.search(n)]
    if scraper.statement_is_promise(text):
        cues.append("promise / future commitment")
    return cues


ATTRIB_RE = re.compile(
    r"\b(?:a (?:mai )?(?:spus|declarat|afirmat|sustinut|precizat|anuntat|explicat|acuzat|adaugat|"
    r"subliniat|mentionat|transmis|promis|reiterat|insistat|scris|aratat|criticat|replicat|"
    r"raspuns|dezvaluit)|(?:spune|afirma|declara|sustine|considera|crede|promite|anunta|acuza) ca|"
    r"potrivit|conform|in opinia)\b"
)


# ============================================================
# PASSAGES ("units") AND BATCHING
# ============================================================

@dataclass
class Unit:
    kind: str                 # speech | quote | reported
    text: str
    context: str
    source: dict
    cues: list = field(default_factory=list)
    priority: float = 0.0


KIND_LABEL = {"speech": "speech", "quote": "direct quote", "reported": "article passage"}
KIND_BASE_PRIORITY = {"speech": 3.0, "quote": 2.0, "reported": 1.0}


def _src_meta(d: dict, kind_hint: str = "") -> dict:
    return {
        "id": d.get("source_id") or d.get("id"),
        "url": d.get("source_url") or d.get("url"),
        "title": d.get("source_title") or d.get("title") or "",
        "domain": d.get("source_domain") or d.get("domain") or "",
        "date": d.get("date") or d.get("source_date") or "",
        "author": d.get("author") or d.get("source_author") or "Necunoscut",
        "source_score": d.get("source_score", 0),
        "doc_kind": kind_hint or d.get("kind", ""),
    }


def build_units(name: str, scraped: dict, max_units: int, piece_chars: int,
                include_reported: bool = True, since_date: str = "") -> list[Unit]:
    surname = scraper.strip(name.split()[-1])
    sources = {s["id"]: s for s in scraped.get("sources", [])}
    units: list[Unit] = []
    seen: set[str] = set()

    def add(kind, text, context, meta):
        if since_date and not (meta.get("date") and meta["date"] >= since_date):
            return                  # only dated passages inside the window (the site shows the last 12 months)
        text = scraper.clean_text(text)
        key = norm_words(text)[:300]
        if len(text) < 40 or key in seen:
            return
        seen.add(key)
        cues = heuristic_cues(text)
        pr = KIND_BASE_PRIORITY[kind] + 0.4 * len(cues) + (meta.get("source_score") or 0) / 100.0
        units.append(Unit(kind, text, scraper.clean_text(context), meta, cues, pr))

    # 1) verbatim speeches
    for sp in scraped.get("speeches", []):
        meta = _src_meta(sp, sources.get(sp.get("source_id"), {}).get("kind", ""))
        for piece in split_text(sp.get("text", ""), piece_chars):
            add("speech", piece, "", meta)

    # 2) direct quotes (+ their paragraph as context)
    contexts_by_source: dict[str, list[str]] = {}
    for st in scraped.get("statements", []):
        meta = _src_meta(st, sources.get(st.get("source_id"), {}).get("kind", ""))
        ctx = st.get("context", "")
        contexts_by_source.setdefault(meta["id"], []).append(norm_words(ctx))
        add("quote", st.get("text", ""), ctx if len(ctx) > len(st.get("text", "")) + 30 else "", meta)

    # 3) reported speech from the scraper's evidence excerpts (press articles about the politician)
    for sid, s in (sources.items() if include_reported else []):
        meta = _src_meta(s, s.get("kind", ""))
        for ex in s.get("evidence", []):
            exn = scraper.strip(ex)
            if surname not in exn or not ATTRIB_RE.search(exn):
                continue
            ex_words = norm_words(ex)
            if any(c and c in ex_words for c in contexts_by_source.get(sid, [])):
                continue            # already covered by a direct-quote unit
            add("reported", ex, "", meta)

    units.sort(key=lambda u: u.priority, reverse=True)
    return units[:max_units]


def _plain_quotes(text: str) -> str:
    """Typographic quotes become apostrophes: models copy quotes into JSON strings and sometimes close them with a curly quote."""
    return re.sub(r"[„”“«»\"]", "'", text)


def render_unit(local_id: str, u: Unit) -> str:
    lines = [f"[{local_id}] TYPE: {KIND_LABEL[u.kind]}"]
    if u.cues:
        lines.append("CUES: " + "; ".join(u.cues))
    lines.append("STATEMENT: " + _plain_quotes(u.text))
    if u.context:
        lines.append("SURROUNDING TEXT: " + _plain_quotes(u.context))
    return "\n".join(lines)


def make_batches(units: list[Unit], batch_chars: int) -> list[list[Unit]]:
    by_src: dict[str, list[Unit]] = {}
    for u in units:
        by_src.setdefault(u.source["id"], []).append(u)
    batches: list[list[Unit]] = []
    for us in by_src.values():
        cur, size = [], 0
        for u in us:
            r = len(render_unit("P99", u)) + 2
            if cur and (size + r > batch_chars or len(cur) >= MAX_PASSAGES_PER_BATCH):
                batches.append(cur)
                cur, size = [], 0
            cur.append(u)
            size += r
        if cur:
            batches.append(cur)
    batches.sort(key=lambda b: max(u.priority for u in b), reverse=True)
    return batches


def batch_char_budget(system_prompt: str) -> int:
    """How many characters of passages fit in one request without risking truncation."""
    prompt_tokens_allowed = llm.REQUEST_TOKEN_CAP - NUM_PREDICT_FINDINGS - SAFETY_TOKENS
    system_tokens = int(len(system_prompt) / SYSTEM_CHARS_PER_TOKEN)
    header_tokens = 160
    free = prompt_tokens_allowed - system_tokens - header_tokens
    return max(1500, min(MAX_BATCH_CHARS, int(free * CHARS_PER_TOKEN)))


# ============================================================
# PASS 1: per-passage findings
# ============================================================

def locate_quote(quote: str, texts: list[str]):
    """
    Find the model's quote in the source text. Returns (quote_to_use, repaired, text_index)
    or None when it cannot be found (hallucination).
    """
    q_clean = scraper.clean_text(quote)
    qn = norm_words(q_clean)
    if len(qn) < 15:
        return None

    for ti, text in enumerate(texts):
        if not text:
            continue
        t_clean = scraper.clean_text(text)
        if q_clean and q_clean in t_clean:
            return q_clean, False, ti

    for ti, text in enumerate(texts):
        if not text:
            continue
        sents = [s for s in scraper.SENTENCE_SPLIT.split(scraper.clean_text(text)) if s.strip()]
        # normalized containment inside one or two consecutive sentences -> return the original wording
        for span in (1, 2):
            for i in range(len(sents)):
                cand = " ".join(sents[i:i + span])
                if qn in norm_words(cand):
                    return cand, True, ti
        if qn in norm_words(text):
            return q_clean, True, ti
        # fuzzy: the model slightly altered the sentence
        best, best_r = None, 0.0
        for span in (1, 2):
            for i in range(len(sents)):
                cand = " ".join(sents[i:i + span])
                r = difflib.SequenceMatcher(None, qn, norm_words(cand), autojunk=False).ratio()
                if r > best_r:
                    best, best_r = cand, r
        if best and best_r >= 0.85:
            return best, True, ti
    return None


def analyse_batch(name, batch, language, stats, deadline, depth=0, model=None) -> list[dict]:
    if time.time() > deadline:
        stats["batches_skipped_time_budget"] += 1
        return []

    ids = [f"P{i + 1}" for i in range(len(batch))]
    first = batch[0].source
    header = (
        f"POLITICIAN UNDER ANALYSIS: {name}\n"
        f"SOURCE: {first['title'] or 'untitled'} | {first['domain']} | "
        f"{first['date'] or 'date unknown'} | {first['doc_kind'] or 'article'}\n\n"
    )
    body = "\n\n".join(render_unit(i, u) for i, u in zip(ids, batch))
    footer = (
        f"\n\nTASK: Examine the passages above. Report every statement made by {name} that may be "
        f"false, contradictory, conspiratorial, unverifiable, implausible, fallacious, misleading or "
        f"otherwise suspicious. Copy quotes exactly. If nothing qualifies, return {{\"findings\": []}}."
    )

    stats["batches"] += 1
    obj, reason = chat_json(
        SYSTEM_FINDINGS(language), header + body + footer,
        findings_schema(ids), NUM_PREDICT_FINDINGS, stats, model,
    )

    # Output cut off or unusable: halve the batch and retry (smaller input -> shorter output).
    if (obj is None or reason == "length") and len(batch) > 1 and depth < 3:
        mid = len(batch) // 2
        return (
            analyse_batch(name, batch[:mid], language, stats, deadline, depth + 1, model)
            + analyse_batch(name, batch[mid:], language, stats, deadline, depth + 1, model)
        )
    if not isinstance(obj, dict):
        return []

    results = []
    for raw in (obj.get("findings") or [])[:MAX_FINDINGS_PER_CALL]:
        if not isinstance(raw, dict):
            continue
        cat = raw.get("category")
        if cat not in CATEGORIES:
            continue
        pid = raw.get("passage_id")
        unit = batch[ids.index(pid)] if pid in ids else None

        # Verify the quote against the claimed passage first, then against the whole batch.
        found, repaired, in_context = None, False, False
        candidates = ([unit] if unit else []) + [u for u in batch if u is not unit]
        for cand in candidates:
            loc = locate_quote(raw.get("quote", ""), [cand.text, cand.context])
            if loc:
                quote, repaired, ti = loc
                found, unit, in_context = quote, cand, (ti == 1)
                break
        if found is None:
            stats["quotes_dropped_not_found"] += 1
            continue
        if repaired:
            stats["quotes_repaired"] += 1

        sev = raw.get("severity") if raw.get("severity") in LEVELS else "medium"
        conf = raw.get("confidence") if raw.get("confidence") in LEVELS else "low"
        results.append({
            "category": cat,
            "severity": sev,
            "confidence": conf,
            "scope": "within_passage",
            "quote": found,
            "problem": scraper.clean_text(raw.get("problem", "")),
            "reasoning": scraper.clean_text(raw.get("reasoning", "")),
            "how_to_verify": scraper.clean_text(raw.get("how_to_verify", "")),
            "passage_type": unit.kind,
            "cues": unit.cues,
            "quote_found_only_in_surrounding_text": in_context,
            "quote_was_repaired": repaired,
            "source": unit.source,
        })
    return results


def SYSTEM_FINDINGS(language: str) -> str:
    return (
        FINDINGS_SYSTEM_PROMPT
        .replace("<<LANGUAGE>>", LANGUAGES.get(language, "Romanian"))
        .replace("<<MAX_FINDINGS>>", str(MAX_FINDINGS_PER_CALL))
        .replace("<<EXAMPLE_OUTPUT>>", EXAMPLE_OUTPUT.get(language, EXAMPLE_OUTPUT["ro"]))
    )


def SYSTEM_PAIR(language: str) -> str:
    return PAIR_SYSTEM_PROMPT.replace("<<LANGUAGE>>", LANGUAGES.get(language, "Romanian"))


# ============================================================
# PASS 2: cross-statement contradictions
# ============================================================

STOPWORDS = set("""
acest aceasta aceste acestea acesta acestei acestui acolo adica aceea acele acelea acelor ainte alta
alte altele altfel anul anului asta astfel atunci avem aveti avand avea bine cand care carei caror
carui cate catre chiar cine cineva cred daca dupa desi doar deja dintre foarte fost fiind fiecare
face facut fara iata inca intre langa lucru mult multe multi nostru noastra noastre nostri nimic
niste noua oricare pentru poate pana prin putea sunt sale sau sale spre sunt suntem toate toti tot
trebuie unde unui unei unor vom voi vreau vrem vedem vorbim zicem acum aici apoi cat cum deci ceea
ceva cele cei cel este fie era erau sunteti ale
""".split())

NEG_RE = re.compile(r"\b(?:nu|nici|niciodata|fara|nicio|niciun|nimeni|nimic)\b")
NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _stems(text: str) -> set[str]:
    n = scraper.strip(text)
    out = set()
    for w in re.findall(r"[a-z]+", n):
        if len(w) >= 5 and w not in STOPWORDS:
            out.add(w[:6])
    return out


def build_snippets(units: list[Unit], cap: int = 160) -> list[dict]:
    snippets = []
    seen: set[str] = set()
    for u in units:
        if u.kind == "quote":
            pieces = [u.text[:500]]
        else:
            pieces = []
            for s in scraper.SENTENCE_SPLIT.split(u.text):
                s = s.strip()
                if not (60 <= len(s) <= 500):
                    continue
                sn = scraper.strip(s)
                if u.kind == "reported" and not ATTRIB_RE.search(sn):
                    continue
                if u.kind == "speech" and not heuristic_cues(s):
                    continue
                pieces.append(s)
        for p in pieces:
            key = norm_words(p)
            if key in seen:
                continue
            seen.add(key)
            snippets.append({
                "text": p,
                "stems": _stems(p),
                "nums": set(NUM_RE.findall(p)),
                "neg": bool(NEG_RE.search(scraper.strip(p))),
                "source": u.source,
                "kind": u.kind,
            })
    snippets.sort(key=lambda s: (s["source"].get("source_score") or 0), reverse=True)
    return snippets[:cap]


def candidate_pairs(snippets: list[dict], max_pairs: int) -> list[tuple]:
    scored = []
    for i in range(len(snippets)):
        for j in range(i + 1, len(snippets)):
            a, b = snippets[i], snippets[j]
            shared = a["stems"] & b["stems"]
            if len(shared) < 3:
                continue
            union = a["stems"] | b["stems"]
            if union and len(shared) / len(union) > 0.8:
                continue            # near-duplicate (same text republished), not a contradiction
            score = float(len(shared))
            if a["nums"] and b["nums"] and a["nums"] != b["nums"] and len(shared) >= 2:
                score += 2.0        # same topic, different figures
            if a["neg"] != b["neg"]:
                score += 1.5        # opposite polarity on the same topic
            if a["source"].get("id") != b["source"].get("id"):
                score += 0.5        # cross-document inconsistencies are the interesting ones
            scored.append((score, i, j))
    scored.sort(reverse=True)
    return [(snippets[i], snippets[j]) for _, i, j in scored[:max_pairs]]


def compare_pair(name, a, b, language, stats, model=None) -> dict | None:
    t = tr(language)
    # Order by date so "reversal" has a meaningful direction.
    if (b["source"].get("date") or "") and (a["source"].get("date") or "") > (b["source"].get("date") or ""):
        a, b = b, a

    def fmt(label, s):
        m = s["source"]
        return (
            f"STATEMENT {label} (date: {m.get('date') or 'unknown'}; "
            f"source: {m.get('title') or 'untitled'}):\n\"{s['text']}\""
        )

    user = (
        f"POLITICIAN: {name}\n\n{fmt('A', a)}\n\n{fmt('B', b)}\n\n"
        f"TASK: Decide how A and B relate. Be conservative."
    )
    obj, _ = chat_json(SYSTEM_PAIR(language), user, PAIR_SCHEMA, NUM_PREDICT_PAIR, stats, model)
    stats["pairs_checked"] += 1
    if not isinstance(obj, dict) or obj.get("relationship") not in ("direct_contradiction", "reversal", "tension"):
        return None

    rel = obj["relationship"]
    conf = obj.get("confidence") if obj.get("confidence") in LEVELS else "low"
    severity = {"direct_contradiction": "high", "reversal": "medium", "tension": "low"}[rel]
    return {
        "category": "contradiction",
        "severity": severity,
        "confidence": conf,
        "scope": "between_statements",
        "relationship": rel,
        "quote": a["text"],
        "related_quote": b["text"],
        "relationship_label": t["relationship"][rel],
        "problem": scraper.clean_text(obj.get("key_conflict", "")) or t["pair_problem"],
        "reasoning": scraper.clean_text(obj.get("explanation", "")),
        "how_to_verify": t["pair_verify"],
        "passage_type": a["kind"],
        "cues": [],
        "quote_found_only_in_surrounding_text": False,
        "quote_was_repaired": False,
        "source": a["source"],
        "related_source": b["source"],
    }


# ============================================================
# ORCHESTRATION
# ============================================================

LLM_LOCK = threading.Lock()        # never run two jobs' LLM phases at once: the rate limits are per model, shared by all jobs
_SCRAPE_CACHE: dict = {}
_SCRAPE_TTL = 3600


def _scrape(name, scrape_opts, progress, refresh):
    key = (name.lower(), json.dumps(scrape_opts, sort_keys=True, ensure_ascii=False, default=list))
    hit = _SCRAPE_CACHE.get(key)
    if hit and not refresh and time.time() - hit[0] < _SCRAPE_TTL:
        progress("Using cached scrape results")
        return hit[1]
    result = scraper.analyze(name, on_progress=lambda m: progress(f"[scrape] {m}"), **scrape_opts)
    _SCRAPE_CACHE[key] = (time.time(), result)
    return result


def _finding_id(f: dict) -> str:
    return hashlib.sha1((norm_words(f["quote"])[:200] + f["category"]).encode()).hexdigest()[:10]


def fact_check(
    name: str,
    scrape_opts: dict | None = None,
    language: str = "ro",
    max_passages: int = 60,
    max_pairs: int = 20,
    contradictions: bool = True,
    min_confidence: str = "low",
    llm_budget_s: int = 1200,
    include_sources: bool = False,
    refresh: bool = False,
    on_progress=None,
    scraped: dict | None = None,
    include_reported: bool = True,
    since_date: str = "",
) -> dict:
    t = tr(language)
    progress = on_progress or (lambda m: None)
    name = scraper.clean_text(name)
    if len(name.split()) < 2:
        raise ValueError("'name' must be the politician's full name (first + last name).")
    started = time.time()

    if scraped is None:
        scraped = _scrape(name, dict(scrape_opts or {}), progress, refresh)

    batch_chars = batch_char_budget(SYSTEM_FINDINGS(language))
    piece_chars = min(MAX_UNIT_CHARS, int(batch_chars * 0.8))
    units = build_units(name, scraped, max_passages, piece_chars, include_reported, since_date)
    batches = make_batches(units, batch_chars)
    progress(f"{len(units)} passages in {len(batches)} batches (≤{batch_chars} chars each)")

    stats = new_stats()
    findings: list[dict] = []

    with LLM_LOCK:
        preflight()
        deadline = time.time() + llm_budget_s

        def run_batch(i: int, batch):
            """Batch i goes to model i % n; if that model is unavailable (e.g. its daily limit is used up) the next one takes over."""
            last = None
            for k in range(len(MODELS)):
                try:
                    return analyse_batch(name, batch, language, stats, deadline, model=MODELS[(i + k) % len(MODELS)])
                except LLMError as exc:
                    last = exc
            raise last

        done = 0
        with ThreadPoolExecutor(max_workers=len(MODELS)) as pool:
            futures = [pool.submit(run_batch, i, b) for i, b in enumerate(batches)]
            for fut in as_completed(futures):
                findings.extend(fut.result())
                done += 1
                progress(f"Pass 1: batch {done}/{len(batches)} ({len(findings)} flags so far)")

        if contradictions and time.time() < deadline:
            pairs = candidate_pairs(build_snippets(units), max_pairs)
            for k, (a, b) in enumerate(pairs, 1):
                if time.time() > deadline:
                    break
                progress(f"Pass 2: comparing statements {k}/{len(pairs)}")
                f = compare_pair(name, a, b, language, stats)
                if f:
                    findings.append(f)

    # ---- dedupe, filter, rank ----
    unique, seen = [], set()
    for f in findings:
        fid = _finding_id(f)
        if fid in seen:
            continue
        seen.add(fid)
        f["id"] = fid
        unique.append(f)

    for f in unique:
        f["category_label"] = t["category"][f["category"]]
        f["severity_label"] = t["level"][f["severity"]]
        f["confidence_label"] = t["level"][f["confidence"]]

    floor = CONF_W.get(min_confidence, 1)
    unique = [f for f in unique if CONF_W[f["confidence"]] >= floor]
    unique.sort(
        key=lambda f: (
            SEV_W[f["severity"]] * 3 + CONF_W[f["confidence"]] * 2,
            f["source"].get("date") or "",
        ),
        reverse=True,
    )

    by_cat, by_sev = {}, {}
    for f in unique:
        by_cat[f["category"]] = by_cat.get(f["category"], 0) + 1
        by_sev[f["severity"]] = by_sev.get(f["severity"], 0) + 1

    stats["llm_seconds"] = round(stats["llm_seconds"], 1)
    out = {
        "politician": name,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": ", ".join(MODELS),
        "language": language,
        "disclaimer": t["disclaimer"],
        "summary": {
            "flags": len(unique),
            "by_category": by_cat,
            "by_severity": by_sev,
            "passages_analysed": len(units),
            "scraped_sources": scraped.get("stats", {}).get("sources", 0),
        },
        "findings": unique,
        "stats": {
            **stats,
            "elapsed_s": round(time.time() - started, 1),
            "scraper": scraped.get("stats", {}),
            "llm_config": llm_config(),
        },
    }
    if not units:
        out["note"] = t["no_units"]
    # declarațiile analizate (și cele fără semnalări): scorul de credibilitate are nevoie de ele, nu doar de erori
    out["passages"] = [
        {"kind": u.kind, "text": u.text[:400],
         "source": {k: u.source.get(k) for k in ("id", "title", "domain", "date", "url")}}
        for u in units
    ]
    if include_sources:
        out["sources"] = [
            {k: s.get(k) for k in ("id", "url", "title", "domain", "date", "author", "kind", "source_score")}
            for s in scraped.get("sources", [])
        ]
    progress("Done")
    return out


def llm_config() -> dict:
    return {
        "provider": "groq",
        "models": MODELS,
        "request_token_cap": llm.REQUEST_TOKEN_CAP,
        "num_predict_findings": NUM_PREDICT_FINDINGS,
        "num_predict_pair": NUM_PREDICT_PAIR,
        "batch_chars": batch_char_budget(SYSTEM_FINDINGS("en")),
        "system_prompt_chars": len(FINDINGS_SYSTEM_PROMPT),
        "system_prompt_tokens_est": int(len(FINDINGS_SYSTEM_PROMPT) / SYSTEM_CHARS_PER_TOKEN),
        "max_findings_per_call": MAX_FINDINGS_PER_CALL,
        "sampling": SAMPLING,
    }


def report_text(result: dict) -> str:
    s = result["summary"]
    lines = [
        f"FACT-CHECK FLAGS — {result['politician']}",
        f"Model: {result['model']} | passages analysed: {s['passages_analysed']} | flags: {s['flags']}",
        result["disclaimer"],
        "",
    ]
    if not result["findings"]:
        lines.append("No statements were flagged." + (" " + result["note"] if result.get("note") else ""))
    for n, f in enumerate(result["findings"], 1):
        src = f["source"]
        lines += [
            f"{n}. [{f['severity'].upper()} severity | {f['confidence']} confidence] {f['category']}"
            + (" (between statements)" if f["scope"] == "between_statements" else ""),
            f"   “{f['quote']}”",
        ]
        if f.get("related_quote"):
            rs = f["related_source"]
            lines.append(f"   vs. “{f['related_quote']}” ({rs.get('date') or 'n/a'}, {rs.get('domain')})")
        lines += [
            f"   Problem: {f['problem']}",
            f"   Reasoning: {f['reasoning']}",
            f"   How to verify: {f['how_to_verify']}",
            f"   Source: {src['title'] or 'untitled'} — {src['domain']} — {src['date'] or 'date n/a'}",
            f"   URL: {src['url']}",
            "",
        ]
    return "\n".join(lines)


# ============================================================
# HTTP API
# ============================================================

JOBS: dict = {}
JLOCK = threading.Lock()

SCRAPE_KEYS = {"extra_urls", "aliases", "domains", "since_year", "depth", "max_sources", "budget", "speed"}
LLM_KEYS = {"language", "max_passages", "max_pairs", "contradictions", "min_confidence", "llm_budget_s", "include_sources"}


def _validate(scrape_opts: dict, llm_opts: dict) -> None:
    if scrape_opts.get("speed", "fast") not in scraper.PRESETS:
        raise ValueError("speed must be fast, normal or deep.")
    for k in ("extra_urls", "aliases", "domains"):
        if k in scrape_opts and not (
            isinstance(scrape_opts[k], list) and all(isinstance(x, str) for x in scrape_opts[k])
        ):
            raise ValueError(f"{k} must be a list of strings.")
    for k in ("since_year", "depth", "max_sources", "budget"):
        if k in scrape_opts and not isinstance(scrape_opts[k], int):
            raise ValueError(f"{k} must be an integer.")
    if llm_opts.get("language", "en") not in LANGUAGES:
        raise ValueError(f"language must be one of {sorted(LANGUAGES)}.")
    if llm_opts.get("min_confidence", "low") not in LEVELS:
        raise ValueError(f"min_confidence must be one of {LEVELS}.")
    for k, lo, hi in (("max_passages", 1, 300), ("max_pairs", 0, 100), ("llm_budget_s", 30, 7200)):
        if k in llm_opts and not (isinstance(llm_opts[k], int) and lo <= llm_opts[k] <= hi):
            raise ValueError(f"{k} must be an integer between {lo} and {hi}.")
    for k in ("contradictions", "include_sources"):
        if k in llm_opts and not isinstance(llm_opts[k], bool):
            raise ValueError(f"{k} must be true or false.")


def start_job(name, scrape_opts, llm_opts, refresh=False):
    name = scraper.clean_text(name)
    if len(name.split()) < 2:
        raise ValueError("'name' must be the politician's full name (first + last name).")
    _validate(scrape_opts, llm_opts)

    key = (name.lower(), json.dumps([scrape_opts, llm_opts], sort_keys=True, ensure_ascii=False))
    with JLOCK:
        existing = JOBS.get(key)
        if existing and not refresh and (
            existing["status"] == "running"
            or (existing["status"] == "done" and time.time() - existing["t"] < 3600)
        ):
            return existing

    preflight()   # fail fast (503) instead of scraping for minutes and then failing

    with JLOCK:
        job = {
            "job_id": uuid.uuid4().hex[:12],
            "status": "running",
            "progress": "Started",
            "result": None,
            "error": None,
            "done": threading.Event(),
            "t": time.time(),
        }
        JOBS[key] = job
        JOBS[job["job_id"]] = job

    def work():
        try:
            job["result"] = fact_check(
                name,
                scrape_opts=scrape_opts,
                refresh=refresh,
                on_progress=lambda m: job.__setitem__("progress", m),
                **llm_opts,
            )
            job["status"] = "done"
        except Exception as exc:                      # surfaced to the client via the job
            job["error"] = f"{type(exc).__name__}: {exc}"
            job["status"] = "error"
        finally:
            job["done"].set()

    threading.Thread(target=work, daemon=True).start()
    return job


def public(job: dict) -> dict:
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "progress": job["progress"],
        "error": job["error"],
        "result": job["result"],
        "status_url": f"/jobs/{job['job_id']}",
    }


def _truthy(v) -> bool:
    return str(v).lower() in ("1", "true", "yes")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code: int, obj=None):
        body = b"" if obj is None else json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        for k, v in (
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type"),
        ):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204)

    def _dispatch(self, data: dict):
        scrape_opts = {k: data[k] for k in SCRAPE_KEYS if k in data}
        llm_opts = {k: data[k] for k in LLM_KEYS if k in data}
        try:
            job = start_job(data.get("name", ""), scrape_opts, llm_opts, refresh=bool(data.get("refresh", False)))
        except ValueError as exc:
            return self._send(400, {"error": str(exc)})
        except LLMError as exc:
            return self._send(503, {"error": str(exc)})

        if data.get("wait"):
            job["done"].wait()

        code = {"done": 200, "error": 500}.get(job["status"], 202)
        self._send(code, public(job))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/health":
            try:
                return self._send(200, {"ok": True, **preflight()})
            except LLMError as exc:
                return self._send(503, {"ok": False, "error": str(exc)})

        if parsed.path == "/config":
            return self._send(200, llm_config())

        if parsed.path.startswith("/jobs/"):
            job = JOBS.get(parsed.path[6:])
            return self._send(200, public(job)) if job else self._send(404, {"error": "unknown job"})

        if parsed.path in ("/factcheck", "/analyze"):
            data: dict = {"name": q.get("name", [""])[0]}
            for k, src in (("extra_urls", "url"), ("aliases", "alias"), ("domains", "domain")):
                if q.get(src):
                    data[k] = q[src]
            for k in ("speed", "language", "min_confidence"):
                if q.get(k):
                    data[k] = q[k][0]
            for k in ("since_year", "depth", "max_sources", "budget", "max_passages", "max_pairs", "llm_budget_s"):
                if q.get(k):
                    if not q[k][0].isdigit():
                        return self._send(400, {"error": f"{k} must be an integer."})
                    data[k] = int(q[k][0])
            for k in ("contradictions", "include_sources", "refresh", "wait"):
                if q.get(k):
                    data[k] = _truthy(q[k][0])
            return self._dispatch(data)

        return self._send(200, {
            "endpoints": {
                "POST /factcheck": "JSON body: {name, speed?, language?, wait?, ...} -> starts a job (or returns the cached one)",
                "GET /factcheck?name=First+Last&wait=1": "same, via query string",
                "GET /jobs/<job_id>": "status + result",
                "GET /health": "checks that a Groq key is configured",
                "GET /config": "effective model / context / sampling configuration",
            },
            "options": {
                "scraper": sorted(SCRAPE_KEYS),
                "analysis": sorted(LLM_KEYS) + ["refresh", "wait"],
            },
        })

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > 2_000_000:
                return self._send(413, {"error": "request too large"})
            data = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(data, dict):
                raise ValueError
        except Exception:
            return self._send(400, {"error": "invalid JSON"})
        self._dispatch(data)


def serve(host: str = "127.0.0.1", port: int = 8100):
    print(f"Fact-check API on http://{host}:{port}  (Groq models: {', '.join(MODELS)})")
    try:
        preflight()
        print("Groq key found.")
    except LLMError as exc:
        print(f"WARNING: {exc}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


def main():
    ap = argparse.ArgumentParser(description="Politician statement fact-check API")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=_env_int("FACTCHECK_PORT", 8100))
    ap.add_argument("--check", metavar="NAME", help="run once from the command line and print the JSON result")
    ap.add_argument("--speed", default="fast", choices=sorted(scraper.PRESETS))
    ap.add_argument("--language", default="ro", choices=sorted(LANGUAGES))
    args = ap.parse_args()

    if args.check:
        res = fact_check(args.check, {"speed": args.speed}, language=args.language,
                         on_progress=lambda m: print(m, file=sys.stderr, flush=True))
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        serve(args.host, args.port)


if __name__ == "__main__":
    main()
