const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pending = '<span class="muted">în analiză</span>';
const fmt = (v, d = 2) => (v === null || v === undefined ? pending : Number(v).toFixed(d));
const initials = name => name.split(" ").map(w => w[0]).join("");
const has = v => v !== null && v !== undefined;
const fmtDate = d => d ? new Date(d).toLocaleDateString("ro-RO", { day: "numeric", month: "long", year: "numeric" }) : "";
// Credibility colour: green >= 7, amber >= 4.5, red below (gauge, news badges, home cards)
const credColor = v => (v >= 7 ? "#2e7d32" : v >= 4.5 ? "#e08a00" : "#d32f2f");
const host = u => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch (e) { return u; } };

// Photo with initials fallback if the image fails to load.
const avatar = (p, cls = "") => !p.photo
  ? `<div class="avatar avatar-text ${cls}">${esc(p.short || initials(p.name))}</div>`
  : `
  <div class="avatar ${p.kind === "party" ? "avatar-logo" : ""} ${cls}" data-initials="${esc(p.short || initials(p.name))}">
    <img src="${esc(p.photo)}" alt="${esc(p.name)}" loading="lazy"
         onerror="this.parentNode.textContent=this.parentNode.dataset.initials">
  </div>`;

const page = document.body.dataset.page;

if (page === "home") {
  const credLine = p => {
    if (p.kind === "party") return `Scor: ${p.stats.finalScore === null ? pending : fmt(p.stats.finalScore * 10, 1) + " / 10"}`;
    const c = readCredibilityCache(p.id);
    return c ? `Credibilitate: <b style="color:${credColor(c.score)}">${c.score.toFixed(1)}</b> / 10` : `Credibilitate: ${pending}`;
  };
  const card = p => `
    <a class="card" href="politician.html?id=${esc(p.id)}">
      ${avatar(p)}
      <div>
        <h3>${esc(p.name)}</h3>
        <p class="muted">${credLine(p)}</p>
      </div>
    </a>`;
  if ($("#parties")) $("#parties").innerHTML = PARTIES.map(card).join("");
  $("#list").innerHTML = POLITICIANS.map(card).join("");
}

// ---------- Shared pieces ----------

// markers: [{ value, cls, label }]
function renderIndex(markers) {
  const shown = markers.filter(m => has(m.value));
  return `
    <div class="index">
      <div class="index-bar">${shown.map(m =>
        `<span class="index-marker ${m.cls || ""}" style="left:${m.value}%" title="${esc(m.label)}"></span>`).join("")}</div>
      <div class="index-labels"><span>Dreapta</span><span>Centru</span><span>Stânga</span></div>
      ${shown.length ? "" : '<p class="muted small index-note">Poziție în analiză</p>'}
    </div>`;
}

// series: [{ values, cls, label }] — first series' number is printed between the labels.
function renderAxes(series) {
  return AXES.map(([l, r, , desc], i) => {
    const main = series[0].values[i];
    const dots = series.map(s => has(s.values[i])
      ? `<span class="dot ${s.cls || ""}" style="left:${s.values[i]}%" title="${esc(s.label)}: ${s.values[i]}"></span>` : "").join("");
    return `<div class="axis" title="${esc(desc)}">
      <div class="axis-labels"><span>${esc(l)}</span><span class="axis-val" title="Scor 1–5">${has(main) ? +posToScore(main).toFixed(1) : ""}</span><span>${esc(r)}</span></div>
      <div class="track">${dots}</div>
    </div>`;
  }).join("");
}

function legend(items) {
  return `<div class="legend">${items.map(([cls, label]) =>
    `<span><i class="key ${cls}"></i>${esc(label)}</span>`).join("")}</div>`;
}

// Hexagonal radar over RADAR axes. series: [{ values (17 axes), cls }]
function renderRadar(series) {
  const N = RADAR.length, C = 130, Rmax = 92;
  const pt = (k, r) => {
    const a = -Math.PI / 2 + (2 * Math.PI * k) / N;
    return [C + Math.cos(a) * r, C + Math.sin(a) * r];
  };
  const poly = r => RADAR.map((_, k) => pt(k, r).map(n => n.toFixed(1)).join(",")).join(" ");
  const grid = [0.25, 0.5, 0.75, 1].map(f => `<polygon class="radar-grid" points="${poly(Rmax * f)}"/>`).join("");
  const spokes = RADAR.map((_, k) => { const [x, y] = pt(k, Rmax); return `<line class="radar-grid" x1="${C}" y1="${C}" x2="${x}" y2="${y}"/>`; }).join("");
  const labels = RADAR.map(([, label], k) => {
    const [x, y] = pt(k, Rmax + 18);
    const anchor = Math.abs(x - C) < 4 ? "middle" : x > C ? "start" : "end";
    return `<text class="radar-label" x="${x}" y="${y}" text-anchor="${anchor}" dominant-baseline="middle">${esc(label)}</text>`;
  }).join("");
  // An axis without a score (insufficient evidence) is drawn at the centre ring with a hollow marker instead of hiding the whole shape.
  let drawn = 0, missing = 0;
  const shapes = series.map(s => {
    const vals = RADAR.map(([i]) => s.values[i]);
    if (vals.every(v => !has(v))) return "";
    drawn++;
    const gaps = vals.map(v => !has(v));
    if (s === series[series.length - 1] || series.length === 1) missing = gaps.filter(Boolean).length;
    const pts = vals.map((v, k) => pt(k, Rmax * (100 - (has(v) ? v : 50)) / 100).map(n => n.toFixed(1)).join(",")).join(" ");
    const holes = gaps.map((g, k) => { if (!g) return ""; const [x, y] = pt(k, Rmax * 0.5); return `<circle class="radar-gap" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3"/>`; }).join("");
    return `<polygon class="radar-shape ${s.cls || ""}" points="${pts}"/>${holes}`;
  }).join("");
  return `<svg class="radar" viewBox="-60 -10 380 280" role="img" aria-label="Hartă ideologică pe ${N} axe">
      ${grid}${spokes}${shapes}${labels}
    </svg>
    ${drawn ? "" : '<p class="muted small index-note">Hartă în analiză</p>'}
    ${missing ? `<p class="muted small index-note">${missing} ${missing === 1 ? "axă fără dovezi suficiente e marcată" : "axe fără dovezi suficiente sunt marcate"} cu cerc gol, la mijloc.</p>` : ""}`;
}

