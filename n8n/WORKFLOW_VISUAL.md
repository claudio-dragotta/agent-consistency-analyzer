# N8N Workflow - Agent 2 Consistency Analyzer

## Diagramma Visuale Completo

```
┌────────────────────────────────────────────────────────────────────┐
│                    AGENT 2 - N8N WORKFLOW                          │
└────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ STEP 1: Webhook Trigger                                             │
├─────────────────────────────────────────────────────────────────────┤
│ Type: n8n-nodes-base.webhook                                        │
│ Method: POST                                                        │
│ Path: /analyze-domain                                               │
│                                                                     │
│ Input Format:                                                       │
│ {                                                                   │
│   "domain_model": { ... },                                          │
│   "use_llm": true,                                                  │
│   "apply_auto_fixes": true                                          │
│ }                                                                   │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 2: Agent 2 - Analyze                                           │
├─────────────────────────────────────────────────────────────────────┤
│ Type: n8n-nodes-base.httpRequest                                    │
│ Method: POST                                                        │
│ URL: http://localhost:8002/analyze                                  │
│ Timeout: 120000ms (2 minutes)                                       │
│                                                                     │
│ Headers:                                                            │
│   - Content-Type: application/json                                  │
│                                                                     │
│ Body (JSON):                                                        │
│   {                                                                 │
│     "domain_model": $json.body.domain_model,                        │
│     "use_llm": $json.body.use_llm ?? true,                          │
│     "apply_auto_fixes": $json.body.apply_auto_fixes ?? true         │
│   }                                                                 │
│                                                                     │
│ Output: Validation results with issues and summary                  │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 3: Has Issues? (IF Condition)                                  │
├─────────────────────────────────────────────────────────────────────┤
│ Type: n8n-nodes-base.if                                             │
│ Condition: $json.summary.total_issues > 0                           │
│                                                                     │
│ Checks if the domain model has any validation issues                │
└─────┬──────────────────────────────────────────────────┬────────────┘
      │                                                  │
      │ TRUE (Has Issues)                                │ FALSE (Valid)
      │                                                  │
      ▼                                                  ▼
┌──────────────────────────────────┐    ┌────────────────────────────┐
│ STEP 4: Extract Summary          │    │ STEP 5: Respond Valid      │
├──────────────────────────────────┤    ├────────────────────────────┤
│ Type: n8n-nodes-base.set         │    │ Type: respondToWebhook     │
│                                  │    │                            │
│ Extracts key fields:             │    │ Response:                  │
│  - status                        │    │ {                          │
│  - total_issues                  │    │   "status": "VALID",       │
│  - entity_overlaps               │    │   "message": "No issues    │
│  - semantic_ambiguities          │    │               found"       │
│  - requirement_conflicts         │    │ }                          │
│                                  │    └────────────────────────────┘
│ Creates clean response object    │
└─────────┬────────────────────────┘
          │
          ▼
┌──────────────────────────────────┐
│ STEP 6: Respond with Issues      │
├──────────────────────────────────┤
│ Type: respondToWebhook           │
│                                  │
│ Response: Full summary object    │
│ {                                │
│   "status": "...",               │
│   "total_issues": N,             │
│   "entity_overlaps": N,          │
│   "semantic_ambiguities": N,     │
│   "requirement_conflicts": N     │
│ }                                │
└──────────────────────────────────┘
```

## Configurazione Nodi

### 1. Webhook Trigger
- **Node ID**: `webhook-trigger`
- **Type**: Webhook
- **HTTP Method**: POST
- **Path**: `analyze-domain`
- **Response Mode**: Response Node (risponde dopo elaborazione)

### 2. Agent 2 - Analyze
- **Node ID**: `agent2-analyze`
- **Type**: HTTP Request
- **URL**: `http://localhost:8002/analyze`
- **Method**: POST
- **Timeout**: 120000ms
- **Headers**: Content-Type: application/json

**IMPORTANTE**: Se N8N è in Docker, cambia URL in:
```
http://host.docker.internal:8002/analyze
```

### 3. Has Issues? (IF)
- **Node ID**: `check-issues`
- **Type**: IF Condition
- **Condition**: `{{ $json.summary.total_issues }} > 0`
- **Output**:
  - TRUE → Extract Summary
  - FALSE → Respond Valid

### 4. Extract Summary
- **Node ID**: `extract-summary`
- **Type**: Set
- **Purpose**: Estrae campi chiave dal report
- **Fields**:
  - status
  - total_issues
  - entity_overlaps
  - semantic_ambiguities
  - requirement_conflicts

### 5. Respond Valid
- **Node ID**: `respond-valid`
- **Type**: Respond to Webhook
- **Response**: Static JSON (no issues message)

### 6. Respond with Issues
- **Node ID**: `respond-issues`
- **Type**: Respond to Webhook
- **Response**: Extracted summary

## Flusso di Esecuzione

```
Input → Webhook → HTTP Request → Condition Check
                                      │
                      ┌───────────────┴────────────────┐
                      │                                │
                   Issues?                           No Issues?
                      │                                │
                   Extract                          Respond
                   Summary                          "Valid"
                      │
                   Respond
                 with Issues
```

## Test del Workflow

### Metodo 1: Via N8N (dopo import)
1. Attiva il workflow (toggle in alto a destra)
2. Copia il webhook URL
3. Usa Postman o cURL per testare

### Metodo 2: Via cURL
```bash
# Ottieni webhook URL da N8N (es: http://localhost:5678/webhook/abc123)
curl -X POST http://localhost:5678/webhook/YOUR-WEBHOOK-ID \
  -H "Content-Type: application/json" \
  -d @input_agent/example_bad.json
```

### Metodo 3: Test diretto (senza N8N)
```bash
# Testa direttamente Agent 2
curl -X POST http://localhost:8002/analyze \
  -H "Content-Type: application/json" \
  -d @input_agent/example_bad.json
```

## Expected Response (Con Issues)

```json
{
  "status": "ISSUES_FOUND",
  "total_issues": 23,
  "entity_overlaps": 3,
  "semantic_ambiguities": 17,
  "requirement_conflicts": 2
}
```

## Expected Response (Nessun Issue)

```json
{
  "status": "VALID",
  "message": "No issues found in domain model"
}
```

## Troubleshooting

| Problema | Soluzione |
|----------|-----------|
| N8N non raggiunge Agent 2 | Cambia URL in `host.docker.internal:8002` |
| Timeout | Aumenta timeout nel nodo HTTP Request |
| Agent 2 non risponde | Verifica che sia avviato: `uvicorn app.main:app --port 8002` |
| Webhook non risponde | Assicurati che il workflow sia ATTIVO (toggle verde) |

## Estensioni Possibili

1. **Notifiche Slack**: Aggiungi nodo Slack dopo "Has Issues?"
2. **Salva in DB**: Aggiungi nodo PostgreSQL/MongoDB per storico
3. **Email Report**: Invia report via email se ci sono HIGH severity issues
4. **Agent 3 Trigger**: Se VALID, chiama automaticamente Agent 3

## File Locations

- **Workflow JSON**: `n8n/workflow_example.json`
- **README N8N**: `n8n/README.md`
- **Test Input**: `input_agent/example_bad.json`
