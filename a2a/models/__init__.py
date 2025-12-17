"""
A2A Protocol Models

This package contains the Pydantic models for the A2A (Agent-to-Agent) protocol.
Based on A2A Protocol Specification v0.3
"""

from a2a.models.task import (
    Task,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent
)

from a2a.models.message import (
    Message,
    Part,
    Role,
    FilePart,
    DataPart,
    TextPart
)

from a2a.models.artifact import (
    Artifact,
    ValidationReportArtifact,
    FollowUpQuestionsArtifact,
    RefinedModelArtifact
)

__all__ = [
    # Task models
    "Task",
    "TaskState",
    "TaskStatus",
    "TaskStatusUpdateEvent",
    "TaskArtifactUpdateEvent",
    
    # Message models
    "Message",
    "Part",
    "Role",
    "FilePart",
    "DataPart",
    "TextPart",
    
    # Artifact models
    "Artifact",
    "ValidationReportArtifact",
    "FollowUpQuestionsArtifact",
    "RefinedModelArtifact"
]