// Differences between two orientations (personal vs candidate, or candidate vs candidate).
function renderDiff(a, b, aLabel, bLabel) {
  const cmp = compareOrientation(a, b, AXES);
  if (!cmp) return null;
  const rows = cmp.major.map(x => {
    const pa = poleOf(x.a, x.labels) || "centru", pb = poleOf(x.b, x.labels) || "centru";
    return `<li>
      <div class="diff-head"><b>${esc(x.labels[0])} ↔ ${esc(x.labels[1])}</b><span class="diff-pts">${x.diff} pct.</span></div>
      <div class="diff-bar"><span class="dot dot-user" style="left:${x.a}%"></span><span class="dot" style="left:${x.b}%"></span></div>
      <div class="small muted">${esc(aLabel)}: ${x.a} (${esc(pa)}) · ${esc(bLabel)}: ${x.b} (${esc(pb)})</div>
    </li>`;
  }).join("");
  return `
    <div class="match"><b>${cmp.match}%</b><span>compatibilitate pe ${cmp.compared} ${cmp.compared === 1 ? "axă" : "axe"}</span></div>
    ${cmp.major.length
      ? `<ul class="diff-list">${rows}</ul>`
      : `<p class="small muted">Nicio diferență majoră (≥ ${MAJOR_DIFF} puncte) pe axele comparate.</p>`}`;
}

// ---------- Profile page ----------

// Cached AI scores (see js/api.js) replace the empty defaults from data.js. Returns the cache entry or null.
function applyCachedOrientation(p) {
  const c = readOrientationCache(p.id);
  if (!c || !Array.isArray(c.positions) || c.positions.length !== AXES.length) return null;
  p.orientation = c.positions;
  p.leaning = leaningFrom(c.positions, AXES);
  return c;
}

// Value from the manual table in data.js (FACTS); approximate and not verified by the site.
function manualFact(value, label) {
  return value ? `<div class="fact"><span class="fact-label">${esc(label)}</span><p>${esc(value)}</p><p class="small muted">Date introduse manual, aproximative: verifică la sursă.</p></div>` : "";
}

const CONF = { high: "încredere mare", medium: "încredere medie", low: "încredere mică" };

function orientationPanel(cache) {
  const note = cache
    ? `Scoruri 1–5 estimate de ${esc(cache.model)} din sursele analizate · ${esc(fmtDate(cache.generatedAt))}`
    : "Scorurile 1–5 se estimează cu un model AI (Groq) din sursele analizate. Poate dura câteva minute.";
  const why = cache ? `<details class="why"><summary>Cum a fost stabilit fiecare scor</summary><ul>${cache.details.map((d, i) => `
      <li><b>${esc(AXES[i][2])}</b>: ${d.score === null ? "dovezi insuficiente" : d.score + " / 5"}
        <span class="small muted">(${CONF[d.confidence] || CONF.low}${d.dropped_unsupported ? ", verdictul modelului a fost eliminat: niciun citat verificabil" : ""})</span>
        ${d.rationale ? `<div class="small">${esc(d.rationale)}</div>` : ""}
        ${(d.evidence || []).map(e => `<blockquote class="ev">„${esc(e.quote)}” — <a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.domain)}</a></blockquote>`).join("")}
      </li>`).join("")}</ul>
      <p class="small muted">Estimare automată din fragmente de text: verifică manual.</p></details>` : "";
  return `<div class="orient-actions">
      <p class="small muted" id="orient-status">${note}</p>
      <button class="pill-link" id="orient-run">${cache ? "Regenerează" : "Generează orientarea"}</button>
    </div>${why}`;
}

let orientationRunning = false;
async function generateOrientation(p, refresh = false) {
  const btn = $("#orient-run"), status = $("#orient-status");
  if (!btn || orientationRunning) return;
  orientationRunning = true;
  btn.disabled = true;
  status.classList.remove("err");
  try {
    const res = await runOrientation(p, { refresh, onProgress: m => { status.textContent = m || "Se procesează…"; } });
    writeOrientationCache(p.id, adaptOrientation(res, AXES));
    location.reload();                       // everything (radar, index, axes, differences) re-renders from the cache
  } catch (err) {
    status.textContent = err.message;
    status.classList.add("err");
    btn.disabled = false;
    orientationRunning = false;
  }
}

// The radar is filled by the AI scores, so a profile without them starts the scoring on first open (the button regenerates).
function wireOrientation(p, hasScores) {
  const btn = $("#orient-run");
  if (!btn) return;
  btn.addEventListener("click", () => generateOrientation(p, hasScores));
  if (!hasScores) generateOrientation(p);
}

const STATUS = {
  kept: ["Respectată", "st-kept"], partial: ["Parțial", "st-partial"],
  broken: ["Nerespectată", "st-broken"], unverifiable: ["Neverificabilă", "st-unv"],
  unevaluated: ["Neevaluată", "st-unv"]
};

function promisesBlock(list) {
  if (!list || !list.length) return "";
  return `<div class="promises">
    <h4>Promisiuni detectate în această sursă (${list.length})</h4>
    <ul>${list.map(p => {
      const [label, cls] = STATUS[p.status] || STATUS.unverifiable;
      return `<li>
        <span class="pstatus ${cls}">${label}</span>
        <q>${esc(p.quote)}</q>
        ${p.rationale ? `<div class="small muted">${esc(p.rationale)}</div>` : ""}
        ${p.evidence.length ? `<div class="small evidence">Dovezi: ${p.evidence.map((e, k) =>
          `<a href="${esc(e.url)}" target="_blank" rel="noopener" title="${esc(e.quote)}">${esc(host(e.url))}${p.evidence.length > 1 ? " " + (k + 1) : ""}</a>`).join(", ")}</div>` : ""}
      </li>`;
    }).join("")}</ul>
  </div>`;
}

