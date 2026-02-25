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
Write-Host " 1. Ollama (LLM locale per analisi)"
Write-Host " 2. Docker con i servizi core (agent2-api + n8n)"
Write-Host " 3. n8n (workflow visuale)"
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

# ── Ensure Ollama is running on the host ──────────────────────────────────
function Ensure-OllamaReady {
  Write-Info "[CHECK] Verifica Ollama..."

  $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
  if (-not $ollamaCmd) {
    # Cerca nei percorsi comuni di Windows
    $candidates = @(
      "$env:LocalAppData\Programs\Ollama\ollama.exe",
      "$env:ProgramFiles\Ollama\ollama.exe",
      "C:\Users\$env:USERNAME\AppData\Local\Programs\Ollama\ollama.exe"
    )
    foreach ($p in $candidates) {
      if (Test-Path $p) { $ollamaCmd = $p; break }
    }
  }

  if (-not $ollamaCmd) {
    Write-Err "Ollama non trovato. Scaricalo da https://ollama.com/download"
    Write-Err "Senza Ollama il sistema non puo' interpretare le risposte e il loop non si risolve."
    exit 1
  }

  # Verifica se Ollama e' raggiungibile
  $ollamaReady = $false
  try {
    $r = Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -UseBasicParsing -TimeoutSec 3
    if ($r.StatusCode -eq 200) { $ollamaReady = $true }
  } catch {}

  if (-not $ollamaReady) {
    Write-Warn "Ollama non e' in esecuzione. Provo ad avviarlo..."
    Start-Process -FilePath 'ollama' -ArgumentList 'serve' -WindowStyle Hidden
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt 30) {
      Start-Sleep -Seconds 2
      try {
        $r = Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $ollamaReady = $true; break }
      } catch {}
      Write-Host "." -NoNewline
    }
    Write-Host ""
    if (-not $ollamaReady) {
      Write-Err "Ollama non si e' avviato dopo 30 secondi. Avvialo manualmente con: ollama serve"
      exit 1
    }
  }
  Write-Ok "[OK] Ollama attivo su localhost:11434"

  # Leggi il modello configurato da .env (o usa il default del docker-compose)
  $model = "qwen2.5:14b"
  if (Test-Path ".env") {
    $envLine = Get-Content ".env" | Where-Object { $_ -match "^OLLAMA_MODEL=" }
    if ($envLine) { $model = ($envLine -split "=", 2)[1].Trim() }
  }

  # Verifica se il modello e' scaricato
  Write-Info "[CHECK] Verifica modello '$model'..."
  try {
    $tags = (Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -UseBasicParsing -TimeoutSec 5).Content | ConvertFrom-Json
    $found = $tags.models | Where-Object { $_.name -eq $model -or $_.name -eq "$model`:latest" -or $_.name.StartsWith("$model`:") }
    if (-not $found) {
      Write-Warn "Modello '$model' non trovato. Lo scarico (puo' richiedere qualche minuto)..."
      & ollama pull $model
      if ($LASTEXITCODE -ne 0) {
        Write-Err "Errore durante il download del modello '$model'."
        exit 1
      }
    }
  } catch {
    Write-Warn "Non riesco a verificare i modelli Ollama, continuo comunque..."
  }
  Write-Ok "[OK] Modello '$model' disponibile"
}

Ensure-OllamaReady

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
  Write-Info "[1/6] Creazione file .env da template..."
  Copy-Item .env.docker .env -Force
  Write-Ok "OK File .env creato"
}

# Build immagine (sempre rebuild per avere codice aggiornato; Docker cache rende veloce se nulla e' cambiato)
Write-Info "[2/6] Build immagine Docker (la cache Docker salta i layer invariati)..."
if ($useComposeV2) { & docker compose build } else { & docker-compose build }
if ($LASTEXITCODE -ne 0) { Write-Err "Errore durante il build"; exit 1 }

Write-Host ""
Write-Info "[3/6] Avvio servizi core (agent2-api + n8n)..."

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
Write-Info "[4/6] Attesa inizializzazione servizi..."

# Polling attivo su agent2-api /health invece di sleep fisso
$maxWait = 120
$sw = [Diagnostics.Stopwatch]::StartNew()
$apiReady = $false
while ($sw.Elapsed.TotalSeconds -lt $maxWait) {
  try {
    $r = Invoke-WebRequest -Uri 'http://localhost:8002/health' -UseBasicParsing -TimeoutSec 3
    if ($r.StatusCode -eq 200) { $apiReady = $true; break }
  } catch {}
  Write-Host "." -NoNewline
  Start-Sleep -Seconds 3
}
Write-Host ""
if ($apiReady) {
  Write-Ok "[OK] Agent2 API pronta in $([math]::Round($sw.Elapsed.TotalSeconds))s"
} else {
  Write-Warn "Agent2 API non risponde dopo ${maxWait}s, potrebbe essere ancora in avvio (download modello embeddings al primo run)"
}

Write-Host ""
Write-Info "[5/6] Verifica health status..."
if ($useComposeV2) { & docker compose ps } else { & docker-compose ps }

