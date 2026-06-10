import json
import logging
import os
from datetime import UTC, datetime

from dotenv import load_dotenv
from fastapi.exceptions import HTTPException
from pydantic import Field
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from uuid_extensions import uuid7str

from chatapi.config import DEFAULT_MODEL_CONFIG
from chatapi.models.history import AgentReasoning, AgentUsedTools
from chatapi.models.orm import BaseStorage, ChatHistory, ChatRole, ChatType

load_dotenv()

logger = logging.getLogger("database")


class BaseChatHistory(BaseSettings):
    DB_URI: str = Field(
        default=f"postgresql://postgres:{os.getenv('PGPASSWORD', 'postgres')}@localhost:5432/postgres",
    )
    DB_POOL_SIZE: int = Field(default=50)
    DB_OVERFLOW: int = Field(default=0)

    model_config = DEFAULT_MODEL_CONFIG

    def __init__(self, db: Session | None = None) -> None:
        super().__init__()
        self._db = None

        if db is not None:
            self._connected = True
            self._db = db
            return

        try:
            self._connected = False
            logger.debug(f"connection '{self.DB_URI}'")
            logger.info(f" - overflow:{self.DB_OVERFLOW} pool_size:{self.DB_POOL_SIZE}")
            self._engine = create_engine(self.DB_URI, pool_size=self.DB_POOL_SIZE, max_overflow=self.DB_OVERFLOW)
            self._session = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)
        except OperationalError as e:
            logger.error(f"Failed to connect to database: {e!s}")

        BaseStorage.metadata.create_all(bind=self._engine)
        logger.info("Tables have been created.")

    def __enter__(self) -> "BaseChatHistory":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        # self._session.close_all()
        # self._engine.clear_compiled_cache()
        return

    def conn(self) -> Session:
        if not self._session:
            logger.error("Database session failure.")

        return self._session()

    def add_message(
        self,
        content: str,
        role: ChatRole,
        chat_type: ChatType,
        session_id: str,
        state: dict | None = None,
        chat_id: str | None = None,
        agent_reasoning: list[AgentReasoning] | None = None,
        used_tools: list[AgentUsedTools] | None = None,
    ) -> None:
        """Adds a new message to current transaction."""
        if used_tools is None:
            used_tools = []
        if agent_reasoning is None:
            agent_reasoning = []
        if self._db is None or not self._connected:
            self._connected = True
            self._db = self.conn()

        self._db.add(
            ChatHistory(
                chatId=chat_id,
                sessionId=session_id,
                role=role,
                content=content,
                state=json.dumps(state, ensure_ascii=False) if state else None,
                createdDate=datetime.now(UTC),
                agentReasoning=f"[{','.join([json.dumps(reason, ensure_ascii=False) for reason in agent_reasoning])}]",
                usedTools=f"[{','.join([json.dumps(tool, ensure_ascii=False) for tool in used_tools])}]",
                chatType=chat_type,
            ),
        )

    def save(self) -> None:
        """Commits the current transaction to the database."""
        if self._db is None or not self._connected:
            return

        try:
            self._db.commit()
        except SQLAlchemyError as e:
            self._db.rollback()
            raise HTTPException(status_code=500, detail=f"SQLAlchemyError::{e}") from e
        # Connection is kept open for future use

    def extract_human_message(
        self,
        session_id: str,
        chat_type: ChatType,
        content: str,
        state: dict | None,
        reasoning: dict | None = None,
    ) -> str:
        """Extract and store a human message."""

        if not session_id:
            raise HTTPException(status_code=500, detail="SessionId cannot be empty")

        chat_id = uuid7str()
        if reasoning and not reasoning.get("nodeId"):
            reasoning["nodeId"] = chat_id

        # Store the message
        self.add_message(
            chat_id=chat_id,
            session_id=session_id,
            chat_type=chat_type,
            content=content,
            state=state,
            role=ChatRole.HUMAN,
            agent_reasoning=[reasoning] if reasoning is not None else [],  # type: ignore
        )
        return chat_id

    def extract_ai_message(
        self,
        chat_id: str,
        session_id: str,
        chat_type: ChatType,
        content: str,
        state: dict | None,
        reasoning: list,
        tools: list,
    ) -> None:
        """Extract and store a ai message."""
        # Store the message
        if not reasoning:
            raise HTTPException(status_code=500, detail="AI `content` or `agent_reasoning` data cannot be empty")

        self.add_message(
            chat_id=chat_id,
            content=content,
            session_id=session_id,
            role=ChatRole.AI,
            chat_type=chat_type,
            state=state,
            agent_reasoning=reasoning,  # No need to convert to string
            used_tools=tools,
        )
