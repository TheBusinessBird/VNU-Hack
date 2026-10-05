// Placeholder data. Fields set to null mean "în analiză" in the UI.
// Fill real values only from an actual analysis of the sources; nothing here is an evaluation.
// News, speeches, sources and authors come from the API (see js/api.js), not from this file.

// 10 axes: [left pole (score 1), right pole (score 5), short name (radar), what it covers (tooltip), id].
// Same order and ids as AXES in api/orientation_llm.py. Values are stored 0..100 (score 1 -> 0, 3 -> 50, 5 -> 100).
const AXES = [
  ["Pro-Occident / euro-atlantic", "Suveranist / eurosceptic", "Geopolitică",
    "Integrare UE/NATO, modernizare PNRR, orientare spre viitorul occidental vs. suveranitate națională, nostalgie post-comunistă, realiniere spre Est", "geopolitics"],
  ["Progresist și secular", "Tradițional și naționalist", "Identitate",
    "Drepturi sociale, naționalism civic, stat secular vs. „familia tradițională”, aliniere cu BOR, naționalism etnic", "identity"],
  ["Piață liberă și disciplină fiscală", "Taxare progresivă și stat social", "Economie",
    "Politici pro-business, cota unică, controlul deficitului vs. taxare progresivă, creșteri imediate de pensii/salarii, ajutoare sociale", "economy"],
  ["Tehnocratic și transparent", "Patronaj și birocrație", "Guvernare",
    "Meritocrație, digitalizare, reforma justiției, anti-corupție vs. numiri politice, birocrația statului, clientelism și patronaj local", "governance"],
  ["Anti-establishment și urban/diaspora", "Establishment și rețele locale/rurale", "Sistem",
    "Disrupția sistemului, impuls reformist, modernizare urbană/diaspora vs. stabilitatea status quo-ului, continuitatea mașinii de partid, administrația rurală", "system"],
  ["Centralism și stat unitar", "Descentralizare și autonomie regională", "Structură",
    "Putere bugetară și administrativă concentrată la București, stat unitar strict vs. control financiar local, regionalizare, dezbateri de autonomie a minorităților", "structure"],
  ["Modernizare verde și obiective climatice", "Exploatarea resurselor și suveranitate energetică", "Energie",
    "Regenerabile, eliminarea cărbunelui, aliniere la Pactul Verde vs. extracție internă de combustibili fosili, independență energetică industrială, rezistență la reglementări costisitoare", "energy"],
  ["Privatizare și reformă sistemică", "Monopol de stat și schimbări graduale", "Servicii publice",
    "Alternative private în sănătate și educație, finanțare pe performanță vs. servicii publice monopol de stat, salarii în sectorul public înaintea reformei, status quo", "services"],
  ["Multiculturalism și incluziune civică", "Etnocentrism și asimilare", "Minorități",
    "Drepturi lingvistice, reprezentare politică a minorităților, diversitate culturală vs. statul național unitar strict, primat etnic român, scepticism față de influența politică a minorităților", "ethnic"],
  ["Liberalizarea muncii și imigrație", "Protecționism economic și focus intern", "Muncă",
    "Cote mai largi pentru muncitori non-UE, legislație flexibilă a muncii, repatrierea diasporei vs. protejarea lucrătorilor interni, restrângerea forței de muncă străine, reguli rigide", "labor"]
];

// Scores 1..5 from the API <-> the 0..100 positions used by the UI.
const scoreToPos = s => (s === null || s === undefined ? null : (s - 1) * 25);
const posToScore = v => (v === null || v === undefined ? null : v / 25 + 1);

