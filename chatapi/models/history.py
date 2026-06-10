import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from chatapi.models.orm import ChatRole, ChatType  # Import Enums

RowTable = Any


class AgentUsedTools(BaseModel):
    id: str = Field(description="Tool usage ID")
    tool: str = Field(description="Tool name")
    toolInput: dict = Field(description="Tool input parameters")
    toolOutput: str | None = Field(default=None, description="Tool output")
    artifact: dict | None = Field(default=None, description="Generated artifact")

    class ConfigDict:
        from_attributes = True


class AgentReasoning(BaseModel):
    agentName: str | None = Field(default="", description="Agent name")
    messages: list[str] = Field(description="Reasoning messages")
    structured: Any | None = Field(default=None, description="Structured reasoning data")
    usedTools: list[AgentUsedTools] = Field(description="Tools used")
    invalids: list[dict] = Field(default=[], description="Failed operations")
    state: dict | None = Field(default=None, description="Reasoning state")
    nodeId: str | None = Field(default=None, description="Node ID")
    meta: dict = Field(description="Reasoning metadata")

    class ConfigDict:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    chatId: str = Field(description="Chat message ID")
    sessionId: str = Field(description="Chat session ID")
    role: ChatRole = Field(description="Message sender role")
    content: str = Field(description="Chat message content")
    structured: Any | None = Field(description="Structured payload format")
    state: dict | None = Field(description="Chat message state")
    agentReasoning: list[AgentReasoning] = Field(description="Agent reasoning details")
    usedTools: list[AgentUsedTools] = Field(description="Tools used in chat")
    sourceDocuments: list[dict] = Field(description="Source documents")
    chatType: ChatType = Field(description="Chat type")
    createdDate: str = Field(description="Message creation timestamp")
    deleted: bool = Field(description="Message deletion status")

    class ConfigDict:
        from_attributes = True  # Enables ORM serialization

    @classmethod
    def from_orm(cls, obj: RowTable) -> "ChatHistoryResponse":
        chat_type = ChatRole(obj.role)
        reasoning = json.loads(obj.agentReasoning)
        used = json.loads(obj.usedTools) if obj.usedTools and chat_type == ChatRole.AI else []
        return cls(
            chatId=obj.chatId,
            sessionId=obj.sessionId,
            role=ChatRole(obj.role),
            content=obj.content,
            structured=None,
            state=json.loads(obj.state or "{}"),
            agentReasoning=[AgentReasoning(**item) for item in reasoning],
            usedTools=[AgentUsedTools(**item) for item in used],
            sourceDocuments=[],
            chatType=obj.chatType,
            createdDate=obj.createdDate.replace(tzinfo=UTC).isoformat() if obj.createdDate else "",
            deleted=obj.deleted,
        )


class ChatMessageResponse(BaseModel):
    chatId: str = Field(description="Chat message ID")
    role: str = Field(description="Message sender role")
    content: str = Field(description="Chat message content")

    class ConfigDict:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj: RowTable) -> "ChatMessageResponse":
        return cls(
            chatId=obj.chatId,
            role=obj.role,
            content=obj.content,
        )


class ChatSessionHistoryResponse(BaseModel):
    sessionId: str = Field(description="Chat session ID")
    content: str | None = Field(default=None, description="Chat message content")
    usedTools: list[str] = Field(default_factory=list, description="Tools used in chat")
    chatType: ChatType = Field(description="Chat type")
    deleted: bool = Field(default=False, description="Session deletion status")
    beginDate: datetime = Field(description="Session start date")
    lastDate: datetime = Field(description="Session end date")
    files: int = Field(default=0, description="Uploaded files count")

    class ConfigDict:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj: RowTable) -> "ChatSessionHistoryResponse":
        return cls(
            sessionId=obj.sessionId,
            content=obj.content,
            usedTools=json.loads(obj.usedTools),
            chatType=obj.chatType,
            deleted=obj.deleted,
            beginDate=obj.beginDate,
            lastDate=obj.lastDate,
            files=obj.files,
        )


class ChatFullSessionHistoryResponse(BaseModel):
    sessionId: str = Field(description="Chat session ID")
    chatType: ChatType = Field(description="Chat type")
    deleted: bool = Field(default=False, description="Session deletion status")
    beginDate: datetime = Field(description="Session start date")
    lastDate: datetime = Field(description="Session end date")
    files: int = Field(default=0, description="Uploaded files count")
    turns: list["ChatExportTurnResponse"] = Field(description="Exported chat turns in this session")


class ChatExportToolResponse(BaseModel):
    tool: str = Field(description="Tool name")
    toolInput: dict = Field(description="Tool input parameters")
    toolOutput: str | None = Field(default=None, description="Tool output")


class ChatExportTurnResponse(BaseModel):
    chatId: str = Field(description="Chat turn ID")
    input: str | None = Field(default=None, description="User input")
    answer: str | None = Field(default=None, description="AI answer")
    contextWindow: list[dict[str, str]] = Field(
        default_factory=list,
        description="Messages and tool results available to the AI before generating this answer",
    )
    tools: list[ChatExportToolResponse] = Field(default_factory=list, description="Tools used by AI")
