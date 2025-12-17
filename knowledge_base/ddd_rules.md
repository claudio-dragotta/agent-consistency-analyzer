# Knowledge Base: Domain-Driven Design, Regole di Coerenza ed Event-Driven Architecture

> **Scopo di questo documento**: Fornire all'Agente 2 (Consistency & Conflict Analyzer) tutte le regole, i criteri e le checklist necessarie per validare un modello di dominio generato dall'Agente 1. Questo documento deve essere usato come context per l'analisi semantica e la rilevazione di conflitti.

---

## PARTE 1: CLASSIFICAZIONE DEI DOMINI

### 1.1 Core Domain

#### Definizione
Il Core Domain è la parte del sistema che genera il **vantaggio competitivo** o il **massimo valore** per l'organizzazione. È ciò che non può essere acquistato "già fatto" senza perdere identità o prestazioni decisive.

#### Criteri di Identificazione (TUTTI devono essere considerati)

| Criterio | Domanda da porsi | Se SÌ → probabilmente Core |
|----------|------------------|---------------------------|
| **Differenziazione** | Se lo facciamo meglio degli altri, vinciamo? | ✓ Core |
| **Impatto economico** | Influenza direttamente ricavi, KPI principali, retention? | ✓ Core |
| **Complessità intrinseca** | Ha molte regole, eccezioni, vincoli temporali/operativi? | ✓ Core |
| **Frequenza di cambiamento** | Evolve spesso con nuove regole, promozioni, policy? | ✓ Core |
| **Sensibilità agli errori** | Un errore costa molto (SLA, sicurezza, legale, reputazione)? | ✓ Core |

#### Caratteristiche Attese di un Core Domain Ben Definito

1. **Ubiquitous Language curato**: termini precisi, pochi sinonimi, definizioni condivise
2. **Modello ricco (Rich Domain Model)**: logica nel dominio, non solo in servizi applicativi
3. **Eventi di dominio significativi**: esprimono cambiamenti di stato "di business"
4. **Invarianti esplicite**: regole che non possono MAI essere violate

#### Segnali di Allarme (Classificazione ERRATA come Core)

- ❌ È una commodity: esistono prodotti/servizi standard che lo fanno bene
- ❌ Le regole sono poche e stabili
- ❌ Non c'è investimento in linguaggio e modello ("basta farlo funzionare")
- ❌ Può essere facilmente sostituito con un servizio esterno

---

### 1.2 Supporting Domain

#### Definizione
Un Supporting Domain **supporta** il Core Domain: è necessario per far funzionare il sistema, ma **non è la fonte primaria di vantaggio competitivo**.

#### Criteri di Identificazione

| Criterio | Domanda da porsi | Se SÌ → probabilmente Supporting |
|----------|------------------|--------------------------------|
| **Necessità** | Serve per far funzionare il Core? | ✓ Supporting |
| **Non differenziante** | Se lo facciamo come gli altri, non perdiamo? | ✓ Supporting |
| **Stabilità** | Le regole cambiano raramente? | ✓ Supporting |
| **Sostituibilità parziale** | Potremmo usare una soluzione standard con adattamenti? | ✓ Supporting |

#### Differenze dal Core Domain

| Aspetto | Core Domain | Supporting Domain |
|---------|-------------|-------------------|
| **Priorità** | Guida le scelte architetturali | Si adatta al Core |
| **Investimento** | Modello ricco, team dedicato | Modello più semplice |
| **Buy vs Build** | Quasi sempre Build | Accettabile Buy con adattamenti |
| **Ottimizzazione** | Per evoluzione e qualità semantica | Per efficienza e costo |

---

### 1.3 Generic Domain

#### Definizione
Un Generic Domain è una **capacità comune e non differenziante** che può essere acquistata o riusata senza impatto sull'identità di business.

#### Criteri di Identificazione

| Criterio | Domanda da porsi | Se SÌ → probabilmente Generic |
|----------|------------------|------------------------------|
| **Standardizzazione** | È un problema risolto e ben compreso? | ✓ Generic |
| **Sostituibilità totale** | Possiamo cambiare provider senza impatto sul business? | ✓ Generic |
| **Nessun vantaggio** | Reinventarlo non porta alcun vantaggio competitivo? | ✓ Generic |
| **Complessità tecnica** | La complessità è tecnica, non di business? | ✓ Generic |

#### Esempi Tipici di Generic Domain

- Autenticazione e autorizzazione (Identity Provider)
- Notifiche (email, SMS, push)
- Logging e monitoraggio
- Billing standard
- File storage
- Retry, circuit breaker, rate limiting

#### Scelte Implementative Tipiche

