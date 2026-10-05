"""python tools/build_quiz.py  ->  regenerează js/quiz.js după ce modifici quiz-ul (SRC).

Builds js/quiz.js from the user's quiz (progressive (2) (2).html): same items and scoring engine,
site styling (qz- classes), results converted to the site's axis convention and saved for the profile pages."""
import re

SRC = r"C:\Users\Ola\Downloads\progressive (2) (2).html"
OUT = r"C:\Users\Ola\politics-mvp\js\quiz.js"

html = open(SRC, encoding="utf-8").read()
js = html[html.index("<script>") + len("<script>"):html.rindex("</script>")]

# 1) the quiz's AXES object would collide with the site's AXES array -> QAXES (R_AXES is untouched: no word boundary)
js = re.sub(r"\bAXES\b", "QAXES", js)

# 2) site-styled class names: prefix every static class token with qz- (4 of them clash with the site's CSS)
def prefix_classes(m):
    tokens = m.group(1).split(" ")
    return 'class="' + " ".join(("qz-" + t) if t else t for t in tokens)
js = re.sub(r'class="([a-z0-9 ]+)', prefix_classes, js)
def rep(old, new, count=1):
    global js
    assert js.count(old) == count, (js.count(old), old[:90])
    js = js.replace(old, new)
rep('?"ok":""', '?"qz-ok":""')
rep('querySelector(".opts")', 'querySelector(".qz-opts")')
rep('querySelectorAll(".sal")', 'querySelectorAll(".qz-sal")')

# 3) texts: titles for the site; the site DOES compare the saved profile with politicians and parties,
#    so the quiz must not claim otherwise
rep('docTitle:"Busola de vot — Arm B: profil progresiv pe zece axe"', 'docTitle:"Quiz — orientare politică"')
rep('docTitle:"Voting compass — Arm B: progressive ten-axis profile"', 'docTitle:"Quiz — political orientation"')
rep('howBody:"Zece axe de poziționare politică, fără partide: răspunsurile tale produc un profil numeric."',
    'howBody:"Zece axe de poziționare politică: răspunsurile tale produc un profil numeric, pe aceleași axe ca politicienii și partidele de pe site."')
rep('howBody:"Ten axes of political positioning, without parties: your answers produce a numeric profile."',
    'howBody:"Ten axes of political positioning: your answers produce a numeric profile on the same axes as the politicians and parties on this site."')
rep('"Nu îți spunem pe cine să votezi și nu te comparăm cu partide."',
    '"Nu îți spunem pe cine să votezi. Pe paginile politicienilor și partidelor vezi diferențele dintre pozițiile tale și ale lor."')
rep('"We do not tell you who to vote for and we do not compare you with parties."',
    '"We do not tell you who to vote for. On the politicians\' and parties\' pages you see how your positions differ from theirs."')
rep('"Poți cere ștergerea datelor; răspunsurile politice sunt date protejate (art. 9 GDPR)."',
    '"Rezultatul se salvează doar în acest browser și îl poți șterge oricând; răspunsurile politice sunt date protejate (art. 9 GDPR)."')
rep('"You can request deletion; political answers are protected data (GDPR Art. 9)."',
    '"The result is saved only in this browser and you can delete it at any time; political answers are protected data (GDPR Art. 9)."')
rep('consentBody:"Îmi dau consimțământul explicit pentru prelucrarea răspunsurilor mele politice (date din categoria specială, art. 9 GDPR), exclusiv pentru calcularea profilului. Fără mesaje politice țintite, fără vânzarea datelor. Pot cere ștergerea oricând."',
    'consentBody:"Îmi dau consimțământul explicit pentru prelucrarea răspunsurilor mele politice (date din categoria specială, art. 9 GDPR), exclusiv pentru calcularea profilului și compararea lui, în acest browser, cu pozițiile politicienilor și partidelor de pe site. Fără mesaje politice țintite, fără vânzarea datelor. Pot șterge rezultatul oricând."')
