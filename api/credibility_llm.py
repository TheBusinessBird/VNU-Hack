"""credibility_llm - scorul de credibilitate (1..10) al unui politician, calculat prin Groq (implicit openai/gpt-oss-120b) din erorile logice găsite.

    from credibility_llm import score_credibility
    rez = score_credibility(factcheck_result, "Prenume Nume")      # factcheck_result = fact_checker_api.fact_check(...)

Variabile (fiecare 1..10):
    x = fezabilitate   cât de realiste sunt declarațiile, în circumstanțele actuale
    y = precizie       cât de explicite, precise și detaliate sunt (vag = scor mic)
    z = istoric        trecut curat = mare; minciuni sau conspirații repetate = mic (doar din semnalările primite)
    w = manipulare     discurs onest, care își recunoaște defectele = mare; înșelător sau manipulator = mic
Scor = 0.2*x + 0.2*y + 0.4*z + 0.2*w

Fluxul: (1) o cerere pentru z, din semnalările de erori (cel mult 50); (2) cereri în loturi pentru x, y, w pe fiecare articol, din declarațiile lui
și semnalările de pe el. x, y, w ale politicianului = media pe articole. Scorul unui articol folosește z-ul politicianului.
Temperatura este 0 (seed fix). Groq (planul gratuit) are 8.000 tokeni/minut pe model: datele din fiecare cerere se taie ca prompt + răspuns
să încapă în llm.REQUEST_TOKEN_CAP; ritmarea și reîncercările sunt în llm.py.
Scorurile sunt estimări ale unui model, făcute doar din textele primite: de verificat manual.

Variabile de mediu: CREDIBILITY_MODEL (implicit openai/gpt-oss-120b), cheia în api/groq_key.txt sau GROQ_API_KEY.
"""
import json, os, re, time

import llm

MODEL = os.environ.get("CREDIBILITY_MODEL", "openai/gpt-oss-120b")
FALLBACKS = [m for m in os.environ.get("CREDIBILITY_FALLBACKS", "openai/gpt-oss-20b,qwen/qwen3.8-27b").split(",") if m]
OPTIONS = {"temperature": 0, "seed": 7}                              # temperatură 0: același input dă același scor

WEIGHTS = {"feasibility": 0.2, "precision": 0.2, "history": 0.4, "manipulation": 0.2}
MAX_FINDINGS = 50                 # cerință: cel mult 50 de erori în prompt
PREDICT_HISTORY = 1500            # gpt-oss gândește scurt (efort mic) înainte de JSON; la reîncercare se mărește
PREDICT_BATCH = 2000
ARTICLES_PER_BATCH = 8
CHARS_PER_TOKEN = llm.CHARS_PER_TOKEN
SYSTEM_CHARS_PER_TOKEN = 3.4
SAFETY_TOKENS = 300
QUOTE_CHARS, PROBLEM_CHARS, PASSAGE_CHARS = 110, 80, 200

CATEGORY_RO = {
    "likely_false": "probabil fals", "contradiction": "contradicție", "conspiratorial": "conspiraționist",
    "unverifiable": "neverificabil", "implausible": "improbabil", "logical_fallacy": "eroare logică",
    "misleading": "înșelător", "other_suspicious": "altfel suspect",
}

SYSTEM_HISTORY = """You rate the HISTORY of one Romanian politician from a list of FLAGS: automatic warnings raised earlier by a fact-checking pass over his or her recent speeches and quotes. Use ONLY the flags provided. You have no internet access: do not use outside knowledge about the person and never invent facts.

Score "history" from 1 to 10:
- 10 = clean record: no flags, or only a few weak ones among many analysed statements.
- 1 = a history of lying or conspiracy talk: repeated flags in the categories likely_false, contradiction, conspiratorial and misleading, across different sources and dates, with high severity.
Weigh severity and confidence. One weak flag barely matters; repetition across sources and dates matters most; flags that are only "unverifiable" or "implausible" weigh less than "likely_false" or "conspiratorial".
First write "reason": one or two sentences in Romanian that name the pattern behind the score. Then give "history". Answer with the JSON object only."""