function statementsBlock(list) {
  if (!list || !list.length) return "";
  return `<div class="promises">
    <h4>Declarații citate (${list.length})</h4>
    <ul>${list.slice(0, 6).map(x => `<li><q>${esc(x.quote)}</q></li>`).join("")}</ul>
    ${list.length > 6 ? `<div class="small muted">Încă ${list.length - 6} declarații în sursă.</div>` : ""}
    <div class="small muted">Citate cu numele candidatului în apropiere: atribuirea nu e verificată semantic.</div>
  </div>`;
}

const TONE = { positive: ["Pozitiv", "st-kept"], negative: ["Negativ", "st-broken"], mixed: ["Mixt", "st-partial"] };

function opinionsBlock(list) {
  if (!list || !list.length) return "";
  const toned = list.some(o => TONE[o.tone]);
  return `<div class="promises">
    <h4>${toned ? "Opinii" : "Fragmente"} despre candidat (${list.length})</h4>
    <ul>${list.map(o => `<li>${TONE[o.tone] ? `<span class="pstatus ${TONE[o.tone][1]}">${TONE[o.tone][0]}</span> ` : ""}<q>${esc(o.quote)}</q></li>`).join("")}</ul>
    ${toned ? '<div class="small muted">Ton stabilit pe cuvinte-cheie: verifică manual.</div>' : ""}
  </div>`;
}

// AI summaries (Groq) for the current politician (null until generated); set on the profile page.
let summaries = null;

function aiSummaryBlock(ai) {
  if (!ai) return "";
  if (ai.empty) return `<div class="ai-summary"><span class="ai-tag">Rezumat</span><p class="muted">Modelul nu a găsit date relevante despre candidat în acest material.</p></div>`;
  let lines = String(ai.summary).split(/\r?\n/).map(l => l.replace(/^\s*[-•*]\s*/, "").trim()).filter(Boolean);
  if (lines.length === 1) lines = lines[0].split(/(?<=[.!?])\s+(?=[A-ZĂÂÎȘȚ])/);
  const body = lines.length > 1 ? `<ul>${lines.map(l => `<li>${esc(l)}</li>`).join("")}</ul>` : `<p>${esc(lines[0] || "")}</p>`;
  return `<div class="ai-summary"><span class="ai-tag">Rezumat ${esc(summaries && summaries.model || "AI")}</span>${body}
    ${ai.verified ? "" : `<p class="small err">Conține elemente care nu apar în sursă (${esc((ai.unsupported || []).join(", "))}): verifică manual.</p>`}</div>`;
}

// ---------- Credibility score ----------
// Latest /credibility result for the current politician (null until computed); set on the profile page.
let credibility = null;

const CRED_LABELS = [
  ["feasibility", "Fezabilitate", "x", 0.2, "cât de realiste sunt declarațiile în circumstanțele actuale"],
  ["precision", "Precizie", "y", 0.2, "cât de explicite, precise și detaliate sunt (vag = scor mic)"],
  ["history", "Istoric", "z", 0.4, "trecut curat = scor mare; minciuni sau conspirații repetate = scor mic"],
  ["manipulation", "Manipulare", "w", 0.2, "10 = discurs onest, care își recunoaște defectele; 1 = înșelător sau manipulator"]
];

function credibilityTip(c) {
  return `Scor de credibilitate ${c.score.toFixed(1)} / 10 · Fezabilitate ${c.feasibility} · Precizie ${c.precision} · Istoric ${c.history} · Manipulare ${c.manipulation}`;
}

function credibilityPopover(c) {
  const b = c.basis || {};
  const rows = CRED_LABELS.map(([k, label, sym, w, hint]) => `
    <div class="cp-row" title="${esc(hint)}">
      <span class="cp-name">${esc(label)} <i>(${sym})</i></span>
      <span class="cp-w">× ${w}</span>
      <b>${Number(c.components[k]).toFixed(1)}</b>
      <span class="cp-bar"><i style="width:${c.components[k] * 10}%"></i></span>
    </div>`).join("");
  return `<div class="gauge-pop" role="tooltip">
    <div class="cp-title">Cum s-a calculat</div>
    ${rows}
    <div class="cp-formula">0,2·x + 0,2·y + 0,4·z + 0,2·w = <b>${c.score.toFixed(1)}</b></div>
    ${c.history_reason ? `<p class="cp-note"><b>Istoric:</b> ${esc(c.history_reason)}</p>` : ""}
    <p class="cp-note">Bazat pe ${esc(b.statements ?? "?")} declarații din ${esc(b.articles ?? "?")} articole; ${esc(b.findings_used ?? 0)} din ${esc(b.findings_total ?? 0)} erori semnalate au intrat în analiză (maximum ${esc(b.findings_cap ?? 50)}). Fezabilitatea, precizia și manipularea sunt mediile pe articole.</p>
    <p class="cp-note">${esc(c.disclaimer || "")}</p>
    <p class="cp-note">${esc(c.model)} · temperatura ${esc(c.run ? c.run.temperature : 0)} · ${esc(fmtDate(c.generated_at))}</p>
  </div>`;
}

function credibilityGauge(c) {
  const v = c ? c.score : null;
  return `<div class="gauge" tabindex="0" aria-label="${c ? esc(credibilityTip(c)) : "Scor de credibilitate necalculat"}">
    <svg viewBox="0 0 200 120" class="gauge-svg" role="img">
      <path class="gauge-track" d="M20 100 A80 80 0 0 1 180 100" pathLength="100"/>
      ${c ? `<path class="gauge-fill" style="stroke:${credColor(v)}" d="M20 100 A80 80 0 0 1 180 100" pathLength="100" stroke-dasharray="${(v * 10).toFixed(1)} 100"/>` : ""}
      <text x="100" y="86" class="gauge-num" text-anchor="middle" ${c ? `style="fill:${credColor(v)}"` : ""}>${c ? v.toFixed(1) : "–"}</text>
      <text x="100" y="106" class="gauge-sub" text-anchor="middle">din 10</text>
      <text x="20" y="116" class="gauge-end" text-anchor="middle">1</text>
      <text x="180" y="116" class="gauge-end" text-anchor="middle">10</text>
    </svg>
    ${c ? credibilityPopover(c) : ""}
  </div>`;
}

