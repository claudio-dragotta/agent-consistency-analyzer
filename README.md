# Agent 2 — Consistency & Conflict Analyzer

Validatore intelligente per modelli Domain‑Driven Design (DDD). Analizza la coerenza semantica, rileva conflitti tra bounded context, verifica la correttezza dell’architettura event‑driven, genera domande di follow‑up e produce un modello raffinato pronto per Agent 3 (generazione specifiche).

## Panoramica Ecosistema

- Pipeline: Agent 1 (Domain Interviewer) → Agent 2 (Consistency & Conflict Analyzer) → Agent 3 (Specification Generator).
- Ingresso Agent 2:
  - REST: `POST /analyze` con `domain_model` (demo/locale).
  - Kafka: topic input `agent1-output` (produzione).
- Uscita Agent 2:
  - Kafka: topic output `agent2-output` (consumato da Agent 3).
  - File: salvataggio risultati in `output_agent/` nel container.
- Endpoint chiave Agent 2: `/health`, `/.well-known/agent.json`, `/analyze`, A2A (`/a2a/message/send`, `/a2a/tasks`).
- Strumenti: n8n (http://127.0.0.1:5678), Kafka UI (http://localhost:8080), API Docs (http://localhost:8002/docs).

## Quick Start (2 minuti)

### 1) Prerequisiti
- Docker Desktop installato.
- Ollama con modello `llama3` scaricato: `ollama pull llama3`.
- Facoltativo: Python 3.11 per esecuzione senza Docker.

### 2) Avvio Demo (unico script PowerShell)
- Apri PowerShell e lancia:
  - `cd C:\Users\TUO_USERNAME\Desktop\agent-consistency-analyzer`
  - `powershell -ExecutionPolicy Bypass -File .\START_DEMO.ps1`

Lo script verifica/avvia Docker Desktop, seleziona automaticamente `docker compose`/`docker-compose`, avvia lo stack e apre le pagine.

Pagine utili:
- n8n: http://127.0.0.1:5678
- Kafka UI: http://localhost:8080
- API Docs: http://localhost:8002/docs

### 3) Demo in n8n
- Primo accesso: crea account.
- Importa workflow da file: Workflows → Import from File.
  - `n8n/workflow_demo_simple.json` → esecuzione singola, più semplice.
  - `n8n/workflow_complete_loop.json` → loop interattivo con domande/risposte.
- Avvio:
  - Demo semplice: premi “Execute Workflow” e osserva i risultati.
  - Loop interattivo: attiva il workflow (toggle verde) e apri http://127.0.0.1:5678/webhook/agent2-start.

Nota Webhook n8n:
- URL “test” (`/webhook-test/...`) funziona solo dopo “Execute Workflow” ed è valido per una sola richiesta.
- URL “prod” (`/webhook/...`) richiede il workflow ATTIVO. L’errore 404 “requested webhook … not registered” indica che non è attivo o non sei in test mode.

## Cosa fa Agent 2

- Input: modello funzionale (JSON) da Agent 1.
- Processo:
  - Regole DDD e checklist dalla knowledge base.
  - Analisi semantica (embeddings) per overlap/ambiguità.
  - Rilevazione conflitti (regole + LLM con Ollama/Llama3).
  - Validazioni EDA (naming eventi, single‑emitter, payload minimo).
  - Auto‑fix per violazioni semplici e generazione domande di follow‑up.
- Output:
  - Report dettagliato per categoria e severità.
  - Domande prioritarie e suggerimenti.
  - Modello raffinato con metadati pronto per Agent 3.

## API REST principali

- `GET /` — info agente ed elenco endpoint.
- `GET /health` — stato servizi e configurazione.
- `GET /.well-known/agent.json` — Agent Card (A2A Protocol).
- `POST /analyze` — analizza un modello e restituisce report + modello raffinato.

Esempio `POST /analyze`:

```json
{
  "domain_model": { "..." },
  "use_llm": true,
  "apply_auto_fixes": true,
  "previous_answers": { "FUQ-001": "risposta utente opzionale" }
}
```

Endpoint A2A per orchestrazione fra agenti:
- `POST /a2a/message/send`
- `GET /a2a/tasks`, `GET /a2a/tasks/{task_id}`, `POST /a2a/tasks/{task_id}/cancel`

Endpoint locali per test/file picker (usati dal workflow con fallback se manca il modello in ingresso):
- `GET /source/files` — elenco dei JSON in `input_agent`.
- `GET /source/file?name=...` — contenuto del file richiesto.
- `POST /source/analyze-by-file` — analizza un file per nome.

## Workflow n8n

### `n8n/workflow_demo_simple.json`
- Quando: primo utilizzo, demo rapide, debug.
- Caratteristiche: trigger manuale, input demo incorporato.

### `n8n/workflow_complete_loop.json`
- Quando: flusso interattivo reale, integrazione con Agent 1/3.
- Caratteristiche: trigger Webhook, form HTML per le risposte, safety limit max 5 iterazioni.
- Flusso: “Invio modello → Analisi → Domande → Risposte → Raffinamento → Ripeti finché valido”.
- URL ANALIZZA preconfigurato per Docker Compose: `http://agent2-api:8002/analyze` (via env `AGENT2_API_URL`).
- Se non passi `domain_model`, il workflow mostra una pagina “Seleziona Modello” che legge l’elenco da `http://localhost:8002/source/files` e prosegue automaticamente dopo la scelta.

## Integrazione Kafka

- Consumer avanzato: `app/kafka/consumer_advanced.py` (processi paralleli, invio ad Agent 3).
- Producer risultati: `app/kafka/producer.py` (topic output).
- Topic predefiniti: input `agent1-output`, output `agent2-output` (configurabili via env).
- Kafka UI: monitoraggio messaggi e topic.

## Configurazione

- File `.env.example` (locale) e `.env.docker` (Docker):
  - Ollama: `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT`.
  - Kafka: `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_INPUT_TOPIC`, `KAFKA_OUTPUT_TOPIC`, `KAFKA_GROUP_ID`.
  - API: `API_PORT` (default 8002), `LOG_LEVEL`.
  - Analisi: `EMBEDDINGS_MODEL`, `ENTITY_OVERLAP_THRESHOLD`, `SEMANTIC_SIMILARITY_THRESHOLD`, `MAX_FOLLOW_UP_QUESTIONS`.
- Knowledge base: `knowledge_base/ddd_rules.md`, `knowledge_base/validation_checklist.json`.
- Esempi input: `input_agent/` (guida in `input_agent/README_DEMO.md`).

Esecuzione locale senza Docker:
- `pip install -r requirements.txt`
- `uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload`

## Novità v1.2.0 — Raffinamento Iterativo

- Body `/analyze` esteso con `previous_answers` per passare le risposte dell’utente.
- Applicazione risposte in `ModelRefiner._apply_user_answers()` con 5 handler:
  - `entity_overlap`, `requirement_conflict`, `duplicate_event`, `naming_violation`, `domain_classification`.
- Tracciabilità in `_userGuidedFixes` dentro il modello raffinato.
- Effetto: ad ogni iterazione i problemi diminuiscono fino a `VALID`.

## Struttura progetto (principale)

- `app/main.py` — FastAPI, endpoint REST e A2A, orchestrazione pipeline.
- `app/services/semantic_analyzer.py` — embeddings e similarità (overlap/ambiguità).
- `app/services/conflict_detector.py` — conflitti (regole + LLM via Ollama).
- `app/services/question_generator.py` — generazione domande.
- `app/services/model_refiner.py` — raffinamento modello e report.
- `app/kafka/*` — consumer/producer Kafka.
- `knowledge_base/*` — regole DDD e checklist.
- `n8n/*` — workflow pronti all’uso.
- `Dockerfile`, `docker-compose.yml`, `START_DEMO.ps1` — packaging e demo.

## Info progetto

- Versione: 1.2.0 (vedi `CHANGELOG.md`).
- Stato: Production Ready.
- Ultimo aggiornamento: 2025‑12‑19.
- Licenza: MIT.
- Changelog: `CHANGELOG.md`.

## Troubleshooting rapido

- Webhook 404: attiva il workflow (toggle verde) oppure usa “Execute Workflow” e chiama l’URL “test”.
- Porta 5678 occupata: lo script riusa n8n esterno se già in esecuzione; altrimenti arresta il container esterno o libera la porta.
- Docker non parte: apri manualmente Docker Desktop, poi rilancia `START_DEMO.ps1`.
- Analisi lenta: imposta `use_llm=false` in `/analyze`.

Buon lavoro con Agent 2!

**Blocchi Workflow (Complete Loop)**
- START – Webhook Principale
  - Tipo: `Webhook` (POST), path `agent2-start`, `responseMode=responseNode`.
  - Input: `domain_model?`, `session_id?`, `iteration?`, `previous_answers?`, `max_iterations?`.
  - Note: per l’URL produzione usa `/webhook/agent2-start` con workflow attivo; in test usa `/webhook-test/...` dopo “Execute Workflow”.
- Prepara Dati
  - Tipo: `Set`.
  - Imposta: `iteration=0` se assente; `max_iterations=5`; `session_id` default ISO now; `domain_model` da `$json.body.domain_model || $json.domain_model` (stringificato); `previous_answers` da `$json.body.answers || {}`.
  - Output: normalizza i campi per i nodi successivi.
- Modello Presente?
  - Tipo: `IF`.
  - Condizione: il `domain_model` è valorizzato? Se no → “Seleziona Modello”.
- Seleziona Modello
  - Tipo: `Respond to Webhook` (HTML).
  - Cosa fa: mostra lista dei file da `GET http://localhost:8002/source/files`; al click legge `GET /source/file?name=...` e re‑POSTa a `/webhook/agent2-start` con `domain_model` scelto.
- Max Iterazioni?
  - Tipo: `IF`.
  - Condizione: `iteration < max_iterations`. Se false → “Pagina Successo” (stop di sicurezza).
- ANALIZZA (iterativa)
  - Tipo: `HTTP Request` POST.
  - URL: `={{ $env.AGENT2_API_URL || 'http://host.docker.internal:8002' }}/analyze`.
  - Body: `domain_model` (JSON), `use_llm=true`, `apply_auto_fixes=true`, `previous_answers` (se presenti).
  - Output: risposta dell’API con `status`, `summary`, `follow_up_questions`, `refined_model`.
- Combina Risultati con Contesto
  - Tipo: `Function/Set`.
  - Cosa fa: incrementa `iteration`, aggiorna `domain_model` con `refined_model`, serializza `summary`/`follow_up_questions` per il form.
- Modello Valido?
  - Tipo: `IF`.
  - Condizione: `status === 'VALID'`. Se true → “Pagina Successo”, altrimenti → “Form Domande HTML”.
- Form Domande HTML
  - Tipo: `Respond to Webhook` (HTML form).
  - Cosa fa: visualizza le domande con severità, raccoglie le risposte e le invia a `/webhook/agent2-start` per l’iterazione successiva.
- Pagina Successo
  - Tipo: `Respond to Webhook`.
  - Cosa fa: mostra riepilogo finale (conteggi, stato) e termina il flusso.
