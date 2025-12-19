# Workflow Interactive Loop - Guida Completa

## Cosa Fa Questo Workflow

`workflow_complete_loop.json` implementa un **loop interattivo completo** dove Agent 2:

1. Analizza il modello funzionale
2. Trova problemi e genera domande
3. Mostra un form HTML per le risposte
4. Raccoglie le risposte dell'utente
5. Ri-analizza il modello con le nuove informazioni
6. Ripete fino a quando il modello è perfetto (max 5 iterazioni)

## Setup Iniziale

### 1. Avvia i Servizi

```powershell
.\START_DEMO.bat
```

Aspetta che tutti i servizi siano attivi (30-60 secondi).

### 2. Importa il Workflow in n8n

1. Apri: http://127.0.0.1:5678
2. Login (email: `demo@test.com`, password: `password123`)
3. Clicca "Workflows" → "Import from File"
4. Seleziona: `n8n/workflow_complete_loop.json`
5. Clicca "Save" per salvare il workflow

### 3. Attiva il Workflow

**IMPORTANTE:** Il workflow usa un webhook, quindi deve essere attivo.

1. Apri il workflow importato
2. Clicca l'interruttore in alto a destra per attivarlo (deve diventare verde)
3. Il workflow è ora pronto a ricevere richieste

## Come Usare il Workflow

### Metodo 1: Usa il File Demo (Raccomandato)

**Da PowerShell:**

```powershell
cd C:\Users\TUO_USERNAME\Desktop\agent-consistency-analyzer

# Invia il file demo al webhook
curl -X POST http://127.0.0.1:5678/webhook/agent2-start `
  -H "Content-Type: application/json" `
  -d "@input_agent/example_demo.json"
```

**Risultato:**
- Si apre una pagina HTML con il form
- Vedi i problemi trovati
- Vedi le domande generate
- Rispondi alle domande
- Il workflow continua automaticamente

### Metodo 2: Apri Direttamente nel Browser

1. Prepara il modello JSON (usa `input_agent/example_demo.json` come riferimento)
2. Apri: http://127.0.0.1:5678/webhook/agent2-start
3. Fai un POST con il JSON del modello

**Con curl:**

```bash
curl -X POST http://127.0.0.1:5678/webhook/agent2-start \
  -H "Content-Type: application/json" \
  -d '{
    "domain_model": { ... },
    "use_llm": true,
    "apply_auto_fixes": true
  }'
```

### Metodo 3: Integrazione con Agent 1

Configura Agent 1 per inviare il modello generato a:

```
POST http://127.0.0.1:5678/webhook/agent2-start
```

Agent 1 → Webhook Agent 2 → Form HTML → User → Agent 2 → Loop

## Struttura del Form HTML

### Pagina di Domande

Il form HTML mostra:

1. **Header**
   - Badge con numero iterazione
   - Titolo con status

2. **Summary Card**
   - Numero totale problemi
   - Breakdown per categoria (entity overlaps, conflicts, violations)

3. **Question Cards**
   - Domanda con badge severity (HIGH, CRITICAL, etc.)
   - Campo textarea per la risposta
   - Risposte suggerite (in grigio)

4. **Action Buttons**
   - Submit: Invia risposte e continua il loop
   - Loading state durante invio

### Pagina di Successo

Quando il modello è valido:

- Badge verde "SUCCESS"
- Statistiche finali (iterazioni, problemi risolti)
- Link per tornare a n8n o vedere Kafka UI

### Pagina di Errore

Se si raggiunge il limite di 5 iterazioni:

- Badge rosso "MAX ITERATIONS"
- Messaggio di errore
- Link per ricominciare

## Formato JSON Richiesto

### Request Iniziale

```json
{
  "domain_model": {
    "metadata": { ... },
    "domainMap": { ... },
    "eventDrivenModel": { ... }
  },
  "use_llm": true,
  "apply_auto_fixes": true
}
```

### Request con Risposte (gestito automaticamente dal form)

```json
{
  "session_id": "2025-12-18T10:00:00.000Z",
  "iteration": 1,
  "max_iterations": 5,
  "domain_model": { ... },
  "answers": {
    "q0": "Risposta alla prima domanda",
    "q1": "Risposta alla seconda domanda"
  }
}
```

## Architettura del Workflow

### Nodi Principali

1. **START - Webhook Principale**
   - Riceve POST con modello o risposte
   - URL: `/webhook/agent2-start`

2. **Prepara Dati Iterazione**
   - Estrae iteration count
   - Genera session_id se nuovo
   - Prepara previous_answers

3. **Check Limite Iterazioni**
   - Verifica se iteration < 5
   - Se >= 5, mostra pagina di errore

4. **Chiama Agent 2 API**
   - POST a `http://host.docker.internal:8002/analyze`
   - Passa modello + previous_answers
   - Timeout: 120 secondi

5. **Merge Contesto**
   - Combina risultati API con dati sessione
   - Preserva session_id e iteration

6. **Check Validazione**
   - Se status === "VALID": pagina successo
   - Se status === "ISSUES_FOUND": form domande

7. **Form HTML Domande**
   - Genera HTML dinamico
   - JavaScript per async submission
   - POST back allo stesso webhook

8. **Respond to Webhook**
   - Restituisce HTML al browser

### Flow Ricorsivo

```
Webhook → Prepara → Check Iterazioni → API Call → Merge → Check Status
                                                              ↓
                                                         Form HTML
                                                              ↓
                                                    User risponde
                                                              ↓
                                                     POST a Webhook
                                                              ↓
                                                      (Loop ricomincia)
```

