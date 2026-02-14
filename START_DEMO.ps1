param()

$ErrorActionPreference = 'Stop'

function Write-Info($msg) { Write-Host $msg -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host $msg -ForegroundColor Green }
function Write-Warn($msg) { Write-Host $msg -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host $msg -ForegroundColor Red }

Write-Host "========================================"
Write-Host "  DEMO AUTOMATICA - Agent 2"
Write-Host "  Consistency & Conflict Analyzer"
Write-Host "========================================"
Write-Host ""
Write-Host "Questa demo avviera' automaticamente:"
Write-Host " 1. Docker con i servizi core (agent2-api + n8n)"
Write-Host " 2. n8n (workflow visuale)"
Write-Host ""
Write-Host "E aprira' automaticamente le pagine web"
Write-Host ""
Read-Host "Premi INVIO per continuare"

function Ensure-DockerReady {
  Write-Info "[CHECK] Verifica Docker CLI..."
  if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Err "Docker non risulta installato o non e' nel PATH."
    Write-Host "Scarica Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
  }

  Write-Info "[CHECK] Verifica stato Docker Engine..."
  & docker info *> $null
  if ($LASTEXITCODE -ne 0) {
    Write-Warn "Docker Desktop non sembra in esecuzione. Provo ad avviarlo..."

    # Tenta avvio servizio backend (se presente)
    try {
      $svc = Get-Service 'com.docker.service' -ErrorAction SilentlyContinue
      if ($svc -and $svc.Status -ne 'Running') {
        Start-Service 'com.docker.service' -ErrorAction SilentlyContinue
      }
    } catch {}

    # Tenta avvio app Desktop dai percorsi noti
    $candidates = @(
      'C:\Program Files\Docker\Docker\Docker Desktop.exe',
      "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
      "$env:ProgramFiles(x86)\Docker\Docker\Docker Desktop.exe",
      "$env:LocalAppData\Docker\Docker Desktop.exe",
      "$env:LocalAppData\Programs\Docker\Docker Desktop.exe"
    )
    $started = $false
    foreach ($p in $candidates) {
      if (Test-Path $p) {
        Write-Info "[INFO] Avvio Docker Desktop: $p"
        Start-Process -FilePath $p | Out-Null
        $started = $true
        break
      }
    }
    if (-not $started) {
      # Fallback: prova avvio per nome applicazione
      try { Start-Process -FilePath 'Docker Desktop' -ErrorAction SilentlyContinue | Out-Null } catch {}
    }

    Write-Host "Attendo che Docker Desktop sia pronto (max ~300s)..."
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt 300) {
      & docker info *> $null
      if ($LASTEXITCODE -eq 0) { break }
      Start-Sleep -Seconds 3
    }
    if ($LASTEXITCODE -ne 0) {
      Write-Err "Docker non e' pronto dopo 300 secondi. Apri Docker Desktop manualmente e riprova."
      exit 1
    }
  }
  Write-Ok "[OK] Docker Desktop attivo"
}

Ensure-DockerReady

$useComposeV2 = $false
& docker compose version *> $null
if ($LASTEXITCODE -eq 0) { $useComposeV2 = $true }
if (-not $useComposeV2) {
  & docker-compose version *> $null
  if ($LASTEXITCODE -ne 0) { Write-Err "Ne' 'docker compose' ne' 'docker-compose' sono disponibili."; exit 1 }
}
Write-Info ("[CHECK] Comando compose: {0}" -f ($useComposeV2 ? 'docker compose' : 'docker-compose'))

# Crea .env se manca
if (-not (Test-Path ".env")) {
  Write-Info "[1/5] Creazione file .env da template..."
  Copy-Item .env.docker .env -Force
  Write-Ok "OK File .env creato"
}

Write-Info "[2/5] Build immagini Docker..."
if ($useComposeV2) { & docker compose build } else { & docker-compose build }
if ($LASTEXITCODE -ne 0) { Write-Err "Errore durante il build"; exit 1 }

Write-Host ""
Write-Info "[3/5] Avvio servizi core (agent2-api + n8n)..."

# Se n8n e' gia' attivo localmente (porta 5678), riusalo e non avviare il servizio n8n dello stack
$useExternalN8n = $false
try {
  $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:5678' -UseBasicParsing -TimeoutSec 2
  if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) { $useExternalN8n = $true }
} catch {}

if ($useExternalN8n) {
  Write-Warn "n8n e' gia' in esecuzione su 127.0.0.1:5678. Uso quello esterno e non avvio il servizio n8n del compose."
  $services = @('agent2-api')
  if ($useComposeV2) { & docker compose up -d @services } else { & docker-compose up -d @services }
} else {
  if ($useComposeV2) { & docker compose up -d } else { & docker-compose up -d }
}
if ($LASTEXITCODE -ne 0) { Write-Err "Errore durante l'avvio"; exit 1 }

Write-Host ""
Write-Info "[4/5] Attesa inizializzazione servizi..."
Write-Host "Attendo 20 secondi per il startup completo..."
Start-Sleep -Seconds 20

Write-Host ""
Write-Info "[5/5] Verifica health status..."
if ($useComposeV2) { & docker compose ps } else { & docker-compose ps }

Write-Host ""
Write-Info "Apertura pagine web..."
Start-Sleep -Seconds 5
Start-Process 'http://127.0.0.1:5678'
Start-Sleep -Seconds 2
Start-Process 'http://localhost:8002/docs'

Write-Host ""
Write-Host "========================================"
Write-Ok   "OK Demo avviata con successo!"
Write-Host "========================================"
Write-Host ""
Write-Host "Pagine aperte nel browser:"
Write-Host "  1. n8n Workflow:     http://127.0.0.1:5678"
Write-Host "  2. API Docs:         http://localhost:8002/docs"
Write-Host ""
Write-Host "Servizi attivi:"
Write-Host "  - Agent 2 API:       http://localhost:8002"
Write-Host "  - Health Check:      http://localhost:8002/health"
Write-Host ""
Write-Host "========================================"
Write-Host "PROSSIMI PASSI:"
Write-Host "========================================"
Write-Host ""
Write-Host "1. In n8n (http://127.0.0.1:5678):"
Write-Host "   - Se prima volta: crea account (email/password)"
Write-Host "   - Workflows > Import from File"
Write-Host "   - Seleziona: n8n/workflow_complete_loop.json"
Write-Host "   - Attiva il workflow (toggle verde)"
Write-Host "   - Apri: http://127.0.0.1:5678/webhook/agent2-start"
Write-Host ""
Write-Host "2. Per testare Agent 2:"
Write-Host "   - Usa il workflow n8n (interfaccia visuale)"
Write-Host "   - Oppure: docker exec -it agent2-api curl http://localhost:8002/health"
Write-Host ""
Write-Host "3. Per attivare anche Kafka (implementazione futura):"
Write-Host "   - docker compose -f docker-compose.yml -f docker-compose.kafka.yml up -d --build"
Write-Host ""
Read-Host "Premi INVIO per uscire"