rep('consentBody:"I give explicit consent to process my political answers (special category data, GDPR Art. 9), solely to compute my profile. No political messaging targeting, no data sales. Deletable at any time."',
    'consentBody:"I give explicit consent to process my political answers (special category data, GDPR Art. 9), solely to compute my profile and compare it, in this browser, with the positions of the politicians and parties on this site. No political messaging targeting, no data sales. Deletable at any time."')
rep('privacy:"Datele rămân în această pagină (prototip local). Într-o versiune publică: stocate criptat în UE, șterse la cerere, DPIA înainte de lansare."',
    'privacy:"Răspunsurile și profilul rămân în acest browser (stocare locală); nu sunt trimise nicăieri."')
rep('privacy:"In this prototype everything stays in your browser. A public version: encrypted storage in the EU, deletion on request, DPIA before launch."',
    'privacy:"Your answers and profile stay in this browser (local storage); they are not sent anywhere."')
rep('resBody:"Scoruri pe scala 1–5, cu zecimale. Bara arată intervalul de incertitudine (± marja). Aproape de 1 înseamnă primul pol, aproape de 5 al doilea pol."',
    'resBody:"Scoruri pe scala 1–5, cu zecimale, ca la politicieni: aproape de 1 înseamnă primul pol (stânga), aproape de 5 al doilea pol (dreapta). Bara arată intervalul de incertitudine (± marja)."')
rep('resBody:"1-5 scores with decimals. The bar shows the uncertainty interval (± the margin). Near 1 means the first pole, near 5 the second pole."',
    'resBody:"1-5 scores with decimals, as for the politicians: near 1 means the first pole (left), near 5 the second pole (right). The bar shows the uncertainty interval (± the margin)."')
rep('Structura de corelații dintre axe e folosită doar pentru indicatorul de coerență. Fără partide, fără potriviri."',
    'Structura de corelații dintre axe e folosită doar pentru indicatorul de coerență. Comparația cu politicienii și partidele se face separat, pe paginile lor."')
rep('The axis-correlation structure is used only for the coherence indicator. No parties, no matches."',
    'The axis-correlation structure is used only for the coherence indicator. The comparison with politicians and parties happens separately, on their pages."')
rep('endNote:"Acest prototip nu îți spune pe cine să votezi și nu compară răspunsurile cu partide. Profilul este o descriere a pozițiilor tale, nu o recomandare."',
    'endNote:"Quiz-ul nu îți spune pe cine să votezi. Profilul este o descriere a pozițiilor tale, nu o recomandare."')
rep('endNote:"This prototype does not tell you who to vote for and does not compare your answers with parties. The profile describes your positions; it is not a recommendation."',
    'endNote:"The quiz does not tell you who to vote for. The profile describes your positions; it is not a recommendation."')
rep('  again:"Reia"\n', '''  again:"Reia",
  radarTitle:"Harta ta ideologică · 10 axe",
  savedNote:"Rezultatul e salvat în acest browser. Pe pagina fiecărui politician și partid vezi radarul tău peste al lor și diferențele majore.",
  compare:"Compară-te cu politicienii și partidele →",
  forget:"Șterge rezultatul salvat",
  forgotten:"Rezultatul a fost șters din acest browser.",
  hasSaved:"Ai deja un rezultat salvat; dacă refaci quiz-ul, cel nou îl va înlocui."
''')
rep('  again:"Restart"\n', '''  again:"Restart",
  radarTitle:"Your ideological map · 10 axes",
  savedNote:"The result is saved in this browser. On each politician's and party's page you see your radar over theirs and the major differences.",
  compare:"Compare yourself with politicians and parties →",
  forget:"Delete the saved result",
  forgotten:"The result was deleted from this browser.",
  hasSaved:"You already have a saved result; if you retake the quiz, the new one replaces it."
''')

# 4) intro: tell the user a saved result exists
rep('''    <div class="qz-row">
      <div class="qz-note">${t().privacy}</div>''', '''    ${getUserOrientation(AXES.length) ? `<p class="qz-note">${t().hasSaved}</p>` : ""}
    <div class="qz-row">
      <div class="qz-note">${t().privacy}</div>''')

