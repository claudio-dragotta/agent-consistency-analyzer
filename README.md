# Agent 2 — Consistency & Conflict Analyzer

> Microservizio intelligente per la validazione di modelli Domain-Driven Design.
> Parte della pipeline **Intelligent Domain Architect** (Agent 1 → **Agent 2** → Agent 3).

Agent 2 riceve un domain model JSON, lo analizza per coerenza semantica, rileva conflitti tra bounded context, genera domande di follow-up contestuali tramite LLM e produce un modello raffinato pronto per Agent 3.

---

## Indice

1. [Architettura](#architettura)
2. [Quick Start](#quick-start)
3. [Pipeline di Analisi](#pipeline-di-analisi)
4. [API Reference](#api-reference)
5. [Workflow n8n](#workflow-n8n)
6. [Modello LLM](#modello-llm)
7. [Schema Domain Model](#schema-domain-model)
8. [Struttura Progetto](#struttura-progetto)
9. [Configurazione](#configurazione)
10. [Integrazione Kafka](#integrazione-kafka)
11. [Knowledge Base](#knowledge-base)
12. [Troubleshooting](#troubleshooting)

---

## Architettura

```
                          +-----------------------+
                          |      Agent 1          |
                          | Domain Interviewer    |
                          +----------+------------+
                                     |
                                     | domain_model JSON
                                     v
                          +----------+------------+
                     +--->|  Kafka: agent1-output  |
                     |    +----------+------------+
                     |               |
                     |               v
+--------+     +----+---------------+----+     +--------------------------+
|  n8n   |---->|      Agent 2 API        |---->|  Kafka: agent2-output    |---> Agent 3
| (UI)   |<----|  :8002/analyze          |     +--------------------------+
+--------+     +-------------------------+
                     |
                     | Ollama (mistral:7b)
                     v
               +-----+------+
               |   GPU/CPU   |
               | RTX 4070    |
               +-------------+
```

### Infrastruttura Docker Compose

Lo stack Docker e suddiviso in **due file** per separare i servizi core (usati nel flusso attuale) dai servizi Kafka (predisposti per implementazione futura).

#### Struttura dei file Docker Compose

| File | Servizi | Quando usarlo |
|------|---------|---------------|
| `docker-compose.yml` | agent2-api, n8n | **Sempre** — flusso interattivo REST (default) |
| `docker-compose.kafka.yml` | zookeeper, kafka, agent2-consumer, kafka-ui | **Solo** se si attiva la pipeline automatica Agent1 → Agent2 → Agent3 via Kafka |

**Comandi**:

```bash
# Flusso standard (solo REST): 2 container
docker compose up -d --build

# Flusso completo con Kafka: 6 container
docker compose -f docker-compose.yml -f docker-compose.kafka.yml up -d --build
```

#### Diagramma — Flusso REST (default)

```
┌──────────────────────────────────────────────────┐
│                agent2-network (bridge)             │
│                                                    │
│    ┌────────────┐         ┌──────────┐            │
│    │ agent2-api │◄────────│   n8n    │            │
│    │   :8002    │  HTTP   │  :5678   │            │
│    └─────┬──────┘         └──────────┘            │
│          │ host.docker.internal                    │
└──────────┼─────────────────────────────────────────┘
           ▼
    ┌────────────┐
    │   Ollama   │  (host Windows, accesso diretto GPU)
    │  :11434    │
    └────────────┘
```

#### Diagramma — Flusso completo con Kafka (implementazione futura)

```
┌──────────────────────────────────────────────────────────────────┐
│                     agent2-network (bridge)                       │
│                                                                  │
│  ┌───────────┐    ┌─────────┐    ┌────────────────┐             │
│  │ Zookeeper │◄───│  Kafka  │◄───│ agent2-consumer │             │
│  │   :2181   │    │  :9092  │    │  (N repliche)   │             │
│  └───────────┘    └────┬────┘    └────────────────┘             │
│                        │                                         │
│  ┌───────────┐    ┌────┴─────┐   ┌──────────┐                  │
│  │ Kafka UI  │    │ agent2   │◄──│   n8n    │                   │
│  │   :8080   │    │  -api    │   │  :5678   │                   │
│  └───────────┘    │  :8002   │   └──────────┘                   │
│                   └────┬─────┘                                   │
│                        │ host.docker.internal                    │
└────────────────────────┼─────────────────────────────────────────┘
                         ▼
                  ┌────────────┐
                  │   Ollama   │  (host Windows, accesso diretto GPU)
                  │  :11434    │
                  └────────────┘
```

#### Servizi core (`docker-compose.yml`)

| Servizio | Immagine | Porta | Perche esiste |
|----------|----------|-------|---------------|
| **agent2-api** | Build da `Dockerfile` locale | 8002 | **Cuore dell'applicazione**: FastAPI con 13 endpoint (`/analyze`, `/source/files`, `/health`, A2A). Chiamato da n8n per il loop interattivo e da Agent 1/3 via A2A. Limiti: 2 CPU, 2GB RAM. |
| **n8n** | `n8nio/n8n:latest` | 5678 | **Orchestratore workflow interattivo**: gestisce il loop ricorsivo (scelta file → analisi → form domande → reinvio risposte → ri-analisi fino a VALID). Comunica con agent2-api via HTTP interno (`http://agent2-api:8002`). |

#### Servizi Kafka (`docker-compose.kafka.yml`) — implementazione futura

| Servizio | Immagine | Porta | Perche esiste |
|----------|----------|-------|---------------|
| **Zookeeper** | `confluentinc/cp-zookeeper:7.5.0` | 2181 (interna) | Kafka richiede Zookeeper per coordinare i broker (leader election, metadata dei topic). Non esposto all'esterno — solo Kafka lo contatta. |
| **Kafka** | `confluentinc/cp-kafka:7.5.0` | 9092 (interno), 9093 (host) | **Message broker** per la comunicazione A2A. Agent 1 pubblica su `agent1-output`, Agent 2 consuma e pubblica su `agent2-output` per Agent 3. 4 partizioni per topic, retention 7 giorni. |
| **agent2-consumer** | Stessa immagine di agent2-api | — | **Consumer Kafka parallelo**: ascolta `agent1-output` e processa automaticamente i domain model in arrivo da Agent 1. Usa `use_llm=False` per velocita. Scalabile a N repliche con `CONSUMER_REPLICAS`. Limiti: 4 CPU, 4GB RAM. |
| **kafka-ui** | `provectuslabs/kafka-ui:latest` | 8080 | **Dashboard di monitoraggio**: interfaccia web per ispezionare topic, messaggi, consumer group e lag. Utile per debug. |

> **Perche due file separati?** Nel flusso attuale n8n chiama direttamente `http://agent2-api:8002/analyze` via HTTP. I 4 servizi Kafka (Zookeeper, Kafka, consumer, Kafka UI) sono predisposti per la pipeline automatica Agent 1 → Agent 2 → Agent 3, ma non sono utilizzati nel loop interattivo. Separandoli in `docker-compose.kafka.yml` si risparmiano risorse significative (~6GB RAM, 6 CPU) e si avviano solo 2 container invece di 6.

#### Perche due servizi Agent 2 separati?

`agent2-api` e `agent2-consumer` usano la **stessa immagine Docker** ma con entry point diversi:

- **agent2-api** avvia FastAPI (entry point del Dockerfile) → modalita **sincrona/interattiva** per l'utente che usa n8n o chiama direttamente le API REST
- **agent2-consumer** avvia `python -m app.kafka.consumer_advanced` → modalita **asincrona/batch** per la pipeline automatica Agent1 → Agent2 → Agent3

Questa separazione permette di **scalare indipendentemente**: 1 sola API ma N consumer Kafka in parallelo per gestire picchi di carico.

#### Perche Ollama NON e in Docker?

Ollama gira sull'**host** (macchina Windows) perche ha bisogno di accesso diretto alla GPU (NVIDIA RTX 4070, 8GB VRAM). I container Docker lo raggiungono tramite `host.docker.internal:11434`, alias che Docker Desktop su Windows risolve automaticamente all'IP dell'host.

#### Immagini custom vs prefatte

| Servizio | Tipo immagine | Dettaglio |
|----------|---------------|-----------|
| **agent2-api** | **Custom** (build da `Dockerfile`) | Multi-stage build Python 3.11, installa dipendenze del progetto e lancia FastAPI con Uvicorn. Unica immagine costruita da zero per il nostro caso specifico. |
| **agent2-consumer** | **Custom** (stessa immagine di agent2-api) | Stessa immagine `agent2-consistency-analyzer:latest`, ma con entry point diverso (`python -m app.kafka.consumer_advanced`). |
| **Zookeeper** | Prefatta (`confluentinc/cp-zookeeper:7.5.0`) | Immagine ufficiale Confluent, usata as-is. Configurata solo tramite variabili d'ambiente. |
| **Kafka** | Prefatta (`confluentinc/cp-kafka:7.5.0`) | Immagine ufficiale Confluent, usata as-is. Configurata solo tramite variabili d'ambiente. |
| **n8n** | Prefatta (`n8nio/n8n:latest`) | Immagine ufficiale n8n, usata as-is. I workflow vengono importati manualmente dalla UI. |
| **kafka-ui** | Prefatta (`provectuslabs/kafka-ui:latest`) | Immagine ufficiale Provectus, usata as-is. Nessuna personalizzazione. |

In sintesi: l'unica immagine Docker costruita da noi e quella dell'Agent 2 (`Dockerfile`). Tutti gli altri servizi usano immagini pubbliche configurate esclusivamente tramite variabili d'ambiente, senza alcuna modifica al codice o all'immagine.

#### Variabili d'ambiente condivise

Il blocco YAML anchor `x-common-env: &common-env` in cima al file definisce tutte le variabili una sola volta, poi le inietta in entrambi i servizi Agent 2 con `<<: *common-env`. Ogni variabile ha un default hardcoded (es. `${OLLAMA_MODEL:-mistral:7b}`) sovrascrivibile dal file `.env`.

---

## Quick Start

### Prerequisiti

- **Docker Desktop** installato e in esecuzione
- **Ollama** con modello `mistral:7b`:
  ```bash
  ollama pull mistral:7b
  ```

### Avvio

```powershell
# 1. Clona e entra nella directory
cd agent-consistency-analyzer

# 2. Avvia tutto lo stack
docker compose up -d --build

# 3. Verifica che tutto sia healthy
curl http://localhost:8002/health
```

Oppure usa lo script automatico:
```powershell
powershell -ExecutionPolicy Bypass -File .\START_DEMO.ps1
```

### Pagine utili

| URL | Cosa |
|-----|------|
| http://localhost:8002/docs | Swagger API docs |
| http://localhost:8002/health | Health check |
| http://127.0.0.1:5678 | n8n workflow editor |
| http://127.0.0.1:5678/webhook/agent2-start | Loop interattivo |
| http://localhost:8085 | Kafka UI |

---

## Pipeline di Analisi

Ogni chiamata a `POST /analyze` esegue fino a 5 step in sequenza. Se sono presenti risposte utente da un'iterazione precedente, viene eseguito prima lo **Step 0** di pre-applicazione.

### Step 0 — Pre-applicazione Risposte (solo iterazioni successive)

Quando `/analyze` viene chiamato con `previous_answers` (ovvero dalla seconda iterazione in poi nel loop n8n), le risposte dell'utente vengono **applicate al domain model PRIMA** di eseguire l'analisi.

**Perche prima e non dopo?** Se le risposte venissero applicate dopo l'analisi (come nella v1.x), i problemi gia risolti dall'utente verrebbero rilevati nuovamente, rendendo il loop inutile — il modello verrebbe analizzato N volte in modo identico.

**Cosa fa lo Step 0**:

1. Recupera le domande dell'iterazione precedente da `_followUpQuestions` nel modello
2. Chiama `model_refiner._apply_user_answers()` per interpretare ogni risposta (via LLM o keyword matching) e applicare le modifiche concrete (rename, set_owner, reclassify, ecc.)
3. Rimuove i metadati dell'iterazione precedente (`_validationAnnotations`, `_followUpQuestions`) per partire puliti

### Step 1 — Analisi Semantica (Embeddings)

**Servizio**: `semantic_analyzer.py`

Usa il modello `all-MiniLM-L6-v2` (sentence-transformers) per calcolare similarita semantica tra entita e concetti.

**Rileva**:
- **ENTITY_OVERLAP** — stessa entita in piu bounded context senza differenziazione
- **SEMANTIC_AMBIGUITY** — termini con significati diversi nello stesso contesto

**Filtraggio intelligente**: le entita marcate `_referenceOnly` (ovvero gia assegnate a un owner dallo Step 0) vengono **escluse** dall'analisi. Inoltre, gli issue i cui `affected_elements` sono gia presenti in `_userGuidedFixes` o `_ownershipDecisions` vengono scartati automaticamente, evitando di riproporre problemi gia risolti dall'utente.

**Soglie configurabili**:
- `ENTITY_OVERLAP_THRESHOLD`: 0.85 (default)
- `SEMANTIC_SIMILARITY_THRESHOLD`: 0.75 (default)

### Step 2 — Conflict Detection (Regole + LLM)

**Servizio**: `conflict_detector.py`

Applica 23 regole DDD dalla knowledge base + analisi LLM per rilevamento approfondito.

**Rileva**:
- **REQUIREMENT_CONFLICT** — requisiti che si contraddicono (es. immutabile vs modificabile)
- **DUPLICATE_EVENT** — stesso evento emesso da piu domini
- **NAMING_VIOLATION** — eventi non al passato (es. `CreateOrder` anziche `OrderCreated`)
- **INCOMPATIBLE_PATTERN** — pattern sincrono richiesto ma comunicazione solo asincrona
- **MISCLASSIFIED_DOMAIN** — dominio Core che dovrebbe essere Generic/Supporting

**Filtraggio intelligente**: come per lo Step 1, gli issue con `affected_elements` gia presenti in `_conflictResolutions`, `_userGuidedFixes` o `_ownershipDecisions` vengono filtrati per non ripetere problemi gia risolti.

### Step 3 — Generazione Domande (LLM-first)

**Servizio**: `question_generator.py`

**Approccio LLM-first** (v2.0): quando `use_llm=true`, TUTTE le domande vengono generate da Mistral in una singola chiamata. Il LLM riceve tutti gli issue e produce domande **specifiche** con nomi reali e risposte suggerite azionabili.

**Esempio output LLM**:
```
Domanda: "Come gestire l'ownership di 'Product' tra CatalogContext e OrderContext?"
Risposte suggerite:
  1. "Assegnare ownership di Product a CatalogContext e usare ProductRef in OrderContext"
  2. "Rinominare Product in CatalogProduct e OrderProduct per distinguere i ruoli"
  3. "Consolidare in un unico bounded context con mapping esplicito"
```

**Fallback**: se il LLM fallisce (timeout, JSON malformato), usa template dalla `validation_checklist.json`.

### Step 4 — Raffinamento Modello (LLM-interpreted)

**Servizio**: `model_refiner.py`

**Auto-fix** per problemi semplici (naming violations → conversione al passato).

**LLM-interpreted answers** (v2.0): quando l'utente risponde alle domande, il LLM interpreta ogni risposta e applica modifiche concrete al modello:

| Azione LLM | Cosa fa |
|-------------|---------|
| `rename_event` | Rinomina l'evento nel modello |
| `set_owner` | Assegna ownership e sostituisce l'entita nei contesti non-owner con riferimento |
| `reclassify_domain` | Sposta il dominio tra core/supporting/generic |
| `resolve_conflict` | Registra la risoluzione del conflitto |
| `add_mapping` | Aggiunge un mapping anti-corruption layer |
| `update_pattern` | Aggiorna il pattern di integrazione |

### Stima Dinamica delle Iterazioni

Dopo i 4 step di analisi, Agent 2 stima quante iterazioni del loop saranno necessarie per portare il modello allo stato VALID. Il valore viene restituito nel campo `suggested_max_iterations` della risposta `/analyze`.

**Strategia a due livelli**:

1. **LLM (prioritario)**: se Ollama e raggiungibile, Mistral riceve un riepilogo dei problemi trovati (quantita, severita, tipologia) e restituisce un numero intero tra 1 e 10. Viene usato con `temperature: 0.1` per massima determinismo.

2. **Euristica (fallback)**: se l'LLM non e disponibile o restituisce un valore non valido, viene applicata una formula basata sulla quantita e severita dei problemi:

| Problemi manuali | Issue HIGH | Iterazioni stimate |
| ------------------ | ------------ | --------------------- |
| 0 | — | 1 |
| 1 | — | 1 |
| 2-3 | — | 2 |
| 4-5 | — | 3 |
| 6+ | >= 3 | min(N, 7) |
| qualsiasi | — | 5 (default) |

**Come viene usato nel workflow n8n (v2.0 aggiornato)**:

- `suggested_max_iterations` viene riletto a **ogni iterazione** nel nodo "Combina Risultati" (non solo al primo giro).
- Il valore viene trasformato in un limite **adattivo**: `max_iterations` viene esteso dinamicamente in base alla stima piu recente.
- Il check "Max Iterazioni?" e trattato come **soft cap**: se il contatore raggiunge il limite, "Prepara Dati" lo incrementa automaticamente (`max_iterations = iteration + 1`) e il loop continua.
- Risultato pratico: il workflow non si blocca prematuramente con problemi ancora aperti; continua fino a `status=VALID` (o intervento manuale esterno).

---

## API Reference

### Endpoints principali

#### `GET /health`
Stato dei servizi e configurazione.
```json
{
  "status": "healthy",
  "services": {
    "semantic_analyzer": true,
    "conflict_detector": true,
    "question_generator": true,
    "model_refiner": true
  },
  "config": {
    "llm_model": "mistral:7b",
    "embeddings_model": "all-MiniLM-L6-v2"
  }
}
```

#### `POST /analyze`
Analisi completa del domain model.

**Request**:
```json
{
  "domain_model": { "..." },
  "use_llm": true,
  "apply_auto_fixes": true,
  "previous_answers": { "q0": "risposta utente", "q1": "altra risposta" }
}
```

**Response**:
```json
{
  "status": "ISSUES_FOUND",
  "task_id": "uuid",
  "summary": {
    "total_issues": 6,
    "entity_overlaps": 1,
    "semantic_ambiguities": 1,
    "requirement_conflicts": 1,
    "duplicate_events": 2,
    "naming_violations": 0,
    "incompatible_patterns": 0,
    "misclassified_domains": 1,
    "auto_fixed": 0,
    "requires_manual": 6
  },
  "follow_up_questions": [
    {
      "question_id": "FUQ-001",
      "question": "Come gestire l'ownership di 'Product' tra CatalogContext e OrderContext?",
      "severity": "HIGH",
      "related_issue_type": "ENTITY_OVERLAP",
      "suggested_answers": [
        "Assegnare ownership a CatalogContext e usare ProductRef in OrderContext",
        "Rinominare in CatalogProduct e OrderProduct",
        "Consolidare in un unico bounded context"
      ]
    }
  ],
  "refined_model": { "...modello con fix e annotazioni..." },
  "refinement_report": {
    "total_issues": 6,
    "auto_fixed": 0,
    "requires_manual": 6,
    "refinements": []
  },
  "suggested_max_iterations": 3
}
```

### Endpoints file locali (test)

| Metodo | Path | Descrizione |
|--------|------|-------------|
| `GET` | `/source/files` | Lista JSON in `input_agent/` |
| `GET` | `/source/file?name=example_demo.json` | Contenuto file |
| `POST` | `/source/analyze-by-file` | Analizza per nome file |

### Endpoints A2A Protocol

| Metodo | Path | Descrizione |
|--------|------|-------------|
| `GET` | `/.well-known/agent.json` | Agent Card |
| `POST` | `/a2a/message/send` | Invia messaggio (trigger analisi) |
| `GET` | `/a2a/tasks` | Lista task |
| `GET` | `/a2a/tasks/{task_id}` | Stato task |
| `POST` | `/a2a/tasks/{task_id}/cancel` | Cancella task |

---

## Workflow n8n

### `workflow_complete_loop.json` — Loop Interattivo

Workflow principale con 17 nodi. Gestisce l'intero ciclo di vita dell'analisi:

```
Browser GET /webhook/agent2-start
    |
    v
[Pagina Scelta] --> File Locale? --> [Lista File] --> Selezione
    |                                                     |
    v                                                     v
[Prepara Dati] <------------------------------------------+
    |
    v
[Max Iterazioni?] --(soft cap adattivo)--> [POST /analyze] --> [Combina Risultati]
    |
    v
[Modello Valido?] --SI--> [Pagina Successo]
    |
    NO
    v
[Form Domande HTML] --> Utente risponde --> [POST /webhook/agent2-submit]
    |                                              |
    +----------------------------------------------+
    (loop fino a VALID, con limite adattivo)
```

**Nodi chiave**:

| Nodo | Tipo | Funzione |
|------|------|----------|
| START | Webhook GET | Pagina iniziale nel browser |
| SUBMIT | Webhook POST | Riceve tutte le form submissions |
| Detect Request Type | Code | Classifica la richiesta (file/answers/initial) |
| Prepara Dati | Code | Normalizza iteration/sessione e applica soft cap (`max_iterations` si auto-estende quando raggiunto) |
| Analizza Modello | HTTP Request | `POST http://agent2-api:8002/analyze` |
| Combina Risultati | Code | Pre-renderizza HTML domande e aggiorna `max_iterations` usando l'ultima `suggested_max_iterations` |
| Form Domande | Respond to Webhook | Mostra domande con radio buttons + testo libero |
| Pagina Successo | Respond to Webhook | Risultato finale quando `status=VALID` |

### Esiti finali del loop

Il loop termina quando l'API restituisce `status: "VALID"` (0 problemi).  
Il limite iterazioni e dinamico e viene esteso automaticamente se necessario, quindi non interrompe il flusso in modo definitivo mentre ci sono ancora problemi risolvibili.

#### Modello VALID — Pagina di Successo

Quando l'API restituisce `status: "VALID"` (0 problemi), il workflow mostra una pagina verde con:

- **Iterazioni completate**: quante analisi sono state necessarie (es. "Dopo 2 iterazioni")
- **Status finale**: VALID
- **Session ID**: identificativo univoco della sessione di analisi
- **Modello Raffinato (Output)**: il domain model corretto con tutte le modifiche applicate durante il loop (rename, ownership, reclassificazioni, mapping aggiunti). Disponibile con tre azioni:
  - **Scarica JSON**: download del file `refined_model_{session_id}.json`
  - **Copia negli appunti**: copia il JSON formattato nella clipboard
  - **Mostra/Nascondi JSON**: anteprima inline con syntax highlighting (chiavi, stringhe, numeri, booleani colorati)

Il modello raffinato e anche salvato lato server in `output_agent/validation_{task_id}.json` e, se il percorso Kafka e attivo, pubblicato su `agent2-output` per Agent 3.

#### Comportamento del limite iterazioni (soft cap)

Nel workflow corrente il nodo "Max Iterazioni?" resta come guardrail, ma non e un blocco hard:

- se `iteration >= max_iterations`, il nodo "Prepara Dati" estende automaticamente `max_iterations` di almeno 1;
- il ciclo prosegue con una nuova chiamata `/analyze`;
- la stima LLM viene riacquisita al giro successivo e il limite si riallinea ai problemi residui.

In questo modo si evita lo scenario in cui appare un messaggio di "limite raggiunto" mentre il modello non e ancora stato risolto.

**Nota deploy N8N v2**: il workflow usa URL diretti (`http://agent2-api:8002`) invece di `$env` perche N8N v2 Task Runner blocca l'accesso alle variabili d'ambiente nelle espressioni.

### `workflow_demo_simple.json` — Demo Rapida

Workflow semplice per test. Trigger manuale, esegue una singola analisi e mostra i risultati.

---

## Modello LLM

### Perche Mistral 7B e non Llama3

La v1.x usava `llama3` (8B parametri). La v2.0 passa a `mistral:7b` per tre motivi:

1. **VRAM**: la GPU di riferimento e una NVIDIA RTX 4070 con **8 GB VRAM**. Mistral 7B in formato Q4_K_M occupa ~4.4 GB e sta interamente in VRAM con margine per context window e batch. Llama3 8B occupa ~4.7 GB — funziona ma lascia meno spazio, rischiando offload su RAM con conseguente calo di velocita.

2. **Qualita output strutturato**: Agent 2 richiede che l'LLM generi **JSON valido** (array di domande con `suggested_answers`, azioni strutturate per il refiner). Mistral 7B usa un instruction format piu rigido e rispetta meglio i vincoli di schema rispetto a Llama3 8B, che tende a generare testo di contorno prima del JSON.

3. **Velocita di inferenza**: Mistral usa un'architettura con **Grouped-Query Attention (GQA)** e **Sliding Window Attention (SWA)**, che lo rende piu veloce in generazione a parita di parametri. Per un agente che fa piu chiamate LLM per iterazione (generare domande + interpretare ogni risposta), la velocita e un fattore critico.

### Configurazione attuale

| Parametro | Valore |
|-----------|--------|
| Modello | `mistral:7b` |
| Quantizzazione | Q4_K_M |
| Dimensione | 4.4 GB |
| VRAM necessaria | ~5 GB |
| Provider | Ollama (locale) |

### Dove viene usato l'LLM

1. **Conflict Detection** (`conflict_detector.py`): analisi approfondita del modello con DDD rules come contesto
2. **Question Generation** (`question_generator.py`): genera domande contestuali con risposte suggerite specifiche
3. **Answer Interpretation** (`model_refiner.py`): interpreta le risposte utente e decide le modifiche da applicare

### Parametri LLM per servizio

| Servizio | Temperature | Max tokens | Timeout |
|----------|------------|------------|---------|
| Conflict Detector | 0.3 | 2048 | 120s |
| Question Generator | 0.4 | 4096 | 120s |
| Model Refiner | 0.2 | 2048 | 120s |

### Modelli compatibili testati

| Modello | VRAM | Velocita | Qualita JSON |
|---------|------|----------|--------------|
| `mistral:7b` | ~5 GB | Veloce | Buona |
| `llama3` (8B) | ~5.5 GB | Veloce | Media |
| `qwen2.5-coder:14b` | ~10 GB | Lenta (CPU offload) | Buona |

---

## Schema Domain Model

### Schema minimo

```json
{
  "metadata": { "modelId": "...", "version": "..." },
  "domainMap": {
    "coreDomains": [
      {
        "id": "order-management",
        "name": "Order Management",
        "boundedContext": { "name": "OrderContext" },
        "entities": [{ "name": "Order", "type": "aggregate-root" }],
        "functionalRequirements": [{ "id": "FR-ORD-001", "description": "..." }]
      }
    ]
  },
  "eventDrivenModel": {
    "events": [
      { "name": "OrderCreated", "emitter": "order-management", "consumers": ["inventory"] }
    ]
  }
}
```

### Schema completo

```json
{
  "metadata": {
    "modelId": "dm-ecommerce-001",
    "version": "1.0.0",
    "createdAt": "2025-01-15T10:00:00Z",
    "createdBy": "Agent 1",
    "projectName": "E-Commerce Platform",
    "description": "Domain model for e-commerce platform"
  },
  "businessContext": {
    "objectives": ["Place orders online", "Manage inventory"],
    "boundaries": ["B2C only", "Single currency"]
  },
  "domainMap": {
    "coreDomains": [
      {
        "id": "order-management",
        "name": "Order Management",
        "description": "Handles order lifecycle",
        "boundedContext": {
          "name": "OrderContext",
          "ubiquitousLanguage": {
            "Order": "A customer's purchase request",
            "OrderLine": "A single item in an order"
          }
        },
        "entities": [
          {
            "name": "Order",
            "type": "aggregate-root",
            "identity": "orderId (UUID)",
            "invariants": ["Order total must be positive"]
          }
        ],
        "valueObjects": [
          { "name": "Money", "attributes": [{ "name": "amount", "type": "Decimal" }] }
        ],
        "functionalRequirements": [
          { "id": "FR-ORD-001", "description": "Customer can create an order", "priority": "HIGH" }
        ]
      }
    ],
    "supportingDomains": [],
    "genericDomains": []
  },
  "eventDrivenModel": {
    "events": [
      {
        "name": "OrderCreated",
        "emitter": "order-management",
        "consumers": ["payment-processing", "inventory"],
        "payload": { "orderId": "UUID", "customerId": "UUID" }
      }
    ],
    "patterns": {
      "primary": "pub-sub",
      "messaging": { "broker": "Apache Kafka" },
      "guarantees": { "delivery": "at-least-once" }
    }
  },
  "contextIntegrations": [
    {
      "upstream": "order-management",
      "downstream": "payment-processing",
      "relationship": "customer-supplier",
      "integrationPattern": "event-driven",
      "communication": "async"
    }
  ]
}
```

### Tipi di issue rilevati

| Tipo | Severita | Descrizione |
|------|----------|-------------|
| `ENTITY_OVERLAP` | HIGH | Stessa entita in piu bounded context |
| `SEMANTIC_AMBIGUITY` | MEDIUM | Termine con significati diversi |
| `REQUIREMENT_CONFLICT` | HIGH | Requisiti contraddittori |
| `DUPLICATE_EVENT` | HIGH | Stesso evento emesso da piu domini |
| `NAMING_VIOLATION` | LOW-MEDIUM | Evento non al tempo passato |
| `INCOMPATIBLE_PATTERN` | HIGH | Pattern comunicazione incompatibile |
| `MISCLASSIFIED_DOMAIN` | MEDIUM | Classificazione dominio errata |

### File di esempio

| File | Dominio | Issue mirati | Uso |
|------|---------|-------------|-----|
| `example_demo.json` | E-Commerce | ENTITY_OVERLAP, REQUIREMENT_CONFLICT, DUPLICATE_EVENT | Demo rapida (3 problemi) |
| `example_bad.json` | E-Commerce | Tutti e 7 i tipi | Stress test (23 errori) |
| `example_good.json` | E-Commerce | Nessuno | Verifica VALID |
| `case_healthcare.json` | Sanita | ENTITY_OVERLAP (Patient x3), SEMANTIC_AMBIGUITY (Visita), MISCLASSIFIED_DOMAIN (Auth) | Case test dominio clinico |
| `case_banking.json` | Banking | NAMING_VIOLATION (3 eventi), INCOMPATIBLE_PATTERN (sincrono su async), REQUIREMENT_CONFLICT (consistenza saldi) | Case test dominio finanziario |

**Copertura issue per file**:

| Tipo issue | demo | bad | healthcare | banking |
|---|---|---|---|---|
| ENTITY_OVERLAP | x | x | x | x |
| SEMANTIC_AMBIGUITY | | x | x | |
| REQUIREMENT_CONFLICT | x | x | | x |
| DUPLICATE_EVENT | x | x | | |
| NAMING_VIOLATION | | x | | x |
| INCOMPATIBLE_PATTERN | | x | | x |
| MISCLASSIFIED_DOMAIN | | x | x | |

---

## Struttura Progetto

```
agent-consistency-analyzer/
|
+-- app/
|   +-- main.py                    # FastAPI, 13 endpoint, orchestrazione pipeline
|   +-- config.py                  # Settings da env (Pydantic)
|   +-- services/
|   |   +-- semantic_analyzer.py   # Step 1: embeddings, entity overlap
|   |   +-- conflict_detector.py   # Step 2: regole DDD + LLM
|   |   +-- question_generator.py  # Step 3: domande LLM-first + fallback template
|   |   +-- model_refiner.py       # Step 4: auto-fix + LLM answer interpretation
|   +-- kafka/
|       +-- consumer_advanced.py   # Consumer parallelo da agent1-output
|       +-- producer.py            # Producer verso agent2-output
|
+-- a2a/
|   +-- agent_card.json            # Metadati A2A Protocol v0.3
|   +-- handlers/                  # Gestione messaggi A2A
|   +-- models/                    # Strutture dati A2A
|
+-- knowledge_base/
|   +-- ddd_rules.md               # 23 regole DDD (20 KB)
|   +-- validation_checklist.json  # Checklist strutturata con template
|
+-- input_agent/
|   +-- example_demo.json          # E-Commerce, 3 bug intenzionali
|   +-- example_bad.json           # E-Commerce, 23 errori per stress test
|   +-- example_good.json          # E-Commerce, modello valido
|   +-- case_healthcare.json       # Sanita, 4 issue (ambiguity, overlap, misclassified)
|   +-- case_banking.json          # Banking, 4 issue (naming, pattern, conflict)
|
+-- n8n/
|   +-- workflow_complete_loop.json  # Loop interattivo (17 nodi)
|   +-- workflow_demo_simple.json    # Demo singola esecuzione
|
+-- docker-compose.yml             # Core: agent2-api + n8n (2 servizi)
+-- docker-compose.kafka.yml      # Extra: zookeeper, kafka, consumer, kafka-ui (4 servizi)
+-- Dockerfile                     # Multi-stage build, Python 3.11
+-- requirements.txt               # 30 dipendenze
+-- .env                           # Configurazione ambiente
+-- START_DEMO.ps1                 # Script avvio rapido PowerShell
```

---

## Configurazione

### Variabili d'ambiente (`.env`)

```bash
# Ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=mistral:7b
OLLAMA_TIMEOUT=120

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_INPUT_TOPIC=agent1-output
KAFKA_OUTPUT_TOPIC=agent2-output
KAFKA_GROUP_ID=agent2-consistency-analyzer

# API
API_PORT=8002
LOG_LEVEL=INFO

# Analisi
EMBEDDINGS_MODEL=all-MiniLM-L6-v2
ENTITY_OVERLAP_THRESHOLD=0.85
SEMANTIC_SIMILARITY_THRESHOLD=0.75
MAX_FOLLOW_UP_QUESTIONS=5
```

### Esecuzione locale (senza Docker)

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

---

## Integrazione Kafka

### Consumer (`consumer_advanced.py`)

Ascolta il topic `agent1-output` per messaggi da Agent 1. Processa automaticamente ogni domain model ricevuto e pubblica il risultato su `agent2-output`.

- Processamento parallelo con `MAX_WORKERS=4`
- Scalabile con `CONSUMER_REPLICAS` in docker-compose
- Usa `use_llm=False` per velocita nella pipeline automatica

### Producer (`producer.py`)

Pubblica i risultati dell'analisi su `agent2-output`, consumato da Agent 3.

### Monitoraggio

Kafka UI disponibile su http://localhost:8085 per ispezionare topic, messaggi e consumer groups.

---

## Knowledge Base

### `ddd_rules.md` (20 KB)

Contiene le regole DDD strutturate in sezioni:
1. **Classificazione Domini** — criteri Core/Supporting/Generic
2. **Bounded Context** — ubiquitous language, confini, integrazioni
3. **Entity vs Value Object** — identita, ciclo di vita, immutabilita
4. **Event Architecture** — naming, single emitter, payload
5. **Communication Patterns** — consistenza, pattern compatibili

### `validation_checklist.json`

Checklist strutturata con 23 regole organizzate in 7 categorie:
- DC (Domain Classification): 3 regole
- BC (Bounded Context): 3 regole
- EVO (Entity/Value Object): 3 regole
- EO (Entity Ownership): 3 regole
- RC (Requirement Consistency): 3 regole
- EA (Event Architecture): 4 regole
- CP (Communication Patterns): 3 regole

Ogni regola include `question_template` per il fallback quando l'LLM non e disponibile.

---

## Troubleshooting

| Problema | Soluzione |
|----------|----------|
| Webhook 404 in n8n | Il workflow deve essere **attivo** (toggle verde). URL prod: `/webhook/agent2-start` |
| Pagina bianca dopo click | Verifica che N8N usi URL prod, non test (`/webhook-test/` e monouso) |
| `access to env vars denied` | N8N v2 blocca `$env` nelle espressioni. Usare URL diretti nel workflow |
| Analisi lenta | Imposta `use_llm=false` in `/analyze` per saltare le chiamate LLM |
| Ollama non raggiungibile | Verificare che Ollama sia avviato: `ollama list` |
| Docker non parte | Aprire Docker Desktop manualmente, poi `docker compose up -d` |
| Domande generiche | Verificare che `OLLAMA_MODEL=mistral:7b` nel `.env` e che Ollama sia raggiungibile |

---

## Versione

- **Versione**: 2.0.0
- **Stato**: Production Ready
- **Ultimo aggiornamento**: 2026-02-13
- **Changelog**: vedi `CHANGELOG.md`
- **Licenza**: MIT
