"""
A2A Protocol Implementation

This package provides a Python implementation of the Agent-to-Agent (A2A) protocol
for the Consistency & Conflict Analyzer agent.

Based on A2A Protocol Specification v0.3
https://a2a-protocol.org/latest/specification/
"""

__version__ = "0.3.0"
__protocol_version__ = "0.3"

from a2a.models import (
    # Task models
    Task,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
    
    # Message models
    Message,
    Part,
    Role,
    FilePart,
    DataPart,
    
    # Artifact models
    Artifact,
    ValidationReportArtifact,
    FollowUpQuestionsArtifact,
    RefinedModelArtifact
)

from a2a.models.requests import (
    # Request models
    SendMessageRequest,
    SendMessageConfiguration,
    PushNotificationConfig,
    AuthenticationInfo,
    GetTaskRequest,
    ListTasksRequest,
    ListTasksResponse,
    CancelTaskRequest,
    SubscribeToTaskRequest,
    StreamResponse,
    
    # Error models
    A2AError,
    TaskNotFoundError,
    TaskNotCancelableError,
    PushNotificationNotSupportedError,
    UnsupportedOperationError,
    ContentTypeNotSupportedError,
    InvalidAgentResponseError
)

__all__ = [
    # Version info
    "__version__",
    "__protocol_version__",
    
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
    
    # Artifact models
    "Artifact",
    "ValidationReportArtifact",
    "FollowUpQuestionsArtifact", 
    "RefinedModelArtifact",
    
    # Request models
    "SendMessageRequest",
    "SendMessageConfiguration",
    "PushNotificationConfig",
    "AuthenticationInfo",
    "GetTaskRequest",
    "ListTasksRequest",
    "ListTasksResponse",
    "CancelTaskRequest",
    "SubscribeToTaskRequest",
    "StreamResponse",
    
    # Error models
    "A2AError",
    "TaskNotFoundError",
    "TaskNotCancelableError",
    "PushNotificationNotSupportedError",
    "UnsupportedOperationError",
    "ContentTypeNotSupportedError",
    "InvalidAgentResponseError"
]
