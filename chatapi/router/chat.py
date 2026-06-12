import csv
import json
import logging
from collections.abc import AsyncGenerator
from io import StringIO
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from chatapi.invokes.checkpoint import checkpoint_delete
from chatapi.invokes.prediction import prediction_stream
from chatapi.models.chat import (
    ChunkPredictionResponse,
    FormatType,
    PredictionConfig,
    PredictionRequest,
    PredictionResponse,
    UpdateSessionResponse,
)
from chatapi.models.history import AgentReasoning, ChatHistoryResponse, ChatMessageResponse
from chatapi.models.orm import ChatType
from chatapi.router.middleware import api_key_authentication, param_get_messages, param_history
from chatapi.router.queries import delete_session_history, query_chat_history, query_chat_message
from chatapi.router.utils import get_session
from chatapi.workflow.transform import deserialize_stream

router = APIRouter(prefix="/api/chat", dependencies=[Depends(api_key_authentication)])
logger = logging.getLogger("fastapi.chat")
MAX_LOG_TEXT = 500


class ListReason(BaseModel):
    reason: list[AgentReasoning]


def _get_authenticated_username(req: Request) -> str:
    claims = getattr(req.state, "auth_claims", None)
    if not isinstance(claims, dict):
        return ""

    return (
        claims.get("preferred_username")
        or claims.get("upn")
        or claims.get("email")
        or claims.get("name")
        or claims.get("oid")
        or claims.get("sub")
        or ""
    )


def _normalize_payload_config(payload: PredictionRequest) -> None:
    if isinstance(payload.config, PredictionConfig):
        payload.config = payload.config.__dict__
    if payload.config is None:
        payload.config = {}

    if payload.username:
        payload.config.setdefault("username", payload.username)
    if payload.userAgent:
        payload.config.setdefault("userAgent", payload.userAgent)


def _trim_log_value(value: str | None, max_len: int = MAX_LOG_TEXT) -> str:
    text = str(value or "")
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}...<truncated {len(text) - max_len} chars>"


def _attachment_log_summary(payload: PredictionRequest) -> list[dict]:
    summary = []
    for attachment in payload.attachments or []:
        if isinstance(attachment, str):
            summary.append({"type": "", "url_count": 1, "urls": [_trim_log_value(attachment, 120)]})
            continue

        urls = attachment.url if isinstance(attachment.url, list) else [attachment.url]
        summary.append(
            {
                "type": attachment.type or "",
                "url_count": len(urls),
                "urls": [_trim_log_value(url, 120) for url in urls[:3]],
            }
        )
    return summary


def _log_prediction_received(payload: PredictionRequest) -> None:
    config = payload.config if isinstance(payload.config, dict) else {}
    logger.info(
        {
            "event": "prediction_request_received",
            "sessionId": payload.sessionId,
            "username": config.get("username") or payload.username or "",
            "userAgent": config.get("userAgent") or payload.userAgent or "",
            "streaming": payload.streaming,
            "question": _trim_log_value(payload.question),
            "attachments": _attachment_log_summary(payload),
        },
        extra={"session_id": payload.sessionId},
    )


async def event_stream(db: Session, req: Request, payload: PredictionRequest) -> AsyncGenerator[str, None]:
    try:
        async for node, mode, chunk_tool in prediction_stream(db, payload, ChatType.INTERNAL):
            if await req.is_disconnected():
                break

            if payload.format == FormatType.RAW:
                yield json.dumps(
                    {"node": node, "mode": mode, "chunk": chunk_tool},
                    default=lambda o: o.__dict__ if hasattr(o, "__dict__") else str(o),
                    ensure_ascii=False,
                )
                continue

            if (mode != "messages") and isinstance(chunk_tool, dict):
                if mode == "summary":
                    chunk_tool.pop("agentReasoning", None)

                yield ChunkPredictionResponse(mode=mode, chunk=chunk_tool).model_dump_json()
                continue

            data = deserialize_stream(chunk_tool)
            message, metadata = data[0], data[1]

            if message["type"] in ["system"]:
                continue

            chunk_tool = {
                "id": message["id"],
                "name": message["name"],
                "type": message["type"],
                "content": message["content"],
            }
            if isinstance(message, dict) and message.get("type") == "tool":
                chunk_tool["tool_call_id"] = message.get("tool_call_id", None)
                chunk_tool["artifact"] = message.get("artifact", None)

            yield ChunkPredictionResponse(
                mode=mode,
                chunk=chunk_tool
                if message["type"] == "tool"
                else {
                    "id": message["id"],
                    "content": message["content"],
                    "tool_calls": [tc for tc in message.get("tool_calls", []) if tc.get("id")],
                    "invalid_tool_calls": [tc for tc in message.get("invalid_tool_calls", []) if tc.get("id")],
                    "langgraph_step": metadata["langgraph_step"],
                    "langgraph_node": metadata["langgraph_node"],
                    "ls_model_name": metadata.get("ls_model_name")
                    or message.get("response_metadata", {}).get("model_name")
                    or ("directive" if message.get("type") == "ai" else ""),
                    "ls_model_type": metadata.get("ls_model_type", message["type"]),
                },
            ).model_dump_json()

        logger.info(
            {"event": "prediction_stream_success", "sessionId": payload.sessionId},
            extra={"session_id": payload.sessionId},
        )

    except Exception as e:
        logger.error(e, extra={"session_id": payload.sessionId})
        yield ChunkPredictionResponse(mode="error", chunk={"message": str(e)}).model_dump_json()