- SaaS/servizi esterni
- Librerie/framework standard
- Microservizi "piatti" (CRUD)
- Componenti infrastrutturali condivisi

---

## PARTE 2: BOUNDED CONTEXT

### 2.1 Definizione

Il **Bounded Context (BC)** è un confine esplicito entro il quale un modello di dominio e un linguaggio (Ubiquitous Language) sono **coerenti**. Fuori dal confine, lo stesso termine può cambiare significato.

### 2.2 Criteri per Definire i Confini

#### Metodo Meticoloso (Step-by-Step)

1. **Raccogli termini e definizioni**: costruisci un mini-glossario per area funzionale
2. **Individua le regole/invarianti**: dove cambiano, spesso cambia anche il contesto
3. **Osserva i flussi**: un processo end-to-end attraversa più contesti
4. **Allinea con team e ownership**: un BC ideale ha un owner/team responsabile
5. **Separa modelli con lifecycle diverso**: se una parte cambia spesso e un'altra no, separa
6. **Valuta la consistenza richiesta**: consistenza forte → stesso BC o stesso Aggregate

#### Regole Decisionali Rapide

| Situazione | Decisione |
|------------|-----------|
| Stesso termine ma significato diverso | → BC SEPARATI |
| Regole/invarianti diverse | → BC SEPARATI |
| Dati aggiornati da owner diversi | → BC SEPARATI |
| Serve transazione unica e invarianti forti | → STESSO BC |

### 2.3 Esempio Pratico

**Termine "Utente"** in contesti diversi:

| Bounded Context | Significato di "Utente" | Attributi Rilevanti |
|-----------------|------------------------|---------------------|
| Identity | Account + credenziali | username, password_hash, 2FA |
| Billing | Intestatario fiscale | ragione_sociale, partita_iva, indirizzo_fatturazione |
| Support | Persona che apre ticket | ticket_history, priority_level, SLA |

**Conclusione**: Stesso termine, modelli DIVERSI, traduzione tramite ID/adapter.

---

## PARTE 3: ENTITY vs VALUE OBJECT

### 3.1 Entity

#### Definizione
Oggetto definito dalla sua **identità (ID)** e dal suo **ciclo di vita**. Anche se cambiano gli attributi, rimane "lo stesso" oggetto.

#### Criteri di Identificazione

| Criterio | Domanda | Se SÌ → Entity |
|----------|---------|----------------|
| **Tracciabilità temporale** | Devo tracciarlo nel tempo (storia, audit, stato)? | ✓ Entity |
| **Distinguibilità** | Devo distinguerlo da altri con stessi attributi? | ✓ Entity |
| **Ciclo di vita** | Ha stati: creato → aggiornato → archiviato? | ✓ Entity |
| **Riferimenti esterni** | Altri oggetti lo puntano tramite ID? | ✓ Entity |

#### Esempi Tipici
- Order, Customer, Product, Shipment, Invoice, Ticket, Reservation

---

### 3.2 Value Object

#### Definizione
Oggetto definito dai suoi **valori**. Non ha identità propria; se due VO hanno gli stessi valori, sono **intercambiabili**. Idealmente è **immutabile**.

#### Criteri di Identificazione

| Criterio | Domanda | Se SÌ → Value Object |
|----------|---------|---------------------|
| **Solo valore** | Conta solo il valore, non "quale" istanza? | ✓ VO |
| **Immutabilità** | È naturalmente immutabile o trattabile come tale? | ✓ VO |
| **Sostituibilità** | Posso sostituirlo con uno equivalente senza cambiare significato? | ✓ VO |
| **Regole locali** | Aiuta a esprimere regole di validazione locali? | ✓ VO |

#### Esempi Tipici
- Money (amount + currency), Address, TimeWindow, GeoPoint, DateRange, Email, PhoneNumber

---

### 3.3 Errore Comune: Address come Entity

**Errore**: Trattare Address come Entity perché "può cambiare".

**Correzione**: Se un indirizzo cambia, di solito si vuole registrare un **nuovo valore** (nuovo VO) e mantenere lo storico, NON "aggiornare" l'indirizzo come se fosse lo stesso oggetto.

**Eccezione**: Address diventa Entity SOLO se ha identità e lifecycle separato (es. indirizzi salvati in rubrica con preferenze, validazioni, geocoding).

---

## PARTE 4: REGOLE DI COERENZA TRA DOMINI

### 4.1 Regola: Un'Entità Appartiene a UN SOLO Bounded Context

#### Enunciato
Una Entity appartiene a **un solo** Bounded Context come **fonte di verità (owner)**. Altri contesti possono riferirsi ad essa solo tramite:
- Identificatori (ID)
- Viste locali (read model)
- MAI importando l'intero oggetto con le sue invarianti

