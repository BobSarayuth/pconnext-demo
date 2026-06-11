from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from uuid_extensions import uuid7str

from chatapi.models.history import AgentReasoning


class FormatType(str, Enum):
    JSON = "json"
    RAW = "raw"


class PredictionConfig(BaseModel):
    username: str | None = Field(default="", description="User identifier", examples=["test"])
    userAgent: str | None = Field(
        default="",
        description="Agent or service identifier from header",
        examples=["scg-home@1.0"],
    )


class PredictionAttachment(BaseModel):
    type: str | None = Field(default=None, description="Attachment media type, e.g. image, audio, image/jpeg")
    url: str | list[str] = Field(description="One or more attachment URLs")


class PredictionRequest(BaseModel):
    userAgent: str | None = Field(
        default=None,
        description="Agent or service identifier, accepted for LINE-style payloads",
        examples=["LINE"],
    )
    username: str | None = Field(
        default=None,
        description="User identifier, accepted for LINE-style payloads",
        examples=["user_123"],
    )
    question: str | None = Field(description="User's question", examples=["What is Python?"])
    config: PredictionConfig | dict | None = Field(
        default=None,
        description="Model invoke configuration",
        examples=[{"username": "abc"}],
    )
    attachments: list[str | PredictionAttachment] | None = Field(
        default_factory=list,
        description="List of attachment URLs or grouped attachments related to the question",
        examples=[
            ["http://example.com/image.jpg"],
            [{"type": "image", "url": ["http://example.com/image.jpg"]}],
            [{"type": "audio", "url": ["http://example.com/audio.m4a"]}],
        ],
    )
    sessionId: str | None = Field(
        default="",
        description="Session identifier",
        examples=["session_123"],
    )
    streaming: bool | None = Field(default=False, description="Streaming response flag", examples=[False])
    reasoning: bool | None = Field(default=False, description="Include agent reasoning flag", examples=[False])
    format: FormatType = Field(
        default=FormatType.JSON,
        description="Response format type",
        examples=[FormatType.JSON, FormatType.RAW],
    )

    class ConfigDict:
        from_attributes = True

    def generate_session(self) -> str:
        """Generate a unique session ID, optionally prefixed with username if available."""
        session_uuid = uuid7str()

        # If no config is provided, return just the UUID
        if not self.config:
            return session_uuid

        return session_uuid


class PredictionResponse(BaseModel):
    question: str | None = Field(description="Original user question", examples=["What is Python?"])
    text: str = Field(
        description="AI model response",
        examples=[
            "Python is a high-level, interpreted programming language known for its simplicity, "
            "readability, and versatility.",
        ],
    )
    artifact: list[dict] | dict[str, Any] | None = Field(
        default=None,
        description="Additional data or objects generated during the Responded message.",
        examples=[[{"success": True}], {"action": "NORMAL"}, None],
    )
    chatId: str = Field(description="Chat interaction ID", examples=["chat_123"])
    sessionId: str = Field(description="Chat session ID", examples=["session_123"])
    elapsed: float = Field(description="Response time in seconds")
    agentReasoning: list[AgentReasoning] = Field(
        description="Reasoning steps during response generation",
        default_factory=list,
        examples=[
            [
                AgentReasoning(
                    agentName="agent",
                    messages=["I need to explain what Python is"],
                    nodeId="node_123",
                    structured=None,
                    usedTools=[],
                    meta={},
                ),
            ],
        ],
    )


class UpdateSessionResponse(BaseModel):
    ok: bool = Field(description="Session deletion status", default=True)
    detail: str = Field(description="Details of session cleanup")


class ChunkPredictionResponse(BaseModel):
    mode: str
    chunk: dict
