# Demo n8n - Setup Completo

## Cosa Mostra Questa Demo

Questa demo mostra il funzionamento completo di Agent 2:

**INPUT** → **PROCESSO** → **OUTPUT**

### INPUT (Modello Funzionale)
Un modello Domain-Driven Design con:
- 2 domini core (Order Management, Product Catalog)
- 2 bounded context
- Entità e aggregati
- Requisiti funzionali
- Eventi e pattern di comunicazione
- **3 problemi intenzionali** da trovare

### PROCESSO (Agent 2 Analizza)
Agent 2 esegue:
1. **Semantic Analysis**: Trova entità duplicate ("Product" in 2 contesti)
2. **Conflict Detection**: Rileva requisiti contraddittori (immutable vs modifiable)
3. **Event Architecture**: Trova evento con multipli emitters
4. **Question Generation**: Genera domande mirate
5. **Model Refining**: Corregge automaticamente dove possibile

### OUTPUT (3 Componenti)
1. **Report di Validazione**: Riepilogo problemi trovati
2. **Domande di Follow-up**: Massimo 5 domande prioritizzate
3. **Modello Raffinato**: Versione corretta pronta per Agent 3

---

## Importa il Workflow in n8n

### Passo 1: Apri n8n
```
http://127.0.0.1:5678
```

### Passo 2: Importa Workflow
1. Clicca "Workflows" nel menu
2. Clicca "Import from File"
3. Seleziona: `n8n/workflow_demo_simple.json`
4. Il workflow si apre automaticamente

### Passo 3: Verifica Connessione
Nel nodo "2. AGENT 2 - Analizza Modello":
- URL dovrebbe essere: `http://host.docker.internal:8002/analyze`
- Se n8n gira localmente (non Docker), usa: `http://localhost:8002/analyze`

---

## Struttura del Workflow

```
┌──────────────────────────────────┐
│  1. INPUT                        │
│  Modello da Validare             │
│                                  │
│  Contiene:                       │
│  - domainMap (domini, context)   │
│  - eventDrivenModel (eventi)     │
│  - 3 problemi intenzionali       │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│  2. AGENT 2                      │
│  HTTP POST /analyze              │
│                                  │
│  Esegue:                         │
│  - Semantic Analysis             │
│  - Conflict Detection            │
│  - Event Validation              │
│  - Question Generation           │
│  - Model Refining                │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│  Problemi Trovati?               │
│  (IF Node)                       │
└─────┬──────────────────┬─────────┘
      │ SÌ               │ NO
      ▼                  ▼
┌─────────────┐    ┌─────────────┐
│ 3a. Summary │    │ 3d. Valido  │
│ Report      │    │             │
└─────┬───────┘    └──────┬──────┘
      │                   │
      ▼                   │
┌─────────────┐          │
│ 3b. Domande │          │
│ Follow-up   │          │
└─────┬───────┘          │
      │                   │
      ▼                   │
┌─────────────┐          │
│ 3c. Modello │          │
│ Raffinato   │          │
└─────┬───────┘          │
      │                   │
      └───────┬───────────┘
              │
              ▼
     ┌────────────────┐
     │ 4. RISULTATI   │
     │    FINALI      │
     │                │
     │ Formato:       │
     │ - Report       │
     │ - Domande      │
     │ - Modello      │
     └────────────────┘
```

---

## Esegui la Demo

### 1. Clicca "Execute Workflow"

Bottone in alto a destra nel workflow.

### 2. Attendi Processamento

L'analisi richiede ~10-30 secondi (dipende da LLM).

Vedrai i nodi accendersi in sequenza:
1. INPUT (verde)
2. AGENT 2 (verde)
3. Problemi Trovati? (verde)
4. 3a, 3b, 3c (verdi)
5. RISULTATI FINALI (verde)

### 3. Vedi i Risultati

Clicca sul nodo **"4. RISULTATI FINALI"** per vedere l'output completo.

---

## Cosa Vedrai nell'Output

### Esempio di Output Completo:

