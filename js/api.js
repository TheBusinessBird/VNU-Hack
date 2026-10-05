// Client for api/promise_tracker_no_ai_v2.py (python promise_tracker_no_ai_v2.py -> http://127.0.0.1:8000).
//   GET /analyze?name=Prenume+Nume&include_text=1&speed=normal[&refresh=1] -> job { job_id, status: running|done|error, progress, result }
//   GET /jobs/<job_id>                                                      -> same job, polled until status != running
// result = { politician, generated_at, stats,
//            education: [{excerpt, source_url, source_title, source_domain, source_date, source_author}],
//            funding:   [{... same, funding_channels}],
//            sources:   [{id,url,domain,title,date,author,kind,primary,evidence:[excerpt],text}],
//            speeches:  [{source_id, speaker, text, ...}],
//            statements:[{source_id, text, context, is_promise, attributed_same_paragraph, ...}] }
// The API does not verify promises or classify press tone: promises are shown as detected, not as kept/broken.
const API_BASE = "http://127.0.0.1:8000";
const POLL_MS = 3000;
const ANALYSIS_SPEED = "normal";
const OFFICIAL_DOMAINS = ["cdep.ro", "senat.ro", "gov.ro", "presidency.ro"]; // sources shown as "Discurs"
// Promise status -> score on the 0..1 scale from the spec. Only verified statuses count; "unevaluated" (detected only) is left out.
const PROMISE_SCORE = { kept: 1, partial: 0.5, broken: 0 };

async function apiGet(path) {
  let res;
  try {
    res = await fetch(API_BASE + path);
  } catch (e) {
    throw new Error(`API-ul nu răspunde la ${API_BASE}. Pornește-l cu „python promise_tracker_no_ai_v2.py” din folderul api.`);
  }
  const body = await res.json().catch(() => ({}));
  if (body.job_id) return body;                 // 200 done, 202 running, 500 job error
  throw new Error(body.error || `API ${res.status}`);
}

// Extra search options for a politician or party: alias (party acronym) and the attribution term.
const whoQuery = p => (p.alias ? `&alias=${encodeURIComponent(p.alias)}` : "") + (p.term ? `&term=${encodeURIComponent(p.term)}` : "");

async function runAnalysis(p, { refresh = false, onProgress } = {}) {
  const name = p.name;
  // include_text=1: the same job also feeds the orientation scoring, so the sources are scraped once.
  let job = await apiGet(`/analyze?name=${encodeURIComponent(name)}&include_text=1&speed=${ANALYSIS_SPEED}${whoQuery(p)}${refresh ? "&refresh=1" : ""}`);
  while (job.status === "running") {
    if (onProgress) onProgress(job.progress);
    await new Promise(r => setTimeout(r, POLL_MS));
    job = await apiGet(`/jobs/${job.job_id}`);
  }
  if (job.status === "error") throw new Error(job.error || "Analiza a eșuat.");
  return job.result;
}

const clip = (s, n) => (s.length > n ? s.slice(0, n).replace(/\s+\S*$/, "") + "…" : s);
const realAuthor = a => (a && a !== "Necunoscut" ? a : null);

// API result -> what the profile page renders.
function adaptAnalysis(result) {
  const grouped = {};
  for (const k of ["speeches", "statements"])
    for (const x of result[k] || []) (grouped[x.source_id] = grouped[x.source_id] || { speeches: [], statements: [] })[k].push(x);

  const items = [], press = [];
  for (const s of result.sources || []) {
    const g = grouped[s.id] || { speeches: [], statements: [] };
    const official = OFFICIAL_DOMAINS.some(d => (s.domain || "").endsWith(d));
    const base = {
      id: s.id, title: s.title || s.domain, date: s.date || null, source: s.domain,
      author: realAuthor(s.author), url: s.url, truth: { promiseScores: [] }
    };
    if (g.speeches.length || g.statements.length) {
      const lead = g.speeches.length ? g.speeches[0].text : g.statements[0].text;
      items.push({
        ...base,
        type: g.speeches.length || official ? "discurs" : "articol",
        summary: clip(lead, 420),
        promises: g.statements.filter(x => x.is_promise).map(x => ({ quote: x.text, status: "unevaluated", rationale: "", evidence: [] })),
        statements: g.statements.filter(x => !x.is_promise).map(x => ({ quote: x.text })),
        speeches: g.speeches.length
      });
    }
    if (!official && (s.evidence || []).length) {     // "Despre candidat": non-official sources with passages mentioning the politician
      press.push({ ...base, type: "presa", tone: null, opinions: s.evidence.map(e => ({ quote: e, tone: null })) });
    }
  }

  const ev = e => ({
    quote: e.excerpt, source: e.source_domain, title: e.source_title, url: e.source_url,
    date: e.source_date || null, author: realAuthor(e.source_author), channels: e.funding_channels || []
  });
  const education = (result.education || []).map(ev), funding = (result.funding || []).map(ev);

  const promises = items.reduce((n, i) => n + i.promises.length, 0);
  return {
    generatedAt: result.generated_at,
    items, press, education, funding,
    stats: {
      sources: (result.stats || {}).sources ?? (result.sources || []).length,
      promises, kept: 0, partial: 0, broken: 0, unverifiable: 0,
      press: { articles: press.length, positive: 0, negative: 0, mixed: 0 }
    }
  };
}

