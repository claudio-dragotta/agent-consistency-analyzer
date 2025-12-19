# Changelog

## [1.1.0] - 2025-12-18

### Added

#### Interactive Loop Workflow (NEW)
- **workflow_complete_loop.json**: Workflow completo con loop interattivo
  - Analisi ricorsiva fino a modello perfetto
  - Form HTML professionale per Q&A con utente
  - Tracking iterazioni con session_id
  - Safety limit (max 5 iterazioni)
  - Pagine di successo/errore
  - Integrazione webhook per automazione

#### Documentazione
- **n8n/README_INTERACTIVE_LOOP.md**: Guida completa workflow interattivo
  - Setup passo-passo
  - Esempi di utilizzo
  - Troubleshooting specifico
  - Personalizzazione e best practices

#### Scripts
- **TEST_INTERACTIVE_LOOP.bat**: Script automatico per testare workflow interattivo
  - Verifica servizi attivi
  - Invia modello demo al webhook
  - Apre risultati nel browser
  - Gestione errori con messaggi chiari

### Changed

#### README.md
- Aggiunta sezione "Differenze tra i Workflow"
- Confronto dettagliato workflow_demo_simple vs workflow_complete_loop
- Istruzioni aggiornate per entrambi i workflow
- Struttura file aggiornata

#### n8n Workflows
- Mantenuto workflow_demo_simple.json (raccomandato per iniziare)
- workflow_example.json marcato come deprecato (bug: usa localhost invece di host.docker.internal)

## [1.0.0] - 2025-12-17

### Added

#### Core Features
- Agent 2 - Consistency & Conflict Analyzer
- Validazione 23 regole DDD
- Semantic analysis con embeddings
- Conflict detection con LLM (Llama3)
- Event architecture validation
- Auto-fix errori semplici
- Generazione domande follow-up

#### Infrastructure
- Docker Compose setup completo
- Kafka + Zookeeper
- n8n workflow automation
- Kafka UI per monitoring
- Health check endpoints

#### Documentation
- README.md principale
- n8n/DEMO_SETUP.md
- n8n/WORKFLOW_VISUAL.md
- knowledge_base/ddd_rules.md
- knowledge_base/validation_checklist.json

#### Scripts
- START_DEMO.bat: Avvio completo demo
- docker-stop.bat: Shutdown sistema

#### Test Data
- input_agent/example_demo.json (3 problemi)
- input_agent/example_bad.json (23 problemi)
- input_agent/example_good.json (modello valido)

## Roadmap

### [1.2.0] - Planned

#### Features
- [ ] Integrazione Agent 1 → Agent 2 via Kafka
- [ ] Integrazione Agent 2 → Agent 3 via Kafka
- [ ] Dashboard real-time con metriche
- [ ] Export report PDF
- [ ] API endpoint per history sessioni
- [ ] Webhook notifications (Slack, Teams, etc.)

#### Improvements
- [ ] Cache risultati analisi
- [ ] Parallel processing per multiple analisi
- [ ] Persistent storage per session history
- [ ] Rate limiting webhook
- [ ] Authentication webhook (API key)

#### Documentation
- [ ] Video tutorial
- [ ] Postman collection
- [ ] Swagger UI customization
- [ ] Architecture diagrams (C4 model)

---

## Tipo di Changes

- **Added**: Nuove funzionalità
- **Changed**: Modifiche a funzionalità esistenti
- **Deprecated**: Funzionalità deprecate (da rimuovere in futuro)
- **Removed**: Funzionalità rimosse
- **Fixed**: Bug fix
- **Security**: Patch di sicurezza

---

## Versioning

Questo progetto segue [Semantic Versioning](https://semver.org/):
- MAJOR: Breaking changes
- MINOR: Nuove funzionalità backward-compatible
- PATCH: Bug fix backward-compatible