# 5) result display in the SITE's convention. Quiz engine: 5 = first pole listed by the site (e.g. Pro-Occident).
#    Site: 1 = first pole. So site score = 6 - quiz score; position 0..100 = (site score - 1) * 25.
a = js.index("function profileCards(prof, items, compact){")
b = js.index("function renderResult(){")
js = js[:a] + r'''// Quiz engine scores: 5 = the first pole listed on the site (e.g. Pro-Occident). Shown in the site's convention:
// 1 = first pole (left), 5 = second pole (right), like the politicians' axes.
const toSite = score => 6 - score;
const sitePositions = prof => AXIS_ORDER.map(ax =>
  prof[ax].status === "ok" ? Math.max(0, Math.min(100, (toSite(prof[ax].score) - 1) * 25)) : null);
const poleLabels = (ax, i) => LANG === "ro"
  ? [AXES[i][0], AXES[i][1]]
  : [QAXES[ax].hiEn, QAXES[ax].loEn];

function profileCards(prof, items, compact){
  return AXIS_ORDER.map((ax, i) => {
    const s = prof[ax];
    const meta = QAXES[ax];
    const name = meta[LANG] || meta.ro;
    if (s.status !== "ok"){
      return `<div class="qz-axis"><div class="qz-name">${i + 1} · ${esc(name)}</div>
        <div class="qz-note">${t().insufficient(s.k)}</div></div>`;
    }
    const [first, second] = poleLabels(ax, i);
    const score = toSite(s.score);
    const pos = (v) => ((v-1)/4)*100;
    const left = pos(Math.max(1, score - s.margin));
    const right = pos(Math.min(5, score + s.margin));
    return `<div class="qz-axis">
      <div class="qz-name">${i + 1} · ${esc(name)}</div>
      <div class="qz-lbl"><span>1 · ${esc(first)}</span><span>5 · ${esc(second)}</span></div>
      <div class="qz-track">
        <div class="qz-base"></div>
        <div class="qz-boxes">${[1,2,3,4,5].map(v=>`<div>${v}</div>`).join("")}</div>
        <div class="qz-marg" style="left:${left}%;width:${Math.max(2,right-left)}%"></div>
        <div class="qz-marker" style="left:calc(${pos(score)}% - 1.5px)"></div>
      </div>
      <div class="qz-row">
        <div class="qz-val"><b>${score.toFixed(2)}</b> / 5 <span class="qz-note">± ${s.margin.toFixed(2)}</span></div>
        <div>${t().k(items.filter(it=>it.ax===ax).length)} ·
          <span class="qz-pill ${s.clarity.includes("CLEAR")?"qz-ok":""}">${t()[s.clarity]}</span> ·
          <span class="qz-note">${t().pct(Math.round(100 - s.percentile))}</span></div>
      </div>
    </div>`;
  }).join("");
}
''' + js[b:]

# 6) result: radar like the politicians', saved for the profile pages, deletable
rep('''  d.sub.textContent = t().subResult;
  d.app.innerHTML = `
  <div class="qz-card">
    <h2>${t().resTitle}</h2>''', '''  const positions = sitePositions(prof);
  saveUserOrientation(positions, leaningFrom(positions, AXES));
  d.sub.textContent = t().subResult;
  d.app.innerHTML = `
  <div class="qz-card">
    <h2>${t().radarTitle}</h2>
    ${renderRadar([{ values: positions, cls: "radar-user" }])}
    <p class="qz-note" id="savedNote">${t().savedNote}</p>
    <div class="qz-row">
      <a class="pill-link" href="index.html">${t().compare}</a>
      <button class="qz-ghost" id="forget">${t().forget}</button>
    </div>
  </div>
  <div class="qz-card">
    <h2>${t().resTitle}</h2>''')
rep('''${(coh.mostDecided||[]).map(x=>`<tr><td>${x.axis} · ${esc((QAXES[x.axis][LANG]||QAXES[x.axis].ro))}</td>
        <td>${x.score.toFixed(2)} · ${t()[x.clarity]}</td></tr>`).join("")}''',
    '''${(coh.mostDecided||[]).map(x=>`<tr><td>${AXIS_ORDER.indexOf(x.axis) + 1} · ${esc((QAXES[x.axis][LANG]||QAXES[x.axis].ro))}</td>
        <td>${toSite(x.score).toFixed(2)} · ${t()[x.clarity]}</td></tr>`).join("")}''')