SYSTEM_ARTICLES = """You rate several news items about ONE Romanian politician. Each item contains the politician's statements taken from that article and the automatic FLAGS raised on them. Rate every item independently, on three scales from 1 to 10, using only the text given (no outside knowledge, no internet):
- feasibility: how realistic the statements are given current circumstances (budgets, deadlines, legal and practical limits, known facts). 10 = clearly realistic, 1 = impossible or absurd. If the statements contain no plan and no checkable claim, give 5.
- precision: how explicit, precise and detailed the statements are (numbers, dates, named institutions, concrete measures). Vague slogans and generalities score low, concrete commitments score high.
- manipulation: 10 = on point and honest, directly naming flaws and drawbacks of the own approach; 1 = misleading or manipulative (fallacies, conspiracy talk, cherry-picking, loaded language, using accusations as proof). Statements flagged as fallacious, conspiratorial or misleading must score lower.
Answer with the JSON object only: one entry per item id."""


class CredibilityError(RuntimeError):
    pass


def credibility(x, y, z, w):
    """Formula cerută: x*0.2 + y*0.2 + z*0.4 + w*0.2, rotunjită la o zecimală."""
    return round(x * WEIGHTS["feasibility"] + y * WEIGHTS["precision"] + z * WEIGHTS["history"] + w * WEIGHTS["manipulation"], 1)


def _clamp(v):
    try:
        return max(1, min(10, int(round(float(v)))))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Groq: JSON structurat, temperatura 0
# ---------------------------------------------------------------------------
def _parse(text):
    text = re.sub(r"<think>.*?(?:</think>|$)", "", text or "", flags=re.S).strip()
    try:
        return json.loads(text)
    except ValueError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except ValueError:
                pass
    return None


def groq_json(system, user, schema, num_predict, model=MODEL):
    try:
        r = llm.chat(model, [{"role": "system", "content": system}, {"role": "user", "content": user}],
                     temperature=OPTIONS["temperature"], seed=OPTIONS["seed"], max_tokens=num_predict, schema=schema, fallbacks=FALLBACKS)
    except llm.LLMError as e:
        raise CredibilityError(str(e))
    return {"obj": _parse(r["content"]), "done_reason": "length" if r["finish_reason"] == "length" else "stop",
            "prompt_tokens": r["prompt_tokens"], "output_tokens": r["completion_tokens"]}


def data_budget_chars(system, num_predict):
    """Câte caractere de date încap într-o cerere: bugetul de tokeni al cererii minus instrucțiunile, minus răspunsul, minus o rezervă."""
    tokens = llm.REQUEST_TOKEN_CAP - int(len(system) / SYSTEM_CHARS_PER_TOKEN) - num_predict - SAFETY_TOKENS
    return max(1500, int(tokens * CHARS_PER_TOKEN))


def _cut(s, n):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


def fit(lines, budget):
    """Păstrează liniile (în ordinea priorității) cât timp încap în buget. Întoarce (linii păstrate, câte au fost scoase)."""
    out, used = [], 0
    for ln in lines:
        if used + len(ln) + 1 > budget:
            break
        out.append(ln); used += len(ln) + 1
    return out, len(lines) - len(out)


# ---------------------------------------------------------------------------
# Datele din rezultatul erorilor logice
# ---------------------------------------------------------------------------
def render_finding(i, f):
    src = f.get("source") or {}
    return (f"[F{i}] {CATEGORY_RO.get(f.get('category'), f.get('category'))} | gravitate {f.get('severity')} | încredere {f.get('confidence')}"
            f" | {src.get('date') or 'fără dată'} | {src.get('domain') or ''} | „{_cut(f.get('quote'), QUOTE_CHARS)}” | {_cut(f.get('problem'), PROBLEM_CHARS)}")


