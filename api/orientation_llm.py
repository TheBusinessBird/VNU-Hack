"""orientation_llm - scoruri 1..5 pe 10 axe ideologice, calculate prin Groq (implicit openai/gpt-oss-20b) din textele scraper-ului.

    from orientation_llm import score_orientation
    rez = score_orientation(analysis_result, "Prenume Nume")      # analysis_result = promise_tracker.analyze(...)

Câte O cerere scurtă pe axă, cu doar fragmentele relevante pentru axa respectivă (selectate cu cuvinte-cheie, fără AI). Dacă pentru o
axă nu există niciun fragment relevant, modelul nu e deloc apelat: scorul e null (dovezi insuficiente).
Modelul alege polul (left/balanced/right/none) și intensitatea; scorul 1..5 se derivă determinist din ele (1 = polul stâng, 3 = echilibrat,
5 = polul drept). Citatele care nu apar în fragmentele trimise sunt eliminate; un verdict fără niciun citat verificat devine null.

Groq (planul gratuit): 8.000 tokeni/minut pe model, deci fiecare cerere (prompt + răspuns) rămâne mică; ritmarea și reîncercările sunt în llm.py.
Parametri (variabile de mediu): ORIENTATION_MODEL (implicit openai/gpt-oss-20b), cheia în api/groq_key.txt sau GROQ_API_KEY.
"""
import json, os, re, time

import llm
from llm import LLMError

MODEL = os.environ.get("ORIENTATION_MODEL", "openai/gpt-oss-20b")
FALLBACKS = [m for m in os.environ.get("ORIENTATION_FALLBACKS", "openai/gpt-oss-120b,qwen/qwen3.8-27b").split(",") if m]
OUTPUT_TOKENS = 1200            # gpt-oss gândește scurt (efort mic) înainte de JSON-ul unei axe; la reîncercare se dublează
PROMPT_OVERHEAD_TOKENS = 700    # instrucțiunile + descrierea axei
CHARS_PER_TOKEN = llm.CHARS_PER_TOKEN
MAX_CONTEXT_CHARS = 5000        # ~1,9k tokeni de dovezi pe cerere: încap 2-3 cereri pe minut în limita de 8.000 tokeni/minut
OFFICIAL = ["cdep.ro", "senat.ro", "gov.ro", "presidency.ro"]

# Temperatura 0 și seed fix: scoruri cât mai stabile.
OPTIONS = {"temperature": 0, "seed": 42}

