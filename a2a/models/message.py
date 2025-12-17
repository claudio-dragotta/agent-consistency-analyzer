"""
A2A Protocol - Message Model

Message is one unit of communication between client and server. 
It is associated with a context and optionally a task.

Based on A2A Protocol Specification v0.3
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, model_validator
import uuid
import base64


class Role(str, Enum):
    """
    Defines the sender of a message in A2A protocol communication.
    """
    UNSPECIFIED = "unspecified"
    USER = "user"    # Communication from client to server
    AGENT = "agent"  # Communication from server to client


class TextPart(BaseModel):
    """
    A part containing text content.
    """
    text: str = Field(..., description="The string content of the text part")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class FilePart(BaseModel):
    """
    FilePart represents the different ways files can be provided.
    Either as a URI reference or as base64-encoded bytes.
    """
    file_with_uri: Optional[str] = Field(
        None, 
        alias="fileWithUri",
        description="A URL pointing to the file's content"
    )
    file_with_bytes: Optional[str] = Field(
        None, 
        alias="fileWithBytes",
        description="The base64-encoded content of the file"
    )
    media_type: Optional[str] = Field(
        None, 
        alias="mediaType",
        description="The media type of the file (e.g., 'application/pdf')"
    )
    name: Optional[str] = Field(
        None, 
        description="An optional name for the file (e.g., 'document.pdf')"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")

    class Config:
        populate_by_name = True

    @model_validator(mode='after')
    def check_file_source(self):
        """Ensure exactly one of file_with_uri or file_with_bytes is set."""
        if self.file_with_uri and self.file_with_bytes:
            raise ValueError("FilePart must have either fileWithUri or fileWithBytes, not both")
        if not self.file_with_uri and not self.file_with_bytes:
            raise ValueError("FilePart must have either fileWithUri or fileWithBytes")
        return self

    @classmethod
    def from_bytes(cls, data: bytes, media_type: str, name: Optional[str] = None) -> "FilePart":
        """Create a FilePart from raw bytes."""
        return cls(
            file_with_bytes=base64.b64encode(data).decode('utf-8'),
            media_type=media_type,
            name=name
        )

    @classmethod
    def from_uri(cls, uri: str, media_type: Optional[str] = None, name: Optional[str] = None) -> "FilePart":
        """Create a FilePart from a URI."""
        return cls(
            file_with_uri=uri,
            media_type=media_type,
            name=name
        )


class DataPart(BaseModel):
    """
    DataPart represents a structured data blob (JSON object).
    """
    data: Dict[str, Any] = Field(..., description="A JSON object containing arbitrary data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class Part(BaseModel):
    """
    Part represents a container for a section of communication content.
    Parts can be purely textual, some sort of file (image, video, etc) 
    or a structured data blob (i.e. JSON).
    
    A Part MUST contain exactly one of: text, file, data
    """
    text: Optional[str] = Field(None, description="The string content of the text part")
    file: Optional[FilePart] = Field(None, description="The file content")
    data: Optional[DataPart] = Field(None, description="The structured data content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")

    @model_validator(mode='after')
    def check_exactly_one_content(self):
        """Ensure exactly one of text, file, or data is set."""
        contents = [self.text is not None, self.file is not None, self.data is not None]
        if sum(contents) != 1:
            raise ValueError("Part must contain exactly one of: text, file, data")
        return self

    @classmethod
    def from_text(cls, text: str, metadata: Optional[Dict[str, Any]] = None) -> "Part":
        """Create a Part from text."""
        return cls(text=text, metadata=metadata)

    @classmethod
    def from_file(cls, file_part: FilePart, metadata: Optional[Dict[str, Any]] = None) -> "Part":
        """Create a Part from a file."""
        return cls(file=file_part, metadata=metadata)

    @classmethod
    def from_data(cls, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> "Part":
        """Create a Part from structured data."""
        return cls(data=DataPart(data=data), metadata=metadata)

    def get_content_type(self) -> str:
        """Get the type of content in this part."""
        if self.text is not None:
            return "text"
        elif self.file is not None:
            return "file"
        elif self.data is not None:
            return "data"
        return "unknown"


class Message(BaseModel):
    """
    Message is one unit of communication between client and server.
    
    It is associated with a context and optionally a task. Since the server 
    is responsible for the context definition, it must always provide a 
    context_id in its messages. The client can optionally provide the 
    context_id if it knows the context to associate the message to.
    """
    message_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        alias="messageId",
        description="The unique identifier (UUID) of the message"
    )
    context_id: Optional[str] = Field(
        None,
        alias="contextId",
        description="The context id of the message"
    )
    task_id: Optional[str] = Field(
        None,
        alias="taskId",
        description="The task id of the message"
    )
    role: Role = Field(
        ...,
        description="Identifies the sender of the message"
    )
    parts: List[Part] = Field(
        ...,
        min_length=1,
        description="Parts is the container of the message content"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Any optional metadata to provide along with the message"
    )
    extensions: Optional[List[str]] = Field(
        None,
        description="The URIs of extensions that are present or contributed to this Message"
    )
    reference_task_ids: Optional[List[str]] = Field(
        None,
        alias="referenceTaskIds",
        description="A list of task IDs that this message references for additional context"
    )

    class Config:
        populate_by_name = True

    @classmethod
    def create_user_message(
        cls,
        parts: List[Part],
        context_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "Message":
        """Factory method to create a user message."""
        return cls(
            role=Role.USER,
            parts=parts,
            context_id=context_id,
            task_id=task_id,
            metadata=metadata
        )

    @classmethod
    def create_agent_message(
        cls,
        parts: List[Part],
        context_id: str,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "Message":
        """Factory method to create an agent message."""
        return cls(
            role=Role.AGENT,
            parts=parts,
            context_id=context_id,
            task_id=task_id,
            metadata=metadata
        )

    @classmethod
    def from_text(
        cls,
        text: str,
        role: Role,
        context_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> "Message":
        """Create a simple text message."""
        return cls(
            role=role,
            parts=[Part.from_text(text)],
            context_id=context_id,
            task_id=task_id
        )

    @classmethod
    def from_data(
        cls,
        data: Dict[str, Any],
        role: Role,
        context_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> "Message":
        """Create a message with structured data."""
        return cls(
            role=role,
            parts=[Part.from_data(data)],
            context_id=context_id,
            task_id=task_id
        )

    def get_text_content(self) -> str:
        """Extract all text content from message parts."""
        texts = []
        for part in self.parts:
            if part.text is not None:
                texts.append(part.text)
        return "\n".join(texts)

    def get_data_content(self) -> List[Dict[str, Any]]:
        """Extract all data content from message parts."""
        data_list = []
        for part in self.parts:
            if part.data is not None:
                data_list.append(part.data.data)
        return data_list

    def has_data(self) -> bool:
        """Check if message contains any data parts."""
        return any(part.data is not None for part in self.parts)

    def has_files(self) -> bool:
        """Check if message contains any file parts."""
        return any(part.file is not None for part in self.parts)