async def event_no_stream(db: Session, payload: PredictionRequest) -> PredictionResponse:
    result = PredictionResponse(
        question=payload.question,
        sessionId=str(payload.sessionId),
        artifact=None,
        text="",
        chatId="",
        elapsed=0,
        agentReasoning=[],
    )

    async for _, mode, chunk in prediction_stream(db, payload, ChatType.EXTERNAL):
        if not isinstance(chunk, dict):
            continue

        if mode == "error":
            raise Exception(f"[{chunk.get('name')}] {chunk.get('message')}")
        elif mode == "init":
            result.chatId = chunk.get("chatId", "")
        elif mode == "summary":
            result.elapsed = float(chunk.get("elapsed", 0))
            result.text = chunk.get("message", "N/A")
            agent_reasoning = chunk.get("agentReasoning", [])
            state = chunk.get("state", {})

            if isinstance(state, dict) and state.get("artifact"):
                result.artifact = state.get("artifact")

            result.agentReasoning = (
                ([AgentReasoning(**reason) for reason in agent_reasoning]) if payload.reasoning else []  # type: ignore
            )
    logger.info(
        {
            "event": "prediction_success",
            "sessionId": payload.sessionId,
            "chatId": result.chatId,
            "elapsed": result.elapsed,
            "text": _trim_log_value(result.text),
        },
        extra={"session_id": payload.sessionId},
    )
    return result


@router.post("/prediction", response_model=PredictionResponse | str, tags=["Chat"])
async def prediction(
    req: Request,
    payload: PredictionRequest,
    db: Annotated[Session, Depends(get_session)],
) -> PredictionResponse | EventSourceResponse:
    """Processes prediction request and generates reasoning."""
    try:
        _normalize_payload_config(payload)

        if payload.config and not payload.config.get("userAgent") and not req.headers.get("user-agent"):
            raise HTTPException(status_code=400, detail="Field required header.userAgent")

        if not payload.question and not payload.attachments:
            raise HTTPException(status_code=400, detail="Field required body.question or body.attachments is empty")

        payload.sessionId = payload.generate_session() if payload.sessionId == "" else payload.sessionId
        username = _get_authenticated_username(req)
        if username:
            if payload.config is None:
                payload.config = {}
            payload.config.setdefault("username", username)

        if payload.config:
            user_agent = payload.config.get("userAgent", req.headers.get("user-agent", ""))
            payload.config.setdefault("userAgent", user_agent)

        _log_prediction_received(payload)

        if payload.streaming:
            return EventSourceResponse(event_stream(db, req, payload), sep="\n")
        else:
            return await event_no_stream(db, payload)

    except Exception as e:
        logger.error(
            {
                "event": "prediction_failed",
                "sessionId": payload.sessionId,
                "error": str(e),
            },
            extra={"session_id": payload.sessionId},
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{session_id}", response_model=list[ChatMessageResponse] | str, tags=["Chat"])
async def get_chat_message(
    query: Annotated[dict, Depends(param_get_messages)],
    db: Annotated[Session, Depends(get_session)],
) -> list[ChatMessageResponse] | StreamingResponse:
    """Retrieve all chat history records where sessionId matches the provided session_id."""
    try:
        results = query_chat_message(db, query=query)
        if query.get("format", "json").lower() == "json":
            return results

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["id", "role", "content"], quoting=1)
        writer.writeheader()
        writer.writerows([{"id": item.chatId, "role": item.role, "content": item.content} for item in results])

        return StreamingResponse(
            content=output.getvalue(),
            headers={
                "Content-Disposition": "attachment; filename={file_name}.csv".format(file_name=query.get("session_id")),
            },
            media_type="text/csv",
        )

    except Exception as e:
        logger.error(e, extra={"session_id": query.get("session_id")})
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{session_id}", response_model=UpdateSessionResponse, tags=["Chat"])
async def session_delete(
    query: Annotated[dict, Depends(param_get_messages)],
    db: Annotated[Session, Depends(get_session)],
) -> UpdateSessionResponse:
    """Deletes a chat session based on the provided query parameters."""

    try:
        detail = await checkpoint_delete(query.get("session_id", ""))
        delete_session_history(db, query.get("session_id", ""))
        return UpdateSessionResponse(ok=True, detail=detail)
    except Exception as e:
        logger.error(e, extra={"session_id": query.get("session_id")})
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{session_id}/history", response_model=list[ChatHistoryResponse], tags=["Chat"])
async def get_chat_reasoning(
    query: Annotated[dict, Depends(param_history)],
    db: Annotated[Session, Depends(get_session)],
) -> list[ChatHistoryResponse]:
    """Retrieve all chat history records where sessionId matches the provided session_id."""
    try:
        return query_chat_history(db, query=query)
    except Exception as e:
        logger.error(e, extra={"session_id": query.get("session_id")})
        raise HTTPException(status_code=500, detail=str(e)) from e
