# Agent 2 — Consistency Analyzer: Casi di Test

> **Progetto**: Microservizi — Agent Consistency Analyzer
> **Corso**: Architetture a Microservizi
> **Repository**: https://github.com/claudio-dragotta/agent-consistency-analyzer

---

## Panoramica

L'agente analizza modelli di dominio scritti in Domain-Driven Design (DDD) e individua problemi di coerenza come entità duplicate tra contesti, conflitti tra requisiti funzionali, eventi mal nominati e pattern architetturali incompatibili.

Sono stati definiti **5 casi di test** che coprono tre scenari di dominio distinti:

| # | File | Scenario | Problemi Attesi | Scopo |
|---|------|----------|-----------------|-------|
| 1 | `example_good.json` | E-Commerce (corretto) | 0 | Baseline — modello valido |
| 2 | `example_demo.json` | E-Commerce (demo) | 3 | Demo rapida — problemi essenziali |
| 3 | `example_bad.json` | E-Commerce (stress) | 13 | Stress test — tutti i tipi di errore |
| 4 | `case_healthcare.json` | Gestione Ospedaliera | 4 | Dominio verticale — sanità |
| 5 | `case_banking.json` | Digital Banking | 4 | Dominio verticale — finanza |

---

## Tipologie di Problemi Rilevati

L'agente è in grado di rilevare **7 tipi di problemi**, classificati per severità:

| Tipo | Descrizione | Severità |
|------|-------------|----------|
| `ENTITY_OVERLAP` | La stessa entità è definita in più Bounded Context senza un owner chiaro | HIGH |
| `REQUIREMENT_CONFLICT` | Due requisiti funzionali si contraddicono logicamente | HIGH |
| `SEMANTIC_AMBIGUITY` | Un termine è usato con significati diversi in contesti diversi | MEDIUM |
| `DUPLICATE_EVENT` | Lo stesso evento di dominio è emesso da più di un servizio | HIGH |
| `NAMING_VIOLATION` | Un evento non segue la convenzione `<Aggregato><VerboPastato>` | MEDIUM |
| `INCOMPATIBLE_PATTERN` | Un pattern di comunicazione è incompatibile con i requisiti di consistenza | HIGH |
| `MISCLASSIFIED_DOMAIN` | Un dominio è classificato in modo errato (es. Generic classificato come Core) | MEDIUM |

---

## Caso di Test 1 — `example_good.json`

### Scenario
**E-Commerce Platform** completa e corretta. Modello di riferimento senza problemi.

### Dominio
- **Core Domains**: Order Management, Product Catalog
- **Supporting Domains**: Payment Processing, Shipping, Customer Management, Inventory
- **Generic Domains**: Notification Service, Authentication & Authorization
- **Shared Kernel**: Money, Address (Value Objects condivisi)

### Scopo del Test
Verificare che l'agente **non produca falsi positivi** su un modello correttamente progettato. L'output atteso è `VALID` con zero problemi rilevati.

### Caratteristiche del Modello (Corrette)
- Ogni entità ha un unico Bounded Context proprietario
- Gli eventi sono tutti nominati al passato (`OrderCreated`, `PaymentAuthorized`, `ShipmentDispatched`)
- Ogni evento ha un unico emittente
- I requisiti di consistenza sono compatibili tra loro
- Le integrazioni tra contesti usano pattern documentati (`event-driven`, `open-host-service`)
- Authentication è classificato come Generic (corretto)

### Output Atteso

```
Status: VALID
Problemi rilevati: 0
```

---

## Caso di Test 2 — `example_demo.json`

### Scenario
**E-Commerce Platform** con 3 problemi intenzionali scelti per rappresentare le categorie principali. Usato nella demo interattiva mostrata al professore.

### Dominio
- **Core Domains**: Order Management, Product Catalog, Inventory

### Scopo del Test
Mostrare il comportamento dell'agente in una sessione interattiva, con un numero limitato di problemi facilmente spiegabili e un ciclo di domanda-risposta gestibile.

### Problemi Intenzionali

#### Problema 1 — ENTITY_OVERLAP
| Campo | Valore |
|-------|--------|
| Tipo | `ENTITY_OVERLAP` |
| Severità | HIGH |
| Entità coinvolta | `Product` |
| Contesti coinvolti | `OrderContext` e `CatalogContext` |
| Descrizione | L'entità `Product` è definita in entrambi i contesti. Non è chiaro quale dei due sia il proprietario. In DDD, ogni entità deve appartenere a un solo Bounded Context; gli altri vi accedono tramite riferimento (`ProductId`). |

#### Problema 2 — REQUIREMENT_CONFLICT
| Campo | Valore |
|-------|--------|
| Tipo | `REQUIREMENT_CONFLICT` |
| Severità | HIGH |
| Requisiti coinvolti | FR-ORD-001 e FR-ORD-002 |
| Descrizione | FR-ORD-001 afferma che un ordine è **immutabile dopo la conferma**, mentre FR-ORD-002 consente di **modificarlo entro 24 ore**. I due requisiti si contraddicono logicamente. |

