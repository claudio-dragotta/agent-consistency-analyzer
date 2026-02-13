"""
Advanced Kafka Consumer for Agent 2
Gestisce molteplici analisi in parallelo da Agent 1
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from concurrent.futures import ThreadPoolExecutor

from app.config import settings
from app.kafka.producer import send_to_agent3

logger = logging.getLogger(__name__)


class Agent2KafkaConsumer:
    """
    Kafka consumer avanzato per Agent 2.

    Gestisce:
    - Molteplici messaggi da Agent 1
    - Processing in parallelo
    - Tracciamento dei task (A2A Protocol)
    - Produzione automatica risultati per Agent 3
    """

    def __init__(self, max_workers: int = 4):
        """
        Args:
            max_workers: Numero massimo di analisi in parallelo
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        self.consumer = KafkaConsumer(
            settings.KAFKA_INPUT_TOPIC,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
            group_id=settings.KAFKA_GROUP_ID,
            auto_offset_reset=settings.KAFKA_AUTO_OFFSET_RESET,
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            # Configurazioni per performance
            max_poll_records=10,  # Processa max 10 messaggi alla volta
            session_timeout_ms=30000,
            heartbeat_interval_ms=10000,
        )

        logger.info(
            f"Kafka consumer initialized: "
            f"topic={settings.KAFKA_INPUT_TOPIC}, "
            f"workers={max_workers}"
        )

    async def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Processa un singolo messaggio da Agent 1.

        Args:
            message: Messaggio Kafka con domain model

        Returns:
            Risultato dell'analisi per Agent 3
        """
        try:
            # Estrai informazioni dal messaggio
            message_id = message.get("message_id") or message.get("id")
            domain_model = message.get("payload", {}).get("domain_model") or message.get("domain_model")

            if not domain_model:
                logger.error(f"No domain model found in message {message_id}")
                return None

            logger.info(f"Processing message {message_id} from Agent 1...")

            # Import qui per evitare circular imports
            from app.services import (
                SemanticAnalyzer, ConflictDetector,
                QuestionGenerator, ModelRefiner
            )

            # Inizializza servizi (può essere fatto una volta sola in produzione)
            semantic_analyzer = SemanticAnalyzer(
                model_name=settings.EMBEDDINGS_MODEL,
                similarity_threshold=settings.SEMANTIC_SIMILARITY_THRESHOLD
            )
            conflict_detector = ConflictDetector(settings)
            question_generator = QuestionGenerator(settings)
            model_refiner = ModelRefiner(settings)

            # Step 1: Semantic Analysis
            logger.info(f"[{message_id}] Running semantic analysis...")
            semantic_issues = semantic_analyzer.analyze(domain_model)

            # Step 2: Conflict Detection (senza LLM per velocità)
            logger.info(f"[{message_id}] Running conflict detection...")
            conflict_issues = await conflict_detector.analyze(domain_model, use_llm=False)

            # Step 3: Generate Questions
            logger.info(f"[{message_id}] Generating questions...")
            questions = await question_generator.generate_questions(
                semantic_issues,
                conflict_issues,
                max_questions=settings.MAX_FOLLOW_UP_QUESTIONS,
                use_llm=False
            )

            # Step 4: Refine Model
            logger.info(f"[{message_id}] Refining model...")
            refined_model, refinement_report = await model_refiner.refine_model(
                domain_model,
                semantic_issues,
                conflict_issues,
                questions,
                apply_auto_fixes=True,
                use_llm=False
            )

            # Costruisci risultato
            result = {
                "message_id": f"agent2-{message_id}",
                "correlation_id": message_id,
                "timestamp": message.get("timestamp"),
                "agent": "agent-2",
                "status": "COMPLETED",
                "payload": {
                    "validation_status": "ISSUES_FOUND" if (semantic_issues or conflict_issues) else "VALID",
                    "summary": {
                        "total_issues": len(semantic_issues) + len(conflict_issues),
                        "entity_overlaps": sum(1 for i in semantic_issues if i.issue_type.value == "ENTITY_OVERLAP"),
                        "semantic_ambiguities": sum(1 for i in semantic_issues if i.issue_type.value == "SEMANTIC_AMBIGUITY"),
                        "requirement_conflicts": sum(1 for i in conflict_issues if i.conflict_type.value == "REQUIREMENT_CONFLICT"),
                        "duplicate_events": sum(1 for i in conflict_issues if i.conflict_type.value == "DUPLICATE_EVENT"),
                        "naming_violations": sum(1 for i in conflict_issues if i.conflict_type.value == "NAMING_VIOLATION"),
                        "incompatible_patterns": sum(1 for i in conflict_issues if i.conflict_type.value == "INCOMPATIBLE_PATTERN"),
                        "misclassified_domains": sum(1 for i in conflict_issues if i.conflict_type.value == "MISCLASSIFIED_DOMAIN"),
                        "auto_fixed": refinement_report.auto_fixed,
                        "requires_manual": refinement_report.requires_manual
                    },
                    "semantic_issues": [i.to_dict() for i in semantic_issues],
                    "conflict_issues": [i.to_dict() for i in conflict_issues],
                    "follow_up_questions": [q.to_dict() for q in questions],
                    "refinement_report": refinement_report.to_dict(),
                    "refined_model": refined_model
                }
            }

            logger.info(
                f"[{message_id}] Analysis complete: "
                f"{len(semantic_issues) + len(conflict_issues)} issues found"
            )

            return result

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return {
                "message_id": f"agent2-{message_id}",
                "correlation_id": message_id,
                "agent": "agent-2",
                "status": "FAILED",
                "error": str(e)
            }

    def start(self):
        """Avvia il consumer Kafka in modalità continua."""
        logger.info("Starting Agent 2 Kafka consumer...")
        logger.info(f"Listening on topic: {settings.KAFKA_INPUT_TOPIC}")
        logger.info(f"Max parallel workers: {self.max_workers}")

        try:
            for message in self.consumer:
                try:
                    logger.info(
                        f" Received message from topic={message.topic}, "
                        f"partition={message.partition}, offset={message.offset}"
                    )

                    # Processa il messaggio
                    result = asyncio.run(self.process_message(message.value))

                    if result:
                        # Invia risultato ad Agent 3
                        success = send_to_agent3(result)

                        if success:
                            logger.info(
                                f"OK Message {result.get('correlation_id')} processed "
                                f"and sent to Agent 3"
                            )
                        else:
                            logger.error(
                                f" Failed to send result to Agent 3 "
                                f"for message {result.get('correlation_id')}"
                            )
                    else:
                        logger.warning("No result produced from processing")

                except Exception as e:
                    logger.error(f"Error in message processing loop: {e}", exc_info=True)
                    continue

        except KeyboardInterrupt:
            logger.info("Consumer stopped by user")
        except KafkaError as e:
            logger.error(f"Kafka error: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up Kafka consumer...")
        self.executor.shutdown(wait=True)
        self.consumer.close()
        logger.info("Kafka consumer closed")


def main():
    """Entry point for running the Kafka consumer standalone."""
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    consumer = Agent2KafkaConsumer(max_workers=4)
    consumer.start()


if __name__ == "__main__":
    main()