function credibilitySection(c) {
  return `<section class="block cred" id="sec-cred">
    <h2>Scor de credibilitate</h2>
    <div id="cred-gauge">${credibilityGauge(c)}</div>
    <div class="orient-actions">
      <p class="small muted" id="cred-status">${c
        ? `Calculat de ${esc(c.model)} din erorile logice · ${esc(fmtDate(c.generated_at))}. Treci cu mouse-ul peste indicator pentru detalii.`
        : "Se calculează din erorile logice ale declarațiilor (fezabilitate, precizie, istoric, manipulare). Poate dura câteva minute."}</p>
      <button class="pill-link" id="cred-run" ${c ? 'data-refresh="1"' : ""}>${c ? "Recalculează" : "Calculează"}</button>
    </div>
    <p class="small"><a href="metodologie.html#scor-articol">Cum se calculează scorul? →</a></p>
  </section>`;
}

// A politician that was already analysed (in any browser) shows its credibility score and logical errors at once from the server's disk cache.
async function fillFromServerCache(p) {
  if (!credibility) {
    const res = await fetchCached("credibility", p);
    if (res && !credibility) {
      writeCredibilityCache(p.id, res);
      credibility = res;
      $("#sec-cred").outerHTML = credibilitySection(res);
      $("#cred-run").addEventListener("click", () => generateCredibility(p));
      renderTab();
    }
  }
  if (!readFactcheckCache(p.id)) {
    const res = await fetchCached("factcheck", p);
    if (res && !factcheckRunning) {
      writeFactcheckCache(p.id, res);
      renderFallacies(res);
      $("#fc-status").textContent = `Generat de ${res.model}, ${fmtDate(res.generated_at)}`;
      $("#fc-run").textContent = "Regenerează";
      $("#fc-run").dataset.refresh = "1";
    }
  }
}

let credibilityRunning = false;
async function generateCredibility(p) {
  if (credibilityRunning) return;
  credibilityRunning = true;
  const btn = $("#cred-run"), status = $("#cred-status");
  btn.disabled = true;
  status.classList.remove("err");
  try {
    const res = await runCredibility(p.name, { refresh: btn.dataset.refresh === "1", onProgress: m => { status.textContent = m || "Se procesează…"; } });
    writeCredibilityCache(p.id, res);
    credibility = res;
    $("#sec-cred").outerHTML = credibilitySection(res);
    $("#cred-run").addEventListener("click", () => generateCredibility(p));
    renderTab();                                  // the news cards show the per-article score
  } catch (err) {
    status.textContent = err.message;
    status.classList.add("err");
    btn.disabled = false;
  } finally {
    credibilityRunning = false;
  }
}

function newsCard(n) {
  const ai = summaries && summaries.sources ? summaries.sources[n.id] : null;
  const cred = credibility && credibility.articles ? credibility.articles[n.id] : null;
  const score = cred ? cred.score : null;
  const kind = n.type === "discurs" ? "Discurs" : n.type === "presa" ? "Presă" : "Articol";
  const pc = (n.promises || []).length;
  const tone = n.tone && TONE[n.tone]
    ? ` · <span class="pstatus ${TONE[n.tone][1]}">${TONE[n.tone][0]}</span>` : "";
  return `
    <article class="news-card">
      <button class="news-head" aria-expanded="false">
        <span class="score ${score === null ? "score-na" : ""}" ${cred ? `style="background:${credColor(score)}"` : ""} title="${cred ? esc(credibilityTip(cred)) : "Scor de credibilitate: apare după ce calculezi scorul politicianului"}">
          ${score === null ? "–" : score.toFixed(1)}<small>/10</small>
        </span>
        <span class="news-main">
          <span class="news-meta"><b>${kind}</b> · ${esc(n.source || "")} · ${esc(fmtDate(n.date))}${pc ? ` · ${pc} ${pc === 1 ? "promisiune" : "promisiuni"}` : ""}${tone}</span>
          ${n.author ? `<span class="news-author">de ${esc(n.author)}</span>` : ""}
          <span class="news-title">${esc(n.title)}</span>
        </span>
        <span class="chev" aria-hidden="true"></span>
      </button>
      <div class="news-body"><div>
        <div class="ai-slot" data-sid="${esc(n.id)}">${ai ? aiSummaryBlock(ai) : '<p class="small muted">Rezumatul se generează când deschizi articolul.</p>'}</div>
        ${n.body ? `<p class="muted">${esc(n.body)}</p>` : ""}
        ${promisesBlock(n.promises)}
        ${statementsBlock(n.statements)}
        <dl class="news-facts">
          <div><dt>Sursa</dt><dd>${esc(n.source || "—")}</dd></div>
          <div><dt>Autor</dt><dd>${esc(n.author || "—")}</dd></div>
          <div><dt>Scor de credibilitate</dt><dd>${cred ? `${score.toFixed(1)} / 10 (fezabilitate ${cred.feasibility}, precizie ${cred.precision}, istoric ${cred.history}, manipulare ${cred.manipulation})` : "neanalizat"}</dd></div>
        </dl>
        ${n.url ? `<a class="read-more" href="${esc(n.url)}" target="_blank" rel="noopener">Citește la sursă →</a>` : ""}
      </div></div>
    </article>`;
}

// Only the last 12 months, newest first. Undated sources can't be placed in that window, so they are left out.
function recentSorted(items) {
  const cutoff = new Date(); cutoff.setFullYear(cutoff.getFullYear() - 1);
  const dated = items.filter(n => n.date && !isNaN(new Date(n.date)));
  const list = dated
    .filter(n => new Date(n.date) >= cutoff)
    .sort((a, b) => new Date(b.date) - new Date(a.date));
  return { list, older: dated.length - list.length, undated: items.length - dated.length };
}