# id, pol stâng (=1), pol drept (=5), ce acoperă, cuvinte-cheie românești pentru selectarea fragmentelor.
# Ordinea trebuie să fie aceeași ca în js/data.js.
AXES = [
    ("geopolitics", "Pro-Western / Euro-Atlantic", "Sovereignist / Eurosceptic",
     "EU/NATO integration, PNRR modernization, Western future-orientation vs. national sovereignty, post-communist nostalgia, Eastern realignment",
     r"\bUE\b|Uniunea European|NATO|euro-?atlantic|occident|PNRR|Bruxelles|suveran|eurosceptic|Rusia|Moscova|\bvest\b|aderare|aliat|Ucraina|geopolit"),
    ("identity", "Progressive & Secular", "Traditional & Nationalist",
     "Social rights, civic nationalism, secular state vs. 'traditional family' values, Orthodox Church (BOR) alignment, ethnic nationalism",
     r"famili|biseric|ortodox|\bBOR\b|\bBOR\b|patriarh|credin[țt]|tradi[țt]ion|na[țt]ionalis|secular|c[ăa]s[ăa]tori|parteneriat civil|LGBT|avort|drepturi|valori|\bMa[șs]ina\b"),
    ("economy", "Free Market & Fiscal Discipline", "Progressive Taxation & Welfare State",
     "Pro-business policies, flat tax (cota unica), deficit control vs. progressive tax, immediate pension/wage increases, state social handouts",
     r"cot[ăa] unic|impozit|tax[ăa]|TVA|deficit|buget|pensi|salari|austerit|taiere|t[ăa]iere|antreprenor|mediul de afaceri|ajutor|majorare|cre[șs]tere a|investi[țt]"),
    ("governance", "Technocratic & Transparent", "Patronage & Bureaucracy",
     "Meritocracy, digitalization, justice reform, anti-corruption vs. political appointments, traditional state bureaucracy, clientelism/local patronage",
     r"corup[țt]|justi[țt]ie|magistra|DNA\b|numiri|numit|merit|digitaliz|transparen|birocra|clientel|patronaj|concurs|reform[ăa]|integritate|CSM|Parchet"),
    ("system", "Anti-Establishment & Urban/Diaspora", "Establishment & Local/Rural Networks",
     "System disruption, reformist drive, urban/diaspora modernization vs. status quo stability, party machine continuity, rural administration reliance",
     r"anti-?sistem|sistem(ul)?\b|establishment|partide(le)? tradi|status quo|diaspora|ora[șs]|rural|primari|baroni|PSD|PNL|schimbare|ruptur|clasa politic"),
    ("structure", "Centralism & Unitary State", "Decentralization & Regional Autonomy",
     "Budgetary/administrative power concentrated in Bucharest, strict unitary state vs. devolving financial control to local administrations, regionalization, minority autonomy debates",
     r"descentraliz|regionaliz|autonomi|stat unitar|unitar|Bucure[șs]ti|prefect|consili[ul]+ jude[țt]|primării|administra[țt]ie local|fonduri locale|cote defalcate"),
    ("energy", "Green Modernization & Climate Goals", "Resource Exploitation & Energy Sovereignty",
     "Renewables, coal phase-out, EU Green Deal alignment vs. maximizing domestic fossil extraction, immediate industrial energy independence, resisting costly environmental rules",
     r"energi|c[ăa]rbune|gaze?\b|Neptun|Pactul Verde|regenerabil|clim|nuclear|reactoar|Hidroelectrica|Oltenia|emisii|combustibil|petrol|eolian|fotovoltaic|mediu"),
    ("services", "Privatization & Systemic Overhaul", "State Monopoly & Incrementalism",
     "Private alternatives in health and education, performance-based funding, restructuring vs. state-run monopolies, public-sector pay rises over structural reform, status quo networks",
     r"sănătate|sanatate|spital|educa[țt]ie|[șs]coal|universit|privat|privatiz|medic|profesor|cheltuieli publice|sector public|bugetar|reform[ăa]"),
    ("ethnic", "Multiculturalism & Civic Inclusion", "Ethnocentrism & Assimilation",
     "Language rights, political representation of minorities, cultural diversity vs. strict unitary-nation paradigm, Romanian ethnic primacy, skepticism toward minority political leverage",
     r"minorit|maghiar|UDMR|rom[ăa]ni|etnic|limba|limb[ăa] matern|Ungaria|Transilvania|diversitate|asimil|Secuime|na[țt]iune"),
    ("labor", "Labor Liberalization & Immigration", "Economic Protectionism & Domestic Focus",
     "Easing non-EU worker quotas, flexible labor law, diaspora repatriation incentives vs. protecting domestic workers, restricting foreign labor, rigid traditional employment rules",
     r"imigra|migra[țt]|munc[ăa]|angaja|lucr[ăa]tori|[șs]omaj|cote|str[ăa]ini|diaspora|repatri|salariu minim|codul muncii|sindicat|for[țt]a de munc"),
]
AXIS_IDS = [a[0] for a in AXES]


class BadJSON(ValueError):
    """Răspunsul modelului nu conține un JSON utilizabil."""


# ---------------------------------------------------------------------------
# 1) Context: alege fragmentele relevante pentru o axă și care încap în buget
# ---------------------------------------------------------------------------
def _plain_quotes(text):
    """Ghilimelele tipografice („ ” “ « ») și cele drepte din textul trimis modelului devin apostrof: modelul copiază citate în JSON și
    își încheia uneori șirul cu ” în loc de ", ceea ce strica răspunsul."""
    return re.sub(r"[„”“«»\"]", "'", text)


def _mentions(text, surname):
    return re.search(r"(?<![\wăâîșț])" + re.escape(surname) + r"(?![\wăâîșț])", text, re.I) is not None


