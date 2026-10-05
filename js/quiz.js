// Quiz: afirmațiile și motorul de scor provin din „progressive (2) (2).html” (Busola de vot, Arm B), neschimbate.
// Generat cu tools/build_quiz.py: clase CSS cu prefixul qz-, AXES al quiz-ului redenumit QAXES, rezultatul convertit pe axele site-ului
// (1 = primul pol, ca la politicieni) și salvat cu saveUserOrientation pentru paginile politicienilor și partidelor.
(() => {
/* =======================================================================
   1. QAXES + ITEM BANK (generated from items/item_bank.csv)
   ======================================================================= */
const MODE = "progressive";

const QAXES = {
  A1:{ro:"Geopolitică și traiectorie națională", en:"Geopolitics & national trajectory", hiRo:"Pro-occidental / Euro-atlantic", loRo:"Suveranist / Eurosceptic", hiEn:"Pro-Western / Euro-Atlantic", loEn:"Sovereignist / Eurosceptic"},
  A2:{ro:"Identitate socială și culturală", en:"Social & cultural identity", hiRo:"Progresist & secular", loRo:"Tradițional & naționalist", hiEn:"Progressive & secular", loEn:"Traditional & nationalist"},
  A3:{ro:"Filozofie economică", en:"Economic philosophy", hiRo:"Piață liberă & disciplină fiscală", loRo:"Impozitare progresivă & stat social", hiEn:"Free market & fiscal discipline", loEn:"Progressive taxation & welfare"},
  A4:{ro:"Guvernare & anticorupție", en:"Governance & anti-corruption", hiRo:"Tehnocrat & transparent", loRo:"Patronaj & birocrație", hiEn:"Technocratic & transparent", loEn:"Patronage & bureaucracy"},
  A5:{ro:"Atitudinea față de sistem", en:"Systemic stance", hiRo:"Antisistem & reformă", loRo:"Establishment & stabilitate", hiEn:"Anti-establishment & reform", loEn:"Establishment & stability"},
  A6:{ro:"Structură administrativă & putere regională", en:"Administrative structure & regional power", hiRo:"Centralism & stat unitar", loRo:"Descentralizare & autonomie regională", hiEn:"Centralism & unitary state", loEn:"Decentralization & regional autonomy"},
  A7:{ro:"Mediu & tranziție energetică", en:"Environment & energy transition", hiRo:"Modernizare verde & obiective climatice", loRo:"Exploatarea resurselor & suveranitate energetică", hiEn:"Green modernization & climate goals", loEn:"Resource exploitation & energy sovereignty"},
  A8:{ro:"Servicii publice (sănătate & educație)", en:"Public services (health & education)", hiRo:"Privatizare & reformă sistemică", loRo:"Monopol de stat & incrementalism", hiEn:"Privatization & systemic overhaul", loEn:"State monopoly & incrementalism"},
  A9:{ro:"Relații etnice & reprezentare minorități", en:"Ethnic relations & minority representation", hiRo:"Multiculturalism & incluziune civică", loRo:"Etnocentrism & asimilare", hiEn:"Multiculturalism & civic inclusion", loEn:"Ethnocentrism & assimilation"},
  A10:{ro:"Piața muncii & migrație", en:"Labour market & migration", hiRo:"Liberalizare & imigrație", loRo:"Protecționism economic & orientare internă", hiEn:"Labor liberalization & immigration", loEn:"Economic protectionism & domestic focus"}
};
const R_AXES = [[1.0, 0.26, 0.15, 0.3, 0.48, -0.16, 0.45, 0.24, 0.29, 0.24], [0.26, 1.0, 0.2, 0.16, 0.19, 0.04, 0.35, 0.05, 0.53, 0.29], [0.15, 0.2, 1.0, 0.2, 0.09, 0.1, -0.15, 0.55, 0.09, 0.4], [0.3, 0.16, 0.2, 1.0, 0.33, 0.14, 0.2, 0.34, 0.29, 0.14], [0.48, 0.19, 0.09, 0.33, 1.0, -0.09, 0.05, 0.01, -0.23, -0.29], [-0.16, 0.04, 0.1, 0.14, -0.09, 1.0, -0.05, -0.09, -0.39, -0.19], [0.45, 0.35, -0.15, 0.2, 0.05, -0.05, 1.0, 0.05, 0.25, 0.15], [0.24, 0.05, 0.55, 0.34, 0.01, -0.09, 0.05, 1.0, 0.16, 0.1], [0.29, 0.53, 0.09, 0.29, -0.23, -0.39, 0.25, 0.16, 1.0, 0.45], [0.24, 0.29, 0.4, 0.14, -0.29, -0.19, 0.15, 0.1, 0.45, 1.0]];

/* Arm A: the 30-item core form (3 per axis, poles alternating by axis). */
const CORE_ITEMS = [
  {id:"A1-01",ax:"A1",d:1,ro:"România ar trebui să rămână ferm ancorată în NATO, chiar dacă asta ne limitează libertatea de a acționa singuri.",en:"Romania should stay firmly anchored in NATO, even when that limits our freedom to act alone."},
  {id:"A1-02",ax:"A1",d:1,ro:"Banii europeni pentru infrastructură și reforme (PNRR) merită condițiile impuse de Bruxelles.",en:"EU money for infrastructure and reform (PNRR) is worth the conditions that Brussels attaches to it."},
  {id:"A1-06",ax:"A1",d:-1,ro:"România ar trebui să respingă orice regulă europeană care intră în conflict cu o decizie a Parlamentului nostru.",en:"Romania should reject any EU rule that conflicts with a decision of our own parliament."},
  {id:"A2-01",ax:"A2",d:1,ro:"Cuplurile de același sex ar trebui să aibă aceleași drepturi legale ca soții căsătoriți (moștenire, decizii medicale, locuință).",en:"Same-sex couples should have the same legal rights as married couples (inheritance, medical decisions, housing)."},
  {id:"A2-06",ax:"A2",d:-1,ro:"Constituția ar trebui să prevadă că familia este formată dintr-un bărbat și o femeie.",en:"The Constitution should state that a family is formed of a man and a woman."},
  {id:"A2-07",ax:"A2",d:-1,ro:"Ora de religie în școlile de stat ar trebui păstrată și predată de biserică.",en:"Religious education in state schools should be kept and taught by the church."},
  {id:"A3-01",ax:"A3",d:1,ro:"România ar trebui să păstreze cota unică de 16% la impozitul pe venit și pe profit, în loc să introducă impozitarea progresivă.",en:"Romania should keep the single 16% rate for income and profit tax instead of introducing progressive taxation."},
  {id:"A3-02",ax:"A3",d:1,ro:"Echilibrarea bugetului este mai importantă decât creșterea pensiilor și a salariilor publice în acest an.",en:"Balancing the budget is more important than raising pensions and public salaries this year."},
  {id:"A3-06",ax:"A3",d:-1,ro:"Veniturile mari ar trebui impozitate cu o cotă mai ridicată decât astăzi.",en:"Large incomes should be taxed at a higher rate than they are today."},
  {id:"A4-01",ax:"A4",d:1,ro:"Angajarea și promovarea în sectorul public ar trebui făcute pe bază de concursuri deschise, fără influență politică.",en:"Public sector hiring and promotions should be based on open, competitive exams, with no political input."},
  {id:"A4-06",ax:"A4",d:-1,ro:"Primarii și liderii locali ar trebui să fie liberi să numească oameni în care au încredere, pentru că ei răspund pentru rezultate.",en:"Mayors and local leaders should be free to appoint people they trust, because they must answer for the results."},
  {id:"A4-07",ax:"A4",d:-1,ro:"Statul ar trebui să păstreze actualele instituții și angajați, chiar și acolo unde sunt ineficiente, pentru a proteja locurile de muncă din orașele mici.",en:"The state should keep its existing offices and staff, even where they are inefficient, to protect jobs in small towns."},
  {id:"A5-01",ax:"A5",d:1,ro:"Majoritatea politicienilor sunt interesați în principal de propriul interes.",en:"Most politicians are mainly interested in their own advantage."},
  {id:"A5-02",ax:"A5",d:1,ro:"Țara are nevoie de o schimbare mai profundă decât schimbarea guvernului; întregul sistem politic trebuie reconstruit.",en:"The country needs deeper change than replacing the government; the whole political system needs to be rebuilt."},
  {id:"A5-06",ax:"A5",d:-1,ro:"Problema este modul în care sunt aplicate reformele, nu sistemul politic în sine; instituțiile existente ar trebui îmbunătățite.",en:"The problem is how reforms are applied, not the political system itself; the existing institutions should be improved."},
  {id:"A6-01",ax:"A6",d:1,ro:"Bucureștiul ar trebui să controleze cum cheltuiesc județele bugetele, în loc să decidă consiliile locale.",en:"Bucharest should keep control of how counties spend their budgets, instead of letting local councils decide."},
  {id:"A6-06",ax:"A6",d:-1,ro:"Consiliile locale ar trebui să păstreze o parte mult mai mare din taxele pe care le încasează.",en:"Local councils should keep a much larger share of the taxes they collect."},
  {id:"A6-07",ax:"A6",d:-1,ro:"Deciziile despre școli, spitale și drumuri ar trebui să aparțină administrațiilor județene și locale, nu ministerelor.",en:"Decisions about schools, hospitals and roads should belong to county and city administrations, not to ministries."},
  {id:"A7-01",ax:"A7",d:1,ro:"România ar trebui să închidă termocentralele pe cărbune până în 2030, chiar dacă asta costă locuri de muncă.",en:"Romania should close its coal plants by 2030, even if that costs jobs in mining regions."},
  {id:"A7-02",ax:"A7",d:1,ro:"Respectarea țintelor climatice ale UE ar trebui să rămână o prioritate chiar dacă regulile scumpesc facturile.",en:"Meeting EU climate targets should stay a priority even when the rules raise energy bills."},
  {id:"A7-06",ax:"A7",d:-1,ro:"România ar trebui să extragă gazul din Marea Neagră cât mai repede pentru a-și asigura necesarul.",en:"Romania should extract Black Sea gas as fast as possible to secure its own supply."},
  {id:"A8-01",ax:"A8",d:1,ro:"Oamenii ar trebui să poată direcționa contribuțiile de sănătate către un asigurator privat, dacă vor.",en:"People should be able to direct their health contributions to a private insurer if they choose."},
  {id:"A8-06",ax:"A8",d:-1,ro:"Sănătatea ar trebui să rămână în mâinile statului; asigurarea privată să fie un supliment, nu o alternativă.",en:"Health care should stay in state hands; private insurance should remain a supplement, not a substitute."},
  {id:"A8-07",ax:"A8",d:-1,ro:"Prioritatea în sănătate și educație ar trebui să fie salarii mai mari, nu reforme structurale.",en:"The priority in health and education should be higher pay for staff, not structural reform."},
  {id:"A9-01",ax:"A9",d:1,ro:"Vorbitorii de limbă maghiară ar trebui să poată folosi limba lor la autoritățile locale acolo unde sunt numeroși.",en:"Hungarian speakers should be able to use their language with local authorities wherever they are numerous."},
  {id:"A9-02",ax:"A9",d:1,ro:"Comunitățile minoritare ar trebui să aibă reprezentare politică garantată, chiar dacă e nevoie de locuri speciale.",en:"Minority communities should have guaranteed political representation, even if that needs special seats."},
  {id:"A9-06",ax:"A9",d:-1,ro:"Româna ar trebui să fie singura limbă folosită în administrația publică, în toată țara.",en:"Romanian should be the only language used in public administration, everywhere in the country."},
  {id:"A10-01",ax:"A10",d:1,ro:"România ar trebui să simplifice mult obținerea permiselor de muncă pentru lucrătorii din afara UE.",en:"Romania should make it much easier and faster for non-EU workers to get work permits."},
  {id:"A10-06",ax:"A10",d:-1,ro:"România ar trebui să limiteze lucrătorii străini până când șomajul în rândul românilor este mic.",en:"Romania should limit foreign workers until unemployment among Romanians is low."},
  {id:"A10-07",ax:"A10",d:-1,ro:"Firmele care primesc sprijin de stat ar trebui obligate să angajeze mai întâi români.",en:"Companies receiving state support should be required to hire Romanian workers first."}
];
/* Arm B: probe 20 (2/axis) + sharpen pool, up to 5 per axis in total. */
const PROBE_ITEMS = [
  {id:"A1-01",ax:"A1",d:1,ro:"România ar trebui să rămână ferm ancorată în NATO, chiar dacă asta ne limitează libertatea de a acționa singuri.",en:"Romania should stay firmly anchored in NATO, even when that limits our freedom to act alone."},
  {id:"A1-06",ax:"A1",d:-1,ro:"România ar trebui să respingă orice regulă europeană care intră în conflict cu o decizie a Parlamentului nostru.",en:"Romania should reject any EU rule that conflicts with a decision of our own parliament."},
  {id:"A2-01",ax:"A2",d:1,ro:"Cuplurile de același sex ar trebui să aibă aceleași drepturi legale ca soții căsătoriți (moștenire, decizii medicale, locuință).",en:"Same-sex couples should have the same legal rights as married couples (inheritance, medical decisions, housing)."},
  {id:"A2-06",ax:"A2",d:-1,ro:"Constituția ar trebui să prevadă că familia este formată dintr-un bărbat și o femeie.",en:"The Constitution should state that a family is formed of a man and a woman."},
  {id:"A3-01",ax:"A3",d:1,ro:"România ar trebui să păstreze cota unică de 16% la impozitul pe venit și pe profit, în loc să introducă impozitarea progresivă.",en:"Romania should keep the single 16% rate for income and profit tax instead of introducing progressive taxation."},
  {id:"A3-06",ax:"A3",d:-1,ro:"Veniturile mari ar trebui impozitate cu o cotă mai ridicată decât astăzi.",en:"Large incomes should be taxed at a higher rate than they are today."},
  {id:"A4-01",ax:"A4",d:1,ro:"Angajarea și promovarea în sectorul public ar trebui făcute pe bază de concursuri deschise, fără influență politică.",en:"Public sector hiring and promotions should be based on open, competitive exams, with no political input."},
  {id:"A4-06",ax:"A4",d:-1,ro:"Primarii și liderii locali ar trebui să fie liberi să numească oameni în care au încredere, pentru că ei răspund pentru rezultate.",en:"Mayors and local leaders should be free to appoint people they trust, because they must answer for the results."},
  {id:"A5-01",ax:"A5",d:1,ro:"Majoritatea politicienilor sunt interesați în principal de propriul interes.",en:"Most politicians are mainly interested in their own advantage."},
  {id:"A5-06",ax:"A5",d:-1,ro:"Problema este modul în care sunt aplicate reformele, nu sistemul politic în sine; instituțiile existente ar trebui îmbunătățite.",en:"The problem is how reforms are applied, not the political system itself; the existing institutions should be improved."},
  {id:"A6-01",ax:"A6",d:1,ro:"Bucureștiul ar trebui să controleze cum cheltuiesc județele bugetele, în loc să decidă consiliile locale.",en:"Bucharest should keep control of how counties spend their budgets, instead of letting local councils decide."},
  {id:"A6-06",ax:"A6",d:-1,ro:"Consiliile locale ar trebui să păstreze o parte mult mai mare din taxele pe care le încasează.",en:"Local councils should keep a much larger share of the taxes they collect."},
  {id:"A7-01",ax:"A7",d:1,ro:"România ar trebui să închidă termocentralele pe cărbune până în 2030, chiar dacă asta costă locuri de muncă.",en:"Romania should close its coal plants by 2030, even if that costs jobs in mining regions."},
  {id:"A7-06",ax:"A7",d:-1,ro:"România ar trebui să extragă gazul din Marea Neagră cât mai repede pentru a-și asigura necesarul.",en:"Romania should extract Black Sea gas as fast as possible to secure its own supply."},
  {id:"A8-01",ax:"A8",d:1,ro:"Oamenii ar trebui să poată direcționa contribuțiile de sănătate către un asigurator privat, dacă vor.",en:"People should be able to direct their health contributions to a private insurer if they choose."},
  {id:"A8-06",ax:"A8",d:-1,ro:"Sănătatea ar trebui să rămână în mâinile statului; asigurarea privată să fie un supliment, nu o alternativă.",en:"Health care should stay in state hands; private insurance should remain a supplement, not a substitute."},
  {id:"A9-01",ax:"A9",d:1,ro:"Vorbitorii de limbă maghiară ar trebui să poată folosi limba lor la autoritățile locale acolo unde sunt numeroși.",en:"Hungarian speakers should be able to use their language with local authorities wherever they are numerous."},
  {id:"A9-06",ax:"A9",d:-1,ro:"Româna ar trebui să fie singura limbă folosită în administrația publică, în toată țara.",en:"Romanian should be the only language used in public administration, everywhere in the country."},
  {id:"A10-01",ax:"A10",d:1,ro:"România ar trebui să simplifice mult obținerea permiselor de muncă pentru lucrătorii din afara UE.",en:"Romania should make it much easier and faster for non-EU workers to get work permits."},
  {id:"A10-06",ax:"A10",d:-1,ro:"România ar trebui să limiteze lucrătorii străini până când șomajul în rândul românilor este mic.",en:"Romania should limit foreign workers until unemployment among Romanians is low."}
];
const POOL_ITEMS = [
  {id:"A1-01",ax:"A1",d:1,ro:"România ar trebui să rămână ferm ancorată în NATO, chiar dacă asta ne limitează libertatea de a acționa singuri.",en:"Romania should stay firmly anchored in NATO, even when that limits our freedom to act alone."},
  {id:"A1-02",ax:"A1",d:1,ro:"Banii europeni pentru infrastructură și reforme (PNRR) merită condițiile impuse de Bruxelles.",en:"EU money for infrastructure and reform (PNRR) is worth the conditions that Brussels attaches to it."},
  {id:"A1-03",ax:"A1",d:1,ro:"România ar trebui să adopte euro imediat ce condițiile economice sunt îndeplinite.",en:"Romania should adopt the euro as soon as the economic conditions are met."},
  {id:"A1-06",ax:"A1",d:-1,ro:"România ar trebui să respingă orice regulă europeană care intră în conflict cu o decizie a Parlamentului nostru.",en:"Romania should reject any EU rule that conflicts with a decision of our own parliament."},
  {id:"A1-07",ax:"A1",d:-1,ro:"Terenurile agricole, pădurile și resursele energetice nu ar trebui vândute companiilor sau fondurilor străine.",en:"Farmland, forests and energy resources should not be sold to foreign companies or funds."},
  {id:"A2-01",ax:"A2",d:1,ro:"Cuplurile de același sex ar trebui să aibă aceleași drepturi legale ca soții căsătoriți (moștenire, decizii medicale, locuință).",en:"Same-sex couples should have the same legal rights as married couples (inheritance, medical decisions, housing)."},
  {id:"A2-02",ax:"A2",d:1,ro:"Religia nu ar trebui să fie materie obligatorie în școlile de stat; elevii ar trebui să poată alege altceva fără efort.",en:"Religion should not be a compulsory subject in state schools; pupils should be able to opt out without effort."},
  {id:"A2-06",ax:"A2",d:-1,ro:"Constituția ar trebui să prevadă că familia este formată dintr-un bărbat și o femeie.",en:"The Constitution should state that a family is formed of a man and a woman."},
  {id:"A2-07",ax:"A2",d:-1,ro:"Ora de religie în școlile de stat ar trebui păstrată și predată de biserică.",en:"Religious education in state schools should be kept and taught by the church."},
  {id:"A2-08",ax:"A2",d:-1,ro:"Școlile ar trebui să pună mai mult accent pe istoria și tradițiile naționale decât o fac astăzi.",en:"Schools should put more emphasis on national history and traditions than they do today."},
  {id:"A3-01",ax:"A3",d:1,ro:"România ar trebui să păstreze cota unică de 16% la impozitul pe venit și pe profit, în loc să introducă impozitarea progresivă.",en:"Romania should keep the single 16% rate for income and profit tax instead of introducing progressive taxation."},
  {id:"A3-02",ax:"A3",d:1,ro:"Echilibrarea bugetului este mai importantă decât creșterea pensiilor și a salariilor publice în acest an.",en:"Balancing the budget is more important than raising pensions and public salaries this year."},
  {id:"A3-03",ax:"A3",d:1,ro:"Statul administrează prea multe companii; multe ar trebui privatizate sau închise.",en:"The state runs too many companies; many of them should be privatised or closed."},
  {id:"A3-06",ax:"A3",d:-1,ro:"Veniturile mari ar trebui impozitate cu o cotă mai ridicată decât astăzi.",en:"Large incomes should be taxed at a higher rate than they are today."},
  {id:"A3-07",ax:"A3",d:-1,ro:"Salariul minim ar trebui să crească semnificativ, chiar dacă asta pune presiune pe firmele mici.",en:"The minimum wage should rise significantly, even if this puts pressure on small businesses."},
  {id:"A4-01",ax:"A4",d:1,ro:"Angajarea și promovarea în sectorul public ar trebui făcute pe bază de concursuri deschise, fără influență politică.",en:"Public sector hiring and promotions should be based on open, competitive exams, with no political input."},
  {id:"A4-02",ax:"A4",d:1,ro:"Orice contract public peste o valoare mică ar trebui publicat într-o bază de date deschisă și ușor de căutat.",en:"Every public contract above a small value should be published in an open, searchable database."},
  {id:"A4-06",ax:"A4",d:-1,ro:"Primarii și liderii locali ar trebui să fie liberi să numească oameni în care au încredere, pentru că ei răspund pentru rezultate.",en:"Mayors and local leaders should be free to appoint people they trust, because they must answer for the results."},
  {id:"A4-07",ax:"A4",d:-1,ro:"Statul ar trebui să păstreze actualele instituții și angajați, chiar și acolo unde sunt ineficiente, pentru a proteja locurile de muncă din orașele mici.",en:"The state should keep its existing offices and staff, even where they are inefficient, to protect jobs in small towns."},
  {id:"A4-08",ax:"A4",d:-1,ro:"Este normal ca guvernul să aibă un cuvânt de spus în numirea celor care conduc instituții publice, pentru că răspunde pentru ele.",en:"It is normal for the government to have a say in who leads public institutions, because it is accountable for them."},
  {id:"A5-01",ax:"A5",d:1,ro:"Majoritatea politicienilor sunt interesați în principal de propriul interes.",en:"Most politicians are mainly interested in their own advantage."},
  {id:"A5-02",ax:"A5",d:1,ro:"Țara are nevoie de o schimbare mai profundă decât schimbarea guvernului; întregul sistem politic trebuie reconstruit.",en:"The country needs deeper change than replacing the government; the whole political system needs to be rebuilt."},
  {id:"A5-03",ax:"A5",d:1,ro:"Cetățenii ar trebui să decidă direct legile importante prin referendum, în loc să lase totul în seama Parlamentului.",en:"Citizens should decide important laws directly through referendums instead of leaving everything to parliament."},
  {id:"A5-06",ax:"A5",d:-1,ro:"Problema este modul în care sunt aplicate reformele, nu sistemul politic în sine; instituțiile existente ar trebui îmbunătățite.",en:"The problem is how reforms are applied, not the political system itself; the existing institutions should be improved."},
  {id:"A5-07",ax:"A5",d:-1,ro:"Partidele politice sunt necesare pentru democrație, chiar dacă nu ne plac.",en:"Political parties are necessary for democracy, even when we do not like them."},
  {id:"A6-01",ax:"A6",d:1,ro:"Bucureștiul ar trebui să controleze cum cheltuiesc județele bugetele, în loc să decidă consiliile locale.",en:"Bucharest should keep control of how counties spend their budgets, instead of letting local councils decide."},
  {id:"A6-02",ax:"A6",d:1,ro:"Prefecții ar trebui să poată anula deciziile consiliilor locale alese care încalcă regulile naționale.",en:"Prefects should be able to overturn decisions of elected local councils that break national rules."},
  {id:"A6-06",ax:"A6",d:-1,ro:"Consiliile locale ar trebui să păstreze o parte mult mai mare din taxele pe care le încasează.",en:"Local councils should keep a much larger share of the taxes they collect."},
  {id:"A6-07",ax:"A6",d:-1,ro:"Deciziile despre școli, spitale și drumuri ar trebui să aparțină administrațiilor județene și locale, nu ministerelor.",en:"Decisions about schools, hospitals and roads should belong to county and city administrations, not to ministries."},
  {id:"A6-08",ax:"A6",d:-1,ro:"România ar trebui să creeze regiuni administrative cu consilii alese și bugete proprii.",en:"Romania should create administrative regions with elected councils and their own budgets."},
  {id:"A7-01",ax:"A7",d:1,ro:"România ar trebui să închidă termocentralele pe cărbune până în 2030, chiar dacă asta costă locuri de muncă.",en:"Romania should close its coal plants by 2030, even if that costs jobs in mining regions."},
  {id:"A7-02",ax:"A7",d:1,ro:"Respectarea țintelor climatice ale UE ar trebui să rămână o prioritate chiar dacă regulile scumpesc facturile.",en:"Meeting EU climate targets should stay a priority even when the rules raise energy bills."},
  {id:"A7-03",ax:"A7",d:1,ro:"România ar trebui să construiască cât mai multă capacitate eoliană și solară, chiar dacă unii locuitori se opun.",en:"Romania should build as much wind and solar capacity as possible, even where some residents object."},
  {id:"A7-06",ax:"A7",d:-1,ro:"România ar trebui să extragă gazul din Marea Neagră cât mai repede pentru a-și asigura necesarul.",en:"Romania should extract Black Sea gas as fast as possible to secure its own supply."},
  {id:"A7-07",ax:"A7",d:-1,ro:"Statul ar trebui să păstreze și să modernizeze termocentralele pe cărbune și gaze, pentru securitate energetică.",en:"The state should keep and modernise its coal and gas plants, because they guarantee energy security."},
  {id:"A8-01",ax:"A8",d:1,ro:"Oamenii ar trebui să poată direcționa contribuțiile de sănătate către un asigurator privat, dacă vor.",en:"People should be able to direct their health contributions to a private insurer if they choose."},
  {id:"A8-02",ax:"A8",d:1,ro:"Spitalele și școlile private ar trebui să concureze pentru bani publici în condiții egale cu cele de stat.",en:"Private hospitals and schools should compete for public money on equal terms with state ones."},
  {id:"A8-06",ax:"A8",d:-1,ro:"Sănătatea ar trebui să rămână în mâinile statului; asigurarea privată să fie un supliment, nu o alternativă.",en:"Health care should stay in state hands; private insurance should remain a supplement, not a substitute."},
  {id:"A8-07",ax:"A8",d:-1,ro:"Prioritatea în sănătate și educație ar trebui să fie salarii mai mari, nu reforme structurale.",en:"The priority in health and education should be higher pay for staff, not structural reform."},
  {id:"A8-08",ax:"A8",d:-1,ro:"Școlile publice nu ar trebui să concureze cu cele private pentru banii statului.",en:"Public schools should not compete with private schools for state money."},
  {id:"A9-01",ax:"A9",d:1,ro:"Vorbitorii de limbă maghiară ar trebui să poată folosi limba lor la autoritățile locale acolo unde sunt numeroși.",en:"Hungarian speakers should be able to use their language with local authorities wherever they are numerous."},
  {id:"A9-02",ax:"A9",d:1,ro:"Comunitățile minoritare ar trebui să aibă reprezentare politică garantată, chiar dacă e nevoie de locuri speciale.",en:"Minority communities should have guaranteed political representation, even if that needs special seats."},
  {id:"A9-03",ax:"A9",d:1,ro:"Statul ar trebui să finanțeze școlile, teatrele și presa în limbile minorităților în condiții egale.",en:"The state should fund schools, theatres and media in minority languages on equal terms with Romanian ones."},
  {id:"A9-06",ax:"A9",d:-1,ro:"Româna ar trebui să fie singura limbă folosită în administrația publică, în toată țara.",en:"Romanian should be the only language used in public administration, everywhere in the country."},
  {id:"A9-07",ax:"A9",d:-1,ro:"Cererile politice ale minorităților nu ar trebui să poată bloca deciziile susținute de majoritatea națională.",en:"Minority political demands should not be able to block decisions supported by the national majority."},
  {id:"A10-01",ax:"A10",d:1,ro:"România ar trebui să simplifice mult obținerea permiselor de muncă pentru lucrătorii din afara UE.",en:"Romania should make it much easier and faster for non-EU workers to get work permits."},
  {id:"A10-02",ax:"A10",d:1,ro:"Angajatorii ar trebui să poată angaja direct lucrători străini când nu găsesc români.",en:"Employers should be able to hire foreign workers directly when they cannot find Romanian ones."},
  {id:"A10-06",ax:"A10",d:-1,ro:"România ar trebui să limiteze lucrătorii străini până când șomajul în rândul românilor este mic.",en:"Romania should limit foreign workers until unemployment among Romanians is low."},
  {id:"A10-07",ax:"A10",d:-1,ro:"Firmele care primesc sprijin de stat ar trebui obligate să angajeze mai întâi români.",en:"Companies receiving state support should be required to hire Romanian workers first."},
  {id:"A10-08",ax:"A10",d:-1,ro:"Regulile de muncă ar trebui să rămână protectoare: preaviz lung, sindicate puternice, limite la contractele temporare.",en:"Labour rules should stay protective: long notice periods, strong unions, strict limits on temporary contracts."}
];
function MODE_ITEMS(){ return MODE === "progressive" ? POOL_ITEMS : CORE_ITEMS; }
const ITEMS = MODE_ITEMS();

const SALIENCE_Q = {
  ro: {
  "A1": "Cât de important este acest subiect pentru tine? (Geopolitică și traiectorie națională)",
  "A2": "Cât de important este acest subiect pentru tine? (Identitate socială și culturală)",
  "A3": "Cât de important este acest subiect pentru tine? (Filozofie economică)",
  "A4": "Cât de important este acest subiect pentru tine? (Guvernare & anticorupție)",
  "A5": "Cât de important este acest subiect pentru tine? (Atitudinea față de sistem)",
  "A6": "Cât de important este acest subiect pentru tine? (Structură administrativă & putere regională)",
  "A7": "Cât de important este acest subiect pentru tine? (Mediu & tranziție energetică)",
  "A8": "Cât de important este acest subiect pentru tine? (Servicii publice (sănătate & educație))",
  "A9": "Cât de important este acest subiect pentru tine? (Relații etnice & reprezentare minorități)",
  "A10": "Cât de important este acest subiect pentru tine? (Piața muncii & migrație)"
},
  en: {
  "A1": "How important is this topic to you? (Geopolitics & national trajectory)",
  "A2": "How important is this topic to you? (Social & cultural identity)",
  "A3": "How important is this topic to you? (Economic philosophy)",
  "A4": "How important is this topic to you? (Governance & anti-corruption)",
  "A5": "How important is this topic to you? (Systemic stance)",
  "A6": "How important is this topic to you? (Administrative structure & regional power)",
  "A7": "How important is this topic to you? (Environment & energy transition)",
  "A8": "How important is this topic to you? (Public services (health & education))",
  "A9": "How important is this topic to you? (Ethnic relations & minority representation)",
  "A10": "How important is this topic to you? (Labour market & migration)"
}
};
const ATTENTION = {id:"Q-ATT-2",
  ro:"Pentru a răspunde la această întrebare, te rugăm să alegi „Dezacord”.",
  en:"To answer this question, please select “Disagree”."};


/* =========================================================================
   ENGINE (pure, no DOM) -- mirror of scoring/score.py
   score = keyed mean on 1-5 (floats allowed)  |  margin = lambda * SEM
   ========================================================================= */
const SD_ITEM = 1.15;            // bank item SD (calibrate on field data)
const R_BAR = 0.45;              // average inter-item correlation
const LAMBDA = SD_ITEM * Math.sqrt(R_BAR);   // 0.7714 points per theta unit
const MIN_ITEMS = 2;
const MIN_COVERAGE = 0.60;
const MIDPOINT = 3.0;
const DK = "dk";

const AXIS_ORDER = Object.keys(QAXES);

function erf(x){                 // Abramowitz & Stegun 7.1.26
  const s = Math.sign(x); x = Math.abs(x);
  const a1=.254829592,a2=-.284496736,a3=1.421413741,a4=-1.453152027,a5=1.061405429,p=.3275911;
  const t = 1/(1+p*x);
  return s*(1-((((a5*t+a4)*t+a3)*t+a2)*t+a1)*t*Math.exp(-x*x));
}
const normCdf = z => 0.5*(1+erf(z/Math.SQRT2));
const clamp = (x,lo,hi) => Math.max(lo, Math.min(hi, x));

function reliabilityFor(k){
  return k > 0 ? clamp((k*R_BAR)/(1+(k-1)*R_BAR), 0, 0.99) : 0;
}
/* What a k-item axis is worth in advance: the +/- the app promises. */
function precisionFor(k){
  const rel = reliabilityFor(k);
  const sem = Math.sqrt(Math.max(0, (1-rel)/rel));
  return {k, rel, sem, margin: LAMBDA*sem};
}
function keyedValues(responses, items, axis){
  const out = [];
  for (const it of items){
    if (it.ax !== axis) continue;
    const v = responses[it.id];
    if (v === undefined || v === null || v === DK) continue;
    out.push(it.d > 0 ? +v : 6 - (+v));        // reverse-keyed items
  }
  return out;
}
function clarityLabel(theta, sem){
  if (theta === null || theta === undefined || sem === null || sem === undefined)
    return "TXT_CLARITY_UNKNOWN";
  const z = Math.abs(theta)/Math.max(1e-6, sem);
  if (z < 1.0) return "TXT_CLARITY_MID";
  if (z < 2.0) return "TXT_CLARITY_LEAN";
  return "TXT_CLARITY_CLEAR";
}
/* One axis.  formPerAxis = how many items of this axis the user was shown. */
function scoreAxis(responses, items, axis, formPerAxis){
  const vals = keyedValues(responses, items, axis);
  const k = vals.length;
  if (k < MIN_ITEMS || k/Math.max(1, formPerAxis) < MIN_COVERAGE){
    return {axis, status:"insufficient", k, rel:reliabilityFor(k)};
  }
  const score = vals.reduce((a,c)=>a+c,0)/k;
  const theta = (score - MIDPOINT)/LAMBDA;
  const rel = reliabilityFor(k);
  const sem = Math.sqrt(Math.max(0, (1-rel)/rel));
  return {axis, status:"ok", k, rel, score, theta, sem,
          margin: LAMBDA*sem,
          percentile: 100*normCdf(theta),
          clarity: clarityLabel(theta, sem)};
}
function computeProfile(responses, items, formPerAxis){
  const out = {};
  for (const ax of AXIS_ORDER)
    out[ax] = scoreAxis(responses, items, ax, (formPerAxis && formPerAxis[ax]) || MIN_ITEMS);
  return out;
}
/* How typical is this 10-axis shape?  No party information involved. */
function coherence(scores){
  const ok = AXIS_ORDER.filter(a => scores[a].status === "ok");
  if (!ok.length) return {axesScored:0};
  const ranked = [...ok].sort((a,b)=>Math.abs(scores[b].theta)-Math.abs(scores[a].theta));
  let tension = 0, pairs = 0;
  for (let i=0;i<ok.length;i++) for (let j=i+1;j<ok.length;j++){
    const r = R_AXES[i][j];
    pairs++;
    if (r*(scores[ok[i]].theta*scores[ok[j]].theta) < 0) tension++;
  }
  return {axesScored: ok.length,
          mostDecided: ranked.slice(0,3).map(a=>({axis:a, score:scores[a].score, clarity:scores[a].clarity})),
          closestToMiddle: [...ok].sort((a,b)=>Math.abs(scores[a].theta)-Math.abs(scores[b].theta))
                             .slice(0,2).map(a=>({axis:a, score:scores[a].score})),
          tensionShare: pairs ? tension/pairs : 0};
}
/* Data-quality gate: refuse to over-trust a fast, flat or evasive run. */
function qualityGate(responses, items, opts){
  opts = opts || {};
  const answered = items.filter(it => responses[it.id] !== undefined && responses[it.id] !== null);
  const numeric = answered.filter(it => responses[it.id] !== DK).map(it => +responses[it.id]);
  const flags = [];
  const dkShare = answered.length ? 1 - numeric.length/answered.length : 0;
  if (dkShare > 0.25) flags.push("TXT_FLAG_DK");
  if (numeric.length >= 6){
    const mode = {}; numeric.forEach(v => mode[v] = (mode[v]||0)+1);
    const conc = Math.max(...Object.values(mode))/numeric.length;
    if (conc >= 0.60) flags.push("TXT_FLAG_FLAT");
  }
  if (opts.medianSecondsPerItem != null && opts.medianSecondsPerItem < 2.5)
    flags.push("TXT_FLAG_FAST");
  if (opts.attentionFailed) flags.push("TXT_FLAG_ATTN");
  return {flags, trustworthy: flags.length === 0, dkShare};
}
/* Focus mode: importance (1-4, from the user) x uncertainty (margin). */
function focusOrder(weights, scores){
  return [...AXIS_ORDER].sort((a,b)=>{
    const wa = (weights[a]||1) * ((scores[a] && scores[a].margin) || 1.2);
    const wb = (weights[b]||1) * ((scores[b] && scores[b].margin) || 1.2);
    return wb - wa;
  });
}
function nextItems(state, n){
  /* Pick up to n unasked items: highest-priority axis first, alternating poles
     so a single axis is never measured by same-pole items only. */
  const picked = [];
  const order = focusOrder(state.weights || {}, state.scores || {});
  const usedPole = {};
  for (const ax of order){
    for (let round = 0; round < 6 && picked.length < n; round++){
      const poleWanted = (usedPole[ax] = (usedPole[ax] === 1 ? -1 : 1));
      const cand = state.pool.filter(it => it.ax === ax && !picked.includes(it) &&
                                           !state.asked.includes(it.id) && it.d === poleWanted)[0];
      if (cand) picked.push(cand);
    }
  }
  return picked.slice(0, n);
}
/* ======================= END ENGINE ======================= */


/* =======================================================================
   2. UI
   ======================================================================= */
const TXT = {
 ro:{
  docTitle:"Quiz — orientare politică",
  sub:"Zece axe, scoruri cu zecimale de la 1 la 5, marjă de eroare declarată.",
  subSalience:"Pasul 1/2 — ce contează pentru tine",
  subItems:"Răspunde cât mai sincer; nu există răspunsuri greșite.",
  subPreview:"Profilul tău provizoriu",
  subSharpen:"Rotunjirea profilului",
  subResult:"Profilul tău final",
  howTitle:"Cum funcționează",
  howBody:"Zece axe de poziționare politică: răspunsurile tale produc un profil numeric, pe aceleași axe ca politicienii și partidele de pe site.",
  howBullets:["Primești un scor de la 1 la 5 pe fiecare axă, cu zecimale, plus marja de eroare.","Poți opri oricând: după 20 de afirmații ai deja toate cele zece axe.","Nu îți spunem pe cine să votezi. Pe paginile politicienilor și partidelor vezi diferențele dintre pozițiile tale și ale lor.","Rezultatul se salvează doar în acest browser și îl poți șterge oricând; răspunsurile politice sunt date protejate (art. 9 GDPR)."],
  consentTitle:"Consimțământ",
  consentBody:"Îmi dau consimțământul explicit pentru prelucrarea răspunsurilor mele politice (date din categoria specială, art. 9 GDPR), exclusiv pentru calcularea profilului și compararea lui, în acest browser, cu pozițiile politicienilor și partidelor de pe site. Fără mesaje politice țintite, fără vânzarea datelor. Pot șterge rezultatul oricând.",
  privacy:"Răspunsurile și profilul rămân în acest browser (stocare locală); nu sunt trimise nicăieri.",
  start:"Începe",
  salTitle:"Cât de importante sunt aceste subiecte pentru tine?",
  salBody:"1 = deloc important · 4 = decisiv. Folosim răspunsurile doar ca să hotărâm ce axe rafinăm mai întâi. Nu influențează scorurile.",
  salHint:"Poți sări peste acest pas — atunci rafinăm după incertitudinea măsurătorii.",
  skip:"Sari peste",
  startProbe:"Începe afirmațiile",
  progress:(i,total)=>`Afirmația ${i+1} din ${total}`,
  progNote:total=>`Formular scurt: ${total} afirmații, un item pe ecran.`,
  scale:["Dezacord total","Dezacord","Nici-nici","Acord","Acord total"],
  dk:"Nu știu",
  next:"Înainte",
  back:"Înapoi",
  prevTitle:"Profilul tău provizoriu (zece axe)",
  prevBody:(a,b)=>`Ai răspuns la ${b} afirmații: câte două pe fiecare axă. Toate cele zece axe au un scor, cu marjă mare. Poți rafina sau te poți opri aici.`,
  sharpenTitle:"Vrei un profil mai precis?",
  sharpenBody:"Fiecare afirmație în plus strânge marja. Alegem afirmațiile după importanța pe care ai dat-o și după incertitudinea fiecărei axe.",
  addN:n=>`+${n} afirmații`,
  topicOnly:"Doar subiectul care contează pentru mine",
  finish:"Gata, arată-mi profilul",
  sharpenProgress:(d,max)=>`Rafinare: ${d} din maximum ${max} afirmații`,
  sharpenHint:"Poți răspunde „Nu știu”; itemul devine lipsă, nu zero.",
  saveBatch:"Salvează și actualizează profilul",
  answerAll:"Răspunde la toate afirmațiile din acest pas.",
  k:n=>`${n} item${n===1?"":"i"}`,
  pct:p=>`percentila ${p} (față de populația de referință a scalei)`,
  insufficient:n=>`Date insuficiente pe această axă (${n} răspunsuri).`,
  resTitle:"Profilul tău pe zece axe",
  resBody:"Scoruri pe scala 1–5, cu zecimale, ca la politicieni: aproape de 1 înseamnă primul pol (stânga), aproape de 5 al doilea pol (dreapta). Bara arată intervalul de incertitudine (± marja).",
  marginHint:"Marja = 0,77 × eroarea standard; percentila se calculează pe scala normată. Marja tipică: ±0.60 puncte la 2 itemi/axă, ±0.49 la 3, ±0.38 la 5, ±0.27 la 10 (eroare standard din modelul de răspuns; verificată în simulare).",
  cohTitle:"Coerența profilului",
  cohBody:p=>`Cât de neobișnuită e combinația de poziții? ${p}% din perechile de axe trag în direcții care contrazic corelația obișnuită (0% = profil tipic, 100% = foarte neobișnuit).`,
  cohCol1:"Axă", cohCol2:"Scor",
  TXT_CLARITY_MID:"aproape de mijloc",
  TXT_CLARITY_LEAN:"înclinație",
  TXT_CLARITY_CLEAR:"poziție clară",
  TXT_CLARITY_UNKNOWN:"necunoscut",
  TXT_FLAG_DK:"multe răspunsuri „nu știu” — profilul e mai puțin sigur",
  TXT_FLAG_FLAT:"răspunsuri foarte repetitive — verifică dacă ai citit afirmațiile",
  TXT_FLAG_FAST:"ritm foarte rapid — la un test real datele ar fi marcate ca nesigure",
  TXT_FLAG_ATTN:"întrebarea de verificare nu a fost respectată",
  closest:"aproape de mijloc:",
  qualTitle:"Calitatea răspunsurilor",
  qualOk:"Răspunsurile trec verificările de calitate.",
  qualBad:"Au fost detectate semnale de calitate — scorurile se citesc cu prudență.",
  qualNone:"Nicio problemă detectată.",
  qualStats:(a,b,m)=>`${a} din ${b} afirmații completate` + (m === null ? "." : `; timp median ${m} s/item.`),
  methTitle:"Metodă (pe scurt)",
  methBody:"Scorul fiecărei axe = media răspunsurilor cu cheie (1–5), cu zecimale. Incertitudinea = 0,77 × eroarea standard; fiabilitatea crește cu numărul de itemi. Răspunsurile „Nu știu” nu intră în scor. Dacă o axă are mai puțin de 2 itemi sau sub 60% din itemii afișați, nu afișăm scor. Structura de corelații dintre axe e folosită doar pentru indicatorul de coerență. Comparația cu politicienii și partidele se face separat, pe paginile lor.",
  endNote:"Quiz-ul nu îți spune pe cine să votezi. Profilul este o descriere a pozițiilor tale, nu o recomandare.",
  again:"Reia",
  save:"Salvează rezultatul",
  saved:"Rezultat salvat în acest browser și descărcat ca fișier.",
  radarTitle:"Harta ta ideologică · 10 axe",
  savedNote:"Rezultatul e salvat în acest browser. Pe pagina fiecărui politician și partid vezi radarul tău peste al lor și diferențele majore.",
  compare:"Compară-te cu politicienii și partidele →",
  forget:"Șterge rezultatul salvat",
  forgotten:"Rezultatul a fost șters din acest browser.",
  hasSaved:"Ai deja un rezultat salvat; dacă refaci quiz-ul, cel nou îl va înlocui."
 },
 en:{
  docTitle:"Quiz — political orientation",
  sub:"Ten axes, 1-5 scores with decimals, stated margin of error.",
  subSalience:"Step 1/2 — what matters to you",
  subItems:"Answer as honestly as you can; there are no wrong answers.",
  subPreview:"Your provisional profile",
  subSharpen:"Sharpening the profile",
  subResult:"Your final profile",
  howTitle:"How it works",
  howBody:"Ten axes of political positioning: your answers produce a numeric profile on the same axes as the politicians and parties on this site.",
  howBullets:["You get a 1-5 score on every axis, with decimals, plus its margin of error.","You can stop any time: after 20 statements you already have all ten axes.","We do not tell you who to vote for. On the politicians' and parties' pages you see how your positions differ from theirs.","The result is saved only in this browser and you can delete it at any time; political answers are protected data (GDPR Art. 9)."],
  consentTitle:"Consent",
  consentBody:"I give explicit consent to process my political answers (special category data, GDPR Art. 9), solely to compute my profile and compare it, in this browser, with the positions of the politicians and parties on this site. No political messaging targeting, no data sales. Deletable at any time.",
  privacy:"Your answers and profile stay in this browser (local storage); they are not sent anywhere.",
  start:"Start",
  salTitle:"How important are these topics to you?",
  salBody:"1 = not important · 4 = decisive. Used only to decide which axes to sharpen first. It does not change the scores.",
  salHint:"You can skip this — we then sharpen by measurement uncertainty.",
  skip:"Skip",
  startProbe:"Start the statements",
  progress:(i,total)=>`Statement ${i+1} of ${total}`,
  progNote:total=>`Short form: ${total} statements, one per screen.`,
  scale:["Strongly disagree","Disagree","Neutral","Agree","Strongly agree"],
  dk:"Don't know",
  next:"Next",
  back:"Back",
  prevTitle:"Your provisional ten-axis profile",
  prevBody:(a,b)=>`You answered ${b} statements: two per axis. All ten axes have a score, with a wide margin. Sharpen it or stop here.`,
  sharpenTitle:"Want a tighter profile?",
  sharpenBody:"Each extra statement narrows the margin. Statements are chosen by your importance ratings and by each axis's uncertainty.",
  addN:n=>`+${n} statements`,
  topicOnly:"Only the topic that matters to me",
  finish:"Done, show my profile",
  sharpenProgress:(d,max)=>`Sharpening: ${d} of at most ${max} statements`,
  sharpenHint:"You can answer “Don't know”; the item becomes missing, not zero.",
  saveBatch:"Save and update the profile",
  answerAll:"Please answer every statement in this step.",
  k:n=>`${n} item${n===1?"":"s"}`,
  pct:p=>`${ordinal(p)} percentile (against the scale's reference population)`,
  insufficient:n=>`Not enough data on this axis (${n} answers).`,
  resTitle:"Your ten-axis profile",
  resBody:"1-5 scores with decimals, as for the politicians: near 1 means the first pole (left), near 5 the second pole (right). The bar shows the uncertainty interval (± the margin).",
  marginHint:"Margin = 0.77 × standard error; percentile from the normed scale. Typical margin: ±0.60 points at 2 items/axis, ±0.49 at 3, ±0.38 at 5, ±0.27 at 10 (standard error from the response model; checked in simulation).",
  cohTitle:"Profile coherence",
  cohBody:p=>`How unusual is this combination? ${p}% of axis pairs pull against their usual correlation (0% = typical profile, 100% = very unusual).`,
  cohCol1:"Axis", cohCol2:"Score",
  TXT_CLARITY_MID:"near the middle",
  TXT_CLARITY_LEAN:"leaning",
  TXT_CLARITY_CLEAR:"clear position",
  TXT_CLARITY_UNKNOWN:"unknown",
  TXT_FLAG_DK:"many “don't know” answers — the profile is less certain",
  TXT_FLAG_FLAT:"very repetitive answers — check that you read the statements",
  TXT_FLAG_FAST:"very fast pace — in a real test the data would be flagged as unreliable",
  TXT_FLAG_ATTN:"the attention check was not respected",
  closest:"close to the middle:",
  qualTitle:"Answer quality",
  qualOk:"The answers pass the quality checks.",
  qualBad:"Quality flags were detected — read the scores with caution.",
  qualNone:"No problem detected.",
  qualStats:(a,b,m)=>`${a} of ${b} statements answered` + (m === null ? "." : `; median ${m} s/item.`),
  methTitle:"Method (short)",
  methBody:"Each axis score = the keyed mean of the answers (1-5), with decimals. Uncertainty = 0.77 × standard error; reliability rises with the number of items. “Don't know” answers are excluded. An axis with fewer than 2 items or under 60% of its presented items is not scored. The axis-correlation structure is used only for the coherence indicator. The comparison with politicians and parties happens separately, on their pages.",
  endNote:"The quiz does not tell you who to vote for. The profile describes your positions; it is not a recommendation.",
  again:"Restart",
  save:"Save the result",
  saved:"Result saved in this browser and downloaded as a file.",
  radarTitle:"Your ideological map · 10 axes",
  savedNote:"The result is saved in this browser. On each politician's and party's page you see your radar over theirs and the major differences.",
  compare:"Compare yourself with politicians and parties →",
  forget:"Delete the saved result",
  forgotten:"The result was deleted from this browser.",
  hasSaved:"You already have a saved result; if you retake the quiz, the new one replaces it."
 }
};

let LANG = "ro";
const t = () => TXT[LANG];
const ordinal = n => { const r = n % 100; if (r >= 11 && r <= 13) return n + "th";
  return n + (["th","st","nd","rd"][n % 10] || "th"); };
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

const state = {
  consent:false, screen:"intro", responses:{}, asked:[], answersLog:[],
  itemTimes:{}, startedAt:{}, index:0, selItems:[], weights:{},
  attentionFailed:false, sharpenBatches:0, topicOnly:null
};

function allQuestions(){
  /* the items this arm may ask, in presentation order */
  if (MODE === "classic") return CORE_ITEMS.slice(0, 15).concat([null], CORE_ITEMS.slice(15));
  return PROBE_ITEMS.slice(0, 10).concat([null], PROBE_ITEMS.slice(10));
}
function dom(){ return {app:document.getElementById("app"), sub:document.getElementById("sub")}; }

/* ---------------------------------------------------------------- intro */
function renderIntro(){
  const d = dom();
  document.title = t().docTitle;
  d.sub.textContent = t().sub;
  d.app.innerHTML = `
  <div class="qz-card">
    <h2>${t().howTitle}</h2>
    <p class="qz-note">${t().howBody}</p>
    <ul class="qz-note">${t().howBullets.map(x=>`<li>${x}</li>`).join("")}</ul>
  </div>
  <div class="qz-card">
    <h2>${t().consentTitle}</h2>
    <label class="qz-consent"><input type="checkbox" id="consent">
      <span class="qz-note">${t().consentBody}</span></label>
    ${getUserOrientation(AXES.length) ? `<p class="qz-note">${t().hasSaved}</p>` : ""}
    <div class="qz-row">
      <div class="qz-note">${t().privacy}</div>
      <button class="qz-primary" id="go" disabled>${t().start}</button>
    </div>
  </div>`;
  document.getElementById("consent").onchange = e => {
    state.consent = e.target.checked;
    document.getElementById("go").disabled = !state.consent;
  };
  document.getElementById("go").onclick = () => {
    if (MODE === "progressive"){ state.screen = "salience"; render(); }
    else startItems(CORE_ITEMS);
  };
}

/* ------------------------------------------------------------- salience */
function renderSalience(){
  const d = dom();
  const q = SALIENCE_Q[LANG] || SALIENCE_Q.ro;
  d.sub.textContent = t().subSalience;
  d.app.innerHTML = `
  <div class="qz-card">
    <h2>${t().salTitle}</h2>
    <p class="qz-note">${t().salBody}</p>
    ${AXIS_ORDER.map(ax=>`
      <div class="qz-sal"><span class="qz-nm">${esc(q[ax])}</span>
        <span class="qz-opts" data-ax="${ax}">
          ${[1,2,3,4].map(v=>`<label><input type="radio" name="sal-${ax}" value="${v}"><span>${v}</span></label>`).join("")}
        </span>
      </div>`).join("")}
    <p class="qz-hint">${t().salHint}</p>
    <div class="qz-row">
      <button class="qz-ghost" id="skipSal">${t().skip}</button>
      <button class="qz-primary" id="goItems">${t().startProbe}</button>
    </div>
  </div>`;
  d.app.querySelectorAll(".qz-sal").forEach(row=>{
    const ax = row.querySelector(".qz-opts").dataset.ax;
    row.querySelectorAll("input").forEach(inp => inp.onchange = () => state.weights[ax] = +inp.value);
  });
  document.getElementById("skipSal").onclick = () => { state.weights = {}; startItems(PROBE_ITEMS); };
  document.getElementById("goItems").onclick = () => startItems(PROBE_ITEMS);
}

/* ---------------------------------------------------------------- items */
function startItems(items){
  state.selItems = items;
  state.screen = "items"; state.index = 0; state.startedAt = {};
  render();
}
function itemSequence(items){
  /* one attention check, after the middle of the set, in every arm */
  const mid = Math.floor(items.length/2);
  const attn = {id:ATTENTION.id, ax:null, d:0, ro:ATTENTION.ro, en:ATTENTION.en, attn:true};
  return items.slice(0, mid).concat([attn], items.slice(mid));
}
function currentQuestions(){
  return itemSequence(MODE === "classic" ? CORE_ITEMS : state.selItems);
}
function scoredTotal(){
  return MODE === "classic" ? CORE_ITEMS.length : state.selItems.length;
}
function renderItems(){
  const d = dom();
  const list = currentQuestions();
  const it = list[state.index];
  const total = scoredTotal();
  const scoredSoFar = list.slice(0, state.index).filter(x => !x.attn).length;
  const pct = Math.round(100*scoredSoFar/total);
  d.sub.textContent = t().subItems;
  d.app.innerHTML = `
  <div class="qz-bar"><i style="width:${pct}%"></i></div>
  <div class="qz-note" style="margin-bottom:8px">${t().progress(scoredSoFar, total)}</div>
  <div class="qz-q" data-id="${it.id}">
    <div class="qz-txt">${esc(it[LANG] || it.ro)}</div>
    <div class="qz-opts">
      ${[1,2,3,4,5].map(v=>`<label><input type="radio" name="a" value="${v}"><span>${t().scale[v-1]}</span></label>`).join("")}
      <label class="qz-dk"><input type="radio" name="a" value="dk"><span>${t().dk}</span></label>
    </div>
  </div>
  <div class="qz-row">
    <button class="qz-ghost" id="back" ${state.index===0?"disabled":""}>${t().back}</button>
    <div class="qz-note" id="progNote">${t().progNote(total)}</div>
    <button class="qz-primary" id="next" disabled>${t().next}</button>
  </div>`;
  state.startedAt[it.id] = performance.now();
  d.app.querySelectorAll("input[name=a]").forEach(inp => inp.onchange = () => {
    document.getElementById("next").disabled = false;
  });
  document.getElementById("back").onclick = () => { if (state.index>0){ state.index--; render(); } };
  document.getElementById("next").onclick = () => {
    const v = d.app.querySelector("input[name=a]:checked").value;
    state.responses[it.id] = (v === "dk") ? DK : +v;
    state.itemTimes[it.id] = (performance.now() - state.startedAt[it.id])/1000;
    if (it.attn && v !== "2") state.attentionFailed = true;
    state.index++;
    if (state.index >= list.length){
      state.screen = (MODE === "classic") ? "result" : "preview";
    }
    render();
  };
}

/* --------------------------------------- progressive: profile preview */
function askedItems(){
  return state.selItems.concat(state.asked.filter(id => !state.selItems.some(i=>i.id===id))
    .map(id => POOL_ITEMS.find(i=>i.id===id)).filter(Boolean));
}
function formPerAxis(items){
  const out = {};
  for (const it of items) out[it.ax] = (out[it.ax]||0)+1;
  return out;
}
function profileOf(items){
  return computeProfile(state.responses, items, formPerAxis(items));
}
function medianTime(){
  const ts = Object.values(state.itemTimes);
  if (!ts.length) return null;
  const s = [...ts].sort((a,b)=>a-b);
  return s[Math.floor(s.length/2)];
}
function renderPreview(){
  const d = dom();
  const items = askedItems();
  const prof = profileOf(items);
  const k = state.selItems.length;
  d.sub.textContent = t().subPreview;
  d.app.innerHTML = `
  <div class="qz-card">
    <h2>${t().prevTitle}</h2>
    <p class="qz-note">${t().prevBody(10, 20)}</p>
    ${profileCards(prof, items, true)}
  </div>
  <div class="qz-card">
    <h2>${t().sharpenTitle}</h2>
    <p class="qz-note">${t().sharpenBody}</p>
    <div class="qz-row">
      <div>
        <button class="qz-ghost" data-add="5">${t().addN(5)}</button>
        <button class="qz-ghost" data-add="10">${t().addN(10)}</button>
        <button class="qz-ghost" id="topicBtn">${t().topicOnly}</button>
      </div>
      <button class="qz-primary" id="finish">${t().finish}</button>
    </div>
  </div>`;
  d.app.querySelectorAll("[data-add]").forEach(b => b.onclick = () => sharpen(+b.dataset.add, null));
  document.getElementById("topicBtn").onclick = () => {
    const ax = focusOrder(state.weights, prof)[0];
    if (state.weights[ax] === undefined) state.weights[ax] = 4;
    sharpen(6, ax);
  };
  document.getElementById("finish").onclick = () => { state.screen = "result"; render(); };
}
function renderSharpen(){
  const d = dom();
  const items = askedItems();
  const prof = profileOf(items);
  const batch = state.pendingBatch;
  d.sub.textContent = t().subSharpen;
  d.app.innerHTML = `
  <div class="qz-bar"><i style="width:${Math.round(100*(state.selItems.length)/50)}%"></i></div>
  <div class="qz-note" style="margin-bottom:8px">${t().sharpenProgress(state.selItems.length, 50)}</div>
  ${batch.map(it => `
    <div class="qz-q" data-id="${it.id}">
      <div class="qz-txt">${esc(it[LANG] || it.ro)}</div>
      <div class="qz-opts">
        ${[1,2,3,4,5].map(v=>`<label><input type="radio" name="a-${it.id}" value="${v}"><span>${t().scale[v-1]}</span></label>`).join("")}
        <label class="qz-dk"><input type="radio" name="a-${it.id}" value="dk"><span>${t().dk}</span></label>
      </div>
    </div>`).join("")}
  <div class="qz-row">
    <div class="qz-note">${t().sharpenHint}</div>
    <button class="qz-primary" id="saveBatch">${t().saveBatch}</button>
  </div>`;
  document.getElementById("saveBatch").onclick = () => {
    let ok = true;
    for (const it of batch){
      const sel = d.app.querySelector(`input[name="a-${it.id}"]:checked`);
      if (!sel){ ok = false; continue; }
      state.responses[it.id] = sel.value === "dk" ? DK : +sel.value;
      if (!state.asked.includes(it.id)) state.asked.push(it.id);
    }
    if (!ok){ alert(t().answerAll); return; }
    state.screen = "preview";
    render();
  };
}
function sharpen(n, axisOnly){
  const items = askedItems();
  const prof = profileOf(items);
  const poolItems = axisOnly
    ? POOL_ITEMS.filter(i => i.ax === axisOnly)
    : POOL_ITEMS;
  const picked = nextItems({pool: poolItems, asked: items.map(i=>i.id), scores: prof,
                            weights: axisOnly ? {[axisOnly]:4} : state.weights}, n);
  if (!picked.length){ state.screen = "result"; render(); return; }
  state.pendingBatch = picked;
  state.screen = "sharpen";
  render();
}

/* ----------------------------------------------------------- profile UI */
// Quiz engine scores: 5 = the first pole listed on the site (e.g. Pro-Occident). Shown in the site's convention:
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
function renderResult(){
  const d = dom();
  const items = (MODE === "classic") ? CORE_ITEMS : askedItems();
  const prof = profileOf(items);
  const coh = coherence(prof);
  const q = qualityGate(state.responses, items, {medianSecondsPerItem:medianTime(),
                                                 attentionFailed:state.attentionFailed});
  const answered = items.filter(i=>state.responses[i.id] !== undefined).length;
  const medRaw = Object.values(state.itemTimes).length ? medianTime() : null;
  const med = (medRaw !== null && medRaw >= 0.3) ? medRaw.toFixed(1) : null;
  const positions = sitePositions(prof);
  saveUserOrientation(positions, leaningFrom(positions, AXES));
  d.sub.textContent = t().subResult;
  d.app.innerHTML = `
  <div class="qz-card">
    <h2>${t().radarTitle}</h2>
    ${renderRadar([{ values: positions, cls: "radar-user" }])}
    <p class="qz-note" id="savedNote">${t().savedNote}</p>
    <div class="qz-row">
      <a class="pill-link" href="index.html">${t().compare}</a>
      <span><button class="qz-primary" id="saveResult">${t().save}</button>
      <button class="qz-ghost" id="forget">${t().forget}</button></span>
    </div>
  </div>
  <div class="qz-card">
    <h2>${t().resTitle}</h2>
    <p class="qz-note">${t().resBody}</p>
    ${profileCards(prof, items)}
    <p class="qz-hint">${t().marginHint}</p>
  </div>
  <div class="qz-card">
    <h2>${t().cohTitle}</h2>
    <p class="qz-note">${t().cohBody(Math.round(coh.tensionShare*100))}</p>
    <table>
      <tr><th>${t().cohCol1}</th><th>${t().cohCol2}</th></tr>
      ${(coh.mostDecided||[]).map(x=>`<tr><td>${AXIS_ORDER.indexOf(x.axis) + 1} · ${esc((QAXES[x.axis][LANG]||QAXES[x.axis].ro))}</td>
        <td>${toSite(x.score).toFixed(2)} · ${t()[x.clarity]}</td></tr>`).join("")}
      ${(coh.closestToMiddle||[]).map(x=>`<tr><td>${t().closest} ${AXIS_ORDER.indexOf(x.axis) + 1} · ${esc((QAXES[x.axis][LANG]||QAXES[x.axis].ro))}</td>
        <td>${toSite(x.score).toFixed(2)}</td></tr>`).join("")}
    </table>
  </div>
  <div class="qz-card">
    <h2>${t().qualTitle}</h2>
    <p class="qz-note">${q.trustworthy ? t().qualOk : t().qualBad}</p>
    ${q.flags.length ? `<ul class="qz-note">${q.flags.map(f=>`<li>${t()[f]}</li>`).join("")}</ul>`
                     : `<ul class="qz-note"><li>${t().qualNone}</li></ul>`}
    <p class="qz-note">${t().qualStats(answered, items.length, med)}</p>
  </div>
  <div class="qz-card">
    <h2>${t().methTitle}</h2>
    <p class="qz-note">${t().methBody}</p>
  </div>
  <div class="qz-row">
    <div class="qz-note">${t().endNote}</div>
    <button class="qz-ghost" id="again">${t().again}</button>
  </div>`;
  document.getElementById("saveResult").onclick = () => {
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
  document.getElementById("forget").onclick = () => {
    try { localStorage.removeItem(USER_KEY); } catch (e) { /* storage unavailable */ }
    document.getElementById("savedNote").textContent = t().forgotten;
    document.getElementById("forget").disabled = true;
  };
  document.getElementById("again").onclick = () => {
    state.consent = false; state.screen = "intro"; state.responses = {};
    state.asked = []; state.index = 0; state.selItems = []; state.weights = {};
    state.itemTimes = {}; state.attentionFailed = false; state.pendingBatch = null;
    render();
  };
}

/* --------------------------------------------------------------- router */
function render(){
  if (state.screen === "intro") return renderIntro();
  if (state.screen === "salience") return renderSalience();
  if (state.screen === "items") return renderItems();
  if (state.screen === "preview") return renderPreview();
  if (state.screen === "sharpen") return renderSharpen();
  if (state.screen === "result") return renderResult();
}

document.getElementById("langBtn").onclick = () => {
  LANG = (LANG === "ro") ? "en" : "ro";
  document.getElementById("langBtn").textContent = (LANG === "ro") ? "EN" : "RO";
  render();
};
render();
})();
