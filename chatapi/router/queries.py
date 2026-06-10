import hashlib
import json
import logging

from fastapi.exceptions import HTTPException
from sqlalchemy import asc, cast, delete, desc, func, literal, literal_column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from chatapi.models.history import (
    ChatExportToolResponse,
    ChatExportTurnResponse,
    ChatFullSessionHistoryResponse,
    ChatHistoryResponse,
    ChatMessageResponse,
    ChatSessionHistoryResponse,
)
from chatapi.models.orm import ChatHistory, ChatRole, ChatType, FileStorage
from chatapi.router.middleware import OrderType
from chatapi.router.utils import get_exts

logger = logging.getLogger("fastapi.sql")

EXCLUDED_EXPORT_TOOLS = {"maintrusted"}
TOOL_OUTPUT_PROMPT_PREFIXES = (
    "### Guidelines",
    "- Never ",
    "- Default:",
    "- Do not ",
    "- If the user ",
    "- If category ",
    "- If data ",
    "- Accessories ",
    "- Same series ",
    "- Total displayed ",
    "- Always filter ",
    "- Output format:",
    "- Avoid using ",
    "- You do not have to answer ",
)


def _loads_json_list(value: str | None) -> list:
    if not value:
        return []
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _sanitize_tool_output(value: str | None) -> str | None:
    if value is None:
        return None

    lines = []
    for line in value.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append(line)
            continue
        if any(stripped.startswith(prefix) for prefix in TOOL_OUTPUT_PROMPT_PREFIXES):
            continue
        lines.append(line)

    return "\n".join(lines).strip()


def _context_message(role: str, content: str | None, name: str | None = None) -> dict[str, str]:
    message = {"role": role, "content": content or ""}
    if name:
        message["name"] = name
    return message


def _tool_context_messages(tools: list[ChatExportToolResponse]) -> list[dict[str, str]]:
    messages = []
    for tool in tools:
        messages.append(
            _context_message(
                "tool_input",
                json.dumps(tool.toolInput or {}, ensure_ascii=False),
                tool.tool,
            )
        )
        if tool.toolOutput:
            messages.append(_context_message("tool_output", tool.toolOutput, tool.tool))
    return messages


def query_chat_history(db: Session, query: dict) -> list[ChatHistoryResponse]:
    stmt = (
        db.query(ChatHistory)
        .where(ChatHistory.sessionId == query.get("session_id"))
        .order_by(
            asc(ChatHistory.createdDate)
            if query.get("order", "asc").upper() == "ASC"
            else desc(ChatHistory.createdDate),
        )
        .offset(query.get("skip", 0))
        .limit(query.get("limit", 100))
        .all()
    )

    return [ChatHistoryResponse.from_orm(record) for record in stmt]


def query_chat_message(db: Session, query: dict) -> list[ChatMessageResponse]:
    stmt = (
        db.query(ChatHistory.chatId, ChatHistory.role, ChatHistory.content)
        .where(ChatHistory.sessionId == query.get("session_id"))
        .order_by(asc(ChatHistory.createdDate))
        .all()
    )
    return [ChatMessageResponse.from_orm(row) for row in stmt]


def get_session_history(db: Session) -> list[str]:
    """Set the is_deleted flag to True for all chat messages in the given session."""
    stmt = db.query(ChatHistory.sessionId).where(ChatHistory.deleted.is_(False)).group_by(ChatHistory.sessionId).all()
    return [row.sessionId for row in stmt]


def delete_session_history(db: Session, session_id: str | list[str]) -> int:
    """Set the is_deleted flag to True for all chat messages in the given session."""
    updated_count = 0
    try:
        updated_count = (
            db.query(ChatHistory)
            .filter(ChatHistory.sessionId.in_(session_id if isinstance(session_id, list) else [session_id]))
            .update({"deleted": True}, synchronize_session=False)
        )
        delete_stmt = delete(FileStorage).where(
            FileStorage.sessionId.in_(session_id if isinstance(session_id, list) else [session_id]),
        )
        db.execute(delete_stmt)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Unable: {e!s}")
        raise HTTPException(status_code=500, detail=f"unable {e!s}") from e

    return updated_count  # Return number of updated records


