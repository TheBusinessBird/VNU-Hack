// Pagina „Metodologie”: completează cu date reale (GET /methodology) tot ce poate fi citit din cod sau din ce s-a salvat.
(() => {
  const API_BASE = "http://127.0.0.1:8000";
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const chips = (sel, list) => { const el = $(sel); if (el) el.innerHTML = (list || []).map(x => `<li>${esc(x)}</li>`).join(""); };
  const set = (k, v) => document.querySelectorAll(`.live[data-k="${k}"]`).forEach(e => { e.textContent = v; });
  const num = n => Number(n).toLocaleString("ro-RO");
  const fmt = d => d ? new Date(d).toLocaleString("ro-RO", { dateStyle: "long", timeStyle: "short" }) : "";
  const KIND = { analysis: "analize ale surselor", orientation: "scoruri pe axe", factcheck: "analize de erori logice", credibility: "scoruri de credibilitate", summary: "rezumate" };

  function render(d) {
    set("max_queries", d.search.max_queries); set("pages_per_query", d.search.pages_per_query); set("results_per_page", d.search.results_per_page);
    set("max_sources", d.fetch.max_sources); set("crawl_cap", d.fetch.crawl_cap); set("crawl_depth", d.fetch.crawl_depth);
    set("time_budget_s", d.fetch.time_budget_s); set("min_chars", d.fetch.min_chars); set("years_back", d.fetch.years_back);
    set("fc_max_news", d.factcheck.max_news); set("fc_per_news", d.factcheck.per_news);
    set("cr_max_findings", d.credibility.max_findings); set("cr_batch", d.credibility.articles_per_batch); set("tpm", num(d.provider.tpm_limit));
    document.querySelectorAll(".live-w").forEach(e => { e.textContent = String(d.credibility.weights[e.dataset.w]).replace(".", ","); });
    if ($("#ua")) $("#ua").textContent = d.fetch.user_agent;

    chips("#list-templates", d.search.query_templates.map(t => t.replace("{n}", "{nume}")));
    chips("#list-edu-words", d.search.education_words); chips("#list-fund-words", d.search.funding_words);
    chips("#list-official", d.official_domains); chips("#list-promise", d.promise_keywords.map(s => s.trim()));
    chips("#list-edu-kw", d.education_keywords); chips("#list-fund-kw", d.funding_keywords);

    const rows = [
      ["Erori logice (pas 1: declarații)", d.factcheck.models.join(" · "), "se încearcă pe rând, în rotație", d.factcheck.temperature],
      ["Scor de credibilitate", d.credibility.model, d.credibility.fallbacks.join(", "), d.credibility.temperature],
      ["Orientare pe axe", d.orientation.model, d.orientation.fallbacks.join(", "), d.orientation.temperature],
      ["Rezumate", d.summaries.model, d.summaries.fallbacks.join(", "), d.summaries.temperature]
    ];
    $("#model-table tbody").innerHTML = rows.map(r => `<tr><td>${esc(r[0])}</td><td><code>${esc(r[1])}</code></td><td>${esc(r[2])}</td><td class="num">${esc(r[3])}</td></tr>`).join("");

    $("#by-politician").innerHTML = d.politicians.length
      ? "Politicieni analizați până acum: " + d.politicians.map(p => `<b>${esc(p.name)}</b> (${num(p.sources)} surse, ${num(p.speeches)} discursuri, ${num(p.statements)} citate; analizat ${esc(fmt(p.generated_at))})`).join("; ") + "."
      : "Încă nu a fost analizat niciun politician.";

    const body = $("#domain-table tbody"), filter = $("#domain-filter");
    const draw = () => {
      const q = filter.value.trim().toLowerCase();
      const list = d.domains.filter(x => !q || x.domain.toLowerCase().includes(q));
      body.innerHTML = list.map(x => `<tr><td><a href="https://${esc(x.domain)}" target="_blank" rel="noopener">${esc(x.domain)}</a></td>
        <td class="num">${num(x.sources)}</td><td class="num">${num(x.with_statements)}</td><td class="small">${esc(x.politicians.join(", "))}</td>
        <td>${x.official ? '<span class="pstatus st-kept">oficial</span>' : ""}</td></tr>`).join("") || `<tr><td colspan="5" class="muted">Niciun site.</td></tr>`;
      $("#domain-count").textContent = `${num(list.length)} din ${num(d.domains.length)} site-uri`;
    };
    filter.addEventListener("input", draw);
    draw();

    $("#cache-inventory").textContent = Object.entries(d.cache).map(([k, n]) => `${num(n)} ${KIND[k] || k}`).join(", ") || "nimic încă";
    $("#meth-status").textContent = `Date actualizate din API la ${fmt(d.generated_at)}.`;
  }

  fetch(`${API_BASE}/methodology`).then(r => r.json()).then(d => {
    if (d.error) throw new Error(d.error);
    render(d);
  }).catch(() => {
    $("#meth-status").textContent = "API-ul nu răspunde, deci tabelele cu date (site-uri, modele, limite) nu se pot încărca. Textul metodologiei rămâne valabil. Pornește API-ul cu .\\run.ps1.";
    $("#domain-count").textContent = "";
  });
})();