#### Problema 3 — DUPLICATE_EVENT
| Campo | Valore |
|-------|--------|
| Tipo | `DUPLICATE_EVENT` |
| Severità | HIGH |
| Evento coinvolto | `OrderCreated` |
| Emittenti | `order-management` e `product-catalog` |
| Descrizione | L'evento `OrderCreated` viene emesso da due servizi distinti. Questo crea ambiguità sui consumatori e può causare elaborazioni duplicate. |

### Output Atteso

```
Status: ISSUES_FOUND
Problemi rilevati: 3
Follow-up questions: 3 (una per problema)
Iterazioni stimate: 1–2
```

---

## Caso di Test 3 — `example_bad.json`

### Scenario
**E-Commerce Platform** con 13 problemi intenzionali che coprono tutti e 7 i tipi di errore. Usato come stress test del motore di analisi.

### Dominio
- **Core Domains**: Order Management, Product Catalog, Authentication *(classificazione errata)*
- **Supporting Domains**: Payment Processing, Shipping, Customer Management, Inventory

### Scopo del Test
Verificare che l'agente rilevi **tutti i tipi di problema** contemporaneamente, produca domande di chiarimento per ciascuno e suggerisca un numero adeguato di iterazioni di raffinamento.

### Problemi Intenzionali

#### ENTITY_OVERLAP (2 istanze)

| # | Entità | Contesti Coinvolti | Descrizione |
|---|--------|--------------------|-------------|
| 1 | `Product` | Order Management + Product Catalog | Definita in entrambi senza owner chiaro |
| 2 | `Customer` | Order Management + Customer Management | Definita in entrambi senza owner chiaro |

#### REQUIREMENT_CONFLICT (3 istanze)

| # | Requisiti | Conflitto |
|---|-----------|-----------|
| 1 | FR-ORD-002 vs FR-ORD-003 | Prezzo immutabile dopo conferma VS applicazione retroattiva di coupon |
| 2 | FR-ORD-002 vs FR-CAT-002 | Prezzo immutabile nell'ordine VS aggiornamenti di prezzo nel catalogo |
| 3 | FR-ORD-004 vs architettura async | Strong consistency richiesta VS architettura solo event-driven (eventual consistency) |

#### SEMANTIC_AMBIGUITY (2 istanze)

| # | Termine | Contesti | Problema |
|---|---------|----------|----------|
| 1 | `Transaction` | Order Management + Payment Processing | Il termine indica concetti diversi nei due contesti |
| 2 | `Item` | Order, Catalog, Shipping, Inventory (4 contesti) | Usato con significati diversi in quattro contesti |

#### DUPLICATE_EVENT (1 istanza)

| Evento | Emittenti |
|--------|-----------|
| `OrderCreated` | `order-management` e `product-catalog` |

#### NAMING_VIOLATION (3 istanze)

| Evento Attuale | Problema | Nome Corretto |
|----------------|----------|---------------|
| `ProcessPayment` | Verbo all'infinito, non al passato | `PaymentProcessed` |
| `ShipOrder` | Verbo all'infinito, non al passato | `OrderShipped` |
| `Update` | Troppo generico | `StockUpdated` |

#### INCOMPATIBLE_PATTERN (1 istanza)

| Campo | Valore |
|-------|--------|
| Requisito | FR-PAY-002: verifica real-time sincrona dei pagamenti |
| Pattern definito | Solo `pub/sub` asincrono |
| Problema | Un requisito sincrono non può essere soddisfatto con solo comunicazione asincrona |

#### MISCLASSIFIED_DOMAIN (1 istanza)

| Dominio | Classificazione Attuale | Classificazione Corretta | Motivazione |
|---------|------------------------|--------------------------|-------------|
| Authentication | Core | Generic | È una commodity (OAuth, JWT) — non differenzia il business |

### Output Atteso

```
Status: ISSUES_FOUND
Problemi rilevati: 13
Follow-up questions: ≥ 7 (una per categoria di problema)
Iterazioni stimate: 3–5
```

---

## Caso di Test 4 — `case_healthcare.json`

### Scenario
**Hospital Management System** — Sistema di gestione ospedaliera. Caso verticale su un dominio regolamentato.

### Dominio
- **Core Domains**: Clinical Management, Medical Records, Authentication *(classificazione errata)*
- **Entità principali**: `Patient`, `Visit`, `Diagnosis`, `MedicalRecord`, `User`

### Scopo del Test
Verificare che l'agente funzioni correttamente su un dominio non-commerciale, con vincoli di integrità specifici del settore sanitario (es. immodificabilità delle cartelle cliniche).

### Invarianti di Dominio Specifici
- Le cartelle cliniche sono **append-only** — non possono essere cancellate
- Ogni record deve fare riferimento a una visita valida

### Problemi Intenzionali

#### ENTITY_OVERLAP (2 istanze)

| # | Entità | Contesti Coinvolti | Descrizione |
|---|--------|--------------------|-------------|
| 1 | `Patient` | ClinicalContext + RecordsContext | Usata per "visitare un paziente" in Clinical e per "tenere la cartella" in Records — scopi diversi, ma stessa entità |
| 2 | `Patient` | RecordsContext + Authentication (UserContext) | Il profilo paziente e l'account utente vengono confusi nella stessa entità |