#### Se Deve Apparire in Più Domini: Ruoli Diversi Espliciti

**Corretto**:
- `Customer` (Sales Context) 
- `AccountHolder` (Billing Context)
- `User` (Identity Context)

**ERRATO**:
- `Customer` usato ovunque con lo stesso modello

#### Pattern Consigliati

| Pattern | Uso |
|---------|-----|
| **Reference by ID** | Negli eventi/command passa solo EntityId e dati minimi |
| **Anti-Corruption Layer (ACL)** | Adapter che traduce modello esterno → modello interno |
| **Context Mapping** | Definisci relazioni (Upstream/Downstream, Conformist, ACL) |

---

### 4.2 Regola: I Requisiti Non Devono Contraddirsi

#### Enunciato
Ogni dominio deve preservare i propri invarianti. Se un dominio richiede **A** e un altro richiede **non-A** sullo stesso concetto, hai una **collisione di significato**.

#### Soluzioni

1. **Separare i concetti** in contesti diversi
2. **Chiarire l'ownership** e definire una traduzione con perdita/arricchimento informativo

#### Tecniche di Prevenzione

| Tecnica | Descrizione |
|---------|-------------|
| **Glossario versionato** | Definizioni e sinonimi approvati |
| **Contratti espliciti** | Schema eventi/API con semantica documentata |
| **Test di contratto** | Consumer-driven contract testing |
| **Decision log** | Quando un termine cambia significato, registralo |

---

### 4.3 Regola: Un Evento Ha UN SOLO Emettitore

#### Enunciato
Un tipo di evento (es. `OrderPlaced`) deve essere emesso da **un solo contesto** che possiede l'invariante e la transizione di stato che l'evento rappresenta.

#### Perché È Importante
Se due servizi emettono lo stesso evento:
- Non sai chi è la fonte di verità
- Rompi audit e consistenza
- Crei ambiguità nei consumer

#### Come Gestire Casi Ambigui

| Situazione | Soluzione |
|------------|-----------|
| Due contesti vogliono segnalare la stessa cosa | Distinguere: `PaymentAuthorized` (Billing) vs `OrderReadyForFulfillment` (Sales) |
| Serve un evento comune | Definisci un Published Language e l'owner unico |
| Confusione domain/integration events | I domain events sono interni al BC, gli integration events sono contratti esterni |

---

### 4.4 Regola: Pattern di Comunicazione Compatibili

#### Enunciato
Il pattern di comunicazione scelto deve rispettare i requisiti di:
- Consistenza
- Latenza
- Affidabilità
- Autonomia

#### Guida Decisionale

| Requisito | Pattern Consigliato |
|-----------|---------------------|
| Risposta immediata per proseguire | Request/Response (sincrono) |
| Disaccoppiamento, reazioni multiple, audit | Pub/Sub (asincrono) |
| Orchestrazione processo lungo | Saga (orchestrata o coreografata) + eventi |
| Resilienza a fallimenti di rete | Event-driven + retry + idempotenza |

#### Incompatibilità da Rilevare

| Situazione | Problema |
|------------|----------|
| Dominio A usa Event Sourcing, Dominio B (dipendente) usa solo Request/Response sincrono | Incompatibilità: B non può reagire agli eventi di A |
| Dominio A richiede consistenza forte con Dominio B, ma comunicano solo via eventi | Incompatibilità: consistenza eventuale, non forte |

---

## PARTE 5: EVENT-DRIVEN ARCHITECTURE

### 5.1 Pub/Sub vs Request/Response

#### Quando Usare Request/Response (Sincrono)

- Decisione immediata necessaria per proseguire (es. validazione bloccante)
- Il chiamante deve ottenere un dato "adesso"
- Query con SLA basso e cache

#### Quando Usare Pub/Sub (Asincrono)

- Disaccoppiamento produttore/consumatori
- Più servizi devono reagire allo stesso evento
- Processo lungo con consistenza eventuale accettabile
- Resilienza: i consumer recuperano da backlog

#### Regola Chiave: Comandi vs Eventi

| Tipo | Definizione | Destinatario |
|------|-------------|--------------|
| **Command** | Richiesta intenzionale: "Fai X" | Specifico |
| **Event** | Fatto accaduto: "X è successo" | Nessuno specifico |

---

### 5.2 Convenzioni di Naming degli Eventi

#### Formato Consigliato
```
<Aggregate><PastTenseVerb>
```

#### Esempi Corretti
- `OrderPlaced`
- `PaymentAuthorized`
- `ShipmentDispatched`
- `CustomerRegistered`

