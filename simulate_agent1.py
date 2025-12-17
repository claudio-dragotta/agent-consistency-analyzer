"""
Simulatore Agent 1 - Genera molteplici domain models
Utile per testare la capacità di Agent 2 di processare molti input
"""

import json
import time
import uuid
from datetime import datetime
from kafka import KafkaProducer

# Configurazione
KAFKA_SERVERS = "localhost:9092"
OUTPUT_TOPIC = "agent1-output"
NUM_MESSAGES = 10  # Numero di domain models da generare


def load_example_model():
    """Carica il model di esempio"""
    with open("input_agent/example_bad.json", "r", encoding="utf-8") as f:
        return json.load(f)


def create_message(model_index: int) -> dict:
    """Crea un messaggio simile a quello che Agent 1 invierebbe"""
    model = load_example_model()

    # Modifica leggermente il nome per distinguere i messaggi
    model["project_name"] = f"E-Commerce Platform - Iteration {model_index}"

    message = {
        "message_id": f"a1-msg-{str(uuid.uuid4())[:8]}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "agent": "agent-1-simulator",
        "iteration": model_index,
        "payload": {
            "domain_model": model
        }
    }

    return message


def main():
    print("=" * 60)
    print("Agent 1 Simulator - Kafka Producer")
    print("=" * 60)
    print()

    # Crea producer Kafka
    print(f"Connessione a Kafka: {KAFKA_SERVERS}...")
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_SERVERS.split(","),
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print("OK Connesso a Kafka")
    except Exception as e:
        print(f"X Errore connessione Kafka: {e}")
        print()
        print("Assicurati che Kafka sia in esecuzione:")
        print("  docker-compose -f docker-compose.full.yml up -d kafka")
        return

    print()
    print(f"Generazione di {NUM_MESSAGES} domain models...")
    print(f"Topic: {OUTPUT_TOPIC}")
    print()

    # Genera e invia messaggi
    for i in range(1, NUM_MESSAGES + 1):
        message = create_message(i)
        message_id = message["message_id"]

        try:
            # Invia a Kafka
            future = producer.send(OUTPUT_TOPIC, value=message)
            record_metadata = future.get(timeout=10)

            print(
                f"[{i}/{NUM_MESSAGES}] OK Messaggio {message_id} inviato "
                f"(partition={record_metadata.partition}, "
                f"offset={record_metadata.offset})"
            )

            # Attendi un po' prima del prossimo (simula Agent 1 reale)
            time.sleep(0.5)

        except Exception as e:
            print(f"[{i}/{NUM_MESSAGES}] X Errore invio {message_id}: {e}")

    producer.flush()
    producer.close()

    print()
    print("=" * 60)
    print("Simulazione completata!")
    print("=" * 60)
    print()
    print("Agent 2 consumer processerà questi messaggi automaticamente.")
    print()
    print("Per monitorare:")
    print("  1. Logs:      docker logs -f agent2-consumer")
    print("  2. Kafka UI:  http://localhost:8080")
    print("  3. Agent 2:   http://localhost:8002/health")


if __name__ == "__main__":
    main()
