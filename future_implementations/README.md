# Future Implementations

Questa cartella contiene moduli e configurazioni per funzionalita' pianificate ma **non ancora attive** nel flusso principale dell'Agent 2.

---

## Kafka - Pipeline Asincrona (Agent1 -> Agent2 -> Agent3)

**Contenuto:**
- `kafka/` — Consumer e Producer Kafka per la comunicazione asincrona tra agenti
  - `consumer_advanced.py` — Consumer che ascolta il topic `agent1-output`, analizza il modello e pubblica su `agent2-output`
  - `producer.py` — Producer per inviare i risultati ad Agent 3
- `docker-compose.kafka.yml` — Compose override che aggiunge Kafka, Zookeeper e Kafka UI allo stack

**Come attivare:**

1. Spostare la cartella `kafka/` in `app/kafka/`
2. Spostare `docker-compose.kafka.yml` nella root del progetto
3. Avviare con il compose override:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.kafka.yml up -d --build
   ```
4. Il consumer si avvia automaticamente e ascolta sul topic configurato in `.env` (`KAFKA_INPUT_TOPIC`)

**Prerequisiti:**
- Kafka broker raggiungibile (default: `localhost:9092`)
- Topic `agent1-output` creato (auto-create abilitato di default)
- Agent 1 che pubblica i modelli di dominio sul topic
