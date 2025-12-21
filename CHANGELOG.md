# Changelog

Tutte le modifiche importanti a questo progetto saranno documentate in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
e questo progetto aderisce al [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-12-19

### Added
- **Iterative Refinement**: Implementato processing di `previous_answers` per raffinamento progressivo del modello
- 5 handler specializzati per categorie di risposte utente:
  - `_handle_entity_overlap_answer()` - Risolve sovrapposizioni di entità
  - `_handle_requirement_conflict_answer()` - Risolve conflitti nei requisiti
  - `_handle_duplicate_event_answer()` - Assegna emitter unico agli eventi
  - `_handle_naming_answer()` - Applica correzioni di naming
  - `_handle_domain_classification_answer()` - Conferma classificazione domain
- Tracciabilità completa: tutte le decisioni utente registrate in `_userGuidedFixes`
- Sezione README "Come Funziona il Flusso di Processing" con pipeline completa Agent 1→2→3
- Sezione README "Novità v1.2.0" con documentazione del fix

### Changed
- `app/main.py`: Aggiunto campo `previous_answers` a `DomainModelRequest`
- `app/services/model_refiner.py`: Implementato metodo `_apply_user_answers()` (~290 righe)
- README aggiornato a v1.2.0 con documentazione estesa del loop interattivo
- Il workflow ora migliora progressivamente il modello invece di ripetere gli stessi problemi

### Fixed
- **Bug critico**: L'API ora processa correttamente le `previous_answers` inviate dal workflow n8n
- Il loop interattivo ora funziona come previsto: ogni iterazione riduce i problemi fino a modello valido

### Removed
- Documentazione ridondante e obsoleta:
  - `COMPLETAMENTO_WORKFLOW.md`
  - `n8n/README.md` (riferimenti obsoleti)
  - `n8n/DEMO_SETUP.md`
  - `n8n/README_INTERACTIVE_LOOP.md`
  - `n8n/WORKFLOW_VISUAL.md`
- Script di test vecchi: `simulate_agent1.py`, `test_agent.py`

## [1.1.0] - 2025-12-18

### Added
- Workflow interattivo completo (`workflow_complete_loop.json`)
- Form HTML per rispondere alle domande di follow-up
- Loop automatico fino a max 5 iterazioni
- Safety limit per evitare loop infiniti

### Changed
- Migliorata interfaccia utente con form HTML professionale
- Tracking delle iterazioni con `session_id`

## [1.0.0] - 2025-12-17

### Added
- Primo rilascio di Agent 2 - Consistency & Conflict Analyzer
- Validazione automatica di 23 regole DDD
- Semantic analysis per entity overlap detection
- Conflict detection con LLM (Llama3)
- Event architecture validation
- Auto-fix per problemi semplici
- Generazione domande di follow-up
- Workflow n8n demo (`workflow_demo_simple.json`)
- Integrazione Kafka per pipeline completa
- Docker Compose per deployment
- Knowledge base con regole DDD complete

[1.2.0]: https://github.com/your-repo/agent-consistency-analyzer/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/your-repo/agent-consistency-analyzer/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/your-repo/agent-consistency-analyzer/releases/tag/v1.0.0