```json
{
  "validation_report": {
    "status": "ISSUES_FOUND",
    "total_issues": 3,
    "breakdown": {
      "entity_overlaps": 1,
      "requirement_conflicts": 1,
      "event_violations": 1
    }
  },
  "follow_up_questions": {
    "count": 3,
    "questions": [
      {
        "question_id": "FUQ-001",
        "question": "Entity 'Product' appears in OrderContext and CatalogContext. Do they represent the same concept or different aspects?",
        "severity": "HIGH",
        "context": "Multi-context entity definition",
        "suggested_answers": [
          "Same concept - create shared ProductContext",
          "Different aspects - rename to OrderItem and CatalogProduct",
          "Product is aggregate root - keep in CatalogContext, reference from OrderContext"
        ]
      },
      {
        "question_id": "FUQ-002",
        "question": "Requirements FR-ORD-001 states immutability but FR-ORD-002 allows modifications. Should orders be truly immutable after confirmation?",
        "severity": "HIGH",
        "context": "Conflicting functional requirements",
        "suggested_answers": [
          "Fully immutable - remove FR-ORD-002",
          "Allow modifications within 24h - adjust FR-ORD-001 to 'immutable after 24h'",
          "Define order lifecycle: PENDING (modifiable) → CONFIRMED (immutable)"
        ]
      },
      {
        "question_id": "FUQ-003",
        "question": "Event 'OrderCreated' has multiple emitters (OrderService, PaymentService). Which service should be the single source of truth?",
        "severity": "CRITICAL",
        "context": "Event architecture violation - multiple emitters",
        "suggested_answers": [
          "Only OrderService emits OrderCreated - PaymentService subscribes to it",
          "Create separate events: OrderInitiated (OrderService), PaymentConfirmed (PaymentService)"
        ]
      }
    ]
  },
  "refined_model_available": true,
  "refined_model": {
    "metadata": {
      "modelId": "demo-001-refined",
      "version": "1.1",
      "refinedBy": "agent-2-consistency-analyzer",
      "refinedAt": "2025-12-17T10:00:30Z"
    },
    "domainMap": {
      // Modello corretto con:
      // - Eventi con singolo emitter
      // - Naming conventions corrette
      // - Suggerimenti per entità duplicate
    }
  },
  "analyzed_at": "2025-12-17T10:00:30.123Z"
}
```

---

## Interpretazione dei Risultati

### 1. Validation Report

**status**: `ISSUES_FOUND` o `VALID`
- `ISSUES_FOUND`: Problemi rilevati
- `VALID`: Modello valido

**total_issues**: Numero totale di problemi

**breakdown**: Dettaglio per categoria
- `entity_overlaps`: Entità duplicate
- `requirement_conflicts`: Requisiti contraddittori
- `event_violations`: Violazioni architettura eventi

### 2. Follow-up Questions

**count**: Numero di domande generate (max 5)

**questions**: Array di domande con:
- `question_id`: ID univoco domanda
- `question`: Testo della domanda
- `severity`: CRITICAL, HIGH, MEDIUM, LOW
- `context`: Contesto del problema
- `suggested_answers`: Opzioni di risposta pre-formulate

**Come usarle:**
Queste domande vanno poste agli stakeholder business per risolvere ambiguità e conflitti nel modello.

### 3. Refined Model

**refined_model_available**: `true` se disponibile

**refined_model**: Versione corretta del modello con:
- Correzioni automatiche applicate (naming, eventi singoli, ecc.)
- Suggerimenti per problemi complessi
- Pronto per essere passato ad Agent 3

---

## Personalizza l'Input

Puoi testare il tuo modello:

### Passo 1: Prepara il JSON
Crea un file JSON con il tuo domain model seguendo lo schema:
```json
{
  "metadata": {...},
  "domainMap": {
    "coreDomains": [...]
  },
  "eventDrivenModel": {
    "events": [...]
  }
}
```

### Passo 2: Modifica il Nodo INPUT
1. Clicca sul nodo "Prepara Input"
2. Modifica il campo `domain_model`
3. Incolla il tuo JSON

### Passo 3: Esegui
Clicca "Execute Workflow"