function renderNews(items, emptyText, summary = "") {
  const { list, older, undated } = recentSorted(items);
  const note = [older && `${older} mai vechi de un an`, undated && `${undated} fără dată`].filter(Boolean).join(", ");
  $("#news").innerHTML = summary + (list.length ? list.map(newsCard).join("")
    : `<div class="news-empty">${emptyText}</div>`)
    + (note ? `<p class="small muted news-note">Surse omise: ${note}.</p>` : "");
}

// Two categories under "Știri relevante:" — "Discursuri și promisiuni" and "Despre candidat".
let currentData = null, currentTab = "speeches";

function renderTab() {
  document.querySelectorAll(".tab").forEach(t => {
    const on = t.dataset.tab === currentTab;
    t.classList.toggle("active", on);
    t.setAttribute("aria-selected", on);
  });
  if (!currentData) return;
  document.querySelector('[data-tab="speeches"] .count').textContent = recentSorted(currentData.items).list.length;
  document.querySelector('[data-tab="press"] .count').textContent = recentSorted(currentData.press).list.length;
  if (currentTab === "speeches") {
    renderNews(currentData.items, "Nu există discursuri sau articole relevante din ultimul an.");
  } else {
    const shown = recentSorted(currentData.press).list;     // same last-12-months window as the cards
    const count = tone => shown.filter(a => a.tone === tone).length;
    const t = { positive: count("positive"), negative: count("negative"), mixed: count("mixed") };
    const summary = t.positive + t.negative + t.mixed
      ? `<p class="small muted tone-summary">Opiniile presei despre candidat, din ultimul an:
      <span class="pstatus st-kept">${t.positive} pozitive</span><span class="pstatus st-broken">${t.negative} negative</span><span class="pstatus st-partial">${t.mixed} mixte</span></p>`
      : `<p class="small muted tone-summary">${shown.length} articole din ultimul an cu fragmente despre candidat. API-ul nu clasifică tonul opiniilor.</p>`;
    renderNews(currentData.press, "Nu s-au găsit articole despre candidat în ultimul an.", summary);
  }
}

const FC_SEV = { high: "st-broken", medium: "st-partial", low: "st-unv" };

// result: the /factcheck result (or null before the first run).
function renderFallacies(result) {
  const box = $("#fallacies");
  if (!result) {
    box.innerHTML = '<div class="news-empty">Apasă „Generează erori logice”. Un model AI (Groq) analizează declarațiile candidatului; durează câteva minute.</div>';
    return;
  }
  const list = result.findings || [];
  if (!list.length) {
    box.innerHTML = `<div class="news-empty">Modelul nu a semnalat nimic în ${esc(result.summary ? result.summary.passages_analysed : 0)} declarații analizate.</div>`;
    return;
  }
  box.innerHTML = `<p class="small muted">${esc(result.disclaimer || "")}</p>` + list.map(f => {
    const src = f.source || {};
    return `<article class="fallacy">
      <div class="fallacy-type">${esc(f.category_label || f.category)}
        <span class="pstatus ${FC_SEV[f.severity] || "st-unv"}">gravitate ${esc(f.severity_label || f.severity)}</span>
        <span class="small muted">încredere ${esc(f.confidence_label || f.confidence)}</span></div>
      <blockquote>„${esc(f.quote)}”</blockquote>
      ${f.related_quote ? `<p class="small muted">Comparată cu: „${esc(f.related_quote)}”${f.related_source && f.related_source.date ? ` (${esc(fmtDate(f.related_source.date))})` : ""}</p>` : ""}
      ${f.problem ? `<p>${esc(f.problem)}</p>` : ""}
      ${f.reasoning ? `<p class="small muted">${esc(f.reasoning)}</p>` : ""}
      ${f.how_to_verify ? `<p class="small"><b>Cum se verifică:</b> ${esc(f.how_to_verify)}</p>` : ""}
      <div class="small muted">${[src.domain, fmtDate(src.date)].filter(Boolean).map(esc).join(" · ")}
        ${src.url ? ` · <a href="${esc(src.url)}" target="_blank" rel="noopener">sursa</a>` : ""}</div>
    </article>`;
  }).join("");
}

let factcheckRunning = false;
async function generateFactcheck(p) {
  if (factcheckRunning) return;
  factcheckRunning = true;
  const btn = $("#fc-run"), status = $("#fc-status");
  btn.disabled = true;
  status.classList.remove("err");
  try {
    const res = await runFactcheck(p.name, { refresh: btn.dataset.refresh === "1", onProgress: m => { status.textContent = m || "Se procesează…"; } });
    writeFactcheckCache(p.id, res);
    renderFallacies(res);
    status.textContent = `Generat de ${res.model}, ${fmtDate(res.generated_at)}`;
    btn.textContent = "Regenerează";
    btn.dataset.refresh = "1";
  } catch (err) {
    status.textContent = err.message;
    status.classList.add("err");
  } finally {
    btn.disabled = false;
    factcheckRunning = false;
  }
}

function renderPromiseStats(st) {
  $("#stat-promises").innerHTML = `${st.promises}<span class="muted"> detectate</span>`;
  $("#promise-breakdown").innerHTML = st.promises
    ? `<span class="pstatus st-unv">${st.promises} neevaluate</span>
       <div class="small muted">din ${st.sources} surse analizate · API-ul detectează promisiunile pe cuvinte-cheie, dar nu verifică dacă au fost respectate</div>`
    : `<div class="small muted">Nicio promisiune găsită în ${st.sources} surse analizate.</div>`;
}

// Education / "Declarație de venit" evidence: every item keeps its source, date and author.
function evidenceList(list, emptyText, withChannels) {
  if (!list || !list.length) return `<p class="small muted">${emptyText}</p>`;
  const card = e => `<li class="evid">
      <q>${esc(clip(e.quote, 420))}</q>
      ${withChannels && e.channels.length ? `<div class="chips">${e.channels.map(c => `<span class="pstatus st-unv">${esc(c)}</span>`).join("")}</div>` : ""}
      <div class="small muted">${[e.source, fmtDate(e.date), e.author && "de " + e.author].filter(Boolean).map(esc).join(" · ")}
        · <a href="${esc(e.url)}" target="_blank" rel="noopener">sursa</a></div>
    </li>`;
  const first = list.slice(0, 4), rest = list.slice(4);
  return `<ul class="evid-list">${first.map(card).join("")}</ul>` +
    (rest.length ? `<details class="why"><summary>Încă ${rest.length} fragmente</summary><ul class="evid-list">${rest.map(card).join("")}</ul></details>` : "") +
    `<p class="small muted">Fragmente extrase automat din sursele analizate: verifică manual.</p>`;
}