#### Esempi ERRATI

| Errato | Problema | Corretto |
|--------|----------|----------|
| `OrderUpdate` | Presente, non passato | `OrderUpdated` |
| `Updated` | Troppo generico | `OrderStatusChanged` |
| `ProcessOrder` | È un comando, non un evento | `OrderProcessed` |
| `order_table_insert` | Nome tecnico, non di dominio | `OrderCreated` |

#### Linee Guida Meticolose

1. **Usa il linguaggio del dominio** (Ubiquitous Language), non nomi di tabelle
2. **Usa passato (Past Tense)**: l'evento descrive qualcosa già successo
3. **Evita nomi ambigui**: `Updated` è troppo generico
4. **Includi il contesto nel topic/namespace**: es. `billing.payment-authorized`
5. **Versiona**: aggiungi v1/v2 nel topic o nello schema

---

### 5.3 Struttura del Payload degli Eventi

#### Campi Obbligatori (Best Practice)

```json
{
  "eventId": "uuid-v4",
  "eventType": "OrderPlaced",
  "occurredAt": "2025-01-15T10:30:00Z",
  "producer": "order-service",
  "schemaVersion": "1.0",
  "aggregateId": "order-123",
  "correlationId": "req-456",
  "causationId": "evt-789",
  "payload": {
    // dati specifici dell'evento
  }
}
```

#### Principi

- **Dati minimi ma sufficienti**: evita payload enormi
- **Preferisci riferimenti**: usa ID invece di oggetti completi
- **Idempotenza**: i consumer devono poter ignorare duplicati tramite `eventId`

---

### 5.4 Coerenza tra Eventi Emessi e Ricevuti

#### Regola
Ogni consumer deve poter interpretare l'evento **senza assumere dettagli interni** del producer.

#### Pratiche Operative

| Pratica | Descrizione |
|---------|-------------|
| **Event Catalog** | Elenco eventi, owner, schema, semantica, esempi |
| **Contract Testing** | I consumer validano che lo schema non cambi |
| **Backward Compatibility** | Aggiungi campi opzionali; non rimuovere campi |
| **DLQ + Monitoring** | Eventi non processabili tracciati e recuperabili |
| **Outbox Pattern** | Pubblicazione affidabile |
| **Idempotent Consumer** | Nessun doppio effetto |

---

## PARTE 6: CHECKLIST DI VALIDAZIONE

### 6.1 Checklist Classificazione Domini

Per ogni dominio identificato, verificare:

- [ ] La classificazione (Core/Supporting/Generic) è giustificata dai criteri?
- [ ] Il Core Domain è davvero differenziante?
- [ ] I Supporting Domain supportano effettivamente il Core?
- [ ] I Generic Domain sono davvero commoditizzabili?

### 6.2 Checklist Bounded Context

- [ ] Ogni BC ha un glossario/Ubiquitous Language definito?
- [ ] I confini sono allineati con ownership e team?
- [ ] Lo stesso termine ha lo stesso significato dentro il BC?
- [ ] Le integrazioni tra BC sono esplicite (ACL, Published Language)?

### 6.3 Checklist Entity vs Value Object

- [ ] Le Entity hanno un ID e un ciclo di vita?
- [ ] I Value Object sono immutabili?
- [ ] Non ci sono Entity che dovrebbero essere VO (es. Address)?
- [ ] Non ci sono VO che dovrebbero essere Entity?

### 6.4 Checklist Coerenza tra Domini

- [ ] Ogni Entity ha UN SOLO owner (fonte di verità)?
- [ ] Non ci sono Entity duplicate in più domini?
- [ ] I requisiti di domini diversi non si contraddicono?
- [ ] Ogni evento ha UN SOLO emettitore?
- [ ] I pattern di comunicazione sono compatibili?

### 6.5 Checklist Event-Driven Architecture

- [ ] Gli eventi sono nominati in passato (Past Tense)?
- [ ] Gli eventi usano il linguaggio del dominio?
- [ ] Ogni evento ha: eventId, occurredAt, producer, schemaVersion?
- [ ] Gli eventi hanno un solo emettitore?
- [ ] I consumer possono gestire duplicati e out-of-order?

---

## PARTE 7: TIPI DI PROBLEMI DA RILEVARE

### 7.1 Sovrapposizione di Entità (Entity Overlap)

**Definizione**: La stessa entità (stesso nome o stesso concetto) appare in più domini senza differenziazione di ruolo.

**Severità**: HIGH