def _priority(par, surname, official, axis_re=None):
    """Fragmentele cu declarații directe și cu numele candidatului contează cel mai mult; pentru o axă, cuvintele ei-cheie sunt obligatorii."""
    hits = len(axis_re.findall(par)) if axis_re else 0
    if axis_re and not hits: return 0
    p = 3 * min(hits, 3)
    if _mentions(par, surname): p += 2
    if re.search(r"[„\"“]", par): p += 2
    if re.search(r"\b(a spus|a declarat|a afirmat|a anun[țt]at|a promis|susține|propune|vrea|consider[ăa])\b", par, re.I): p += 1
    if not axis_re and not p: return 0
    return p + 2 if official else p


def build_context(result, surname, budget_chars, axis_re=None):
    """Întoarce (text de trimis modelului, {S1: {url, domain, title, date, author}}). Bugetul se împarte între surse,
    ca o singură sursă lungă să nu acopere restul; în fiecare sursă se păstrează fragmentele cu prioritatea cea mai mare, în ordinea textului.
    Cu axis_re, intră doar fragmentele care conțin cuvinte-cheie ale axei ȘI sunt despre candidat sau conțin declarații directe."""
    docs = []
    for s in result.get("sources", []):
        paras = [_plain_quotes(p.strip()) for p in (s.get("text") or "").split("\n\n") if len(p.strip()) > 40]
        if not paras: continue
        official = any((s.get("domain") or "").endswith(o) for o in OFFICIAL)
        scored = [(_priority(p, surname, official, axis_re), i, p) for i, p in enumerate(paras)]
        if axis_re:   # pentru o axă, un fragment trebuie să fie și despre candidat (nume) sau o declarație directă (ghilimele)
            scored = [(pr, i, p) for pr, i, p in scored if pr and (_mentions(p, surname) or re.search(r"[„\"“]", p))]
        docs.append((s, official, [x for x in scored if x[0] > 0]))
    docs = [d for d in docs if d[2]]
    docs.sort(key=lambda d: (d[1], sum(x[0] for x in d[2])), reverse=True)    # surse oficiale și bogate în fragmente relevante primele
    if not docs: return "", {}
    per_doc = max(700, budget_chars // len(docs))
    blocks, refs, used = [], {}, 0
    for n, (s, official, scored) in enumerate(docs, 1):
        header = f"[S{n}] {s.get('domain', '')} | {s.get('date') or 'fără dată'} | autor: {s.get('author') or 'necunoscut'} | {s.get('title', '')[:100]}"
        room = min(per_doc, budget_chars - used) - len(header) - 2
        if room < 200: break
        keep, size = [], 0
        for pr, i, p in sorted(scored, key=lambda x: (-x[0], x[1])):
            p = p[:600]
            if size + len(p) + 3 > room: continue
            keep.append((i, p)); size += len(p) + 3
        if not keep: continue
        body = "\n".join(f"- {p}" for _, p in sorted(keep))
        blocks.append(header + "\n" + body)
        refs[f"S{n}"] = {k: s.get(k) for k in ("url", "domain", "title", "date", "author")}
        used += len(header) + len(body) + 2
    return "\n\n".join(blocks), refs


# ---------------------------------------------------------------------------
# 2) Prompt + schemă de răspuns (o axă pe cerere)
# ---------------------------------------------------------------------------
SYSTEM = """You place ONE Romanian politician or political party on ONE ideological axis using ONLY the numbered excerpts provided. Do not use outside knowledge.
The axis has a LEFT pole and a RIGHT pole (just the two sides listed, NOT political left/right).

Answer with a JSON object with these fields, in this order:
- "evidence": 0-3 items. Each has "source" (the excerpt tag, e.g. "S2") and "quote": a VERBATIM passage copied from that excerpt (max 200 characters) that shows the politician's own position on THIS axis.
- "rationale": one or two sentences in Romanian that name the pole in words.
- "pole": "left" if the politician is closer to the left pole, "right" if closer to the right pole, "balanced" if the evidence is mixed, "none" if the excerpts say nothing about the politician's position on this axis. When unsure, use "none".
- "strength": "clear" if the quotes state the position directly, otherwise "slight".
- "confidence": "high", "medium" or "low".

Rules: the politician's own statements and decisions count more than journalists' opinions or rivals' accusations. Criticising another party is not evidence about this axis. "pole" must agree with your rationale."""


def build_messages(name, axis, context):
    aid, left, right, covers, _ = axis
    user = (f"Politician: {name}\n\nAXIS: {left}  <->  {right}\n"
            f"LEFT pole = {left}. RIGHT pole = {right}.\nCovers: {covers}.\n\nEXCERPTS:\n{context}\n\nPlace {name} on this axis.")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def response_schema():
    return {
        "type": "object",
        "properties": {   # ordinea contează: modelul scrie întâi dovezile și justificarea, apoi verdictul
            "evidence": {"type": "array", "maxItems": 3, "items": {
                "type": "object",
                "properties": {"source": {"type": "string"}, "quote": {"type": "string"}},
                "required": ["source", "quote"]}},
            "rationale": {"type": "string"},
            "pole": {"type": "string", "enum": ["left", "balanced", "right", "none"]},
            "strength": {"type": "string", "enum": ["slight", "clear"]},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        },
        "required": ["evidence", "rationale", "pole", "strength", "confidence"],
    }


def to_score(pole, strength):
    """Scorul 1..5 e derivat determinist din verdictul categorial: left clear=1, left slight=2, balanced=3, right slight=4, right clear=5."""
    if pole == "left": return 1 if strength == "clear" else 2
    if pole == "right": return 5 if strength == "clear" else 4
    if pole == "balanced": return 3
    return None


# ---------------------------------------------------------------------------
# 3) Apelul Groq
# ---------------------------------------------------------------------------
def llm_chat(messages, schema, model=MODEL, num_predict=OUTPUT_TOKENS):
    """O cerere Groq cu răspuns JSON după schemă. Întoarce {message:{content}, prompt_eval_count, eval_count, done_reason}."""
    r = llm.chat(model, messages, temperature=OPTIONS["temperature"], seed=OPTIONS["seed"], max_tokens=num_predict, schema=schema, fallbacks=FALLBACKS)
    return {"message": {"content": r["content"]}, "prompt_eval_count": r["prompt_tokens"], "eval_count": r["completion_tokens"],
            "done_reason": "length" if r["finish_reason"] == "length" else "stop"}


# ---------------------------------------------------------------------------
# 4) Validare + rezultat
# ---------------------------------------------------------------------------
def _norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _empty(axis, why, **extra):
    return {"id": axis[0], "left": axis[1], "right": axis[2], "score": None, "confidence": "low", "rationale": why,
            "evidence": [], "pole": "none", "verified": True, "dropped_unsupported": False, **extra}


def validate_axis(axis, raw, context, refs):
    """Păstrează doar citatele care apar în fragmentele trimise (nu lăsăm modelul să inventeze dovezi); verdict fără citat verificat -> null."""
    ctx = _norm(context)
    score = to_score(raw.get("pole"), raw.get("strength"))
    ev = []
    for e in raw.get("evidence") or []:
        if not isinstance(e, dict): continue
        q, src = _norm(e.get("quote")), e.get("source")
        if q and src in refs and q in ctx:
            ev.append({"source": src, "quote": e["quote"].strip(), **{k: refs[src].get(k) for k in ("url", "domain", "date", "author")}})
    conf = raw.get("confidence") if raw.get("confidence") in ("low", "medium", "high") else "low"
    unsupported = score is not None and not ev
    if unsupported: score, conf = None, "low"
    return {"id": axis[0], "left": axis[1], "right": axis[2], "score": score, "confidence": conf,
            "rationale": (raw.get("rationale") or "").strip(), "evidence": ev,
            "pole": raw.get("pole") if score is not None else "none", "verified": True, "dropped_unsupported": unsupported}


def _salvage(content):
    """Răspuns tăiat (limita de tokeni) sau cu JSON stricat: recuperăm câmpurile care s-au scris întregi.
    Dacă nu avem polul, nu inventăm nimic: întoarce None."""
    content = content or ""
    out = {}
    for key in ("pole", "strength", "confidence"):
        m = re.search(r'"%s"\s*:\s*"([^"]*)"' % key, content)
        if m: out[key] = m.group(1)
    m = re.search(r'"rationale"\s*:\s*"((?:[^"\\]|\\.)*)', content)
    if m: out["rationale"] = m.group(1)
    ev, pos = [], content.find("[", content.find('"evidence"')) if '"evidence"' in content else -1
    if pos != -1:
        dec, i = json.JSONDecoder(), pos + 1
        while i < len(content):
            while i < len(content) and content[i] in " \n\r\t,":
                i += 1
            try:
                obj, i = dec.raw_decode(content, i)
            except ValueError:
                break
            if isinstance(obj, dict): ev.append(obj)
    out["evidence"] = ev
    return out if out.get("pole") else None


def _parse(content):
    try:
        return json.loads(content)
    except ValueError:
        m = re.search(r"\{.*\}", content or "", re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except ValueError:
                pass
        salvaged = _salvage(content)
        if salvaged is None: raise BadJSON("Modelul nu a întors JSON valid.")
        return salvaged


def score_orientation(result, name, on_progress=None, model=MODEL, chat=llm_chat, term=None):
    """result: dict de la promise_tracker.analyze (cu sources[].text). Întoarce axele cu scor 1..5 (sau None) + metadate."""
    log = on_progress or (lambda m: None)
    surname = (term or name.split()[-1]).lower()
    budget = min(MAX_CONTEXT_CHARS, llm.chars_for_tokens(llm.REQUEST_TOKEN_CAP - OUTPUT_TOKENS * 2 - PROMPT_OVERHEAD_TOKENS))
    if not any((s.get("text") or "").strip() for s in result.get("sources", [])):
        raise ValueError("Nu există text de analizat: rulează întâi analiza surselor (cu include_text).")
    t0, axes, all_refs, ptok, otok, calls = time.time(), [], {}, 0, 0, 0
    for n, axis in enumerate(AXES, 1):
        aid = axis[0]
        context, refs = build_context(result, surname, budget, re.compile(axis[4], re.I))
        if not context:
            log(f"Axa {n}/{len(AXES)} ({aid}): niciun fragment relevant, sar peste")
            axes.append(_empty(axis, "Niciun fragment din sursele analizate nu tratează această axă."))
            continue
        log(f"Axa {n}/{len(AXES)} ({aid}): {len(refs)} surse, ~{len(context)} caractere către {model}")
        raw = None
        for attempt, budget_tokens in enumerate((OUTPUT_TOKENS, OUTPUT_TOKENS * 2)):     # a doua încercare: buget dublu, dacă răspunsul a fost tăiat
            kw = {} if attempt == 0 else {"num_predict": budget_tokens}
            resp = chat(build_messages(name, axis, context), response_schema(), model=model, **kw)
            calls += 1; ptok += resp.get("prompt_eval_count") or 0; otok += resp.get("eval_count") or 0
            try:
                raw = _parse((resp.get("message") or {}).get("content", ""))
                break
            except BadJSON:
                log(f"Axa {n}/{len(AXES)} ({aid}): răspuns invalid, reîncerc" if attempt == 0 else f"Axa {n}/{len(AXES)} ({aid}): răspuns invalid")
        if raw is None:
            axes.append(_empty(axis, "Modelul nu a întors un răspuns valid pentru această axă.", error=True))
            continue
        axes.append(validate_axis(axis, raw, context, refs))
        for tag, ref in refs.items():
            all_refs[ref["url"]] = ref
    return {
        "politician": name, "model": model, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "scale": "1 = polul stâng, 3 = echilibrat, 5 = polul drept; null = dovezi insuficiente",
        "axes": axes,
        "sources_used": list(all_refs.values()),
        "run": {"provider": "groq", "context_chars_max": budget, "llm_calls": calls, "seconds": round(time.time() - t0, 1),
                "prompt_tokens": ptok, "output_tokens": otok, "options": OPTIONS},
    }