function evidenceSection(list, emptyText, withChannels, ai, kind) {
  if (!list.length) return evidenceList(list, emptyText, withChannels);
  if (!ai) return `<div class="sum-row"><button class="linkish" data-sum="${kind}">Rezumă (AI)</button> <span class="small muted" data-sum-status></span></div>` +
    evidenceList(list, emptyText, withChannels);
  return aiSummaryBlock(ai) + `<details class="why"><summary>Fragmentele din surse (${list.length})</summary>${evidenceList(list, emptyText, withChannels)}</details>
    <div class="sum-row"><button class="linkish" data-sum="${kind}" data-refresh="1">Regenerează rezumatul</button> <span class="small muted" data-sum-status></span></div>`;
}

function showAnalysis(data) {
  currentData = data;
  renderTab();
  renderPromiseStats(data.stats);
  if ($("#edu-body")) $("#edu-body").innerHTML = evidenceSection(data.education, "Nu s-au găsit informații despre studii în sursele analizate.", false, summaries && summaries.education, "education");
  if ($("#income-body")) $("#income-body").innerHTML = evidenceSection(data.funding, "Nu s-au găsit informații despre finanțare sau venituri în sursele analizate.", true, summaries && summaries.income, "income");
  $("#analysis-status").innerHTML = `Analiză din ${esc(fmtDate(data.generatedAt))} · <button class="linkish" id="refresh">Reîmprospătează</button>`;
}

// On-demand summaries: one article when its card is opened, or one section (education / income) on button click.
const summaryInFlight = new Set();

function storeSummary(p, apply) {
  summaries = summaries || { model: "", sources: {} };
  apply(summaries);
  writeSummaryCache(p.id, summaries);
}

const asSummary = res => (res.summary ? res.summary : { empty: true });

async function ensureArticleSummary(p, card) {
  const slot = card.querySelector(".ai-slot");
  if (!slot) return;
  const id = slot.dataset.sid;
  if ((summaries && summaries.sources && summaries.sources[id]) || summaryInFlight.has(id)) return;
  const n = [...currentData.items, ...currentData.press].find(x => x.id === id);
  if (!n || !n.url) return;
  summaryInFlight.add(id);
  slot.innerHTML = '<p class="small muted"><span class="spinner inline"></span> Se face rezumatul… <span class="ai-progress"></span></p>';
  try {
    const res = await runSummary({ name: p.name, term: p.term, kind: "article", url: n.url },
      { onProgress: m => { const el = slot.querySelector(".ai-progress"); if (el) el.textContent = m || ""; } });
    storeSummary(p, s => { s.model = res.model; s.sources[id] = asSummary(res); });
    slot.innerHTML = aiSummaryBlock(summaries.sources[id]);
  } catch (err) {
    slot.innerHTML = `<p class="small err">${esc(err.message)} <button class="linkish" data-retry-sum="${esc(id)}">Încearcă din nou</button></p>`;
  } finally {
    summaryInFlight.delete(id);
  }
}

async function generateSectionSummary(p, kind, btn) {
  const key = "section-" + kind;
  if (summaryInFlight.has(key) || !currentData) return;
  const status = btn.parentNode.querySelector("[data-sum-status]");
  const list = kind === "education" ? currentData.education : currentData.funding;
  summaryInFlight.add(key);
  btn.disabled = true;
  status.classList.remove("err");
  try {
    const items = list.slice(0, 14).map(e => ({ excerpt: e.quote, source_domain: e.source, source_date: e.date, source_title: e.title }));
    const res = await runSummary({ name: p.name, kind, items, refresh: !!btn.dataset.refresh },
      { onProgress: m => { status.textContent = m || "Se procesează…"; } });
    storeSummary(p, s => { s.model = res.model; s[kind] = asSummary(res); });
    showAnalysis(currentData);
  } catch (err) {
    status.textContent = err.message;
    status.classList.add("err");
    btn.disabled = false;
  } finally {
    summaryInFlight.delete(key);
  }
}

let analysisRunning = false;
async function loadAnalysis(p, refresh = false) {
  if (analysisRunning) return;
  analysisRunning = true;
  const status = $("#analysis-status");
  const progress = msg => {
    status.textContent = "";
    $("#news").innerHTML = `<div class="news-empty"><div class="spinner"></div>Se analizează sursele… <b>${esc(msg || "")}</b><br>
      <span class="small">Prima analiză poate dura câteva minute.</span></div>`;
  };
  progress("Pornit");
  try {
    const data = adaptAnalysis(await runAnalysis(p, { refresh, onProgress: progress }));
    writeAnalysisCache(p.id, data);
    showAnalysis(data);
  } catch (err) {
    const cached = readAnalysisCache(p.id);
    if (cached) { showAnalysis(cached); status.insertAdjacentHTML("beforeend", ` · <span class="err">${esc(err.message)}</span>`); }
    else $("#news").innerHTML = `<div class="news-empty">${esc(err.message)}<br><button class="pill-link" id="retry">Încearcă din nou</button></div>`;
  } finally {
    analysisRunning = false;
  }
}

