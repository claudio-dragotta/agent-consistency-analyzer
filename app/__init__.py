"""
Agent 2 - Consistency & Conflict Analyzer
Main application package

This agent analyzes domain models for:
- Semantic consistency (entity overlaps, ambiguous terms)
- Requirement conflicts
- Event architecture issues
- Domain classification problems

Uses A2A Protocol v0.3 for inter-agent communication.
"""

__version__ = "1.0.0"
__protocol_version__ = "A2A v0.3"

from app.config import settings, get_settings

__all__ = ["settings", "get_settings"]