## Monitoraggio

### Vedi Log in n8n

1. Apri il workflow
2. Clicca "Executions" (icona lista in alto)
3. Vedi tutte le esecuzioni con status
4. Clicca su un'esecuzione per vedere i dettagli

### Vedi Messaggi Kafka

1. Apri: http://localhost:8080
2. Vai a "Topics" → `agent2-analysis-results`
3. Vedi i messaggi pubblicati da Agent 2

### Vedi API Logs

```powershell
docker logs agent2-api -f
```

## Troubleshooting

### Il webhook non risponde

**Problema:** 404 Not Found quando fai POST

**Soluzione:**
1. Verifica che il workflow sia **attivo** (interruttore verde)
2. Verifica l'URL esatto del webhook nel nodo "START - Webhook Principale"
3. Riavvia n8n: `docker restart agent2-n8n`

### Il form non si carica

**Problema:** Timeout o pagina bianca

**Soluzione:**
1. Verifica che Agent 2 API sia attivo: `docker ps | grep agent2-api`
2. Testa l'API: `curl http://localhost:8002/health`
3. Verifica Ollama: `ollama list` (deve mostrare llama3)

### Le risposte non vengono processate

**Problema:** Submit del form non fa nulla

**Soluzione:**
1. Apri Developer Tools (F12) → Console
2. Vedi errori JavaScript
3. Verifica che il POST raggiunga il webhook
4. Controlla i log n8n

### Iterazioni infinite

**Problema:** Il workflow non si ferma mai

**Soluzione:**
- Il workflow ha un safety limit di 5 iterazioni
- Se raggiunge il limite, mostra pagina di errore
- Verifica che Agent 2 stia effettivamente migliorando il modello

### Form HTML non formattato

**Problema:** Il CSS non viene applicato

**Soluzione:**
- Il CSS è embedded nell'HTML
- Verifica che il nodo "Generate HTML Form" non sia stato modificato
- Ricontrolla il workflow originale

## Personalizzazione

### Cambia il Numero di Iterazioni

Nel nodo "Prepara Dati Iterazione":

```javascript
"max_iterations": 5  // Cambia a 10, 3, etc.
```

### Cambia Stile Form HTML

Nel nodo "Generate HTML Form", modifica il CSS:

```css
/* Cambia colori */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

### Cambia Timeout API

Nel nodo "Chiama Agent 2 API":

```json
"options": {
  "timeout": 120000  // 120 secondi (120000 ms)
}
```

### Aggiungi Logging Custom

Inserisci nodo "Code" dopo qualsiasi nodo:

```javascript
console.log('Debug:', $input.item.json);
return $input.all();
```

## Best Practices

1. **Testa sempre con workflow_demo_simple.json prima**
   - Verifica che Agent 2 funzioni correttamente
   - Controlla che Ollama risponda

2. **Attiva il workflow prima di usarlo**
   - I webhook richiedono workflow attivi
   - Interruttore verde in alto a destra

3. **Monitora le iterazioni**
   - Controlla i log per capire come migliora il modello
   - Usa Kafka UI per vedere i messaggi

4. **Usa session_id per tracciare conversazioni**
   - Ogni sessione ha un ID univoco
   - Utile per debugging

5. **Rispetta il safety limit**
   - Non aumentare troppo max_iterations
   - Previene loop infiniti
   - Protegge risorse sistema

## Integrazione con Pipeline Completa

### Agent 1 → Agent 2 (questo workflow) → Agent 3

1. **Agent 1** genera il modello iniziale
2. Agent 1 fa POST a `http://127.0.0.1:5678/webhook/agent2-start`
3. **Agent 2** valida e genera domande
4. User risponde via form HTML
5. Agent 2 raffina il modello
6. Quando valido, Agent 2 pubblica su Kafka topic `agent2-analysis-results`
7. **Agent 3** consuma il topic e genera specifiche funzionali

## Esempi di Uso

### Esempio 1: Test Rapido con Demo File

```powershell
curl -X POST http://127.0.0.1:5678/webhook/agent2-start `
  -H "Content-Type: application/json" `
  -d "@input_agent/example_demo.json"
```

**Output:** Form HTML con 3 problemi

### Esempio 2: Modello Custom

```powershell
curl -X POST http://127.0.0.1:5678/webhook/agent2-start `
  -H "Content-Type: application/json" `
  -d '{
    "domain_model": {
      "metadata": {"modelId": "test-001"},
      "domainMap": {"coreDomains": [...]},
      "eventDrivenModel": {"events": [...]}
    },
    "use_llm": true,
    "apply_auto_fixes": true
  }'
```

### Esempio 3: Da Postman

1. Apri Postman
2. Crea nuova request POST
3. URL: `http://127.0.0.1:5678/webhook/agent2-start`
4. Headers: `Content-Type: application/json`
5. Body: Raw JSON (copia da `input_agent/example_demo.json`)
6. Send

## Link Utili

- **n8n**: http://127.0.0.1:5678
- **Webhook URL**: http://127.0.0.1:5678/webhook/agent2-start
- **Agent 2 API Docs**: http://localhost:8002/docs
- **Kafka UI**: http://localhost:8080

## Supporto

Per problemi o domande:

1. Controlla la sezione Troubleshooting del README principale
2. Verifica i log Docker: `docker logs agent2-api -f`
3. Verifica le execution history in n8n