def query_session_history(db: Session, query: dict) -> list[ChatSessionHistoryResponse]:
    """Fetch all chat records within the date range before applying filters."""
    query_filter = [ChatHistory.createdDate >= query["begin_date"], ChatHistory.createdDate < query["last_date"]]

    if query.get("content", None) is not None:
        query_filter.append(ChatHistory.content.ilike(f"%{query['content']}%"))

    if query.get("chat_type", None) is not None:
        query_filter.append(ChatHistory.chatType == query.get("chat_type"))

    if query.get("deleted", None) is not None:
        query_filter.append(ChatHistory.deleted == query.get("deleted"))

    session_message_cte = (
        db.query(
            ChatHistory.sessionId.label("sessionId"),
            func.first_value(ChatHistory.content)
            .over(partition_by=ChatHistory.sessionId, order_by=desc(ChatHistory.createdDate))
            .label("content"),
            func.first_value(ChatHistory.deleted)
            .over(partition_by=ChatHistory.sessionId, order_by=desc(ChatHistory.createdDate))
            .label("deleted"),
            func.first_value(ChatHistory.chatType)
            .over(partition_by=ChatHistory.sessionId, order_by=desc(ChatHistory.createdDate))
            .label("chatType"),
        )
        .filter(*query_filter)
        .distinct()
        .cte("session_message")
    )

    tools_expr = func.coalesce(
        literal('["') + func.string_agg(func.distinct(literal_column("elem ->> 'tool'")), '", "') + literal('"]'),
        literal("[]"),
    ).label("usedTools")

    counts_subq = (
        db.query(
            FileStorage.sessionId.label("sessionId"),
            func.count(FileStorage.checkSum).label("file_count"),
        ).group_by(FileStorage.sessionId)
    ).subquery("counts")

    elem_table = (
        func.jsonb_array_elements(func.coalesce(cast(ChatHistory.usedTools, JSONB), cast(text("'[]'"), JSONB)))
        .lateral()
        .alias("elem")
    )

    query_obj = (
        db.query(
            session_message_cte.c.sessionId,
            func.coalesce(counts_subq.c.file_count, 0).label("files"),
            func.max(session_message_cte.c.content).label("content"),
            tools_expr,
            session_message_cte.c.chatType,
            session_message_cte.c.deleted,
            func.min(ChatHistory.createdDate).label("beginDate"),
            func.max(ChatHistory.createdDate).label("lastDate"),
        )
        .join(ChatHistory, ChatHistory.sessionId == session_message_cte.c.sessionId)
        .outerjoin(counts_subq, ChatHistory.sessionId == counts_subq.c.sessionId)
        .outerjoin(elem_table, literal_column("true"))
        .group_by(
            session_message_cte.c.sessionId,
            session_message_cte.c.chatType,
            session_message_cte.c.deleted,
            counts_subq.c.file_count,
        )
        .order_by(
            asc(func.min(ChatHistory.createdDate))
            if query.get("order", OrderType.DESC) == OrderType.ASC
            else desc(func.min(ChatHistory.createdDate)),
        )
        .offset(query.get("skip", 0))
        .limit(query.get("limit", 100))
    )

    stmt = query_obj.all()

    return [ChatSessionHistoryResponse.from_orm(record) for record in stmt]


