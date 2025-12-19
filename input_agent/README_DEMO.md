# File di Esempio per Demo Agent 2

## File Disponibili

### 1. example_demo.json
**Uso**: Demo principale per n8n
**Problemi**: 3 problemi intenzionali (facili da capire)
**Scenario**: E-Commerce Platform con Order Management e Product Catalog

### 2. example_bad.json
**Uso**: Test completo di validazione
**Problemi**: 23 errori di vario tipo
**Scenario**: Sistema complesso multi-dominio

### 3. example_good.json
**Uso**: Test con modello valido
**Problemi**: 0-2 problemi minori
**Scenario**: Modello ben strutturato

---

## example_demo.json - I 3 Problemi Intenzionali

### PROBLEMA 1: Entity Overlap (Entità Duplicata)

**Dove**: Entity "Product" definita in 2 contesti diversi

**Location nel JSON**:
```
domainMap.coreDomains[0].boundedContexts[0].entities[1]  ← "Product" in OrderContext
domainMap.coreDomains[1].boundedContexts[0].entities[0]  ← "Product" in CatalogContext
```

**Descrizione del problema**:
L'entità "Product" appare sia in:
- **OrderContext**: Rappresenta il prodotto nell'ordine
- **CatalogContext**: Rappresenta il prodotto nel catalogo

**Perché è un problema**:
- Ambiguità semantica: sono lo stesso concetto o aspetti diversi?
- Rischio di duplicazione dati
- Possibile accoppiamento tra contesti

**Severity**: HIGH

**Cosa si aspetta Agent 2**:
- **Rileva**: Entity overlap con similarity score alto (~0.85-0.95)
- **Genera domanda**: "Entity 'Product' appears in multiple contexts. Same concept or different aspects?"
- **Suggerisce**:
  - Creare un ProductContext condiviso
  - Rinominare in OrderItem (OrderContext) e CatalogProduct (CatalogContext)
  - Usare Product come aggregate root in un contesto, referenziarlo dall'altro

---

### PROBLEMA 2: Requirement Conflict (Requisiti Contraddittori)

**Dove**: Due requisiti funzionali in conflitto

**Location nel JSON**:
```
domainMap.coreDomains[0].functionalRequirements[0]  ← FR-ORD-001
domainMap.coreDomains[0].functionalRequirements[1]  ← FR-ORD-002
```

**Descrizione del problema**:
- **FR-ORD-001**: "Gli ordini devono essere immutabili dopo la conferma"
- **FR-ORD-002**: "Gli utenti possono modificare gli ordini entro 24 ore dalla creazione"

**Perché è un problema**:
Contraddizione logica:
- Se l'ordine è immutabile dopo conferma (FR-001)
- Ma l'utente può modificarlo entro 24h (FR-002)
- Quando esattamente diventa immutabile?

**Severity**: HIGH

**Cosa si aspetta Agent 2**:
- **Rileva**: Requirement conflict tramite analisi LLM
- **Genera domanda**: "Should orders be truly immutable or allow modifications within a time window?"
- **Suggerisce**:
  - Definire chiaramente gli stati dell'ordine (PENDING → CONFIRMED → SHIPPED)
  - Specificare che "immutabile" si intende dopo 24h o dopo spedizione
  - Chiarire quali campi sono modificabili e quali no
  - Creare requisiti più specifici: "immutabile dopo 24h dalla conferma"

---

### PROBLEMA 3: Multiple Emitters (Evento con Multipli Emittenti)

**Dove**: Evento "OrderCreated" con 2 emitters

**Location nel JSON**:
```
eventDrivenModel.events[0].emitters  ← ["OrderService", "PaymentService"]
```

**Descrizione del problema**:
L'evento "OrderCreated" è emesso da:
- **OrderService**
- **PaymentService**

**Perché è un problema**:
Violazione del principio "Single Emitter":
- Ambiguità: chi è la single source of truth?
- Rischio di eventi duplicati
- Difficile tracciare il flusso
- Possibile disallineamento (e se solo uno emette?)