# Attendi che n8n sia pronto (non solo agent2-api)
if (-not $useExternalN8n) {
  Write-Host ""
  Write-Info "Attesa avvio n8n (porta 5678)..."
  $n8nReady = $false
  $sw2 = [Diagnostics.Stopwatch]::StartNew()
  while ($sw2.Elapsed.TotalSeconds -lt 120) {
    try {
      $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5678/healthz' -UseBasicParsing -TimeoutSec 3
      if ($r.StatusCode -eq 200) { $n8nReady = $true; break }
    } catch {}
    Write-Host "." -NoNewline
    Start-Sleep -Seconds 2
  }
  Write-Host ""
  if ($n8nReady) {
    Write-Ok "[OK] n8n pronto in $([math]::Round($sw2.Elapsed.TotalSeconds))s"
  } else {
    Write-Warn "n8n non risponde dopo 120s, apro il browser comunque..."
  }
}

# ── Auto-import workflow n8n (sempre aggiornato dal file su disco) ──────────
if (-not $useExternalN8n -and $n8nReady) {
  Write-Host ""
  Write-Info "Importo automaticamente il workflow n8n..."
  $n8nApiBase = 'http://127.0.0.1:5678/api/v1'
  $n8nApiKey  = 'agent2-api-key-12345'
  $wfFile     = Join-Path $PSScriptRoot 'n8n\workflow_complete_loop.json'
  $n8nHeaders = @{ 'X-N8N-API-KEY' = $n8nApiKey }

  try {
    $wfBody = Get-Content $wfFile -Raw -Encoding UTF8
    $wfName = ($wfBody | ConvertFrom-Json -ErrorAction Stop).name

    # Lista workflow esistenti
    $listResp = Invoke-RestMethod -Uri "$n8nApiBase/workflows?limit=100" `
      -Headers $n8nHeaders -UseBasicParsing -ErrorAction Stop
    $existing = $listResp.data | Where-Object { $_.name -eq $wfName } | Select-Object -First 1

    if ($existing) {
      # Aggiorna workflow esistente
      $wfId = $existing.id
      Invoke-RestMethod -Uri "$n8nApiBase/workflows/$wfId" -Method PUT `
        -Headers $n8nHeaders -Body $wfBody `
        -ContentType 'application/json; charset=utf-8' `
        -UseBasicParsing -ErrorAction Stop | Out-Null
      Write-Ok "[OK] Workflow aggiornato: '$wfName' (id=$wfId)"
    } else {
      # Crea nuovo workflow
      $created = Invoke-RestMethod -Uri "$n8nApiBase/workflows" -Method POST `
        -Headers $n8nHeaders -Body $wfBody `
        -ContentType 'application/json; charset=utf-8' `
        -UseBasicParsing -ErrorAction Stop
      $wfId = $created.id
      Write-Ok "[OK] Workflow creato: '$wfName' (id=$wfId)"
    }

    # Attiva il workflow
    Invoke-RestMethod -Uri "$n8nApiBase/workflows/$wfId/activate" -Method POST `
      -Headers $n8nHeaders -UseBasicParsing -ErrorAction Stop | Out-Null
    Write-Ok "[OK] Workflow attivato -> apri: http://127.0.0.1:5678/webhook/agent2-start"

  } catch {
    Write-Warn "Import automatico workflow fallito: $($_.Exception.Message)"
    Write-Host "  >> Importa manualmente in n8n: Workflows > Import from File > n8n/workflow_complete_loop.json"
    Write-Host "  >> Attiva il workflow (toggle verde in alto a destra)"
  }
}

Write-Host ""
Write-Info "[6/6] Apertura pagine web..."
Start-Process 'http://127.0.0.1:5678'
Start-Sleep -Seconds 1
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
Write-Host "1. Avvia l'analisi DDD:"
Write-Host "   - Apri: http://127.0.0.1:5678/webhook/agent2-start"
Write-Host "   - Il workflow e' gia' importato e attivo automaticamente"
Write-Host "   - (Se prima volta su n8n: potresti dover creare un account)"
Write-Host ""
Write-Host "2. Per testare Agent 2:"
Write-Host "   - Usa il workflow n8n (interfaccia visuale)"
Write-Host "   - Oppure: docker exec -it agent2-api curl http://localhost:8002/health"
Write-Host ""
Write-Host "3. Per attivare anche Kafka (implementazione futura):"
Write-Host "   - Spostare i file da future_implementations/ alla root (vedi future_implementations/README.md)"
Write-Host "   - docker compose -f docker-compose.yml -f docker-compose.kafka.yml up -d --build"
Write-Host ""
Read-Host "Premi INVIO per spegnere tutto e uscire"

Write-Host ""
Write-Host "========================================"
Write-Info "Spegnimento in corso..."
Write-Host "========================================"

# 1. Ferma i container Docker
Write-Info "[STOP] Arresto container Docker..."
if ($useComposeV2) { & docker compose down } else { & docker-compose down }
if ($LASTEXITCODE -eq 0) {
  Write-Ok "[OK] Container Docker fermati"
} else {
  Write-Warn "Problema durante l'arresto dei container"
}

# 2. Ferma Ollama (se avviato da questo script)
Write-Info "[STOP] Arresto Ollama..."
$ollamaProc = Get-Process -Name 'ollama' -ErrorAction SilentlyContinue
if ($ollamaProc) {
  Stop-Process -Name 'ollama' -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 2
  $still = Get-Process -Name 'ollama' -ErrorAction SilentlyContinue
  if (-not $still) {
    Write-Ok "[OK] Ollama fermato"
  } else {
    Write-Warn "Ollama potrebbe essere ancora in esecuzione"
  }
} else {
  Write-Ok "[OK] Ollama non era in esecuzione"
}

Write-Host ""
Write-Ok "Tutto spento. Arrivederci!"