def group_articles(fc_result):
    """{id sursă: {id, title, date, domain, url, passages[], findings[]}} din declarațiile analizate și din semnalări."""
    arts = {}

    def art(src):
        sid = src.get("id")
        if not sid:
            return None
        return arts.setdefault(sid, {"id": sid, "title": src.get("title") or src.get("domain") or "", "date": src.get("date") or "",
                                     "domain": src.get("domain") or "", "url": src.get("url") or "", "passages": [], "findings": []})

    for p in fc_result.get("passages", []):
        a = art(p.get("source") or {})
        if a is not None:
            a["passages"].append(p.get("text") or "")
    for f in fc_result.get("findings", []):
        a = art(f.get("source") or {})
        if a is not None:
            a["findings"].append(f)
    return arts


def render_article(local_id, a):
    lines = [f"[{local_id}] {_cut(a['title'], 110)} | {a['date'] or 'fără dată'} | {a['domain']}"]
    for t in a["passages"][:3]:
        lines.append(f"  - declarație: „{_cut(t, PASSAGE_CHARS)}”")
    for f in a["findings"][:3]:
        lines.append(f"  - semnalare: {CATEGORY_RO.get(f.get('category'), f.get('category'))} (gravitate {f.get('severity')}, încredere {f.get('confidence')}): {_cut(f.get('problem'), PROBLEM_CHARS)}")
    return "\n".join(lines)


def make_batches(order, budget, max_items=ARTICLES_PER_BATCH):
    """Împarte articolele în loturi care încap fiecare în `budget` caractere (și au cel mult `max_items` articole).
    Întoarce [[(id local, articol, text randat), ...], ...]."""
    batches, cur, used = [], [], 0
    for a in order:
        text = render_article(f"A{len(cur) + 1}", a)
        if cur and (used + len(text) + 2 > budget or len(cur) >= max_items):
            batches.append(cur); cur, used = [], 0
            text = render_article("A1", a)
        cur.append((f"A{len(cur) + 1}", a, text)); used += len(text) + 2
    if cur:
        batches.append(cur)
    return batches


def history_schema():
    return {"type": "object", "properties": {"reason": {"type": "string"}, "history": {"type": "integer"}},
            "required": ["reason", "history"]}


def articles_schema(ids):
    item = {"type": "object", "properties": {
        "id": {"type": "string", "enum": ids},
        "feasibility": {"type": "integer"}, "precision": {"type": "integer"}, "manipulation": {"type": "integer"}},
        "required": ["id", "feasibility", "precision", "manipulation"]}
    return {"type": "object", "properties": {"items": {"type": "array", "items": item}}, "required": ["items"]}