**Severity**: CRITICAL

**Cosa si aspetta Agent 2**:
- **Rileva**: Event architecture violation (multiple emitters)
- **Genera domanda**: "Which service should be the single source of truth for OrderCreated?"
- **Suggerisce**:
  - Solo OrderService dovrebbe emettere OrderCreated
  - PaymentService può:
    - Sottoscrivere OrderCreated per processare pagamento
    - Emettere un suo evento PaymentCompleted dopo pagamento riuscito
  - Creare eventi separati: OrderInitiated, PaymentConfirmed

**Auto-fix applicabile**: SÌ
Agent 2 può automaticamente:
- Rimuovere PaymentService da emitters di OrderCreated
- Suggerire creazione di evento separato PaymentConfirmed

---

## Output Atteso da Agent 2

Quando processi `example_demo.json`, Agent 2 produrrà:

### 1. Validation Report

```json
{
  "status": "ISSUES_FOUND",
  "summary": {
    "total_issues": 3,
    "entity_overlaps": 1,
    "requirement_conflicts": 1,
    "event_architecture_violations": 1,
    "auto_fixed": 1,
    "requires_manual": 2
  }
}
```

### 2. Semantic Issues

```json
{
  "semantic_issues": [
    {
      "issue_type": "ENTITY_OVERLAP",
      "severity": "HIGH",
      "description": "Entity 'Product' defined in multiple contexts",
      "affected_elements": ["Product"],
      "contexts": ["OrderContext", "CatalogContext"],
      "similarity_score": 0.89,
      "recommendation": "Consider: 1) Create shared ProductContext, 2) Use different names (OrderItem vs CatalogProduct), 3) Use Product as aggregate root"
    }
  ]
}
```

### 3. Conflict Issues

```json
{
  "conflict_issues": [
    {
      "conflict_type": "REQUIREMENT_CONFLICT",
      "severity": "HIGH",
      "description": "Immutability conflicts with modification requirement",
      "affected_elements": ["FR-ORD-001", "FR-ORD-002"],
      "llm_analysis": "FR-ORD-001 states immutability after confirmation, but FR-ORD-002 allows modifications within 24h. Temporal constraints unclear.",
      "recommendation": "Define order lifecycle states: PENDING (modifiable), CONFIRMED (immutable after 24h), SHIPPED (fully immutable)"
    },
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

### 4. Follow-up Questions (3)

```json
{
  "follow_up_questions": [
    {
      "question_id": "FUQ-001",
      "question": "Entity 'Product' appears in OrderContext and CatalogContext. Do they represent the same concept or different aspects?",
      "severity": "HIGH",
      "context": "Multi-context entity definition",
      "affected_elements": ["Product"],
      "suggested_answers": [
        "Same concept - create shared ProductContext",
        "Different aspects - rename to OrderItem and CatalogProduct",
        "Product is aggregate root - keep in CatalogContext, reference from OrderContext"
      ]
    },
    {
      "question_id": "FUQ-002",
      "question": "Requirements FR-ORD-001 states immutability but FR-ORD-002 allows modifications within 24h. Should orders be truly immutable after confirmation?",
      "severity": "HIGH",
      "context": "Conflicting functional requirements",
      "affected_elements": ["FR-ORD-001", "FR-ORD-002"],
      "suggested_answers": [
        "Fully immutable - remove FR-ORD-002",
        "Allow modifications within 24h - adjust FR-ORD-001 to 'immutable after 24h'",
        "Define order lifecycle: PENDING (modifiable) → CONFIRMED (immutable after 24h)"
      ]
    },
    {
      "question_id": "FUQ-003",
      "question": "Event 'OrderCreated' has multiple emitters (OrderService, PaymentService). Which service should be the single source of truth?",
      "severity": "CRITICAL",
      "context": "Event architecture violation - multiple emitters",
      "affected_elements": ["OrderCreated"],
      "suggested_answers": [
        "Only OrderService emits OrderCreated - PaymentService subscribes to it",
        "Create separate events: OrderInitiated (OrderService), PaymentConfirmed (PaymentService)"
      ]
    }
  ]
}
```

### 5. Refined Model

Il modello raffinato conterrà:
- **OrderCreated** con solo OrderService come emitter
- Suggerimento di rinominare entità duplicate
- Metadati di raffinamento

---

## Come Testare

### Test 1: n8n Workflow

1. Apri n8n: http://127.0.0.1:5678
2. Importa workflow: `n8n/workflow_demo_simple.json`
3. Nel nodo "Prepara Input", sostituisci il JSON con il contenuto di `example_demo.json`
4. Esegui il workflow
5. Vedi i 3 problemi rilevati nel nodo "4. RISULTATI FINALI"

### Test 2: API Diretta

```bash
curl -X POST http://localhost:8002/analyze \
  -H "Content-Type: application/json" \
  -d @input_agent/example_demo.json