**Esempio**:
- `Product` definito in Order Management con attributi di prezzo
- `Product` definito in Inventory con attributi di stock
- PROBLEMA: Chi è l'owner? Quale è la fonte di verità?

**Risoluzione Suggerita**: Separare in `OrderLineItem` (Orders) e `InventoryItem` (Inventory), collegati tramite `productId`.

---

### 7.2 Conflitto di Requisiti (Requirement Conflict)

**Definizione**: Due requisiti in domini diversi (o nello stesso dominio) si contraddicono logicamente.

**Severità**: HIGH

**Esempio**:
- Requisito A: "Il prezzo di un ordine è immutabile dopo la conferma"
- Requisito B: "Il cliente può applicare coupon retroattivi entro 24h"
- PROBLEMA: Contraddizione logica

**Risoluzione Suggerita**: Chiarire con il business quale requisito ha priorità, oppure definire un modello che li concili (es. "prezzo base immutabile, adjustment separato").

---

### 7.3 Ambiguità Semantica (Semantic Ambiguity)

**Definizione**: Un'entità, un evento o un concetto non ha una definizione chiara o può essere interpretato in modi diversi.

**Severità**: MEDIUM

**Esempio**:
- Entità `Transaction` senza specifica: è un pagamento? Un movimento di magazzino? Un'operazione contabile?

**Risoluzione Suggerita**: Rinominare con termine specifico (`PaymentTransaction`, `InventoryMovement`) o aggiungere definizione esplicita.

---

### 7.4 Evento Duplicato (Duplicate Event Emitter)

**Definizione**: Lo stesso tipo di evento viene emesso da più di un dominio/servizio.

**Severità**: HIGH

**Esempio**:
- `OrderCreated` emesso da Order Management
- `OrderCreated` emesso anche da Legacy System
- PROBLEMA: Chi è la fonte di verità?

**Risoluzione Suggerita**: Definire un solo emettitore; l'altro sistema deve consumare l'evento o usare un nome diverso.

---

### 7.5 Pattern Incoerente (Incompatible Communication Pattern)

**Definizione**: Due domini collegati usano pattern di comunicazione incompatibili rispetto ai requisiti di consistenza.

**Severità**: MEDIUM-HIGH

**Esempio**:
- Dominio A usa Event Sourcing e pubblica eventi
- Dominio B (che dipende da A) usa solo chiamate sincrone
- PROBLEMA: B non può reagire agli eventi di A

**Risoluzione Suggerita**: B deve implementare un consumer per gli eventi di A, oppure A deve esporre anche API sincrone.

---

### 7.6 Naming Non Conforme (Event Naming Violation)

**Definizione**: Un evento non segue le convenzioni di naming (non è in passato, è troppo generico, usa termini tecnici).

**Severità**: LOW

**Esempio**:
- `ProcessPayment` invece di `PaymentProcessed`
- `Update` invece di `OrderStatusChanged`

**Risoluzione Suggerita**: Rinominare seguendo la convenzione `<Aggregate><PastTenseVerb>`.

---

### 7.7 Classificazione Errata del Dominio (Misclassified Domain)

**Definizione**: Un dominio è classificato come Core/Supporting/Generic ma i criteri non lo supportano.

**Severità**: MEDIUM

**Esempio**:
- "Autenticazione" classificata come Core Domain
- PROBLEMA: È una commodity, non differenziante

**Risoluzione Suggerita**: Riclassificare come Generic Domain.

---

## PARTE 8: TEMPLATE PER L'OUTPUT DELL'ANALISI

### 8.1 Template Problema Rilevato

```json
{
  "problem_id": "P001",
  "type": "ENTITY_OVERLAP | REQUIREMENT_CONFLICT | SEMANTIC_AMBIGUITY | DUPLICATE_EVENT | INCOMPATIBLE_PATTERN | NAMING_VIOLATION | MISCLASSIFIED_DOMAIN",
  "severity": "HIGH | MEDIUM | LOW",
  "location": {
    "domains_involved": ["Domain1", "Domain2"],
    "elements_involved": ["Entity1", "Event1"]
  },
  "description": "Descrizione chiara del problema",
  "evidence": "Citazione specifica dal modello che evidenzia il problema",
  "suggestion": "Suggerimento di risoluzione",
  "requires_business_clarification": true/false
}
```

### 8.2 Template Domanda di Follow-up

```json
{
  "question_id": "Q001",
  "related_problem": "P001",
  "target": "business_stakeholder",
  "question": "Domanda chiara e specifica",
  "context": "Perché questa domanda è importante",
  "options": ["Opzione A", "Opzione B"],
  "priority": "HIGH | MEDIUM | LOW"
}
```

---

*Fine della Knowledge Base*
