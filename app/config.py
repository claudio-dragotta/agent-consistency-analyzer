"""
Configuration settings for Agent 2 - Consistency & Conflict Analyzer
Loads settings from environment variables
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Ollama Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    OLLAMA_TIMEOUT: int = 120

    # Kafka Configuration (A2A Communication)
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_INPUT_TOPIC: str = "agent1-output"
    KAFKA_OUTPUT_TOPIC: str = "agent2-output"
    KAFKA_GROUP_ID: str = "agent2-consistency-analyzer"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_ENABLE_AUTO_COMMIT: bool = True

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Sentence Transformers
    EMBEDDINGS_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDINGS_CACHE_DIR: str = "./models"

    # Similarity Thresholds
    ENTITY_OVERLAP_THRESHOLD: float = 0.85
    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.75

    # Analysis Settings
    MAX_WORKERS: int = 4
    ENABLE_CACHING: bool = True
    CACHE_TTL_SECONDS: int = 3600

    # Knowledge Base Paths
    KNOWLEDGE_BASE_DIR: str = "./knowledge_base"
    DDD_RULES_PATH: str = "./knowledge_base/ddd_rules.md"
    VALIDATION_CHECKLIST_PATH: str = "./knowledge_base/validation_checklist.json"

    # Input/Output directories
    INPUT_DIR: str = "./input_agent"
    OUTPUT_DIR: str = "./output_agent"

    # A2A Protocol settings
    AGENT_CARD_PATH: str = "./a2a/agent_card.json"

    # Question generation
    MAX_FOLLOW_UP_QUESTIONS: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_ollama_generate_url(self) -> str:
        """Get Ollama generate API URL."""
        return f"{self.OLLAMA_BASE_URL}/api/generate"

    def get_ollama_chat_url(self) -> str:
        """Get Ollama chat API URL."""
        return f"{self.OLLAMA_BASE_URL}/api/chat"

    def load_ddd_rules(self) -> str:
        """Load DDD rules markdown content."""
        from pathlib import Path
        rules_path = Path(self.DDD_RULES_PATH)
        if rules_path.exists():
            return rules_path.read_text(encoding="utf-8")
        raise FileNotFoundError(f"DDD rules file not found: {rules_path}")

    def load_validation_checklist(self) -> dict:
        """Load validation checklist JSON."""
        import json
        from pathlib import Path
        checklist_path = Path(self.VALIDATION_CHECKLIST_PATH)
        if checklist_path.exists():
            return json.loads(checklist_path.read_text(encoding="utf-8"))
        raise FileNotFoundError(f"Validation checklist not found: {checklist_path}")

    def load_agent_card(self) -> dict:
        """Load agent card JSON."""
        import json
        from pathlib import Path
        card_path = Path(self.AGENT_CARD_PATH)
        if card_path.exists():
            return json.loads(card_path.read_text(encoding="utf-8"))
        raise FileNotFoundError(f"Agent card not found: {card_path}")


# Singleton instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings (dependency injection helper)."""
    return settings
