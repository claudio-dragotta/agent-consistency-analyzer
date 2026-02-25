# Changelog

Tutte le modifiche importanti a questo progetto saranno documentate in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
e questo progetto aderisce al [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-02-13

### Added
- **LLM-First Question Generation**: Le domande di follow-up sono ora generate interamente da Qwen2.5 14B
  - Ogni domanda menziona nomi reali di entità, domini ed eventi del modello
  - Ogni domanda ha esattamente 3 `suggested_answers` con azioni specifiche e concrete
  - Sistema di fallback automatico a template se LLM non disponibile
- **LLM-Interpreted Answer Processing**: Le risposte utente vengono interpretate dall'LLM per determinare azioni concrete
  - 6 tipi di azione supportati: `rename_event`, `set_owner`, `reclassify_domain`, `resolve_conflict`, `add_mapping`, `update_pattern`
  - `_interpret_answer_with_llm()` traduce risposte in linguaggio naturale in JSON strutturato
- **Entity Ownership Enforcement**: `_enforce_entity_ownership()` sostituisce entità nei contesti non-owner con `{_referenceOnly: true, _ownedBy: ownerContext}`
- **Domain Reclassification**: `_move_domain()` sposta domini tra core/supporting/generic
- **Context Mapping**: Aggiunta di ACL mapping tramite `_contextMappings`
- **Conflict Resolution Tracking**: Registrazione risoluzioni in `_conflictResolutions`

### Changed
- **Modello LLM predefinito**: Da `llama3` a `qwen2.5:14b` (ottimale per GPU con 8GB+ VRAM)
  - Aggiornato in `docker-compose.yml`, `app/config.py`, `.env`
- **`app/services/question_generator.py`**: Riscrittura completa
  - `_generate_all_questions_llm()` genera tutte le domande in una singola chiamata LLM
  - `_build_issues_data()` converte i problemi in formato compatto per il prompt
  - System prompt in italiano con regole strict per qualità output
  - Post-processing con regex per pulizia prefissi metadata `[ENTITY_OVERLAP|HIGH]`
- **`app/services/model_refiner.py`**: Riscrittura completa
  - `refine_model()` ora è `async` per supportare chiamate LLM
  - `_apply_user_answers()` ora è async, registra SEMPRE le decisioni (rimosso keyword matching rigido)
  - Aggiunto `_call_ollama()` per comunicazione LLM
- **`app/main.py`**: `refine_model` chiamato con `await` e parametro `use_llm`
- **`app/kafka/consumer_advanced.py`**: `refine_model` chiamato con `await` e `use_llm=False`
- **README.md**: Riscrittura completa professionale (~630 righe) con:
  - Diagramma architettura ASCII
  - Tabella servizi Docker Compose
  - Pipeline di analisi dettagliata (4 step)
  - API Reference con esempi request/response
  - Sezione workflow n8n con diagramma flusso
  - Sezione modello LLM con tabella comparativa
  - Schema Domain Model (minimale e completo)
  - Struttura progetto, configurazione, troubleshooting

### Removed
- Generazione domande basata su template hardcoded (sostituita da LLM)
- Keyword matching rigido in `model_refiner.py` (`if "only" in answer.lower()`)
- Dipendenza implicita da `llama3` come modello predefinito

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

[2.0.0]: https://github.com/your-repo/agent-consistency-analyzer/compare/v1.2.0...v2.0.0
[1.2.0]: https://github.com/your-repo/agent-consistency-analyzer/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/your-repo/agent-consistency-analyzer/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/your-repo/agent-consistency-analyzer/releases/tag/v1.0.0
