# Agent 2 - Consistency & Conflict Analyzer

## Indice

1. [Cos'è Agent 2](#cosè-agent-2)
2. [Architettura della Pipeline](#architettura-della-pipeline)
3. [Cosa Fa Esattamente Agent 2](#cosa-fa-esattamente-agent-2)
4. [Setup Completo Passo-Passo](#setup-completo-passo-passo)
5. [Come Usare Agent 2](#come-usare-agent-2)
6. [Integrazione con Agent 1 e Agent 3](#integrazione-con-agent-1-e-agent-3)
7. [Deployment Production](#deployment-production)
8. [Testing e Troubleshooting](#testing-e-troubleshooting)
9. [Esempi Pratici](#esempi-pratici)

---

## Cos'è Agent 2

**Agent 2 - Consistency & Conflict Analyzer** è un agente intelligente specializzato nella validazione di modelli Domain-Driven Design (DDD). È il secondo componente di una pipeline di 3 agenti collaborativi che automatizzano la progettazione di architetture a microservizi.

### Il Problema che Risolve

Quando si progetta un sistema complesso seguendo DDD, è facile commettere errori come:
- Definire la stessa entità in contesti diversi
- Creare requisiti contraddittori
- Usare pattern di comunicazione incompatibili
- Classificare male i domini (Core vs Supporting vs Generic)
- Definire eventi con emittenti multipli
- Usare nomenclature inconsistenti

**Agent 2 trova automaticamente questi problemi** e genera domande mirate per risolverli con il business.

### Tecnologie Utilizzate

- **Python 3.11+**: Linguaggio principale
- **FastAPI**: Web framework per API REST
- **Kafka**: Message queue per comunicazione tra agenti
- **Ollama + Llama3**: LLM locale per analisi semantica
- **Sentence Transformers**: Per embeddings e similarity
- **Docker**: Containerizzazione production-ready

---

## Architettura della Pipeline

### I Tre Agenti

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   AGENT 1       │      │   AGENT 2       │      │   AGENT 3       │
│                 │      │                 │      │                 │
│ Domain          │─────▶│ Consistency &   │─────▶│ Functional      │
│ Interviewer &   │Kafka │ Conflict        │Kafka │ Specification   │
│ Modeler         │      │ Analyzer        │      │ Generator       │
│                 │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
       │                        │                        │
       │                        │                        │
   Intervista              Valida e              Genera Specs
    Business                Corregge             Funzionali
    Stakeholders            Modello              per Sviluppo
```

### Flusso Dati

1. **Agent 1** intervista gli stakeholder e genera un domain model (JSON)
2. **Agent 1** pubblica il model su Kafka topic `agent1-output`
3. **Agent 2** (questo progetto) consuma il model da Kafka
4. **Agent 2** esegue 23 validazioni automatiche
5. **Agent 2** corregge automaticamente errori semplici
6. **Agent 2** genera domande per errori complessi
7. **Agent 2** pubblica risultato validato su Kafka topic `agent2-output`
8. **Agent 3** consuma il model validato e genera specifiche funzionali

### Comunicazione via Kafka

Kafka garantisce:
- **Persistenza**: I messaggi non si perdono
- **Scalabilità**: Gestisce migliaia di messaggi
- **Disaccoppiamento**: Gli agenti non devono essere tutti online simultaneamente
- **Tracciabilità**: Ogni messaggio ha un ID univoco

---

## Cosa Fa Esattamente Agent 2

### Funzionalità Principali

#### 1. Analisi Semantica (Semantic Analyzer)
- Calcola embeddings di entità e concetti usando Sentence Transformers
- Rileva sovrapposizioni semantiche tra bounded context
- Identifica entità duplicate con nomi diversi (es. "Cliente" vs "Utente")
- Usa cosine similarity con threshold configurabile (default: 0.75)

**Esempio di problema rilevato:**
```
Issue: ENTITY_OVERLAP
Severity: HIGH
Description: L'entità "Product" è definita in 2 bounded context:
  - CatalogContext: Product (catalogo completo)
  - OrderContext: Product (solo dati d'ordine)
Raccomandazione: Usa rappresentazioni separate o crea un context condiviso
```

#### 2. Rilevamento Conflitti (Conflict Detector)
- Usa Llama3 via Ollama per analisi logica
- Rileva contraddizioni tra requisiti
- Identifica incompatibilità nei pattern di comunicazione
- Verifica coerenza tra invarianti

**Esempio di problema rilevato:**
```
Issue: REQUIREMENT_CONFLICT
Severity: HIGH
Description: Conflitto tra requisiti:
  - FR-ORD-002: "L'ordine deve essere immutabile dopo conferma"
  - FR-ORD-003: "L'utente può modificare l'ordine entro 24h"
Raccomandazione: Chiarire la finestra temporale per le modifiche
```

#### 3. Validazione Architettura Eventi (Event Architecture)
- Verifica che ogni evento abbia UN SOLO emittente
- Controlla naming convention (es. `DomainEvent` suffix)
- Valida completezza payload degli eventi
- Verifica pattern publish/subscribe correttamente

**Esempio di problema rilevato:**
```
Issue: MULTIPLE_EMITTERS
Severity: CRITICAL
Description: L'evento "OrderCreated" è emesso da:
  - OrderService
  - PaymentService
Raccomandazione: Solo OrderService dovrebbe emettere OrderCreated
```

#### 4. Generazione Domande (Question Generator)
- Genera massimo 5 domande prioritizzate per severity
- Usa template specifici per tipo di errore
- Include suggested_answers per guidare stakeholder
- Contestualizza ogni domanda

**Esempio di domanda generata:**
```
Question ID: FUQ-001
Question: "L'entità 'Product' appare in OrderContext e CatalogContext.
          Rappresentano lo stesso concetto o due aspetti diversi?"
Context: Multi-context entity definition
Severity: HIGH
Suggested Answers:
  - "Stesso concetto, unificare in ProductContext condiviso"
  - "Aspetti diversi, rinominare in OrderItem e CatalogProduct"
  - "Usare Product come aggregate root condiviso"
```

#### 5. Raffinamento Modello (Model Refiner)
- Applica correzioni automatiche per errori semplici
- Normalizza naming conventions
- Rimuove duplicati ovvi
- Produce un `refined_model` pronto per Agent 3

**Correzioni automatiche:**
- Standardizza nomi eventi (aggiunge suffix "Event")
- Rimuove spazi extra e normalizza case
- Corregge piccoli errori sintattici
- Aggiunge campi mancanti obbligatori

### Le 23 Regole di Validazione

Organizzate in 7 categorie:

| Categoria | Regole | Esempi di Controlli |
|-----------|--------|---------------------|
| **Domain Classification (DC)** | 3 | Core vs Supporting vs Generic, Value proposition check |
| **Bounded Context (BC)** | 3 | Ubiquitous language, Context boundaries, Overlaps |
| **Entity/Value Object (EVO)** | 3 | Identity requirement, Immutability, Lifecycle |
| **Entity Ownership (EO)** | 3 | Single source of truth, Responsibility clarity |
| **Requirement Consistency (RC)** | 3 | No logical contradictions, Invariant compatibility |
| **Event Architecture (EA)** | 4 | Single emitter, Naming, Payload completeness |
| **Communication Patterns (CP)** | 3 | Pattern consistency, Bidirectional checks |

**Tutte le regole sono definite in:** `knowledge_base/validation_checklist.json`

---

## Setup Completo Passo-Passo

### Prerequisiti di Sistema

Prima di iniziare, assicurati di avere:

1. **Windows 10/11**, **macOS** o **Linux**
2. **8GB RAM minimo** (consigliati 16GB per LLM)
3. **20GB spazio disco** disponibile
4. **Connessione Internet** (per download dipendenze)

### Passo 1: Installa Docker Desktop

Docker è richiesto per il deployment production.

**Windows / macOS:**
1. Vai su https://www.docker.com/products/docker-desktop
2. Scarica Docker Desktop per il tuo sistema
3. Installa eseguendo il file scaricato
4. Avvia Docker Desktop
5. Verifica installazione:
   ```bash
   docker --version
   docker-compose --version
   ```

**Linux:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Riavvia la sessione
docker --version
```

### Passo 2: Installa Ollama + Llama3

Ollama esegue LLM localmente senza bisogno di API esterne.

**Windows:**
1. Vai su https://ollama.ai/download
2. Scarica "Ollama for Windows"
3. Installa eseguendo il file .exe
4. Apri PowerShell/CMD e scarica Llama3:
   ```bash
   ollama pull llama3
   ```
5. Verifica che funzioni:
   ```bash
   ollama run llama3 "Hello, are you working?"
   ```
6. Ollama ora gira su `http://localhost:11434`

**macOS:**
```bash
brew install ollama
ollama serve &  # Avvia in background
ollama pull llama3
ollama run llama3 "Test message"
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
systemctl start ollama
ollama pull llama3
ollama run llama3 "Test message"
```

### Passo 3: Clone del Repository

```bash
git clone https://github.com/yourusername/agent-consistency-analyzer.git
cd agent-consistency-analyzer
```

Se non hai il repository Git, estrai lo ZIP:
```bash
# Windows: Estrai lo ZIP e apri PowerShell nella cartella
cd path\to\agent-consistency-analyzer

# Linux/macOS
unzip agent-consistency-analyzer.zip
cd agent-consistency-analyzer
```

### Passo 4: Verifica Struttura File

Assicurati di avere questa struttura:

```
agent-consistency-analyzer/
├── Dockerfile                    # Configurazione Docker
├── docker-compose.prod.yml       # Orchestrazione servizi
├── .dockerignore                 # Ottimizzazione build
├── .env.docker                   # Template configurazione
├── docker-start.bat              # Script avvio (Windows)
├── docker-stop.bat               # Script stop
├── docker-test.bat               # Script test
├── docker-logs.bat               # Visualizza logs
├── docker-scale.bat              # Scaling consumer
├── README.md                     # Questa guida
├── requirements.txt              # Dipendenze Python
├── app/                          # Codice applicazione
├── a2a/                          # Modelli A2A protocol
├── knowledge_base/               # Regole DDD
├── input_agent/                  # Esempi input
└── n8n/                          # Workflow N8N (opzionale)
```

---

## Come Usare Agent 2

### Metodo 1: Deployment Production con Docker (CONSIGLIATO)

Questo è il metodo più semplice e robusto.

#### Avvio Sistema

```bash
# Windows
docker-start.bat

# Linux/macOS
chmod +x docker-start.bat
./docker-start.bat
```

**Cosa succede automaticamente:**
1. Crea file `.env` da template (se non esiste)
2. Ti chiede: "Avvia stack completo con N8N e Kafka UI? (s/N)"
   - **N** = Solo Agent 2 + Kafka (minimalista)
   - **S** = Include N8N (workflow) e Kafka UI (monitoring)
3. Build immagine Docker (~300MB, prima volta ci vogliono 5-10 minuti)
4. Avvia Zookeeper (coordinatore Kafka)
5. Avvia Kafka (message queue)
6. Avvia Agent 2 API (porta 8002)
7. Avvia Agent 2 Consumer (processa messaggi Kafka)
8. (Opzionale) Avvia N8N e Kafka UI

**Output finale:**
```
========================================
OK Deployment completato!
========================================

Servizi disponibili:
  - Agent 2 API:    http://localhost:8002
  - Health Check:   http://localhost:8002/health
  - API Docs:       http://localhost:8002/docs
  - N8N:            http://localhost:5678    (se avviato)
  - Kafka UI:       http://localhost:8080    (se avviato)
```

#### Verifica Funzionamento

```bash
# Windows
docker-test.bat

# Linux/macOS
./docker-test.bat
```

**Il test automatico verifica:**
1. Container Docker running
2. Health endpoint API
3. Agent Card (A2A protocol)
4. Analisi con file di esempio
5. Consumer Kafka attivo

**Output atteso:**
```
[1/5] Verifica containers in esecuzione...
agent2-api       Up 2 minutes (healthy)   0.0.0.0:8002->8002/tcp
agent2-consumer  Up 2 minutes
agent2-kafka     Up 2 minutes (healthy)

[2/5] Health check Agent 2 API...
{
  "status": "healthy",
  "version": "1.0.0"
}
OK Agent 2 API healthy

[3/5] Verifica Agent Card (A2A Protocol)...
"name": "agent-2-consistency-analyzer"
OK Agent Card OK

[4/5] Test analisi con example_bad.json...
OK Analisi completata
"status": "ISSUES_FOUND"
"total_issues": 23

[5/5] Verifica consumer Kafka...
OK Consumer attivo

========================================
Test completato!
========================================
```

#### Monitoraggio Logs

```bash
# Script interattivo
docker-logs.bat

# Seleziona container:
# 1. Agent 2 API
# 2. Agent 2 Consumer
# 3. Kafka Broker
# 4. Zookeeper
# 5. Tutti (interleaved)
# 6. N8N
# 7. Kafka UI
```

**Oppure manualmente:**
```bash
# Logs API
docker logs -f agent2-api

# Logs Consumer (vedi processing messaggi)
docker logs -f agent2-consumer

# Logs Kafka
docker logs -f agent2-kafka
```

#### Stop Sistema

```bash
docker-stop.bat

# Conferma: s
# Rimuovere volumi (dati)? N  (di solito lascia i dati)
```

### Metodo 2: Sviluppo Locale (Python Virtual Environment)

Usa questo metodo solo per sviluppo/debug.

#### Setup Ambiente

```bash
# Crea virtual environment
python -m venv venv

# Attiva (Windows)
.\venv\Scripts\activate

# Attiva (Linux/macOS)
source venv/bin/activate

# Installa dipendenze
pip install -r requirements.txt
```

#### Configura Environment

```bash
# Copia template
cp .env.example .env

# Modifica .env
notepad .env  # Windows
nano .env     # Linux/macOS
```

**Configurazione minima `.env`:**
```env
# Ollama (locale)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# Kafka (locale o Docker)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_INPUT_TOPIC=agent1-output
KAFKA_OUTPUT_TOPIC=agent2-output

# API
API_PORT=8002
LOG_LEVEL=INFO
```

#### Avvia Kafka Locale

```bash
# Con Docker (più semplice)
docker run -d --name kafka \
  -p 9092:9092 \
  apache/kafka:latest
```

#### Avvia Agent 2 API

```bash
# Modalità API (REST)
python -X utf8 -m uvicorn app.main:app --reload --port 8002

# Ora apri http://localhost:8002/docs
```

#### Avvia Agent 2 Consumer

```bash
# In un altro terminale
.\venv\Scripts\activate
python -m app.kafka.consumer_advanced
```

#### Test Locale

```bash
# Attiva venv
.\venv\Scripts\activate

# Esegui test
python -X utf8 test_agent.py
```

---

## Integrazione con Agent 1 e Agent 3

### Come Funziona l'Integrazione

#### Architettura Kafka

```
┌─────────────┐   Topic:        ┌─────────────┐   Topic:        ┌─────────────┐
│  AGENT 1    │   agent1-output │  AGENT 2    │   agent2-output │  AGENT 3    │
│             │──────────────────▶│             │──────────────────▶│             │
│ Interviewer │   JSON Model    │ Validator   │   Validated     │ Spec Gen    │
└─────────────┘                 └─────────────┘   Model         └─────────────┘
                                       │
                                       │ Correlation ID
                                       │ per tracciamento
                                       ▼
                                  Kafka Topic
                             (Persistent Queue)
```

#### Message Flow Completo

**1. Agent 1 produce messaggio:**
```json
{
  "message_id": "a1-msg-001",
  "timestamp": "2025-01-17T10:00:00Z",
  "agent": "agent-1-interviewer",
  "iteration": 1,
  "payload": {
    "domain_model": {
      "metadata": {
        "modelId": "dm-ecommerce-001",
        "version": "1.0",
        "createdAt": "2025-01-17T10:00:00Z"
      },
      "domainMap": {
        "coreDomains": [
          {
            "name": "Order Management",
            "description": "Gestione ordini clienti",
            "boundedContexts": [...]
          }
        ]
      }
    }
  }
}
```

**2. Agent 2 consuma e valida:**
- Legge messaggio da topic `agent1-output`
- Estrae `domain_model` dal payload
- Esegue 23 validazioni
- Genera domande se necessario
- Corregge errori automaticamente

**3. Agent 2 produce risultato:**
```json
{
  "message_id": "a2-msg-001",
  "correlation_id": "a1-msg-001",  // LINK all'input!
  "timestamp": "2025-01-17T10:00:15Z",
  "agent": "agent-2-consistency-analyzer",
  "status": "COMPLETED",
  "payload": {
    "validation_status": "ISSUES_FOUND",
    "summary": {
      "total_issues": 5,
      "entity_overlaps": 2,
      "requirement_conflicts": 1,
      "auto_fixed": 1,
      "requires_manual": 4
    },
    "semantic_issues": [...],
    "conflict_issues": [...],
    "follow_up_questions": [...],
    "refined_model": {
      // Model corretto pronto per Agent 3
    }
  }
}
```

**4. Agent 3 consuma risultato:**
- Legge da topic `agent2-output`
- Usa `refined_model` per generare specifiche
- Mantiene `correlation_id` per tracciabilità

### Setup Integrazione Completa

#### Scenario 1: Tutti gli Agenti in Docker

**docker-compose.full.yml** (esempio completo):
```yaml
version: '3.8'

services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092

  agent1:
    image: agent1-interviewer:latest
    environment:
      KAFKA_OUTPUT_TOPIC: agent1-output
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092

  agent2-api:
    image: agent2-consistency-analyzer:latest
    ports:
      - "8002:8002"
    environment:
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      KAFKA_INPUT_TOPIC: agent1-output
      KAFKA_OUTPUT_TOPIC: agent2-output

  agent2-consumer:
    image: agent2-consistency-analyzer:latest
    command: ["python", "-m", "app.kafka.consumer_advanced"]
    environment:
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      KAFKA_INPUT_TOPIC: agent1-output
      KAFKA_OUTPUT_TOPIC: agent2-output

  agent3:
    image: agent3-spec-generator:latest
    environment:
      KAFKA_INPUT_TOPIC: agent2-output
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
```

**Avvio:**
```bash
docker-compose -f docker-compose.full.yml up -d
```

#### Scenario 2: Agent 2 Standalone (Altri Agenti Separati)

Se Agent 1 e Agent 3 girano altrove, configura solo connessione Kafka:

**Nel .env di Agent 2:**
```env
# Kafka condiviso (può essere remoto)
KAFKA_BOOTSTRAP_SERVERS=kafka.example.com:9092
KAFKA_INPUT_TOPIC=agent1-output
KAFKA_OUTPUT_TOPIC=agent2-output
KAFKA_GROUP_ID=agent2-consistency-analyzer

# Oppure localhost se Kafka locale
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

**Avvio Agent 2:**
```bash
docker-start.bat
```

Agent 2 automaticamente:
- Si connette a Kafka
- Crea topic se non esistono
- Consuma messaggi da `agent1-output`
- Pubblica su `agent2-output`

### Tracciamento End-to-End

Ogni messaggio mantiene tracciabilità completa:

```
Agent 1 Message ID: a1-msg-001
       ↓
Agent 2 Correlation ID: a1-msg-001
Agent 2 Message ID: a2-msg-001
       ↓
Agent 3 Correlation ID: a2-msg-001
Agent 3 Message ID: a3-msg-001

Chain completa: a1-msg-001 → a2-msg-001 → a3-msg-001
```

**Per tracciare un messaggio specifico:**
```bash
# Vedi logs Agent 2 per correlation_id
docker logs agent2-consumer | grep "a1-msg-001"

# Output:
# [2025-01-17 10:00:15] Processing message a1-msg-001
# [2025-01-17 10:00:18] Found 5 issues in a1-msg-001
# [2025-01-17 10:00:20] Published result a2-msg-001 (correlation: a1-msg-001)
```

### Test Integrazione con Simulatore

**simulate_agent1.py** simula Agent 1 per testing:

```bash
# Attiva venv
.\venv\Scripts\activate

# Simula 10 messaggi da Agent 1
python simulate_agent1.py

# Output:
# Sent message 1/10: a1-msg-abc123
# Sent message 2/10: a1-msg-def456
# ...
# OK 10 messages sent to agent1-output
```

**Monitora processing:**
```bash
# Vedi Agent 2 processare
docker logs -f agent2-consumer

# Output:
# [INFO] Consumed message a1-msg-abc123
# [INFO] Semantic analysis... found 3 issues
# [INFO] Conflict detection... found 1 conflict
# [INFO] Generated 2 questions
# [INFO] Published result a2-msg-xyz789
```

### API Diretta (Bypass Kafka)

Per test rapidi senza Kafka:

```bash
curl -X POST http://localhost:8002/analyze \
  -H "Content-Type: application/json" \
  -d @input_agent/example_bad.json
```

**Risposta immediata (JSON):**
```json
{
  "status": "ISSUES_FOUND",
  "task_id": "uuid-v4",
  "summary": {...},
  "semantic_issues": [...],
  "follow_up_questions": [...]
}
```

---

## Deployment Production

### Scalabilità

Agent 2 può scalare orizzontalmente per gestire carichi elevati.

#### Scenario: Agent 1 genera 100+ model/minuto

**Problema:** Un solo consumer non riesce a processare abbastanza velocemente

**Soluzione:** Scala i consumer

```bash
# Script automatico
docker-scale.bat

# Inserisci numero di consumer: 5

# Risultato:
# - 5 consumer attivi
# - 5 x 4 workers = 20 analisi parallele
# - Throughput: ~50 analisi/minuto
```

**Manualmente:**
```bash
docker-compose -f docker-compose.prod.yml up -d --scale agent2-consumer=10

# 10 consumer x 4 workers = 40 parallele = ~100 analisi/min
```

#### Configurazione Resource Limits

In `docker-compose.prod.yml`:

```yaml
agent2-consumer:
  deploy:
    resources:
      limits:
        cpus: '4.0'      # Max CPU per consumer
        memory: 4G       # Max RAM
      reservations:
        cpus: '2.0'      # Min garantito
        memory: 2G
    replicas: 3          # Numero di consumer
```

### Cloud Deployment

#### AWS ECS

1. **Build e push immagine:**
```bash
docker build -t agent2-consistency-analyzer:latest .
docker tag agent2-consistency-analyzer:latest <account>.dkr.ecr.us-east-1.amazonaws.com/agent2:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/agent2:latest
```

2. **Crea ECS Task Definition** con variabili ambiente
3. **Deploy come ECS Service** con auto-scaling

#### Google Cloud Run

```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/agent2
gcloud run deploy agent2 \
  --image gcr.io/PROJECT_ID/agent2 \
  --platform managed \
  --set-env-vars KAFKA_BOOTSTRAP_SERVERS=kafka.example.com:9092
```

#### Azure Container Instances

```bash
az container create \
  --resource-group myResourceGroup \
  --name agent2 \
  --image myregistry.azurecr.io/agent2:latest \
  --environment-variables \
    KAFKA_BOOTSTRAP_SERVERS=kafka.example.com:9092 \
    OLLAMA_BASE_URL=http://ollama:11434
```

### Kubernetes

**Converti Docker Compose:**
```bash
# Installa kompose
curl -L https://github.com/kubernetes/kompose/releases/download/v1.31.0/kompose-linux-amd64 -o kompose
chmod +x kompose

# Converti
kompose convert -f docker-compose.prod.yml

# Deploy
kubectl apply -f agent2-api-deployment.yaml
kubectl apply -f agent2-consumer-deployment.yaml
```

**Scaling in Kubernetes:**
```bash
kubectl scale deployment agent2-consumer --replicas=10
```

### Monitoring Production

#### Prometheus + Grafana

**Esponi metriche in Agent 2:**
```python
# app/main.py
from prometheus_client import Counter, Histogram, make_asgi_app

validation_counter = Counter('agent2_validations_total', 'Total validations')
processing_time = Histogram('agent2_processing_seconds', 'Processing time')

app.mount("/metrics", make_asgi_app())
```

**Configurazione Prometheus:**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'agent2'
    static_configs:
      - targets: ['agent2-api:8002']
```

#### Kafka Monitoring

```bash
# Avvia Kafka UI (opzionale durante docker-start.bat)
# Oppure standalone:
docker run -d -p 8080:8080 \
  -e KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS=kafka:9092 \
  provectuslabs/kafka-ui:latest

# Apri http://localhost:8080
```

**Vedi:**
- Topic `agent1-output`: Messaggi in attesa
- Topic `agent2-output`: Risultati pubblicati
- Consumer groups: Offset e lag
- Message throughput

---

## Testing e Troubleshooting

### Testing

#### Test Automatico Completo

```bash
docker-test.bat
```

**Verifica:**
- Container health
- API endpoints
- Analisi funzionante
- Consumer attivo

#### Test Manuale con File di Esempio

**File disponibili:**
- `input_agent/example_good.json` - Model valido
- `input_agent/example_bad.json` - Model con 23 errori

```bash
# Test model valido (pochi issue)
curl -X POST http://localhost:8002/analyze \
  -H "Content-Type: application/json" \
  -d @input_agent/example_good.json

# Test model invalido (molti issue)
curl -X POST http://localhost:8002/analyze \
  -H "Content-Type: application/json" \
  -d @input_agent/example_bad.json
```

#### Test Kafka Flow

```bash
# 1. Simula Agent 1
python simulate_agent1.py

# 2. Monitora Consumer
docker logs -f agent2-consumer

# 3. Verifica output topic
docker exec -it agent2-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic agent2-output \
  --from-beginning
```

### Troubleshooting

#### Problema: Container non si avvia

```bash
# Vedi errori
docker logs agent2-api

# Verifica configurazione
docker-compose -f docker-compose.prod.yml config

# Restart
docker restart agent2-api
```

**Errori comuni:**
- **Port già in uso**: Cambia `API_PORT` in .env
- **Ollama non raggiungibile**: Verifica `OLLAMA_BASE_URL`
- **Out of memory**: Aumenta `memory` in docker-compose.prod.yml

#### Problema: Kafka connection error

```bash
# Verifica Kafka healthy
docker exec agent2-kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Ricrea topic se necessario
docker exec agent2-kafka kafka-topics --create \
  --topic agent1-output \
  --bootstrap-server localhost:9092 \
  --partitions 4 \
  --replication-factor 1
```

#### Problema: LLM molto lento

**Cause possibili:**
- CPU insufficiente
- Modello troppo grande per RAM

**Soluzioni:**
```env
# Usa modello più piccolo in .env
OLLAMA_MODEL=phi  # invece di llama3

# Oppure aumenta timeout
OLLAMA_TIMEOUT=300
```

#### Problema: API restituisce 500 Internal Error

```bash
# Vedi stack trace
docker logs agent2-api

# Testa health
curl http://localhost:8002/health

# Se health OK ma analyze fallisce, verifica input JSON
python -m json.tool < input_agent/example_bad.json
```

#### Logs di Debug

**Abilita debug logging:**
```env
# In .env
LOG_LEVEL=DEBUG
```

**Restart container:**
```bash
docker restart agent2-api agent2-consumer
```

**Vedi logs dettagliati:**
```bash
docker logs -f agent2-consumer

# Output debug:
# [DEBUG] Received message: {...}
# [DEBUG] Semantic analyzer processing 15 entities
# [DEBUG] Found overlap: Product in 2 contexts
# [DEBUG] LLM prompt: {...}
# [DEBUG] LLM response: {...}
```

---

## Esempi Pratici

### Esempio 1: E-Commerce Platform

**Input da Agent 1 (domain model):**
```json
{
  "domainMap": {
    "coreDomains": [
      {
        "name": "Order Management",
        "boundedContexts": [
          {
            "name": "OrderContext",
            "entities": [
              {"name": "Order", "type": "ENTITY"},
              {"name": "Product", "type": "ENTITY"}
            ]
          }
        ]
      },
      {
        "name": "Product Catalog",
        "boundedContexts": [
          {
            "name": "CatalogContext",
            "entities": [
              {"name": "Product", "type": "ENTITY"},
              {"name": "Category", "type": "ENTITY"}
            ]
          }
        ]
      }
    ]
  }
}
```

**Output di Agent 2:**
```json
{
  "status": "ISSUES_FOUND",
  "summary": {
    "total_issues": 1,
    "entity_overlaps": 1
  },
  "semantic_issues": [
    {
      "issue_type": "ENTITY_OVERLAP",
      "severity": "HIGH",
      "description": "Entity 'Product' defined in multiple contexts",
      "affected_elements": ["Product"],
      "contexts": ["OrderContext", "CatalogContext"],
      "similarity_score": 0.92,
      "recommendation": "Consider: 1) Create shared ProductContext, 2) Use different names (OrderItem vs CatalogProduct), 3) Use Product as aggregate root"
    }
  ],
  "follow_up_questions": [
    {
      "question_id": "FUQ-001",
      "question": "The entity 'Product' appears in both OrderContext and CatalogContext. Do they represent the same concept or different aspects of products?",
      "severity": "HIGH",
      "suggested_answers": [
        "Same concept - create shared ProductContext",
        "Different aspects - rename to OrderItem and CatalogProduct",
        "Product is aggregate root - keep in CatalogContext, reference from OrderContext"
      ]
    }
  ]
}
```

**Azioni Stakeholder:**
Risponde "Different aspects", quindi Agent 2 (in iterazione successiva) rinomina:
- `OrderContext.Product` → `OrderItem`
- `CatalogContext.Product` → `CatalogProduct`

### Esempio 2: Event Architecture Issue

**Input:**
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

**Output:**
```json
{
  "status": "ISSUES_FOUND",
  "summary": {
    "event_architecture_violations": 1
  },
  "conflict_issues": [
    {
      "conflict_type": "MULTIPLE_EMITTERS",
      "severity": "CRITICAL",
      "description": "Event 'OrderCreated' has multiple emitters",
      "affected_elements": ["OrderCreated"],
      "emitters": ["OrderService", "PaymentService"],
      "recommendation": "Apply Single Emitter Rule: Only OrderService should emit OrderCreated. PaymentService can emit PaymentConfirmed instead."
    }
  ]
}
```

**Auto-fix applicato:**
```json
{
  "refined_model": {
    "eventDrivenModel": {
      "events": [
        {
          "name": "OrderCreated",
          "emitters": ["OrderService"],  // Fixed!
          "subscribers": ["InventoryService", "PaymentService"]
        },
        {
          "name": "PaymentConfirmed",  // New event
          "emitters": ["PaymentService"],
          "subscribers": ["OrderService"]
        }
      ]
    }
  }
}
```

### Esempio 3: Requirement Conflict

**Input:**
```json
{
  "domainMap": {
    "coreDomains": [
      {
        "functionalRequirements": [
          {
            "id": "FR-001",
            "description": "Orders must be immutable after confirmation"
          },
          {
            "id": "FR-002",
            "description": "Users can modify order items within 24 hours"
          }
        ]
      }
    ]
  }
}
```

**Output:**
```json
{
  "conflict_issues": [
    {
      "conflict_type": "REQUIREMENT_CONFLICT",
      "severity": "HIGH",
      "description": "Immutability conflicts with modification requirement",
      "affected_elements": ["FR-001", "FR-002"],
      "llm_analysis": "These requirements contradict: FR-001 states immutability, but FR-002 allows modifications within 24h. Clarify temporal constraints.",
      "recommendation": "Define order lifecycle states: PENDING (modifiable), CONFIRMED (immutable), or allow modifications only in specific fields"
    }
  ],
  "follow_up_questions": [
    {
      "question": "Should orders be truly immutable after confirmation, or should modifications be allowed within a time window?",
      "suggested_answers": [
        "Fully immutable - remove FR-002",
        "Allow modifications within 24h - adjust FR-001 to 'immutable after 24h'",
        "Allow status changes only - clarify modifiable fields"
      ]
    }
  ]
}
```

---

## Configurazione Avanzata

### Variabili Ambiente Disponibili

```env
# === Ollama LLM ===
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3                    # o phi, mistral, etc.
OLLAMA_TIMEOUT=120                     # secondi

# === Kafka ===
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_INPUT_TOPIC=agent1-output
KAFKA_OUTPUT_TOPIC=agent2-output
KAFKA_GROUP_ID=agent2-consistency-analyzer
KAFKA_AUTO_OFFSET_RESET=earliest      # o latest
KAFKA_EXTERNAL_PORT=9092

# === Semantic Analysis ===
EMBEDDINGS_MODEL=all-MiniLM-L6-v2     # Sentence Transformers model
ENTITY_OVERLAP_THRESHOLD=0.85          # Cosine similarity threshold
SEMANTIC_SIMILARITY_THRESHOLD=0.75

# === Validation ===
MAX_FOLLOW_UP_QUESTIONS=5              # Max domande generate
DDD_RULES_PATH=knowledge_base/ddd_rules.md
VALIDATION_CHECKLIST_PATH=knowledge_base/validation_checklist.json

# === API ===
API_PORT=8002
API_HOST=0.0.0.0
LOG_LEVEL=INFO                         # DEBUG, INFO, WARNING, ERROR

# === Consumer Scaling ===
MAX_WORKERS=4                          # Worker per consumer
CONSUMER_REPLICAS=1                    # Numero di consumer (Docker)

# === N8N (opzionale) ===
N8N_PORT=5678
N8N_HOST=localhost

# === Kafka UI (opzionale) ===
KAFKA_UI_PORT=8080
```

### Tuning Performance

#### Per Sistemi con Poca RAM (8GB)

```env
# Usa modello LLM più piccolo
OLLAMA_MODEL=phi

# Riduci worker
MAX_WORKERS=2

# Riduci batch Kafka
# In docker-compose.prod.yml:
environment:
  KAFKA_MAX_POLL_RECORDS: 5
```

#### Per Sistemi Potenti (32GB+)

```env
# Usa modello più potente
OLLAMA_MODEL=llama3:70b

# Aumenta worker
MAX_WORKERS=8

# Scala consumer
CONSUMER_REPLICAS=5
```

**Risultato:**
```
5 consumer x 8 workers = 40 analisi parallele
Throughput: ~100-150 analisi/minuto
```

---

## Struttura del Codice

### File Principali

```
app/
├── main.py                    # FastAPI app, endpoints A2A e REST
├── config.py                  # Configurazione (Pydantic Settings)
├── models/                    # Pydantic schemas
├── services/
│   ├── semantic_analyzer.py   # Embeddings + cosine similarity
│   ├── conflict_detector.py   # LLM-based conflict detection
│   ├── question_generator.py  # Follow-up questions generation
│   └── model_refiner.py       # Auto-fix e refinement
└── kafka/
    ├── consumer_advanced.py   # Parallel Kafka consumer (ThreadPoolExecutor)
    └── producer.py            # Kafka producer for Agent 3

a2a/
├── agent_card.json            # A2A protocol agent card
└── models/                    # A2A Task, Message, Artifact models

knowledge_base/
├── ddd_rules.md               # 572 lines of DDD knowledge
└── validation_checklist.json  # 23 validation rules (7 categories)
```

### API Endpoints

| Endpoint | Method | Descrizione |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/.well-known/agent.json` | GET | Agent card (A2A protocol) |
| `/a2a/message/send` | POST | Send message to agent (A2A) |
| `/a2a/tasks/{task_id}` | GET | Get task status |
| `/analyze` | POST | Direct analysis (bypass Kafka) |
| `/docs` | GET | Swagger UI |

### Architettura Servizi

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                   │
├─────────────────────────────────────────────────────────┤
│  Endpoints:                                              │
│  ├─ /health                                             │
│  ├─ /.well-known/agent.json                            │
│  ├─ /a2a/message/send                                   │
│  ├─ /a2a/tasks/{id}                                     │
│  └─ /analyze (direct REST)                             │
└────────────────┬────────────────────────────────────────┘
                 │
                 ├─▶ Semantic Analyzer
                 │   └─ Sentence Transformers (embeddings)
                 │
                 ├─▶ Conflict Detector
                 │   └─ Ollama + Llama3 (LLM reasoning)
                 │
                 ├─▶ Question Generator
                 │   └─ Template-based + context-aware
                 │
                 └─▶ Model Refiner
                     └─ Auto-fix + normalization
```

---

## Licenza e Contributi

### Licenza

MIT License - Vedi file LICENSE per dettagli.

### Contributi

Questo è un progetto di ricerca accademica (PhD Thesis).

Per domande, collaborazioni o segnalazioni:
1. Apri una Issue su GitHub
2. Contatta l'autore

### Parte di PhD Thesis

**Università**: Campus Bio-Medico di Roma
**Programma**: Artificial Intelligence for Health and Life Sciences
**Tema**: Collaborative AI Agents for Domain Discovery, Coherent Requirement Analysis and Event-Driven Microservice Design

**Obiettivo**: Dimostrare che sistemi multi-agente con LLM possono automatizzare la progettazione Domain-Driven Design riducendo errori umani e accelerando lo sviluppo.

---

## Support

### Documentazione Aggiuntiva

- **Knowledge Base DDD**: `knowledge_base/ddd_rules.md`
- **Validation Rules**: `knowledge_base/validation_checklist.json`
- **N8N Workflows**: `n8n/workflow_example.json`
- **Input Examples**: `input_agent/`

### Comandi Rapidi

```bash
# Avvio completo
docker-start.bat

# Test sistema
docker-test.bat

# Vedi logs
docker-logs.bat

# Scala consumer (per carichi elevati)
docker-scale.bat

# Stop tutto
docker-stop.bat
```

### Debug Checklist

Se qualcosa non funziona:

1. **Verifica Docker running:**
   ```bash
   docker ps
   ```

2. **Verifica Ollama:**
   ```bash
   curl http://localhost:11434/api/tags
   ```

3. **Verifica Kafka:**
   ```bash
   docker exec agent2-kafka kafka-topics --list --bootstrap-server localhost:9092
   ```

4. **Vedi logs:**
   ```bash
   docker logs agent2-api
   docker logs agent2-consumer
   ```

5. **Test health:**
   ```bash
   curl http://localhost:8002/health
   ```

---

## Quick Start Summary

**Per chi ha fretta:**

```bash
# 1. Installa Docker + Ollama + Llama3

# 2. Clone repository
git clone <repo-url>
cd agent-consistency-analyzer

# 3. Avvia tutto
docker-start.bat

# 4. Testa
docker-test.bat

# 5. Vedi API docs
# Apri browser: http://localhost:8002/docs

# 6. Test analisi
curl -X POST http://localhost:8002/analyze \
  -H "Content-Type: application/json" \
  -d @input_agent/example_bad.json
```

**Fatto! Agent 2 è operativo.**

---

**Versione**: 1.0.0
**Ultimo Aggiornamento**: 2025-01-17
**Status**: Production Ready
