# Agent 2 - Consistency & Conflict Analyzer

> Validatore intelligente per modelli Domain-Driven Design (DDD)

---

## Quick Start (2 Minuti)

### 1. Prerequisiti (Solo Prima Volta)

#### Docker Desktop
1. Scarica: https://www.docker.com/products/docker-desktop
2. Installa e avvia Docker Desktop
3. Aspetta che diventi verde (Running)

#### Ollama + Llama3
```bash
# Installa Ollama da: https://ollama.ai/download
# Poi scarica il modello:
ollama pull llama3
```

### 2. Avvia la Demo

#### Metodo 1: Doppio Click (Raccomandato)
**Da Esplora File:** Doppio click su `START_DEMO.bat`

#### Metodo 2: Da PowerShell
```powershell
cd C:\Users\TUO_USERNAME\Desktop\agent-consistency-analyzer
.\START_DEMO.bat
```

**IMPORTANTE:** In PowerShell devi usare `.\` prima del nome del file!

#### Metodo 3: Solo Container (Senza Browser)
```powershell
docker-compose up -d
```
Poi apri manualmente:
- http://127.0.0.1:5678 (n8n)
- http://localhost:8080 (Kafka UI)
- http://localhost:8002/docs (API Docs)

**Cosa fa START_DEMO.bat:**
1. Build immagini Docker (1-2 min prima volta)
2. Avvio tutti i servizi (Kafka, Agent 2, n8n, Kafka UI)
3. Attesa 30 secondi per inizializzazione
4. Apertura automatica 3 pagine web nel browser

### 3. Usa n8n per Vedere la Demo

1. **Setup n8n (solo prima volta):**
   - Email: `demo@test.com`
   - Password: `password123`
   - Clicca "Get Started"

2. **Scegli il Workflow:**

   **Opzione A: Demo Semplice (Raccomandato per iniziare)**
   - File: `n8n/workflow_demo_simple.json`
   - Trigger: Manuale (clicca Execute Workflow)
   - Output: Report statico con problemi e domande
   - Tempo: 10-30 secondi

   **Opzione B: Loop Interattivo Completo**
   - File: `n8n/workflow_complete_loop.json`
   - Trigger: Webhook (apri pagina web)
   - Output: Form HTML per rispondere alle domande
   - Loop: Agent analizza → chiede → utente risponde → raffina → ripete fino a modello perfetto
   - Tempo: Variabile (dipende dalle tue risposte)

3. **Importa Workflow:**
   - Clicca "Workflows" → "Import from File"
   - Seleziona il file desiderato

4. **Esegui:**

   **Se hai scelto Demo Semplice:**
   - Clicca "Execute Workflow" (icona play)
   - Attendi 10-30 secondi
   - Vedi risultati nel nodo "4. RISULTATI FINALI"

   **Se hai scelto Loop Interattivo:**
   - Attiva il workflow (interruttore in alto a destra)
   - Usa lo script di test: `.\TEST_INTERACTIVE_LOOP.bat`
   - Oppure manualmente: apri http://127.0.0.1:5678/webhook/agent2-start
   - Compila il form con il modello JSON
   - Rispondi alle domande generate
   - Il loop continua automaticamente fino a modello valido

   **Guida completa:** [n8n/README_INTERACTIVE_LOOP.md](n8n/README_INTERACTIVE_LOOP.md)

---

## Cosa Fa Agent 2

**INPUT:** Modello funzionale da Agent 1 (formato JSON)

**PROCESSO:**
1. Valida 23 regole DDD automaticamente
2. Rileva entity overlap (analisi semantica)
3. Trova conflitti nei requisiti (LLM)
4. Valida event-driven architecture
5. Corregge automaticamente errori semplici
6. Genera domande di follow-up per errori complessi

**OUTPUT:**
1. Report di validazione (status, problemi trovati, severity)
2. 3-5 domande di follow-up con risposte suggerite
3. Modello raffinato con correzioni automatiche

---

## Differenze tra i Workflow

### workflow_demo_simple.json (Raccomandato per iniziare)

**Quando usarlo:**
- Prima volta con Agent 2
- Vuoi vedere rapidamente cosa fa l'agent
- Test e debug
- Demo a stakeholder

**Caratteristiche:**
- Trigger: Manuale (clicca Execute Workflow in n8n)
- Input: Modello demo embedded nel workflow (3 problemi)
- Output: Report statico con JSON
- Durata: 10-30 secondi
- Interattività: Nessuna (one-shot)

**Vantaggi:**
- Semplice da usare
- Non richiede configurazione
- Risultati immediati
- Perfetto per capire Agent 2

### workflow_complete_loop.json (Produzione)

**Quando usarlo:**
- Workflow di produzione
- Integrazione con Agent 1 e Agent 3
- Vuoi raffinare il modello iterativamente
- Workflow completo end-to-end

**Caratteristiche:**
- Trigger: Webhook HTTP
- Input: POST con modello JSON custom
- Output: Form HTML interattivo
- Durata: Variabile (dipende dalle iterazioni)
- Interattività: Loop completo con Q&A

**Vantaggi:**
- Loop automatico fino a modello perfetto
- Form HTML professionale
- Integrazione facile con altri sistemi
- Tracking delle iterazioni
- Safety limit (max 5 loop)

**Come funziona il loop:**
```
1. POST modello → Webhook
2. Agent 2 analizza → trova 3 problemi
3. Genera 3 domande → Form HTML
4. Utente risponde → POST risposte
5. Agent 2 ri-analizza con risposte → trova 1 problema
6. Genera 1 domanda → Form HTML
7. Utente risponde → POST risposte
8. Agent 2 ri-analizza → VALIDO!
9. Pagina di successo
```

**URL Webhook:**
```
POST http://127.0.0.1:5678/webhook/agent2-start
```

---

## Esempio di Output

### File Demo: `input_agent/example_demo.json`

Il file contiene **3 problemi intenzionali**:

#### Problema 1: Entity "Product" Duplicata
- **Dove:** In OrderContext E in CatalogContext
- **Severity:** HIGH
- **Output:** Domanda per chiarire se è lo stesso concetto o aspetti diversi

#### Problema 2: Requisiti Contraddittori
- **Dove:** FR-ORD-001 (immutabile) vs FR-ORD-002 (modificabile)
- **Severity:** HIGH
- **Output:** Domanda per definire quando diventa immutabile

#### Problema 3: Evento con 2 Emitter
- **Dove:** OrderCreated emesso da OrderService E PaymentService
- **Severity:** CRITICAL
- **Output:** Correzione automatica + domanda per conferma

---

## Stop Demo

**Doppio click su:** `docker-stop.bat`

Oppure:
```bash
docker-compose down
```

---

## Link Utili

| Servizio | URL | Descrizione |
|----------|-----|-------------|
| **n8n** | http://127.0.0.1:5678 | Workflow visuale |
| **Kafka UI** | http://localhost:8080 | Monitoraggio code |
| **API Docs** | http://localhost:8002/docs | Test API |
| **Health** | http://localhost:8002/health | Stato sistema |

---

## Struttura File

```
agent-consistency-analyzer/
├── START_DEMO.bat                     ← AVVIA QUI!
├── TEST_INTERACTIVE_LOOP.bat          ← Test workflow interattivo
├── docker-stop.bat                    ← Stop tutto
├── docker-compose.yml                 ← Config Docker
├── README.md                          ← Questo file
│
├── input_agent/
│   ├── example_demo.json             ← File demo (3 problemi)
│   ├── example_bad.json              ← Test completo (23 problemi)
│   └── example_good.json             ← Modello valido
│
├── n8n/
│   ├── workflow_complete_loop.json   ← Loop interattivo (PRODUZIONE)
│   ├── workflow_demo_simple.json     ← Test rapidi
│   ├── README_INTERACTIVE_LOOP.md    ← Guida completa loop interattivo
│   ├── DEMO_SETUP.md                 ← Setup iniziale demo
│   └── WORKFLOW_VISUAL.md            ← Diagrammi workflow
│
├── knowledge_base/
│   ├── ddd_rules.md                  ← 23 regole DDD
│   └── validation_checklist.json     ← Checklist validazione
│
└── app/                              ← Codice sorgente Python
    ├── api/                          ← FastAPI endpoints
    ├── services/                     ← Logica validazione
    └── kafka/                        ← Consumer/Producer Kafka
