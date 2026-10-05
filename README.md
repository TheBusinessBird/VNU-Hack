# PoliticieniRO

Site de informare despre politicienii și partidele din România: profil cu știri din ultimul an, orientare politică pe 10 axe, rezumate, erori logice semnalate automat și un **scor de credibilitate** (1–10) pentru fiecare politician și fiecare articol. Un quiz îți calculează propria orientare și îți arată cu cine semeni.

> Scorurile sunt **estimări automate** făcute de modele AI, nu verdicte. Metodologia completă (surse, formule, limite) este pe pagina **Metodologie** a site-ului.

## Pornire rapidă

Cerințe: Windows 10/11 cu PowerShell. Nu e nevoie să instalezi nimic înainte: `run.ps1` caută Python 3.9+ și, dacă lipsește, îl instalează cu `winget`.

```powershell
.\run.ps1
```

sau dublu-click pe `run.cmd` (ocolește restricția de executare a scripturilor PowerShell).

Scriptul pornește API-ul (`http://127.0.0.1:8000`) și site-ul (`http://localhost:8080`) și deschide browserul. **Enter** în fereastră oprește totul.

### Ce poți încerca imediat (fără cheie)

- **Călin Georgescu** și **Nicușor Dan** au analizele salvate în `api/cache` și se deschid instant: știri, scor de credibilitate, erori logice, radar cu 10 axe.
- **Quiz** (meniu): 20 de afirmații, apoi radarul tău. După ce îl termini, pe pagina principală apare lista „Cu cine semeni”, pentru politicienii cu orientare calculată.
- **Partide** (meniu): PSD, PNL, AUR, USR, UDMR, S.O.S. România, POT, cu aceeași analiză ca la politicieni.
- **Metodologie** (meniu): cum se calculează fiecare scor, lista site-urilor din care s-au extras surse, modelele folosite și limitele.

### Cheia Groq (pentru analize noi)

Un politician sau partid **neanalizat încă** are nevoie de o cheie [Groq](https://console.groq.com/keys) (gratuită). `run.ps1` o cere o singură dată, o verifică și o salvează în `api/groq_key.txt` (exclus din git). Alternativ, o poți pune în variabila de mediu `GROQ_API_KEY`. Fără cheie, tot ce e deja salvat se vede, dar nu se generează nimic nou.

Prima analiză a unui politician durează 3–5 minute (căutare și descărcare de pagini); după aceea rezultatul se salvează și profilul apare imediat.

## Comenzi

| Comandă | Ce face |
|---|---|
| `.\run.ps1` | pornește tot și așteaptă (Enter oprește) |
| `.\run.ps1 -NoWait` | pornește serverele și iese, lăsându-le pornite |
| `.\run.ps1 -Stop` | oprește serverele |
| `.\run.ps1 -Test` | rulează testele automate |
| `.\run.ps1 -NoBrowser` | nu deschide browserul |
| `.\run.ps1 -Port 9090` | alt port pentru site (API-ul rămâne pe 8000) |
| `.\run.ps1 -SkipKeyPrompt` | nu întreabă de cheia Groq |

Logurile sunt în `logs/`.

## Cum funcționează

1. **Căutare:** interogări către Bing (web și știri), plus căutări pe site-urile instituțiilor oficiale.
2. **Extragere:** din pagini se scot discursurile, citatele directe, autorul și data, fragmentele despre studii și finanțare.
3. **Erori logice** (la cerere): modele AI semnalează declarațiile care par false, contradictorii, conspiraționiste sau manipulatoare. Fiecare citat semnalat e verificat în textul sursei.
4. **Scor de credibilitate:** pentru fiecare articol, un model notează fezabilitatea (x), precizia (y), istoricul (z) și manipularea (w), de la 1 la 10.

   `scor = 0,2·x + 0,2·y + 0,4·z + 0,2·w`

   Scorul politicianului folosește aceeași formulă, cu mediile pe articole.
5. **Salvare:** tot ce se generează se păstrează în `api/cache` și nu se mai generează. O regenerare se cere explicit, cu `&force=1` în adresa API-ului.

Modelele rulează prin [Groq](https://groq.com) (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`), cu temperatura 0. Planul gratuit are 8.000 tokeni/minut pe model; clientul respectă limita și trece pe alt model când unul eșuează.

## Structura proiectului

```
run.ps1, run.cmd        pornire și instalare
serve_site.py           serverul site-ului (doar Python, fără Node)
index.html, politician.html, compare.html, quiz.html, metodologie.html
js/                     interfața (app.js, api.js, quiz.js, data.js, ...)
styles.css
api/
  promise_tracker_no_ai_v2.py   API-ul: căutare, extragere, joburi, endpoint-uri
  llm.py                        clientul Groq (ritmare, reîncercări, rezervă între modele)
  fact_checker_api.py           erori logice
  credibility_llm.py            scorul de credibilitate
  orientation_llm.py            orientarea pe 10 axe
  summarize_llm.py              rezumate
  diskcache.py                  cache permanent pe disc
  cache/                        datele salvate (demo: Georgescu, Nicușor Dan)
  test_*.py                     teste
tools/build_quiz.py     regenerează js/quiz.js din fișierul quiz-ului
```

## Endpoint-uri API

`GET http://127.0.0.1:8000/` listează toate endpoint-urile. Cele principale: `/analyze`, `/orientation`, `/factcheck`, `/credibility`, `/summary` (POST), `/cached` (citește doar din cache), `/cache` (ce e salvat), `/methodology`, `/jobs/<id>`.

## Limite cunoscute

- Modelele nu au acces la internet și **nu verifică faptele**: semnalările sunt piste pentru un verificator uman.
- Sursele depind de ce returnează Bing; nu sunt un eșantion reprezentativ al presei.
- Scorul se bazează pe cele mai recente 20 de articole și 3 declarații pe articol.
- Textele articolelor sunt trimise către Groq pentru analiză. Răspunsurile din quiz rămân în browser.
- Educația și venitul declarat afișate în profil provin dintr-un tabel introdus manual, aproximativ și neverificat.

Lista completă a limitelor este în secțiunea 13 a paginii **Metodologie**.

## Dezvoltare

```powershell
.\run.ps1 -Test        # 6 seturi Python + test-scoring.js (acesta din urmă doar dacă ai Node)
```

Backend-ul folosește doar biblioteca standard Python (`requirements.txt` e gol). Dacă modifici fișierul quiz-ului, regenerează `js/quiz.js` cu `python tools/build_quiz.py`.
