"""
A2A Protocol - Request/Response Models

Models for A2A protocol operations including SendMessageRequest,
SendMessageConfiguration, and StreamResponse.

Based on A2A Protocol Specification v0.3
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field

from a2a.models.task import Task, TaskStatusUpdateEvent, TaskArtifactUpdateEvent
from a2a.models.message import Message


class PushNotificationConfig(BaseModel):
    """
    Configuration for setting up push notifications for task updates.
    """
    id: Optional[str] = Field(None, description="A unique identifier for this push notification")
    url: str = Field(..., description="URL to send the notification to")
    token: Optional[str] = Field(None, description="Token unique for this task/session")
    authentication: Optional["AuthenticationInfo"] = Field(
        None, 
        description="Information about the authentication to send with the notification"
    )


class AuthenticationInfo(BaseModel):
    """
    Defines authentication details, used for push notifications.
    """
    schemes: List[str] = Field(
        ..., 
        description="A list of supported authentication schemes (e.g., 'Basic', 'Bearer')"
    )
    credentials: Optional[str] = Field(None, description="Optional credentials")


class SendMessageConfiguration(BaseModel):
    """
    Configuration of a send message request.
    """
    accepted_output_modes: Optional[List[str]] = Field(
        None,
        alias="acceptedOutputModes",
        description="A list of media types the client is prepared to accept for response parts"
    )
    push_notification_config: Optional[PushNotificationConfig] = Field(
        None,
        alias="pushNotificationConfig",
        description="Configuration for the agent to send push notifications for task updates"
    )
    history_length: Optional[int] = Field(
        None,
        alias="historyLength",
        description="The maximum number of messages to include in the history"
    )
    blocking: Optional[bool] = Field(
        False,
        description="If true, the operation waits until the task reaches a terminal state"
    )

    class Config:
        populate_by_name = True


class SendMessageRequest(BaseModel):
    """
    Represents a request for the message/send method.
    """
    tenant: Optional[str] = Field(None, description="Optional tenant, provided as a path parameter")
    message: Message = Field(..., description="The message to send to the agent")
    configuration: Optional[SendMessageConfiguration] = Field(
        None, 
        description="Configuration for the send request"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="A flexible key-value map for passing additional context or parameters"
    )


class StreamResponse(BaseModel):
    """
    A wrapper object used in streaming operations to encapsulate different types of response data.
    
    A StreamResponse MUST contain exactly one of: task, message, statusUpdate, artifactUpdate
    """
    task: Optional[Task] = Field(None, description="A Task object containing the current state")
    message: Optional[Message] = Field(None, description="A Message object from the agent")
    status_update: Optional[TaskStatusUpdateEvent] = Field(
        None, 
        alias="statusUpdate",
        description="An event indicating a task status update"
    )
    artifact_update: Optional[TaskArtifactUpdateEvent] = Field(
        None, 
        alias="artifactUpdate",
        description="An event indicating a task artifact update"
    )

    class Config:
        populate_by_name = True

    @classmethod
    def from_task(cls, task: Task) -> "StreamResponse":
        """Create a StreamResponse containing a Task."""
        return cls(task=task)

    @classmethod
    def from_message(cls, message: Message) -> "StreamResponse":
        """Create a StreamResponse containing a Message."""
        return cls(message=message)

    @classmethod
    def from_status_update(cls, event: TaskStatusUpdateEvent) -> "StreamResponse":
        """Create a StreamResponse containing a TaskStatusUpdateEvent."""
        return cls(status_update=event)

    @classmethod
    def from_artifact_update(cls, event: TaskArtifactUpdateEvent) -> "StreamResponse":
        """Create a StreamResponse containing a TaskArtifactUpdateEvent."""
        return cls(artifact_update=event)


class GetTaskRequest(BaseModel):
    """
    Represents a request for the tasks/get method.
    """
    tenant: Optional[str] = Field(None, description="Optional tenant")
    name: str = Field(..., description="The resource name of the task. Format: tasks/{task_id}")
    history_length: Optional[int] = Field(
        None, 
        alias="historyLength",
        description="The maximum number of messages to include in the history"
    )

    class Config:
        populate_by_name = True


class ListTasksRequest(BaseModel):
    """
    Parameters for listing tasks with optional filtering criteria.
    """
    tenant: Optional[str] = Field(None, description="Optional tenant")
    context_id: Optional[str] = Field(None, alias="contextId", description="Filter tasks by context ID")
    status: Optional[str] = Field(None, description="Filter tasks by their current status state")
    page_size: Optional[int] = Field(50, alias="pageSize", description="Maximum number of tasks to return (1-100)")
    page_token: Optional[str] = Field(None, alias="pageToken", description="Token for pagination")
    history_length: Optional[int] = Field(None, alias="historyLength", description="Messages to include in history")
    last_updated_after: Optional[int] = Field(
        None, 
        alias="lastUpdatedAfter",
        description="Filter tasks updated after this timestamp (milliseconds since epoch)"
    )
    include_artifacts: Optional[bool] = Field(
        False, 
        alias="includeArtifacts",
        description="Whether to include artifacts in the returned tasks"
    )

    class Config:
        populate_by_name = True


class ListTasksResponse(BaseModel):
    """
    Result object for tasks/list method.
    """
    tasks: List[Task] = Field(..., description="Array of tasks matching the specified criteria")
    next_page_token: str = Field(
        "", 
        alias="nextPageToken",
        description="Token for retrieving the next page. Empty string if no more results."
    )
    page_size: int = Field(..., alias="pageSize", description="The size of page requested")
    total_size: int = Field(..., alias="totalSize", description="Total number of tasks available")

    class Config:
        populate_by_name = True


class CancelTaskRequest(BaseModel):
    """
    Represents a request for the tasks/cancel method.
    """
    tenant: Optional[str] = Field(None, description="Optional tenant")
    name: str = Field(..., description="The resource name of the task to cancel. Format: tasks/{task_id}")


class SubscribeToTaskRequest(BaseModel):
    """
    Request to subscribe to task updates.
    """
    tenant: Optional[str] = Field(None, description="Optional tenant")
    name: str = Field(..., description="The resource name of the task. Format: tasks/{task_id}")


# ============================================================================
# A2A Error Models
# ============================================================================

class A2AError(BaseModel):
    """
    Base error model for A2A protocol errors.
    """
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class TaskNotFoundError(A2AError):
    """The specified task ID does not correspond to an existing or accessible task."""
    code: str = "TASK_NOT_FOUND"


class TaskNotCancelableError(A2AError):
    """The task is not in a cancelable state."""
    code: str = "TASK_NOT_CANCELABLE"


class PushNotificationNotSupportedError(A2AError):
    """Push notifications are not supported by the agent."""
    code: str = "PUSH_NOTIFICATION_NOT_SUPPORTED"


class UnsupportedOperationError(A2AError):
    """The requested operation is not supported."""
    code: str = "UNSUPPORTED_OPERATION"


class ContentTypeNotSupportedError(A2AError):
    """A media type in the request is not supported."""
    code: str = "CONTENT_TYPE_NOT_SUPPORTED"


class InvalidAgentResponseError(A2AError):
    """An agent returned a response that does not conform to the specification."""
    code: str = "INVALID_AGENT_RESPONSE"