if (page === "politician") {
  const id = new URLSearchParams(location.search).get("id");
  const p = ENTITIES.find(x => x.id === id);
  if (!p) {
    $("#profile").innerHTML = `<div class="empty">Profil necunoscut.<br><a class="back" href="index.html">← Înapoi la listă</a></div>`;
  } else {
    document.title = `${p.name} — Profil`;
    const s = p.stats;
    const me = getUserOrientation(AXES.length);
    const orientCache = applyCachedOrientation(p);
    const meAxes = me ? me.axes : AXES.map(() => null);
    const isParty = p.kind === "party";
    const subj = isParty ? "Partid" : "Candidat";
    credibility = isParty ? null : readCredibilityCache(p.id);

    const diffHtml = me ? renderDiff(me.axes, p.orientation, "Tu", subj) : null;
    const diffBlock = !me
      ? `<p class="small muted">Nu ți-ai aflat încă orientarea politică.</p>
         <a class="pill-link" href="quiz.html">Fă quiz-ul →</a>`
      : diffHtml || `<p class="small muted">Orientarea ${isParty ? "partidului" : "candidatului"} este în analiză. Diferențele apar când există date pe aceleași axe.</p>`;

    $("#profile").innerHTML = `
      <div class="profile-top">
        <a class="back" href="${isParty ? "index.html#partide" : "index.html"}">← ${isParty ? "Partide" : "Politicieni"}</a>
        <a class="pill-link" href="compare.html?a=${esc(p.id)}">Compară cu altul</a>
      </div>
      <div class="layout">
        <aside class="side">
          <div class="profile-head">
            ${avatar(p, "avatar-lg")}
            <div>
              ${p.party ? `<div class="party">${esc(p.party)}</div>` : ""}
              <h1>${esc(p.name)}</h1>
              ${p.role ? `<div class="role">${esc(p.role)}</div>` : ""}
              ${p.photoCredit
                ? `<p class="muted small credit">${esc(p.photoCredit.label)}: <a href="${esc(p.photoCredit.page)}" target="_blank" rel="noopener">Wikimedia Commons</a> · ${esc(p.photoCredit.license)}</p>`
                : p.photo ? '<p class="muted small credit">Foto: Wikimedia Commons</p>' : ""}
            </div>
          </div>
          ${p.bio || p.sources.length ? `<section class="block">
            ${p.bio ? `<p class="bio">${esc(p.bio)}</p>` : ""}
            ${p.sources.length ? `<h2>Surse</h2><div class="sources">${p.sources.map(u =>
              `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(host(u))}</a>`).join("")}</div>` : ""}
          </section>` : ""}

          ${isParty ? "" : credibilitySection(credibility)}

          <section class="block">
            <h2>Poziționare</h2>
            ${renderIndex([{ value: p.leaning, label: p.name }, { value: me && me.leaning, cls: "marker-user", label: "Tu" }])}
            ${me ? legend([["", p.name], ["key-user", "Tu"]]) : ""}
          </section>

          <section class="block">
            <h2>Hartă ideologică · ${AXES.length} axe</h2>
            ${renderRadar([{ values: meAxes, cls: "radar-user" }, { values: p.orientation }])}
            ${me ? legend([["", subj], ["key-user", "Tu"]]) : ""}
          </section>

          <section class="block">
            <h2>Statistici</h2>
            <div class="stats">
              <div class="stat"><span>Afirmații</span><b>${fmt(s.statements, 0)}</b></div>
              <div class="stat"><span>Contradicții</span><b>${fmt(s.contradictions, 0)}</b></div>
              <div class="stat" title="Promisiuni evaluate / găsite"><span>Promisiuni</span><b id="stat-promises">${fmt(s.promisesEvaluated, 0)}</b></div>
              <div class="stat"><span>Scor final</span><b>${s.finalScore === null ? pending : fmt(s.finalScore * 10, 1)}</b></div>
            </div>
            <div id="promise-breakdown" class="breakdown"></div>
          </section>

          <section class="block">
            <h2>Orientare pe axe · ${AXES.length} criterii</h2>
            ${me ? legend([["", subj], ["key-user", "Tu"]]) : ""}
            <div class="axes">${renderAxes([{ values: p.orientation, label: subj }, { values: meAxes, cls: "dot-user", label: "Tu" }])}</div>
            ${orientationPanel(orientCache)}
          </section>

          ${isParty ? "" : `
          <section class="block" id="sec-education">
            <h2>Educație</h2>
            ${manualFact(p.education, "Educație")}
            <div id="edu-body"><p class="small muted">Se încarcă…</p></div>
          </section>

          <section class="block" id="sec-income">
            <h2>Declarație de venit</h2>
            ${manualFact(p.income, "Venit declarat / an")}
            <div id="income-body"><p class="small muted">Se încarcă…</p></div>
          </section>

          `}
          <section class="block diff">
            <h2>Corelare cu orientarea personală</h2>
            <h3 class="diff-title">Diferențe majore dintre orientarea politică personală și cea a ${isParty ? "partidului" : "candidatului"}:</h3>
            ${diffBlock}
          </section>
        </aside>

        <section class="main-col">
          <h2 class="news-heading">Știri relevante:</h2>
          <div class="tabs" role="tablist">
            <button class="tab active" role="tab" aria-selected="true" data-tab="speeches">Discursuri și promisiuni <span class="count"></span></button>
            <button class="tab" role="tab" aria-selected="false" data-tab="press">Despre ${isParty ? "partid" : "candidat"} <span class="count"></span></button>
          </div>
          <p id="analysis-status" class="small muted analysis-status"></p>
          <div id="news" class="news-list"><div class="news-empty">Se încarcă…</div></div>

          ${isParty ? "" : `
          <h2 class="news-heading sub">Erori logice detectate în discursuri</h2>
          <div class="orient-actions">
            <p class="small muted" id="fc-status">La comandă: modele AI (Groq) caută erori logice, contradicții și afirmații suspecte, doar în ultimele 20 de știri din „Discursuri și promisiuni” (max. 3 declarații pe știre).</p>
            <button class="pill-link" id="fc-run">Generează erori logice</button>
          </div>
          <div id="fallacies" class="news-list"><div class="news-empty">Se încarcă…</div></div>
          `}
        </section>
      </div>`;

    $("#news").addEventListener("click", e => {
      if (e.target.closest("#retry")) return loadAnalysis(p);
      const retry = e.target.closest("[data-retry-sum]");
      if (retry) return ensureArticleSummary(p, retry.closest(".news-card"));
      const head = e.target.closest(".news-head");
      if (!head) return;
      const open = head.parentNode.classList.toggle("open");
      head.setAttribute("aria-expanded", open);
      if (open) ensureArticleSummary(p, head.parentNode);
    });
    wireOrientation(p, !!orientCache);
    if (!isParty) $("#cred-run").addEventListener("click", () => generateCredibility(p));
    document.querySelector(".tabs").addEventListener("click", e => {
      const tab = e.target.closest(".tab");
      if (!tab) return;
      currentTab = tab.dataset.tab;
      renderTab();
    });
    $("#analysis-status").addEventListener("click", e => {
      if (e.target.closest("#refresh")) loadAnalysis(p, true);
    });
    for (const sec of isParty ? [] : ["#sec-education", "#sec-income"]) {
      $(sec).addEventListener("click", e => {
        const btn = e.target.closest("[data-sum]");
        if (btn) generateSectionSummary(p, btn.dataset.sum, btn);
      });
    }
    summaries = readSummaryCache(p.id);

    // Cached analysis shows instantly; otherwise run it on the API (can take minutes).
    const cached = readAnalysisCache(p.id);
    if (cached) showAnalysis(cached); else loadAnalysis(p);
    if (!isParty) {
      const fcCached = readFactcheckCache(p.id);
      renderFallacies(fcCached);
      if (fcCached) {
        $("#fc-status").textContent = `Generat de ${fcCached.model}, ${fmtDate(fcCached.generated_at)}`;
        $("#fc-run").textContent = "Regenerează";
        $("#fc-run").dataset.refresh = "1";
      }
      $("#fc-run").addEventListener("click", () => generateFactcheck(p));
    }
    if (!isParty) fillFromServerCache(p);
  }
}