# ---------------------------------------------------------------------------
# Scorul
# ---------------------------------------------------------------------------
def score_credibility(fc_result, name, on_progress=None, chat=groq_json, model=MODEL):
    log = on_progress or (lambda m: None)
    t0 = time.time()
    arts = group_articles(fc_result)
    if not arts:
        raise CredibilityError("Nu există declarații analizate. Rulează mai întâi „Generează erori logice”.")
    all_findings = list(fc_result.get("findings", []))
    findings = all_findings[:MAX_FINDINGS]                      # deja sortate după gravitate și încredere
    stats = {"calls": 0, "prompt_tokens": 0, "output_tokens": 0, "truncated": 0}

    def call(system, user, schema, predict):
        """O cerere; dacă răspunsul e tăiat sau invalid, o singură reîncercare cu un buget de răspuns mai mare (dacă încape în limită)."""
        for attempt in range(2):
            n = predict if attempt == 0 else int(predict * 1.6)
            if attempt and llm.estimate_tokens(system + user) + n > llm.TPM_LIMIT:
                break
            r = chat(system, user, schema, n, model=model)
            stats["calls"] += 1; stats["prompt_tokens"] += r.get("prompt_tokens", 0); stats["output_tokens"] += r.get("output_tokens", 0)
            if r.get("done_reason") == "length":
                stats["truncated"] += 1
            if r.get("obj"):
                return r["obj"]
        return None

    # ---- 1) z = istoric, din semnalările de erori ----
    by_cat = {}
    for f in all_findings:
        by_cat[f.get("category")] = by_cat.get(f.get("category"), 0) + 1
    passages_n = len(fc_result.get("passages", []))
    lines, dropped = fit([render_finding(i, f) for i, f in enumerate(findings, 1)], data_budget_chars(SYSTEM_HISTORY, PREDICT_HISTORY))
    header = (f"Politician: {name}\nDeclarații analizate: {passages_n}, din {len(arts)} articole. Semnalări în total: {len(all_findings)}"
              f" (în prompt: {len(lines)}, cel mult {MAX_FINDINGS}).\nSemnalări pe categorii: "
              + (", ".join(f"{CATEGORY_RO.get(c, c)}: {n}" for c, n in sorted(by_cat.items(), key=lambda kv: -kv[1])) or "niciuna") + "\n\nSEMNALĂRI:\n")
    log("Scor istoric (z) din erorile logice...")
    obj = call(SYSTEM_HISTORY, header + ("\n".join(lines) if lines else "(nicio semnalare)") + "\n\nRate the history of this politician.",
               history_schema(), PREDICT_HISTORY) or {}
    z = _clamp(obj.get("history"))
    if z is None:
        raise CredibilityError("Modelul nu a întors un scor de istoric valid.")
    reason = _cut(obj.get("reason"), 400)

    # ---- 2) x, y, w pe articole, în loturi care încap în limita cererii ----
    order = sorted(arts.values(), key=lambda a: (a["date"] or ""), reverse=True)
    batches = make_batches(order, data_budget_chars(SYSTEM_ARTICLES, PREDICT_BATCH))
    scored = {}
    for bi, batch in enumerate(batches, 1):
        log(f"Scor fezabilitate, precizie, manipulare: lotul {bi}/{len(batches)}")
        ids = {lid: a for lid, a, _ in batch}
        obj = call(SYSTEM_ARTICLES, f"Politician: {name}\n\nITEMS:\n" + "\n\n".join(t for _, _, t in batch) + "\n\nRate every item.",
                   articles_schema(list(ids)), PREDICT_BATCH) or {}
        for it in obj.get("items", []) if isinstance(obj, dict) else []:
            a = ids.get(it.get("id")) if isinstance(it, dict) else None
            x, y, w = (_clamp(it.get(k)) for k in ("feasibility", "precision", "manipulation")) if a else (None, None, None)
            if a is None or None in (x, y, w) or a["id"] in scored:
                continue
            scored[a["id"]] = {"feasibility": x, "precision": y, "manipulation": w, "history": z, "score": credibility(x, y, z, w),
                               "title": a["title"], "date": a["date"], "domain": a["domain"], "url": a["url"],
                               "flags": len(a["findings"]), "statements": len(a["passages"])}
    if not scored:
        raise CredibilityError("Modelul nu a întors scoruri valide pentru articole.")

    mean = lambda k: round(sum(v[k] for v in scored.values()) / len(scored), 1)
    x, y, w = mean("feasibility"), mean("precision"), mean("manipulation")
    return {
        "politician": name, "model": model, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "score": credibility(x, y, z, w),
        "components": {"feasibility": x, "precision": y, "history": z, "manipulation": w},
        "weights": WEIGHTS, "history_reason": reason, "articles": scored,
        "basis": {"statements": passages_n, "articles": len(arts), "articles_scored": len(scored),
                  "findings_total": len(all_findings), "findings_used": len(lines), "findings_cap": MAX_FINDINGS,
                  "findings_cut_by_context": dropped, "by_category": by_cat},
        "top_flags": [{"category": CATEGORY_RO.get(f.get("category"), f.get("category")), "severity": f.get("severity"),
                       "quote": _cut(f.get("quote"), 160), "domain": (f.get("source") or {}).get("domain", "")} for f in findings[:5]],
        "run": {"provider": "groq", "request_token_cap": llm.REQUEST_TOKEN_CAP, "temperature": OPTIONS["temperature"],
                "seconds": round(time.time() - t0, 1), **stats},
        "disclaimer": "Estimare automată a unui model, făcută doar din declarațiile și erorile logice analizate, fără acces la internet. De verificat manual.",
    }