#### SEMANTIC_AMBIGUITY (1 istanza)

| Termine | Contesti | Problema |
|---------|----------|----------|
| `Visit` | ClinicalContext + RecordsContext | In Clinical indica un *appuntamento*, in Records indica un *referto medico* |

#### MISCLASSIFIED_DOMAIN (1 istanza)

| Dominio | Classificazione Attuale | Classificazione Corretta |
|---------|------------------------|--------------------------|
| Authentication | Core | Generic |

### Output Atteso

```
Status: ISSUES_FOUND
Problemi rilevati: 4
Follow-up questions: 4
Iterazioni stimate: 2
```

---

## Caso di Test 5 — `case_banking.json`

### Scenario
**Digital Banking Platform** — Piattaforma bancaria digitale. Caso verticale su un dominio finanziario con requisiti di consistenza stringenti.

### Dominio
- **Core Domains**: Account Management, Payment Processing
- **Supporting Domains**: Card Services
- **Entità principali**: `Account` (IBAN), `Transaction`, `Payment`, `Card`

### Scopo del Test
Verificare che l'agente rilevi contraddizioni tra requisiti di consistenza (strong vs eventual) tipici dei sistemi finanziari, e problemi di pattern comunicativi in un contesto dove la consistenza dei dati è critica.

### Invarianti di Dominio Specifici
- Il saldo non può scendere sotto il limite di scoperto
- I conti bloccati non possono processare transazioni in uscita
- Conto sorgente e conto destinazione devono essere distinti

### Problemi Intenzionali

#### ENTITY_OVERLAP (1 istanza)

| Entità | Contesti Coinvolti | Descrizione |
|--------|--------------------|-------------|
| `Transaction` | Account Management + Payment Processing | In Account rappresenta un movimento contabile; in Payment rappresenta un'operazione di pagamento. Stesso nome, significati diversi. |

#### REQUIREMENT_CONFLICT (1 istanza)

| Requisiti | Conflitto |
|-----------|-----------|
| FR-ACC-001 (strong consistency del saldo) vs FR-ACC-002 (eventual consistency per notifiche) | Il requisito FR-ACC-001 impone che il saldo sia **fortemente consistente** in ogni momento. FR-ACC-002 rilassa questo vincolo per le notifiche. In presenza di un'unica architettura event-driven, questa distinzione non è adeguatamente modellata. |

#### NAMING_VIOLATION (3 istanze)

| Evento Attuale | Nome Corretto |
|----------------|---------------|
| `ProcessPayment` | `PaymentProcessed` |
| `ShipOrder` | `OrderShipped` |
| `Update` | `StockUpdated` |

#### INCOMPATIBLE_PATTERN (1 istanza)

| Campo | Valore |
|-------|--------|
| Requisito | FR-PAY-001: verifica real-time sincrona del pagamento |
| Pattern definito | Solo `pub/sub` asincrono |
| Problema | La verifica sincrona richiesta non può essere soddisfatta con un'architettura esclusivamente asincrona |

### Output Atteso

```
Status: ISSUES_FOUND
Problemi rilevati: 4 (+ 2 naming come sotto-categoria)
Follow-up questions: 4
Iterazioni stimate: 2
```

---

## Riepilogo Complessivo

### Copertura dei Tipi di Errore

| Tipo di Errore | Demo | Bad | Healthcare | Banking | Totale Istanze |
|----------------|:----:|:---:|:----------:|:-------:|:--------------:|
| ENTITY_OVERLAP | ✓ | ✓✓ | ✓✓ | ✓ | 6 |
| REQUIREMENT_CONFLICT | ✓ | ✓✓✓ | — | ✓ | 5 |
| SEMANTIC_AMBIGUITY | — | ✓✓ | ✓ | — | 3 |
| DUPLICATE_EVENT | ✓ | ✓ | — | — | 2 |
| NAMING_VIOLATION | — | ✓✓✓ | — | ✓✓✓ | 6 |
| INCOMPATIBLE_PATTERN | — | ✓ | — | ✓ | 2 |
| MISCLASSIFIED_DOMAIN | — | ✓ | ✓ | — | 2 |

### Copertura dei Domini

| Dominio | File di Test |
|---------|-------------|
| E-Commerce | `example_good.json`, `example_demo.json`, `example_bad.json` |
| Sanità | `case_healthcare.json` |
| Finanza | `case_banking.json` |

### Pipeline di Analisi

Ogni caso di test attraversa la stessa pipeline a 4 step:

```
Input JSON
    ↓
[Step 1] Semantic Analyzer     — Entity overlap, analisi semantica embeddings
    ↓
[Step 2] Conflict Detector     — Conflitti tra requisiti, regole DDD + LLM
    ↓
[Step 3] Question Generator    — Generazione domande di chiarimento (LLM-first)
    ↓
[Step 4] Model Refiner         — Auto-fix e raffinamento iterativo con le risposte
    ↓
Output JSON + Interfaccia n8n
```

---

*Documento generato per il corso di Architetture a Microservizi — A.A. 2024/2025*