// Per-browser cache so a profile opens instantly after the first (slow) analysis.
// "v4": the API returns about half as many sources now (smaller "normal" preset). "v3": the API changed (education, funding, speeches, statements); older cached results have another shape.
const cacheKey = id => `analiza4:${id}`;
function readAnalysisCache(id) {
  try { return JSON.parse(localStorage.getItem(cacheKey(id))); } catch (e) { return null; }
}
function writeAnalysisCache(id, data) {
  try { localStorage.setItem(cacheKey(id), JSON.stringify(data)); } catch (e) { /* quota / storage unavailable */ }
}

// ---- AI summaries (Groq), on demand ----
// POST /summary {name, kind: "article", url} | {name, kind: "education"|"income", items:[{excerpt,source_domain,source_date,source_title}]}
// -> job; result = { kind, model, generated_at, summary: {summary, verified, unsupported} | null (nothing relevant) }
async function apiPost(path, payload) {
  let res;
  try {
    res = await fetch(API_BASE + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  } catch (e) {
    throw new Error(`API-ul nu răspunde la ${API_BASE}.`);
  }
  const body = await res.json().catch(() => ({}));
  if (body.job_id) return body;
  throw new Error(body.error || `API ${res.status}`);
}

async function runSummary(payload, { onProgress } = {}) {
  let job = await apiPost("/summary", payload);
  while (job.status === "running") {
    if (onProgress) onProgress(job.progress);
    await new Promise(r => setTimeout(r, 1500));
    job = await apiGet(`/jobs/${job.job_id}`);
  }
  if (job.status === "error") throw new Error(job.error || "Rezumatul a eșuat.");
  return job.result;
}

const sumKey = id => `rezumate:${id}`;
function readSummaryCache(id) {
  try { return JSON.parse(localStorage.getItem(sumKey(id))); } catch (e) { return null; }
}
function writeSummaryCache(id, data) {
  try { localStorage.setItem(sumKey(id), JSON.stringify(data)); } catch (e) { /* storage unavailable */ }
}

// ---- Logical errors / suspicious statements, on demand (GET /factcheck, Groq models) ----
// result = { model, generated_at, disclaimer, summary:{flags,...}, findings:[{category, category_label, severity, confidence,
//            confidence_label, quote, related_quote?, problem, reasoning, how_to_verify, source:{domain,date,url,title}}] }
async function runFactcheck(name, { refresh = false, onProgress } = {}) {
  let job = await apiGet(`/factcheck?name=${encodeURIComponent(name)}${refresh ? "&refresh=1" : ""}`);
  while (job.status === "running") {
    if (onProgress) onProgress(job.progress);
    await new Promise(r => setTimeout(r, POLL_MS));
    job = await apiGet(`/jobs/${job.job_id}`);
  }
  if (job.status === "error") throw new Error(job.error || "Analiza erorilor logice a eșuat.");
  return job.result;
}

const fcKey = id => `erori:${id}`;
function readFactcheckCache(id) {
  try { return JSON.parse(localStorage.getItem(fcKey(id))); } catch (e) { return null; }
}
function writeFactcheckCache(id, data) {
  try { localStorage.setItem(fcKey(id), JSON.stringify(data)); } catch (e) { /* storage unavailable */ }
}

// ---- Credibility score (GET /credibility, Groq, temperature 0), computed from the logical errors ----
// result = { score, components:{feasibility,precision,history,manipulation}, weights, history_reason,
//            articles:{ <source id>:{score,feasibility,precision,manipulation,history,flags,statements} },
//            basis:{statements,articles,articles_scored,findings_total,findings_used,findings_cap}, top_flags, run, model, generated_at }
async function runCredibility(name, { refresh = false, onProgress } = {}) {
  let job = await apiGet(`/credibility?name=${encodeURIComponent(name)}${refresh ? "&refresh=1" : ""}`);
  while (job.status === "running") {
    if (onProgress) onProgress(job.progress);
    await new Promise(r => setTimeout(r, POLL_MS));
    job = await apiGet(`/jobs/${job.job_id}`);
  }
  if (job.status === "error") throw new Error(job.error || "Calculul scorului de credibilitate a eșuat.");
  return job.result;
}

const credKey = id => `credibilitate:${id}`;
function readCredibilityCache(id) {
  try { return JSON.parse(localStorage.getItem(credKey(id))); } catch (e) { return null; }
}
function writeCredibilityCache(id, data) {
  try { localStorage.setItem(credKey(id), JSON.stringify(data)); } catch (e) { /* storage unavailable */ }
}

// Read-only lookup in the server's disk cache: what was generated once (by anyone) is returned at once, nothing is ever generated.
// kind = "credibility" | "factcheck" | "orientation"; resolves to the result or null.
async function fetchCached(kind, p) {
  try {
    const res = await fetch(`${API_BASE}/cached?kind=${kind}&name=${encodeURIComponent(p.name)}&speed=${ANALYSIS_SPEED}${whoQuery(p)}`);
    const body = await res.json();
    return body && body.found ? body.result : null;
  } catch (e) {
    return null;
  }
}

// ---- Orientation scores (1..5 per axis) computed by a Groq model ----
// GET /orientation?name=…  -> job; result = { model, generated_at, axes:[{id,score,confidence,rationale,evidence,verified}], run }
async function runOrientation(p, { refresh = false, onProgress } = {}) {
  let job = await apiGet(`/orientation?name=${encodeURIComponent(p.name)}${whoQuery(p)}${refresh ? "&refresh=1" : ""}`);
  while (job.status === "running") {
    if (onProgress) onProgress(job.progress);
    await new Promise(r => setTimeout(r, POLL_MS));
    job = await apiGet(`/jobs/${job.job_id}`);
  }
  if (job.status === "error") throw new Error(job.error || "Scorarea a eșuat.");
  return job.result;
}

// API result -> { positions (0..100 per AXES entry, null = insufficient evidence), details, generatedAt, model }
function adaptOrientation(result, axes) {
  const byId = {};
  for (const a of result.axes || []) byId[a.id] = a;
  const details = axes.map(ax => byId[ax[4]] || { id: ax[4], score: null, confidence: "low", rationale: "", evidence: [], verified: true });
  return {
    positions: details.map(d => scoreToPos(d.score)),
    details,
    generatedAt: result.generated_at,
    model: result.model
  };
}

// Leaning index 0 = Dreapta .. 100 = Stânga, derived only from the social and economic axes:
// progressive/secular (score 1) and welfare state (score 5) count as Stânga. null if either axis has no evidence.
function leaningFrom(positions, axes) {
  const i = axes.findIndex(a => a[4] === "identity"), e = axes.findIndex(a => a[4] === "economy");
  if (i < 0 || e < 0 || positions[i] === null || positions[e] === null) return null;
  return Math.round(((100 - positions[i]) + positions[e]) / 2);
}

const orientKey = id => `orientare:${id}`;
function readOrientationCache(id) {
  try { return JSON.parse(localStorage.getItem(orientKey(id))); } catch (e) { return null; }
}
function writeOrientationCache(id, data) {
  try { localStorage.setItem(orientKey(id), JSON.stringify(data)); } catch (e) { /* storage unavailable */ }
}

if (typeof module !== "undefined") {
  module.exports = { adaptAnalysis, PROMISE_SCORE, adaptOrientation, leaningFrom };
}
