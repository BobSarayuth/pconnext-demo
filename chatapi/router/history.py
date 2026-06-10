import csv
import json
import logging
from io import StringIO
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from chatapi.invokes.checkpoint import checkpoint_flush
from chatapi.models.chat import UpdateSessionResponse
from chatapi.models.history import AgentReasoning, ChatFullSessionHistoryResponse, ChatSessionHistoryResponse
from chatapi.router.middleware import api_key_authentication, param_records
from chatapi.router.queries import (
    delete_session_history,
    get_session_history,
    query_full_session_history,
    query_session_history,
)
from chatapi.router.utils import get_session


class ListReason(BaseModel):
    reason: list[AgentReasoning]


router = APIRouter(prefix="/api/history", dependencies=[Depends(api_key_authentication)])

logger = logging.getLogger("fastapi.history")


@router.get("/", response_model=list[ChatSessionHistoryResponse] | str, tags=["History"])
async def get_chat_message(
    query: Annotated[dict, Depends(param_records)],
    db: Annotated[Session, Depends(get_session)],
) -> list[ChatSessionHistoryResponse] | str:
    """
    Retrieve all chat history records where sessionId matches the provided session_id.

    Query Parameters:
    - session_id: The session ID to filter by
    - format: Export format (JSON or CSV, default: JSON)

    Returns:
    - JSON: List[ChatExportResponse]
    - CSV: String containing CSV data
    """
    try:
        return query_session_history(db, query)
    except Exception as e:
        logger.error(e, extra={"session_id": query.get("session_id")})
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/export/full", response_model=list[ChatFullSessionHistoryResponse] | str, tags=["History"])
async def export_full_chat_history(
    query: Annotated[dict, Depends(param_records)],
    db: Annotated[Session, Depends(get_session)],
    res_format: str = "json",
) -> list[ChatFullSessionHistoryResponse] | StreamingResponse:
    """
    Export full chat sessions active within a date range.

    The date range is used to select sessions. Each returned session includes compact turns:
    user input, AI answer, and tool input/output.
    """
    try:
        results = query_full_session_history(db, query)
        if res_format.lower() == "json":
            return results

        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "sessionId",
                "chatId",
                "input",
                "answer",
                "contextWindow",
                "tools",
            ],
            quoting=1,
        )
        writer.writeheader()
        for session in results:
            for turn in session.turns:
                writer.writerow(
                    {
                        "sessionId": session.sessionId,
                        "chatId": turn.chatId,
                        "input": turn.input,
                        "answer": turn.answer,
                        "contextWindow": json.dumps(turn.contextWindow or [], ensure_ascii=False),
                        "tools": json.dumps(
                            [tool.model_dump(mode="json") for tool in turn.tools],
                            ensure_ascii=False,
                        ),
                    }
                )

        return StreamingResponse(
            content=output.getvalue(),
            headers={"Content-Disposition": "attachment; filename=chat-history-export.csv"},
            media_type="text/csv",
        )
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/flush", response_model=UpdateSessionResponse, tags=["Chat"])
async def session_delete(
    db: Annotated[Session, Depends(get_session)],
) -> UpdateSessionResponse:
    """Deletes a chat session based on the provided query parameters."""

    try:
        sessions = get_session_history(db)
        result = delete_session_history(db, sessions)
        await checkpoint_flush()

        return UpdateSessionResponse(ok=True, detail=f"flush {result} record")
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=str(e)) from e
