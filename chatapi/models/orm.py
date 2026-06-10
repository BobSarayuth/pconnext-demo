import enum

from sqlalchemy import TIMESTAMP, Boolean, Column, Enum, LargeBinary, String, Text
from sqlalchemy.orm import declarative_base

BaseStorage = declarative_base()


class ChatRole(enum.Enum):
    HUMAN = "HUMAN"
    AI = "AI"


class ChatType(enum.Enum):
    EXTERNAL = "EXTERNAL"
    INTERNAL = "INTERNAL"


class ChatHistory(BaseStorage):
    __tablename__ = "chat_messages"
    chatId = Column(String, primary_key=True, nullable=False)
    sessionId = Column(String, nullable=False)
    role = Column(Enum(ChatRole), primary_key=True, nullable=False)
    content = Column(Text, nullable=True)
    state = Column(Text, nullable=True, default=None)
    agentReasoning = Column(Text, nullable=True, default="[]")
    usedTools = Column(Text, nullable=True, default="[]")
    sourceDocuments = Column(Text, nullable=True, default="[]")  # this field is for embedding document
    chatType = Column(Enum(ChatType), nullable=False, default=ChatType.INTERNAL)
    deleted = Column(Boolean, nullable=False, default=False)
    createdDate = Column(TIMESTAMP, nullable=False, default="now()")


class FileStorage(BaseStorage):
    __tablename__ = "file_storage"
    sessionId = Column(String, primary_key=True, nullable=False)
    checkSum = Column(String, primary_key=True, nullable=False)
    fileName = Column(String, nullable=False)
    fileType = Column(String, nullable=False)
    blob = Column(LargeBinary, nullable=False)
    createdDate = Column(TIMESTAMP, nullable=False, default="now()")


class DynamicPrompt(BaseStorage):
    __tablename__ = "dynamic_prompts"
    path = Column(String, primary_key=True, nullable=False)
    content = Column(Text, nullable=False)
    createdDate = Column(TIMESTAMP, nullable=False, default="now()")
    updatedDate = Column(TIMESTAMP, nullable=False, default="now()")