def query_full_session_history(db: Session, query: dict) -> list[ChatFullSessionHistoryResponse]:
    """Fetch sessions active in the date range, then return compact export turns for each session."""
    query_filter = [ChatHistory.createdDate >= query["begin_date"], ChatHistory.createdDate < query["last_date"]]

    if query.get("content", None) is not None:
        query_filter.append(ChatHistory.content.ilike(f"%{query['content']}%"))

    if query.get("chat_type", None) is not None:
        query_filter.append(ChatHistory.chatType == query.get("chat_type"))

    if query.get("deleted", None) is not None:
        query_filter.append(ChatHistory.deleted == query.get("deleted"))

    session_rows = (
        db.query(
            ChatHistory.sessionId.label("sessionId"),
            func.min(ChatHistory.createdDate).label("beginDate"),
            func.max(ChatHistory.createdDate).label("lastDate"),
        )
        .filter(*query_filter)
        .group_by(ChatHistory.sessionId)
        .order_by(
            asc(func.min(ChatHistory.createdDate))
            if query.get("order", OrderType.DESC) == OrderType.ASC
            else desc(func.min(ChatHistory.createdDate)),
        )
        .offset(query.get("skip", 0))
        .limit(query.get("limit", 100))
        .all()
    )

    session_ids = [row.sessionId for row in session_rows]
    if not session_ids:
        return []

    messages = (
        db.query(ChatHistory)
        .filter(ChatHistory.sessionId.in_(session_ids))
        .order_by(asc(ChatHistory.sessionId), asc(ChatHistory.createdDate))
        .all()
    )

    files_count = dict(
        db.query(FileStorage.sessionId, func.count(FileStorage.checkSum))
        .filter(FileStorage.sessionId.in_(session_ids))
        .group_by(FileStorage.sessionId)
        .all()
    )

    turns_by_session: dict[str, dict[str, ChatExportTurnResponse]] = {session_id: {} for session_id in session_ids}
    session_meta: dict[str, tuple[ChatType, bool]] = {}
    previous_context_by_session: dict[str, list[dict[str, str]]] = {session_id: [] for session_id in session_ids}
    current_user_context_by_turn: dict[str, dict[str, str]] = {}

    for message in messages:
        session_meta[message.sessionId] = (message.chatType, message.deleted)
        turns = turns_by_session.setdefault(message.sessionId, {})
        turn = turns.setdefault(message.chatId, ChatExportTurnResponse(chatId=message.chatId))
        previous_context = previous_context_by_session.setdefault(message.sessionId, [])

        if ChatRole(message.role) == ChatRole.HUMAN:
            turn.input = message.content
            user_context = _context_message("user", message.content)
            current_user_context_by_turn[message.chatId] = user_context
            turn.contextWindow = [*previous_context, user_context]
            continue

        turn.answer = message.content
        turn.tools = [
            ChatExportToolResponse(
                tool=item.get("tool", ""),
                toolInput=item.get("toolInput") or {},
                toolOutput=_sanitize_tool_output(item.get("toolOutput")),
            )
            for item in _loads_json_list(message.usedTools)
            if isinstance(item, dict) and str(item.get("tool", "")).lower() not in EXCLUDED_EXPORT_TOOLS
        ]
        user_context = current_user_context_by_turn.get(message.chatId)
        turn_context = [*previous_context]
        if user_context:
            turn_context.append(user_context)
        turn_context.extend(_tool_context_messages(turn.tools))
        turn.contextWindow = turn_context

        if user_context:
            previous_context.append(user_context)
        previous_context.append(_context_message("assistant", message.content))

    response: list[ChatFullSessionHistoryResponse] = []
    for row in session_rows:
        chat_type, deleted = session_meta.get(row.sessionId, (ChatType.INTERNAL, False))
        response.append(
            ChatFullSessionHistoryResponse(
                sessionId=row.sessionId,
                chatType=chat_type,
                deleted=deleted,
                beginDate=row.beginDate,
                lastDate=row.lastDate,
                files=files_count.get(row.sessionId, 0),
                turns=list(turns_by_session.get(row.sessionId, {}).values()),
            )
        )

    return response


def get_checksum(db: Session, session_id: str, file: bytearray | str) -> FileStorage | None:
    """Get file storage record by checksum."""
    check_sum = hashlib.sha256(file).hexdigest() if isinstance(file, bytearray) else file

    return db.query(FileStorage).filter(FileStorage.checkSum == check_sum, FileStorage.sessionId == session_id).first()


def delete_checksum(db: Session, query: dict) -> int:
    """Delete file storage record by checksum."""
    updated_count = 0
    try:
        updated_count = (
            db.query(FileStorage)
            .filter(FileStorage.checkSum == query.get("check_sum"), FileStorage.sessionId == query.get("session_id"))
            .delete()
        )
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Unable: {e!s}")
        raise HTTPException(status_code=500, detail=f"unable {e!s}") from e

    return updated_count


def create_file(db: Session, session_id: str, file: bytearray, file_type: str) -> FileStorage:
    """Create a new file storage record."""

    check_sum = hashlib.sha256(file).hexdigest()
    file_ext = get_exts(file_type)

    data = FileStorage(
        sessionId=session_id,
        checkSum=check_sum,
        fileName=f"{check_sum}{file_ext}",
        fileType=file_type,
        blob=bytes(file),
    )

    try:
        db.add(data)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Unable: {e!s}")
        raise HTTPException(status_code=500, detail=f"unable {e!s}") from e

    return data
