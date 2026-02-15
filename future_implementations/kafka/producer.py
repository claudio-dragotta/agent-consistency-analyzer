"""
Kafka Producer for Agent 2
Sends validation results to Agent 3 input topic
"""

import json
import logging
from typing import Dict, Any
from kafka import KafkaProducer
from kafka.errors import KafkaError

from app.config import settings

logger = logging.getLogger(__name__)


class Agent3Producer:
    """
    Kafka producer that sends Agent 2 validation results
    to Agent 3 input topic
    """

    def __init__(self):
        """Initialize Kafka producer"""
        self.producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",  # Wait for all replicas to acknowledge
            retries=3,
            max_in_flight_requests_per_connection=1,  # Ensure ordering
        )
        logger.info(
            f"Kafka producer initialized for topic: {settings.KAFKA_OUTPUT_TOPIC}"
        )

    def send_validation_result(self, result: Dict[str, Any]) -> bool:
        """
        Send validation result to Agent 3

        Args:
            result: Validation result from Agent 2

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            future = self.producer.send(settings.KAFKA_OUTPUT_TOPIC, value=result)

            # Wait for message to be sent
            record_metadata = future.get(timeout=10)

            logger.info(
                f"Message sent successfully to topic {record_metadata.topic}, "
                f"partition {record_metadata.partition}, offset {record_metadata.offset}"
            )

            return True

        except KafkaError as e:
            logger.error(f"Failed to send message: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return False

    def close(self):
        """Close producer connection"""
        self.producer.flush()
        self.producer.close()
        logger.info("Kafka producer closed")


# Singleton instance
_producer_instance = None


def get_producer() -> Agent3Producer:
    """Get or create producer instance"""
    global _producer_instance
    if _producer_instance is None:
        _producer_instance = Agent3Producer()
    return _producer_instance


def send_to_agent3(result: Dict[str, Any]) -> bool:
    """
    Convenience function to send result to Agent 3

    Args:
        result: Validation result from Agent 2

    Returns:
        True if sent successfully, False otherwise
    """
    producer = get_producer()
    return producer.send_validation_result(result)