```

Output: JSON con 3 problemi rilevati

### Test 3: Python Script

```python
import requests
import json

with open('input_agent/example_demo.json') as f:
    model = json.load(f)

response = requests.post(
    'http://localhost:8002/analyze',
    json={
        'domain_model': model,
        'use_llm': True,
        'apply_auto_fixes': True
    }
)

result = response.json()
print(f"Status: {result['status']}")
print(f"Total Issues: {result['summary']['total_issues']}")
print(f"Questions: {len(result['follow_up_questions'])}")
```

---

## Interpretazione Pedagogica

Questi 3 problemi sono stati scelti perché:

### 1. Rappresentatività
Sono errori comuni in progetti reali:
- Entità duplicate: Molto comune quando si definiscono bounded context
- Requisiti contraddittori: Spesso emerge durante interviste stakeholder
- Eventi multipli emitter: Errore architetturale frequente

### 2. Difficoltà Crescente
- **Problema 1** (Entity Overlap): Rilevabile con semantic analysis (embeddings)
- **Problema 2** (Requirement Conflict): Richiede ragionamento logico (LLM)
- **Problema 3** (Multiple Emitters): Richiede conoscenza pattern architetturali

### 3. Azioni Diverse
- **Problema 1**: Richiede decisione business → Domanda
- **Problema 2**: Richiede chiarimento requisiti → Domanda
- **Problema 3**: Correggibile automaticamente → Auto-fix + Domanda opzionale

### 4. Output Completi
Mostrano tutte e 3 le categorie di output di Agent 2:
- Report di validazione (summary)
- Domande di follow-up (3 domande)
- Modello raffinato (con correzioni)

---

## Best Practices per Demo

### Do's:
- Usa `example_demo.json` per demo rapide (3 problemi chiari)
- Usa `example_bad.json` per mostrare la potenza completa (23 problemi)
- Usa `example_good.json` per mostrare casi validi

### Don'ts:
- Non modificare i 3 problemi in `example_demo.json` (sono calibrati)
- Non aspettarti gli stessi risultati con modelli diversi (LLM può variare)
- Non confrontare con validatori sintattici (Agent 2 fa analisi semantica)

---

## Estensione della Demo

Puoi creare varianti:

### Variante 1: Solo Problema 1 (Entity Overlap)
Rimuovi FR-ORD-002 e lascia solo un emitter in OrderCreated

### Variante 2: Solo Problema 2 (Requirement Conflict)
Usa un solo Product e un solo emitter

### Variante 3: Solo Problema 3 (Multiple Emitters)
Usa nomi diversi per Product (OrderItem, CatalogProduct)

### Variante 4: Nessun Problema
Risolvi tutti e 3 i problemi e conferma che Agent 2 restituisce `status: VALID`

---

**Usa questi file per dimostrare il valore di Agent 2 nel rilevare problemi complessi in modelli DDD!**
