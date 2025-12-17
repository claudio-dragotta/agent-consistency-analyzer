"""
Kafka Consumer for Agent 2
Consumes domain models from Agent 1 output topic
"""

import json
import logging
from typing import Dict, Any
from kafka import KafkaConsumer
from kafka.errors import KafkaError

from app.config import settings

logger = logging.getLogger(__name__)


class Agent1Consumer:
    """
    Kafka consumer that listens to Agent 1 output
    and triggers Agent 2 validation pipeline
    """

    def __init__(self):
        """Initialize Kafka consumer"""
        self.consumer = KafkaConsumer(
            settings.KAFKA_INPUT_TOPIC,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
            group_id=settings.KAFKA_GROUP_ID,
            auto_offset_reset=settings.KAFKA_AUTO_OFFSET_RESET,
            enable_auto_commit=settings.KAFKA_ENABLE_AUTO_COMMIT,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        logger.info(
            f"Kafka consumer initialized for topic: {settings.KAFKA_INPUT_TOPIC}"
        )

    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming message from Agent 1

        Args:
            message: Message from Agent 1 containing domain model

        Returns:
            Validation result for Agent 3
        """
        try:
            # Extract domain model from message
            domain_model = message.get("payload", {}).get("domain_model", {})
            message_id = message.get("message_id")

            logger.info(f"Processing message {message_id} from Agent 1")

            # TODO: Call Agent 2 validation pipeline
            # from app.services.validator import validate_domain_model
            # result = validate_domain_model(domain_model)

            # Placeholder response
            result = {
                "status": "PROCESSING",
                "message": "Agent 2 validation pipeline not yet implemented",
            }

            return {
                "message_id": f"agent2-{message_id}",
                "correlation_id": message_id,
                "timestamp": message.get("timestamp"),
                "agent": "agent-2",
                "payload": result,
            }

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            raise

    def start(self):
        """Start consuming messages from Agent 1"""
        logger.info("Starting Agent 2 Kafka consumer...")

        try:
            for message in self.consumer:
                try:
                    logger.info(
                        f"Received message from topic {message.topic}, "
                        f"partition {message.partition}, offset {message.offset}"
                    )

                    # Process message
                    result = self.process_message(message.value)

                    # TODO: Send result to Agent 3 via producer
                    # from app.kafka.producer import send_to_agent3
                    # send_to_agent3(result)

                    logger.info(f"Message processed successfully: {result.get('message_id')}")

                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    continue

        except KeyboardInterrupt:
            logger.info("Consumer stopped by user")
        except KafkaError as e:
            logger.error(f"Kafka error: {str(e)}")
        finally:
            self.consumer.close()
            logger.info("Kafka consumer closed")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Start consumer
    consumer = Agent1Consumer()
    consumer.start()