rep('''${(coh.closestToMiddle||[]).map(x=>`<tr><td>${t().closest} ${x.axis} · ${esc((QAXES[x.axis][LANG]||QAXES[x.axis].ro))}</td>
        <td>${x.score.toFixed(2)}</td></tr>`).join("")}''',
    '''${(coh.closestToMiddle||[]).map(x=>`<tr><td>${t().closest} ${AXIS_ORDER.indexOf(x.axis) + 1} · ${esc((QAXES[x.axis][LANG]||QAXES[x.axis].ro))}</td>
        <td>${toSite(x.score).toFixed(2)}</td></tr>`).join("")}''')
rep('''  document.getElementById("again").onclick = () => {''', '''  document.getElementById("forget").onclick = () => {
    try { localStorage.removeItem(USER_KEY); } catch (e) { /* storage unavailable */ }
    document.getElementById("savedNote").textContent = t().forgotten;
    document.getElementById("forget").disabled = true;
  };
  document.getElementById("again").onclick = () => {''')

# 6b) "Salvează rezultatul": explicit save (kept in the browser + downloaded as JSON + event for a later backend hook)
rep('  again:"Reia",\n', '  again:"Reia",\n  save:"Salvează rezultatul",\n  saved:"Rezultat salvat în acest browser și descărcat ca fișier.",\n')
rep('  again:"Restart",\n', '  again:"Restart",\n  save:"Save the result",\n  saved:"Result saved in this browser and downloaded as a file.",\n')
rep('''      <a class="pill-link" href="index.html">${t().compare}</a>
      <button class="qz-ghost" id="forget">${t().forget}</button>''', '''      <a class="pill-link" href="index.html">${t().compare}</a>
      <span><button class="qz-primary" id="saveResult">${t().save}</button>
      <button class="qz-ghost" id="forget">${t().forget}</button></span>''')
rep('''  document.getElementById("forget").onclick = () => {''', r'''  document.getElementById("saveResult").onclick = () => {
    const payload = {
      version: 1, savedAt: new Date().toISOString(), lang: LANG,
      axes: AXIS_ORDER.map((ax, i) => {
        const s = prof[ax];
        return { n: i + 1, id: ax, name: QAXES[ax].ro, status: s.status, items: s.k,
                 score: s.status === "ok" ? +toSite(s.score).toFixed(2) : null,
                 margin: s.status === "ok" ? +s.margin.toFixed(2) : null, position: positions[i] };
      }),
      leaning: leaningFrom(positions, AXES),
      answers: state.responses,
      quality: { flags: q.flags, trustworthy: q.trustworthy }
    };
    try { localStorage.setItem("quizRezultatSalvat", JSON.stringify(payload)); } catch (e) { /* storage unavailable */ }
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url; a.download = "rezultat-quiz.json"; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    window.dispatchEvent(new CustomEvent("quiz:save", { detail: payload }));   // hook pentru integrări viitoare
    document.getElementById("savedNote").textContent = t().saved;
  };
  document.getElementById("forget").onclick = () => {''')

# 7) isolate everything from the site's globals (esc, render..., AXES)
header = ("// Quiz: afirmațiile și motorul de scor provin din „progressive (2) (2).html” (Busola de vot, Arm B), neschimbate.\n"
          "// Generat cu tools/build_quiz.py: clase CSS cu prefixul qz-, AXES al quiz-ului redenumit QAXES, rezultatul convertit pe axele site-ului\n"
          "// (1 = primul pol, ca la politicieni) și salvat cu saveUserOrientation pentru paginile politicienilor și partidelor.\n")
js = header + "(() => {\n" + js.strip("\n") + "\n})();\n"
open(OUT, "w", encoding="utf-8").write(js)
print("quiz.js written:", len(js.splitlines()), "lines")