// Photos: Wikimedia Commons thumbnails (free licences, credited in the UI).
const COMMONS = "https://upload.wikimedia.org/wikipedia/commons/thumb/";
const PEOPLE = [
  ["Nicușor Dan", "b/b8/Nicusor_Dan_in_2026.jpg"],
  ["Călin Georgescu", "7/77/C%C4%83lin_Georgescu_in_2025.jpg"],
  ["George Simion", "a/a4/Portret_George_Simion_%287%29_%28decupat%29.jpg"],
  ["Marcel Ciolacu", "b/b5/Marcel_Ciolacu%2C_September_2024_%28cropped%29.jpg"],
  ["Klaus Iohannis", "a/a9/Klaus_Iohannis_-_Informal_meeting_of_heads_of_state_or_government_-_November_2024_%28cropped%29.jpg"],
  ["Crin Antonescu", "e/eb/Crin_Antonescu_at_the_General_Assembly_of_the_National_Union_of_County_Councils_of_Romania_%28March_2025%29.jpg"],
  ["Elena Lasconi", "9/93/Elena_Lasconi_%281_July_2024%29_%28cropped%29.jpg"],
  ["Mircea Geoană", "2/2f/Mircea_Geoan%C4%83_-_Feb_2024.jpg"],
  ["Victor Ponta", "4/43/Victor_Ponta_April_2025_%28cropped%29.jpg"],
  ["Ilie Bolojan", "c/cd/Ilie_Bolojan_%2816_April_2026%29_%28cropped%29.jpg"],
  ["Cătălin Predoiu", "a/ae/Catalin_Predoiu_%28portrait_crop%29.jpg"],
  ["Diana Șoșoacă", "1/16/Diana_Iovanovici_%C8%98o%C8%99oac%C4%83_MEP_%282024%29.jpg"]
];

// Date furnizate manual (tabel primit de la proprietarul site-ului): educație și venit declarat pe an. Aproximative și neverificate aici.
const FACTS = {
  "Nicușor Dan": { education: "École Normale Supérieure Paris; matematică, Sorbona", income: "~220.700 lei din indemnizații" },
  "Călin Georgescu": { education: "Agronomie; doctorat în pedologie", income: "~72.000 lei de la Univ. Pitești" },
  "George Simion": { education: "Univ. București – Geografie/istorie?", income: "~170.000 lei" },
  "Marcel Ciolacu": { education: "Univ. Ecologică București – Drept; master administrație publică", income: "~250.000 lei" },
  "Klaus Iohannis": { education: "Univ. Babeș-Bolyai – Fizică; profesor", income: "~185.000 lei" },
  "Crin Antonescu": { education: "Univ. București – Istorie", income: "~0 lei venit salarial în perioada fără funcție; venituri din alte surse pot exista" },
  "Elena Lasconi": { education: "Institutul de Studii Economice din Deva; jurnalism/management", income: "~200.000 lei" },
  "Mircea Geoană": { education: "Politehnica București – mecanică; ASE – economie; doctorat economie", income: "~1,1 mil. lei (venituri externe/internaționale incluse)" },
  "Victor Ponta": { education: "Univ. București – Drept; doctorat în Drept", income: "~300.000 lei" },
  "Ilie Bolojan": { education: "Univ. Timișoara – mecanică; Univ. Oradea – management", income: "~180.000 lei" },
  "Cătălin Predoiu": { education: "Univ. București – Drept; doctorat Drept", income: "~250.000 lei" },
  "Diana Șoșoacă": { education: "Univ. Ecologică București – Drept; doctorat Drept", income: "~250.000 lei" }
};

const POLITICIANS = PEOPLE.map(([name, file]) => ({
  kind: "person",
  id: name.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/\s+/g, "-"),
  name,
  photo: `${COMMONS}${file}/330px-${file.split("/").pop()}`,
  party: null,    // e.g. "Partidul X (PX)" — hidden when null
  role: null,     // current office — hidden when null
  bio: null,      // short neutral description — hidden when null
  education: (FACTS[name] || {}).education || null,   // manual table, see FACTS
  income: (FACTS[name] || {}).income || null,
  sources: [],    // URLs the profile is based on, e.g. ["https://ro.wikipedia.org/wiki/…"]
  stats: {
    statements: null,       // sum of s_i
    contradictions: null,   // sum of u_i
    promisesEvaluated: null,
    finalScore: null        // R * n_percentile, 0..1
  },
  // Overall index: 0 = Dreapta (verde) .. 50 = Centru (gri) .. 100 = Stânga (roșu), or null
  leaning: null,
  // orientation[axisIndex] = 0 (left pole) .. 100 (right pole), or null
  orientation: AXES.map(() => null)
}));