```

---

## Test API Diretti (Opzionale)

### Test 1: Health Check
```bash
curl http://localhost:8002/health
```

**Risposta attesa:**
```json
{"status": "healthy", "version": "1.0.0"}
```

### Test 2: Analisi Completa
```bash
curl -X POST http://localhost:8002/analyze \
  -H "Content-Type: application/json" \
  -d @input_agent/example_demo.json
```

**Risposta attesa:** JSON con:
- `validation_report`: Status + problemi trovati
- `follow_up_questions`: 3 domande
- `refined_model`: Modello corretto

---

## Tecnologie

- **Python 3.11+** - Linguaggio principale
- **FastAPI** - Web framework
- **Kafka** - Message queue
- **Ollama + Llama3** - LLM locale
- **Sentence Transformers** - Embeddings
- **Docker** - Containerizzazione
- **n8n** - Workflow automation

---

## Troubleshooting

### "START_DEMO.bat: The term is not recognized"
**Problema:** In PowerShell il comando non viene riconosciuto
**Soluzione:** Usa `.\START_DEMO.bat` invece di `START_DEMO.bat`

```powershell
# SBAGLIATO
START_DEMO.bat

# CORRETTO
.\START_DEMO.bat
```

### "docker-compose up -d funziona ma non si aprono le pagine"
**Problema:** `docker-compose up -d` avvia solo i container, non apre i browser
**Soluzione:** Usa `.\START_DEMO.bat` oppure apri manualmente le pagine:

```powershell
start http://127.0.0.1:5678
start http://localhost:8080
start http://localhost:8002/docs
```

### "Kafka is unhealthy" o "dependency failed to start"
**Problema:** Kafka impiega tempo a diventare healthy
**Soluzione:** Aspetta 30-60 secondi, poi riavvia i servizi dipendenti:

```powershell
docker-compose up -d agent2-api agent2-consumer
```

### "Docker non parte"
**Soluzione:** Apri Docker Desktop e aspetta che diventi verde (Running)

### "n8n non si apre"
```bash
docker restart agent2-n8n
# Aspetta 30 secondi, poi ricarica http://127.0.0.1:5678
```

### "Kafka UI non si apre"
```bash
docker restart agent2-kafka-ui
# Aspetta 30 secondi, poi ricarica http://localhost:8080
```

### "Timeout nel workflow n8n"
**Causa:** LLM (Llama3) sta processando
**Soluzione:** Aspetta fino a 60 secondi

### "Ollama non risponde"
```bash
# Verifica Ollama
ollama list
# Dovresti vedere "llama3"

