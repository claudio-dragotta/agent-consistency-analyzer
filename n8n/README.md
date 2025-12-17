# Integrazione Agent 2 con n8n

## Quick Start

### 1. Importa il workflow di esempio

1. Apri n8n
2. Vai su **Workflows** → **Import from File**
3. Seleziona `n8n/workflow_example.json`

### 2. Configura la connessione

Se n8n gira in Docker e Agent 2 è sul tuo PC:

```
# Invece di localhost, usa:
URL: http://host.docker.internal:8002/analyze
```

Se entrambi sono sullo stesso PC:
```
URL: http://localhost:8002/analyze
```

---

## Nodi n8n per Agent 2

### Nodo: HTTP Request (Analisi Base)

```json
{
  "Method": "POST",
  "URL": "http://localhost:8002/analyze",
  "Headers": {
    "Content-Type": "application/json"
  },
  "Body": {
    "domain_model": "{{ $json.domain_model }}",
    "use_llm": true,
    "apply_auto_fixes": true
  },
  "Timeout": 120000
}
```

### Nodo: HTTP Request (Health Check)

```json
{
  "Method": "GET",
  "URL": "http://localhost:8002/health"
}
```

### Nodo: HTTP Request (Agent Card A2A)

```json
{
  "Method": "GET",
  "URL": "http://localhost:8002/.well-known/agent.json"
}
```

---

## Esempio di Workflow Completo

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌────────────┐
│   Trigger   │───▶│  Agent 2     │───▶│  Check      │───▶│  Process   │
│  (Webhook)  │    │  Analyze     │    │  Issues     │    │  Results   │
└─────────────┘    └──────────────┘    └─────────────┘    └────────────┘
                                              │
                                              ▼
                                       ┌─────────────┐
                                       │   Send      │
                                       │   Email/    │
                                       │   Slack     │
                                       └─────────────┘
```

---

## Test con cURL

Prima di configurare n8n, testa che l'API funzioni:

```bash
# Health check
curl http://localhost:8002/health

# Analisi completa
curl -X POST http://localhost:8002/analyze \
  -H "Content-Type: application/json" \
  -d @input_agent/example_bad.json
```

---

## Configurazione per Docker

Se usi Docker per n8n, aggiungi questa rete:

```yaml
# docker-compose.yml per n8n
version: '3.8'
services:
  n8n:
    image: n8nio/n8n
    ports:
      - "5678:5678"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - N8N_HOST=localhost
      - WEBHOOK_URL=http://localhost:5678/
```

Poi usa `http://host.docker.internal:8002` come URL.

---

## Response Structure

La risposta di Agent 2 include:

```json
{
  "status": "ISSUES_FOUND",
  "task_id": "uuid",
  "summary": {
    "total_issues": 23,
    "entity_overlaps": 3,
    "semantic_ambiguities": 17,
    "requirement_conflicts": 2,
    "duplicate_events": 0,
    "naming_violations": 0,
    "incompatible_patterns": 0,
    "misclassified_domains": 1,
    "auto_fixed": 0,
    "requires_manual": 23
  },
  "semantic_issues": [...],
  "conflict_issues": [...],
  "follow_up_questions": [...],
  "refined_model": {...}
}
```

### Campi utili per n8n:

| Campo | Path | Descrizione |
|-------|------|-------------|
| Status | `$json.status` | "VALID" o "ISSUES_FOUND" |
| Totale Issues | `$json.summary.total_issues` | Numero totale problemi |
| Domande | `$json.follow_up_questions` | Array di domande |
| Modello Raffinato | `$json.refined_model` | Per passare ad Agent 3 |

---

## Workflow con Notifiche

Per inviare notifiche quando ci sono problemi:

1. **IF Node**: `{{ $json.summary.total_issues > 0 }}`
2. **Slack/Email Node**: Invia il summary
3. **Set Node**: Estrai i campi importanti

```javascript
// Expression per messaggio Slack
`🔍 Analisi DDD completata!
📊 Trovati ${$json.summary.total_issues} problemi:
  - Entity Overlap: ${$json.summary.entity_overlaps}
  - Ambiguità: ${$json.summary.semantic_ambiguities}
  - Conflitti: ${$json.summary.requirement_conflicts}
  
❓ Domande di follow-up: ${$json.follow_up_questions.length}`
```