---

## Test Scenari Diversi

### Scenario 1: Modello Valido
Usa `input_agent/example_good.json`:
- Pochi o nessun problema
- Status: `VALID`
- Poche o nessuna domanda

### Scenario 2: Modello con Molti Errori
Usa `input_agent/example_bad.json`:
- 23 problemi
- Status: `ISSUES_FOUND`
- 5 domande prioritizzate

### Scenario 3: Solo Event Architecture
Crea un modello con solo eventi:
```json
{
  "eventDrivenModel": {
    "events": [
      {
        "name": "OrderCreated",
        "emitters": ["OrderService", "PaymentService"],
        "subscribers": ["InventoryService"]
      }
    ]
  }
}
```
Focus su violazioni eventi.

---

## Integrazione con Altri Sistemi

### Invia Notifiche su Slack/Email

Aggiungi dopo il nodo "4. RISULTATI FINALI":

1. **IF Node**: `{{ $json.validation_report.total_issues > 0 }}`
2. **Slack/Email Node**: Configura con template:

```
🔍 Analisi DDD Completata!

📊 Status: {{ $json.validation_report.status }}
📈 Problemi trovati: {{ $json.validation_report.total_issues }}

Dettagli:
- Entity Overlaps: {{ $json.validation_report.breakdown.entity_overlaps }}
- Conflitti Requisiti: {{ $json.validation_report.breakdown.requirement_conflicts }}
- Violazioni Eventi: {{ $json.validation_report.breakdown.event_violations }}

❓ Domande generate: {{ $json.follow_up_questions.count }}

Vedi dettagli: http://127.0.0.1:5678/workflow/...
```

### Salva Risultati in Database

Aggiungi nodo **PostgreSQL/MySQL/MongoDB**:
- Tabella: `validation_results`
- Campi: `model_id`, `status`, `issues`, `questions`, `timestamp`

### Webhook da Agent 1

Modifica il primo nodo:
1. Sostituisci "Manual Trigger" con "Webhook"
2. URL: `http://127.0.0.1:5678/webhook/agent2-validation`
3. Agent 1 invia POST con domain model

---

## Troubleshooting

### Problema: "Connection refused"

**Causa**: Agent 2 non raggiungibile da n8n

**Soluzione**:
- Se n8n in Docker: usa `http://host.docker.internal:8002/analyze`
- Se n8n locale: usa `http://localhost:8002/analyze`

Verifica:
```bash
# Da dentro n8n container
docker exec -it agent2-n8n curl http://host.docker.internal:8002/health
```

### Problema: "Timeout after 120s"

**Causa**: LLM troppo lento

**Soluzione**:
1. Nel nodo "2. AGENT 2", aumenta timeout:
   - Options → Timeout: `300000` (5 minuti)
2. Oppure usa modello LLM più piccolo in `.env`:
   ```
   OLLAMA_MODEL=phi
   ```

### Problema: "Invalid JSON"

**Causa**: Input malformato

**Soluzione**:
1. Valida JSON con: https://jsonlint.com
2. Controlla virgole, parentesi, quote

### Problema: Workflow non si salva

**Causa**: n8n in modalità read-only

**Soluzione**:
```bash
# Verifica volume n8n_data
docker volume inspect n8n_data

# Restart n8n
docker restart agent2-n8n
```

---

## Link Utili

- **API Docs Agent 2**: http://localhost:8002/docs
- **Health Check**: http://localhost:8002/health
- **Kafka UI**: http://localhost:8080
- **n8n Documentation**: https://docs.n8n.io
- **n8n Community**: https://community.n8n.io

---

## Prossimi Passi

1. **Personalizza il workflow** con i tuoi casi d'uso
2. **Aggiungi notifiche** (Slack, Email, etc.)
3. **Integra con Agent 1 e Agent 3** per pipeline completa
4. **Automatizza** con webhook o schedule trigger
5. **Scala** aumentando consumer Agent 2 per carichi elevati

---

**Fatto! Ora puoi usare Agent 2 con n8n per validare modelli DDD!**
