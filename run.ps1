<#
.SYNOPSIS
  Porneste tot proiectul (API + site) cu o singura comanda si instaleaza ce lipseste.

.DESCRIPTION
  PoliticieniRO: profiluri de politicieni si partide cu orientare pe 10 axe, stiri, rezumate AI, erori logice si scor de credibilitate.

  Pornire:    .\run.ps1          (sau dublu-click pe run.cmd)
  Se opreste: Enter in aceasta fereastra (sau Ctrl+C).

  Ce face:
    1. gaseste Python 3.9+ (daca lipseste, il instaleaza cu winget);
    2. instaleaza pachetele din requirements.txt (acum nu sunt necesare: doar biblioteca standard);
    3. cere o singura data cheia Groq, daca nu exista (fara cheie, datele deja salvate in api\cache se vad, dar nu se genereaza altele);
    4. porneste API-ul (http://127.0.0.1:8000) si site-ul (http://127.0.0.1:8080) si deschide browserul.

  Datele de demo (Calin Georgescu) sunt in api\cache si se deschid instant, fara cheie.

.PARAMETER Port       Portul site-ului (implicit 8080).
.PARAMETER ApiPort    Portul API-ului (implicit 8000; site-ul il asteapta pe 8000).
.PARAMETER NoBrowser  Nu deschide browserul.
.PARAMETER NoWait     Porneste serverele si iese, lasandu-le pornite (le opresti cu .\run.ps1 -Stop).
.PARAMETER Stop       Opreste serverele pornite anterior.
.PARAMETER Test       Ruleaza testele automate si iese.
.PARAMETER SkipKeyPrompt  Nu intreba de cheia Groq.
#>
[CmdletBinding()]
param(
    [int]$Port = 8080,
    [int]$ApiPort = 8000,
    [switch]$NoBrowser,
    [switch]$NoWait,
    [switch]$Stop,
    [switch]$Test,
    [switch]$SkipKeyPrompt
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Api = Join-Path $Root "api"
$Logs = Join-Path $Root "logs"
$KeyFile = Join-Path $Api "groq_key.txt"

function Say($msg, $color = "Gray") { Write-Host $msg -ForegroundColor $color }
function Step($msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }

# ---------------------------------------------------------------- Python
function Test-PythonCmd($exe, $pre) {
    try {
        $out = & $exe @pre -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $out) { return $false }
        $v = [version]($out | Select-Object -First 1)
        return ($v -ge [version]"3.9")
    } catch { return $false }
}

function Find-Python {
    $candidates = @(
        @{ exe = "py";      pre = @("-3") },
        @{ exe = "python";  pre = @() },
        @{ exe = "python3"; pre = @() }
    )
    foreach ($c in $candidates) {
        if (Get-Command $c.exe -ErrorAction SilentlyContinue) {
            if (Test-PythonCmd $c.exe $c.pre) { return $c }
        }
    }
    foreach ($p in (Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe", "$env:ProgramFiles\Python3*\python.exe" -ErrorAction SilentlyContinue)) {
        if (Test-PythonCmd $p.FullName @()) { return @{ exe = $p.FullName; pre = @() } }
    }
    return $null
}

function Update-SessionPath {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}

function Ensure-Python {
    $py = Find-Python
    if ($py) { return $py }
    Say "Python 3.9+ nu a fost gasit. Incerc sa-l instalez cu winget..." "Yellow"
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Python 3.9+ lipseste si winget nu este disponibil. Instaleaza Python de la https://www.python.org/downloads/ (bifeaza 'Add python.exe to PATH'), apoi ruleaza din nou .\run.ps1"
    }
    & winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements | Out-Host
    Update-SessionPath
    $py = Find-Python
    if (-not $py) { throw "Instalarea Python nu a reusit. Instaleaza-l manual de la https://www.python.org/downloads/ si ruleaza din nou .\run.ps1" }
    return $py
}

function Invoke-Py($py, [string[]]$arguments) {
    & $py.exe @($py.pre) @arguments
}

# ---------------------------------------------------------------- porturi / procese
function Stop-ProjectProcesses {
    $names = "promise_tracker_no_ai_v2", "serve_site", "serve-site"
    $procs = Get-CimInstance Win32_Process -Filter "Name like 'python%' or Name = 'py.exe' or Name like 'node%'" -ErrorAction SilentlyContinue |
        Where-Object { $cl = $_.CommandLine; $cl -and ($names | Where-Object { $cl -like "*$_*" }) }
    foreach ($p in $procs) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
    if ($procs) { Start-Sleep -Milliseconds 800 }
}

function Test-PortFree($port) {
    return -not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

# ---------------------------------------------------------------- cheia Groq
function Test-GroqKey($key) {
    try {
        $r = Invoke-RestMethod -Uri "https://api.groq.com/openai/v1/models" -Headers @{ Authorization = "Bearer $key" } -TimeoutSec 15
        return [bool]$r.data
    } catch { return $false }
}

function Ensure-GroqKey {
    if ($env:GROQ_API_KEY) { Say "Cheie Groq: din variabila GROQ_API_KEY." "Green"; return }
    if ((Test-Path $KeyFile) -and ((Get-Content $KeyFile -Raw).Trim())) { Say "Cheie Groq: gasita in api\groq_key.txt." "Green"; return }
    if ($SkipKeyPrompt -or -not [Environment]::UserInteractive) {
        Say "Fara cheie Groq: se vad datele salvate in api\cache, dar nu se pot genera altele. Pune cheia in api\groq_key.txt." "Yellow"
        return
    }
    Say "Pentru a genera analize noi (rezumate, erori logice, credibilitate) e nevoie de o cheie Groq gratuita: https://console.groq.com/keys" "Yellow"
    Say "Poti apasa Enter ca sa sari peste: datele deja salvate (ex. Calin Georgescu) se deschid oricum." "Yellow"
    $secure = Read-Host "Cheie Groq (gsk_...)" -AsSecureString
    $key = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
    if (-not $key) { Say "Sarit peste." "Gray"; return }
    if (Test-GroqKey $key) {
        Set-Content -Path $KeyFile -Value $key -Encoding ASCII
        Say "Cheia este valida si a fost salvata in api\groq_key.txt (fisier exclus din git)." "Green"
    } else {
        Say "Cheia nu a fost acceptata de Groq (sau nu exista conexiune la internet). Nu a fost salvata." "Red"
    }
}

# ---------------------------------------------------------------- principal
Set-Location $Root

if ($Stop) {
    Step "Opresc serverele proiectului"
    Stop-ProjectProcesses
    Say "Oprit." "Green"
    return
}

Step "Python"
$py = Ensure-Python
Say ("Python: " + (Invoke-Py $py @("--version")) + "  (" + $py.exe + ")") "Green"

if ($Test) {
    Step "Teste automate"
    $failed = 0
    $ErrorActionPreference = "Continue"      # PowerShell 5.1 trateaza orice text scris de un program pe stderr ca eroare
    foreach ($t in "test_llm", "test_diskcache", "test_orientation", "test_summaries", "test_credibility", "test_factcheck") {
        Push-Location $Api
        try { $env:PYTHONIOENCODING = "utf-8"; $out = Invoke-Py $py @("$t.py") 2>&1; $code = $LASTEXITCODE } finally { Pop-Location }
        if ($code -eq 0) { Say ("OK    " + $t + "  " + ($out | Select-Object -Last 1)) "Green" } else { $failed++; Say "FAIL  $t" "Red"; $out | Select-Object -Last 8 | Out-Host }
    }
    if (Get-Command node -ErrorAction SilentlyContinue) {
        $out = & node test-scoring.js 2>&1
        if ($LASTEXITCODE -eq 0) { Say "OK    test-scoring.js" "Green" } else { $failed++; Say "FAIL  test-scoring.js" "Red" }
    } else { Say "SKIP  test-scoring.js (Node nu este instalat; e doar pentru testele JS)" "Gray" }
    if ($failed) { exit 1 } else { Say "Toate testele au trecut." "Green"; return }
}

Step "Pachete Python"
$reqFile = Join-Path $Root "requirements.txt"
$reqs = @()
if (Test-Path $reqFile) { $reqs = Get-Content $reqFile | Where-Object { $_.Trim() -and -not $_.Trim().StartsWith("#") } }
if ($reqs.Count -eq 0) {
    Say "Nu sunt necesare pachete externe (doar biblioteca standard Python)." "Green"
} else {
    Invoke-Py $py @("-m", "pip", "install", "--quiet", "--disable-pip-version-check", "-r", $reqFile) | Out-Host
    Say "Pachete instalate: $($reqs -join ', ')" "Green"
}

Step "Cheia Groq"
Ensure-GroqKey

Step "Pornesc serverele"
Stop-ProjectProcesses
if (-not (Test-PortFree $ApiPort)) { throw "Portul $ApiPort este ocupat de alt program. Inchide-l sau ruleaza cu alt port." }
if (-not (Test-PortFree $Port)) { throw "Portul $Port este ocupat de alt program. Ruleaza cu -Port <alt port>." }
if ($ApiPort -ne 8000) { Say "Atentie: site-ul cheama API-ul pe portul 8000 (js\api.js, API_BASE). Cu alt port, schimba si acolo." "Yellow" }
New-Item -ItemType Directory -Force -Path $Logs | Out-Null
$env:PYTHONIOENCODING = "utf-8"

function Start-Bg($name, $workDir, [string[]]$pyArgs) {
    $log = Join-Path $Logs "$name.log"
    $argList = @($py.pre) + @("-u") + $pyArgs
    return Start-Process -FilePath $py.exe -ArgumentList $argList -WorkingDirectory $workDir -WindowStyle Hidden `
        -RedirectStandardOutput $log -RedirectStandardError (Join-Path $Logs "$name.err.log") -PassThru
}
$apiProc = Start-Bg "api" $Api @("promise_tracker_no_ai_v2.py")
$siteProc = Start-Bg "site" $Root @("serve_site.py", "$Port")

$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $h = Invoke-RestMethod -Uri "http://127.0.0.1:$ApiPort/health" -TimeoutSec 2
        Invoke-WebRequest -Uri "http://127.0.0.1:$Port/index.html" -UseBasicParsing -TimeoutSec 2 | Out-Null
        if ($h.ok) { $ready = $true; break }
    } catch { }
}
if (-not $ready) {
    Say "Serverele nu au pornit. Vezi logs\api.err.log si logs\site.err.log:" "Red"
    foreach ($f in "api.err.log", "site.err.log") { $p = Join-Path $Logs $f; if (Test-Path $p) { Get-Content $p -Tail 15 | Out-Host } }
    Stop-ProjectProcesses
    throw "Pornirea a esuat."
}

$url = "http://localhost:$Port/index.html"
Say ""
Say "Gata. Proiectul ruleaza:" "Green"
Say "  Site:  $url"
Say "  API:   http://127.0.0.1:$ApiPort/   (lista de endpoint-uri)"
Say "  Demo:  deschide 'Calin Georgescu' (date salvate, apare instant) sau fa quiz-ul si vezi 'Cu cine semeni'."
Say "  Loguri: $Logs"
if (-not $NoBrowser) { Start-Process $url }

if ($NoWait) { Say "Serverele raman pornite. Opreste-le cu: .\run.ps1 -Stop" "Yellow"; return }

Say ""
Say "Apasa Enter pentru a opri serverele." "Yellow"
try {
    [void](Read-Host)
} finally {
    Say "Opresc serverele..." "Gray"
    foreach ($p in $apiProc, $siteProc) { if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } }
    Stop-ProjectProcesses
}