// Partide: aceeași analiză prin API și aceleași statistici ca politicienii, fără educație, venit și erori logice.
// [id, nume, alias pentru căutare (sigla), termen după care se atribuie declarațiile]
// POT nu are alias: „pot” e și verb, iar căutarea după siglă ar aduce articole fără legătură.
const PARTY_LIST = [
  ["psd", "Partidul Social Democrat", "PSD", "PSD"],
  ["pnl", "Partidul Național Liberal", "PNL", "PNL"],
  ["aur", "Alianța pentru Unirea Românilor", "AUR", "AUR"],
  ["usr", "Uniunea Salvați România", "USR", "USR"],
  ["udmr", "Uniunea Democrată Maghiară din România", "UDMR", "UDMR"],
  ["sos-romania", "S.O.S. România", "SOS România", "SOS România"],
  ["pot", "Partidul Oamenilor Tineri", null, "Oamenilor Tineri"]
];

// Logo-uri de pe Wikimedia Commons, doar cu licență liberă (verificate prin API-ul Commons).
// PSD și AUR au pe Wikipedia logo-uri „fair use”, care nu pot fi folosite pe alt site: pentru ele sunt variantele libere de pe Commons.
const COMMONS_THUMB = "https://upload.wikimedia.org/wikipedia/commons/thumb/";
const PARTY_LOGOS = {
  "psd": ["d/d4/Flag_of_the_Social_Democratic_Party_%28Romania%29_%28cropped%29.svg", "CC BY 2.0",
          "https://commons.wikimedia.org/wiki/File:Flag_of_the_Social_Democratic_Party_(Romania)_(cropped).svg"],
  "pnl": ["b/bf/Partidul_Na%C8%9Bional_Liberal_%28PNL%29_logo.svg", "domeniu public",
          "https://commons.wikimedia.org/wiki/File:Partidul_Na%C8%9Bional_Liberal_(PNL)_logo.svg"],
  "aur": ["2/2a/Logo_of_the_Alliance_for_the_Union_of_Romanians.svg", "domeniu public",
          "https://commons.wikimedia.org/wiki/File:Logo_of_the_Alliance_for_the_Union_of_Romanians.svg"],
  "usr": ["7/7e/Logo_USR_2022_%281%29.svg", "domeniu public",
          "https://commons.wikimedia.org/wiki/File:Logo_USR_2022_(1).svg"],
  "udmr": ["6/63/Party_logo_of_the_Democratic_Alliance_of_Hungarians_in_Romania.svg", "domeniu public",
           "https://commons.wikimedia.org/wiki/File:Party_logo_of_the_Democratic_Alliance_of_Hungarians_in_Romania.svg"],
  "sos-romania": ["2/26/SOS_Romania_logo.svg", "domeniu public",
                  "https://commons.wikimedia.org/wiki/File:SOS_Romania_logo.svg"],
  "pot": ["3/35/Logo_of_the_Party_of_Young_People.png", "domeniu public",
          "https://commons.wikimedia.org/wiki/File:Logo_of_the_Party_of_Young_People.png"]
};
// Thumbnail 330px: SVG files are rendered as PNG by Commons (".svg/330px-<name>.svg.png").
const logoUrl = path => { const file = path.split("/").pop(); return `${COMMONS_THUMB}${path}/330px-${file}${file.endsWith(".svg") ? ".png" : ""}`; };

const PARTIES = PARTY_LIST.map(([id, name, alias, term]) => ({
  kind: "party",
  id,
  name,
  short: alias ? alias.split(" ")[0] : name.split(" ").map(w => w[0]).join(""),
  alias,
  term,
  photo: PARTY_LOGOS[id] ? logoUrl(PARTY_LOGOS[id][0]) : null,
  photoCredit: PARTY_LOGOS[id] ? { label: "Logo", license: PARTY_LOGOS[id][1], page: PARTY_LOGOS[id][2] } : null,
  party: null, role: null, bio: null, sources: [],
  education: null, income: null,
  stats: { statements: null, contradictions: null, promisesEvaluated: null, finalScore: null },
  leaning: null,
  orientation: AXES.map(() => null)
}));

const ENTITIES = [...POLITICIANS, ...PARTIES];

// Axes shown on the ideology radar (index into AXES, label). Radius = strength of the first (left) pole.
const RADAR = AXES.map((ax, i) => [i, ax[2]]);