// ---------- Compare page ----------

if (page === "compare") {
  const q = new URLSearchParams(location.search);
  const options = sel => POLITICIANS.map(p => `<option value="${esc(p.id)}" ${p.id === sel ? "selected" : ""}>${esc(p.name)}</option>`).join("");
  const aId = q.get("a") || POLITICIANS[0].id;
  const bId = q.get("b") || POLITICIANS.find(p => p.id !== aId).id;
  const A = POLITICIANS.find(p => p.id === aId) || POLITICIANS[0];
  const B = POLITICIANS.find(p => p.id === bId) || POLITICIANS[1];
  applyCachedOrientation(A); applyCachedOrientation(B);

  $("#compare").innerHTML = `
    <a class="back" href="politician.html?id=${esc(A.id)}">← ${esc(A.name)}</a>
    <h1>Compară politicieni</h1>
    <form class="compare-pick" method="get">
      <select name="a" aria-label="Primul politician">${options(A.id)}</select>
      <span class="muted">vs</span>
      <select name="b" aria-label="Al doilea politician">${options(B.id)}</select>
      <button class="pill-link" type="submit">Compară</button>
    </form>

    <div class="compare-heads">
      <a class="compare-person" href="politician.html?id=${esc(A.id)}">${avatar(A, "avatar-lg")}<b>${esc(A.name)}</b><i class="key"></i></a>
      <a class="compare-person" href="politician.html?id=${esc(B.id)}">${avatar(B, "avatar-lg")}<b>${esc(B.name)}</b><i class="key key-user"></i></a>
    </div>

    <div class="layout compare-layout">
      <aside class="side">
        <section class="block"><h2>Poziționare</h2>
          ${renderIndex([{ value: A.leaning, label: A.name }, { value: B.leaning, cls: "marker-user", label: B.name }])}
        </section>
        <section class="block"><h2>Hartă ideologică · ${AXES.length} axe</h2>
          ${renderRadar([{ values: B.orientation, cls: "radar-user" }, { values: A.orientation }])}
          ${legend([["", A.name], ["key-user", B.name]])}
        </section>
        <section class="block diff"><h2>Diferențe majore</h2>
          ${renderDiff(A.orientation, B.orientation, A.name, B.name) || '<p class="small muted">Orientările sunt în analiză. Diferențele apar când ambii au date pe aceleași axe.</p>'}
        </section>
      </aside>
      <section class="main-col">
        <h2 class="news-heading">Orientare pe axe</h2>
        ${legend([["", A.name], ["key-user", B.name]])}
        <div class="axes axes-wide">${renderAxes([{ values: A.orientation, label: A.name }, { values: B.orientation, cls: "dot-user", label: B.name }])}</div>
      </section>
    </div>`;
}


// ---------- "Cu cine semeni": politicians ranked by similarity to the user's saved quiz result (home page, right column) ----------
const MATCH_MIN_AXES = 3;   // a politician needs scores on at least this many axes that the user also answered

function politicianMatches() {
  const me = getUserOrientation(AXES.length);
  if (!me) return null;
  const list = [];
  for (const p of POLITICIANS) {
    let c = null;
    try { c = JSON.parse(localStorage.getItem(`orientare:${p.id}`)); } catch (e) { /* storage unavailable */ }
    if (!c || !Array.isArray(c.positions) || c.positions.length !== AXES.length) continue;
    const cmp = compareOrientation(me.axes, c.positions, AXES);
    if (cmp && cmp.compared >= MATCH_MIN_AXES) list.push({ p, match: cmp.match, compared: cmp.compared });
  }
  return list.sort((a, b) => b.match - a.match);
}

if (page === "home" && $("#match-side")) {
  const list = politicianMatches();
  const body = list === null
    ? `<p class="small muted">Fă quiz-ul ca să vezi cu cine semeni.</p><a class="pill-link" href="quiz.html">Află-ți orientarea →</a>`
    : !list.length
      ? `<p class="small muted">Asemănarea apare după ce deschizi profilurile politicienilor, pentru că li se calculează atunci orientarea.</p>`
      : `<ol class="match-list">${list.map((x, i) => `
          <li class="${i === 0 ? "top" : ""}">
            <a href="politician.html?id=${esc(x.p.id)}" title="Asemănare pe ${x.compared} axe comparate">
              <span class="match-rank">${i + 1}</span>
              ${avatar(x.p)}
              <span class="match-name">${esc(x.p.name)}</span>
              <b class="match-pct">${x.match}%</b>
              <span class="match-bar"><i style="width:${x.match}%"></i></span>
            </a>
          </li>`).join("")}</ol>`;
  $("#match-side").innerHTML = `<h2>Cu cine semeni</h2>${body}`;
}