# Testa Ollama
ollama run llama3 "Hello"
```

---

## Architettura Pipeline Completa

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  AGENT 1    │      │  AGENT 2    │      │  AGENT 3    │
│             │      │             │      │             │
│  Domain     │─────▶│ Consistency │─────▶│ Functional  │
│  Modeler    │Kafka │ Analyzer    │Kafka │ Spec Gen    │
└─────────────┘      └─────────────┘      └─────────────┘
      │                     │                     │
   Intervista          Valida &             Genera Specs
  Stakeholder          Corregge             Funzionali
```

**Questo repo contiene Agent 2.**

---

## Deployment Production

Per deployment production-ready, vedi:
- [docker-compose.yml](docker-compose.yml) - Config production
- Sezione "Scaling" per aumentare worker
- Sezione "Monitoring" per Prometheus/Grafana

---

## Le 23 Regole di Validazione

Agent 2 controlla automaticamente:

### Struttura Dominio (7 regole)
1. Core domain deve essere definito
2. Bounded context deve avere almeno un aggregate
3. Aggregate root deve essere definito
4. Entity deve avere ID univoco
5. Value Object deve essere immutabile
6. Domain Service correttamente classificato
7. Anti-Corruption Layer per sistemi legacy

### Requisiti (5 regole)
8. Functional Requirements ben definiti
9. Non-Functional Requirements specificati
10. Nessun conflitto tra requisiti
11. Business Rules complete
12. Invarianti del dominio preservati

### Event-Driven (6 regole)
13. Eventi seguono nomenclatura passato (OrderCreated)
14. Eventi hanno emittente singolo (Single Emitter Rule)
15. Subscribers ben definiti
16. Event Storming completo
17. Saga pattern per transazioni distribuite
18. Event Sourcing dove appropriato

### Comunicazione (5 regole)
19. Context Map ben definito
20. Relationship type corretto (Customer/Supplier, etc.)
21. Shared Kernel minimizzato
22. Published Language per integrazione
23. Conformist pattern solo dove necessario

**Dettaglio completo:** [knowledge_base/validation_checklist.json](knowledge_base/validation_checklist.json)

---

## Info Progetto

- **Versione:** 1.0.0
- **Status:** Production Ready
- **Ultimo Aggiornamento:** 2025-12-17
- **Licenza:** MIT

---

**Buon lavoro con Agent 2!**
