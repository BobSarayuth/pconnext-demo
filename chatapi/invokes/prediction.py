import logging
import base64
import os
import re
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any

import httpx
from agentic import get_graph, is_setup
from agentic.components.provider import llm_provider
from fastapi.exceptions import HTTPException
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import StreamMode
from sqlalchemy.orm import Session
from uuid_extensions import uuid7str

from chatapi.invokes import create_config

# from chatapi.config.app import _config
from chatapi.models.chat import FormatType, PredictionAttachment, PredictionConfig, PredictionRequest
from chatapi.models.history import AgentUsedTools
from chatapi.models.messages import RespondedType
from chatapi.models.orm import ChatType
from chatapi.router.queries import get_checksum
from chatapi.workflow.attachment import AUDIO_TYPES, LOCAL_BLOB, FileAttachment, ImageMessage
from chatapi.workflow.chat_history import BaseChatHistory
from chatapi.workflow.transform import AIMessageChunkTransformer, deserialize_stream
from chatapi.workflow.utils import Timer

stream_mode: list[StreamMode] = ["messages", "updates"]

logger = logging.getLogger("fastapi.prediction")
DEFAULT_AUDIO_MODEL = os.getenv("AGENTIC_AUDIO_MODEL", os.getenv("AGENTIC_AGENT_MODEL", "openai:gpt-4o-mini"))
MAX_LOG_TEXT = 500
_audio_client = httpx.Client(
    verify=False,  # noqa: S501
    timeout=httpx.Timeout(60.0),
    limits=httpx.Limits(max_keepalive_connections=2, max_connections=5),
)


def _trim_log_value(value: str | None, max_len: int = MAX_LOG_TEXT) -> str:
    text = str(value or "")
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}...<truncated {len(text) - max_len} chars>"


def _normalize_attachment_type(value: str | None) -> str:
    return str(value or "").strip().lower()


def _normalize_attachment_refs(attachments: list[str | PredictionAttachment] | None) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    for attachment in attachments or []:
        if isinstance(attachment, str):
            refs.append(("", attachment))
            continue

        declared_type = _normalize_attachment_type(attachment.type)
        urls = attachment.url if isinstance(attachment.url, list) else [attachment.url]
        refs.extend((declared_type, url) for url in urls if url)
    return refs


def _is_declared_audio(declared_type: str) -> bool:
    return declared_type == "audio" or declared_type.startswith("audio/")


def _is_declared_image(declared_type: str) -> bool:
    return declared_type == "image" or declared_type.startswith("image/")


def _is_audio_content_type(content_type: str) -> bool:
    normalized = _normalize_attachment_type(content_type).split(";")[0]
    return normalized.startswith("audio/") or normalized in AUDIO_TYPES


def _audio_format(content_type: str, url: str) -> str:
    normalized = _normalize_attachment_type(content_type).split(";")[0]
    extension = url.split("?")[0].rsplit(".", 1)[-1].lower() if "." in url.split("?")[0] else ""
    if "wav" in normalized or extension == "wav":
        return "wav"
    if "mpeg" in normalized or "mp3" in normalized or extension == "mp3":
        return "mp3"
    return extension or "mp3"


def _audio_mime_type(content_type: str, url: str) -> str:
    normalized = _normalize_attachment_type(content_type).split(";")[0]
    if normalized.startswith("audio/"):
        return normalized
    audio_format = _audio_format(content_type, url)
    if audio_format == "mp3":
        return "audio/mpeg"
    if audio_format == "wav":
        return "audio/wav"
    if audio_format in ("m4a", "mp4"):
        return "audio/mp4"
    return f"audio/{audio_format}"


def _litellm_model_name(model_name: str) -> str:
    normalized = model_name
    prefixes = ("litellm/", "azure/")
    while normalized.startswith(prefixes):
        normalized = normalized.split("/", maxsplit=1)[1]
    return normalized


def _extract_chat_completion_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    if isinstance(content, list):
        return "".join(str(item.get("text", "")) for item in content if isinstance(item, dict)).strip()
    return str(content).strip()


def _audio_payload_candidates(model_name: str, audio_data: str, audio_format: str, mime_type: str) -> list[dict[str, Any]]:
    prompt = "Provide a transcription of this audio by ignoring the noise..."
    data_url = f"data:audio/mp3;base64,{audio_data}"
    model = _litellm_model_name(model_name)
    return [
        {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": data_url},
                    ],
                }
            ],
        }
    ]


def _transcribe_audio_via_litellm_proxy(file: FileAttachment, url: str, model_name: str) -> str:
    base_url = os.getenv("LITELLM_BASE_URL", "").rstrip("/")
    api_key = os.getenv("LITELLM_API_KEY", "")
    if not base_url or not api_key:
        raise RuntimeError("Missing LITELLM_BASE_URL or LITELLM_API_KEY for audio transcription")

    audio_data = base64.b64encode(file.blob).decode("utf-8")
    audio_format = _audio_format(file.content_type, url)
    mime_type = _audio_mime_type(file.content_type, url)
    endpoint = f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    last_error = ""

    for body in _audio_payload_candidates(model_name, audio_data, audio_format, mime_type):
        content_types = [
            item.get("type")
            for item in body["messages"][0]["content"]
            if isinstance(item, dict) and item.get("type") != "text"
        ]
        res = _audio_client.post(endpoint, headers=headers, json=body)
        logger.info(
            {
                "event": "audio_transcription_model_call",
                "model": body["model"],
                "status_code": res.status_code,
                "content_types": content_types,
            }
        )
        if 200 <= res.status_code < 300:
            transcript = _extract_chat_completion_text(res.json())
            if transcript:
                return transcript
            last_error = "empty transcription response"
            continue
        last_error = res.text[:1000]

    raise RuntimeError(f"Audio transcription failed via agent model: {last_error}")


def _transcribe_audio(file: FileAttachment, url: str) -> str:
    if DEFAULT_AUDIO_MODEL.startswith("litellm/"):
        return _transcribe_audio_via_litellm_proxy(file, url, DEFAULT_AUDIO_MODEL)

    audio_model = llm_provider(DEFAULT_AUDIO_MODEL, False, {"temperature": 0, "top_p": 0.7})
    audio_data = base64.b64encode(file.blob).decode("utf-8")
    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": (
                    "Transcribe this Thai or English audio exactly. "
                    "Return only the spoken text. Do not answer the user."
                ),
            },
            {
                "type": "input_audio",
                "input_audio": {
                    "data": audio_data,
                    "format": _audio_format(file.content_type, url),
                },
            },
        ]
    )
    response = audio_model.invoke([message])
    return str(response.content or "").strip()


def _identify_append(content_type: list, res_type: RespondedType) -> None:
    if res_type not in content_type:
        content_type.append(res_type)


def _process_emojis(payload: PredictionRequest, tools: list, content_type: list, state: dict) -> None:
    question = payload.question or ""
    emoji_image = re.findall(r"^:(https?://\S+?):", question)

    # Remove emoji_unique and emoji_image from question
    for em in emoji_image:
        question = re.sub(f":{em}:", "", question)

    payload.question = question.strip()

    if emoji_image:
        sticker = []
        for url in emoji_image:
            file = ImageMessage(url=url)
            tools.append(
                AgentUsedTools(
                    id=uuid7str(),
                    tool="sticker",
                    toolInput={"image_url": url},
                    toolOutput=file.get_thumbnail(),
                ).model_dump(),
            )
            sticker.append(file.to_dict())

        state["messages"].append(HumanMessage(content=sticker))

    emoji_unique = re.findall(r"^:(\w+?):", question)
    if emoji_image or emoji_unique:
        _identify_append(content_type, RespondedType.STICKER)
    else:
        _identify_append(content_type, RespondedType.TEXT)


def _process_attachments(
    db: Session | None,
    payload: PredictionRequest,
    tools: list,
    content_type: list,
    state: dict,
) -> None:
    attachment_refs = _normalize_attachment_refs(payload.attachments)
    if not attachment_refs:
        return

    image_attachments = []
    audio_transcripts = []
    for declared_type, endpoint in attachment_refs:
        if db and endpoint.startswith(LOCAL_BLOB):
            check_sum = endpoint.replace(LOCAL_BLOB, "")
            obj = get_checksum(db, session_id=str(payload.sessionId), file=check_sum)
            if not obj:
                raise HTTPException(status_code=400, detail=f"Invalid attachment: {check_sum!s}")

            file = FileAttachment(blob=bytes(obj.blob), content_type=str(obj.fileType))  # type: ignore
        else:
            file = FileAttachment(url=endpoint)

        logger.info(
            {
                "event": "attachment_loaded",
                "declared_type": declared_type,
                "content_type": file.content_type,
                "url": _trim_log_value(endpoint, 120),
            },
            extra={"session_id": payload.sessionId},
        )

        if file.content_type.startswith("image/") or _is_declared_image(declared_type):
            if declared_type and not _is_declared_image(declared_type):
                raise HTTPException(status_code=400, detail=f"Attachment type mismatch: {declared_type} is not image")
            _identify_append(content_type, RespondedType.IMAGE)
            img = file.to_image()
            tools.append(
                AgentUsedTools(
                    id=uuid7str(),
                    tool="image_thumbnails",
                    toolInput={"image_url": endpoint},
                    toolOutput=img.get_thumbnail(),
                ).model_dump(),
            )
            image_attachments.append(img.to_dict())
            logger.info(
                {
                    "event": "image_attachment_processed",
                    "content_type": file.content_type,
                    "url": _trim_log_value(endpoint, 120),
                },
                extra={"session_id": payload.sessionId},
            )
        elif _is_audio_content_type(file.content_type) or _is_declared_audio(declared_type):
            _identify_append(content_type, RespondedType.TEXT)
            transcript = _transcribe_audio(file, endpoint)
            if not transcript:
                raise HTTPException(status_code=400, detail="Unable to transcribe audio attachment")
            tools.append(
                AgentUsedTools(
                    id=uuid7str(),
                    tool="audio_transcription",
                    toolInput={"audio_url": endpoint},
                    toolOutput=transcript,
                ).model_dump(),
            )
            audio_transcripts.append(transcript)
            logger.info(
                {
                    "event": "audio_attachment_transcribed",
                    "content_type": file.content_type,
                    "url": _trim_log_value(endpoint, 120),
                    "transcript": _trim_log_value(transcript),
                },
                extra={"session_id": payload.sessionId},
            )
        else:
            raise HTTPException(status_code=400, detail=f"Invalid content_type: {file.content_type!s}")

    if audio_transcripts:
        audio_text = "\n".join(f"ข้อความจากเสียง: {text}" for text in audio_transcripts)
        payload.question = "\n".join(part for part in [payload.question or "", audio_text] if part).strip()
        state["messages"].append(HumanMessage(content=audio_text))

    if image_attachments:
        state["messages"].append(HumanMessage(content=image_attachments))


def _bind_attachment_and_tools(db: Session | None, payload: PredictionRequest) -> tuple[dict, list, list]:
    tools = []
    content_type = []

    state: dict = {"messages": [HumanMessage(payload.question)] if payload.question else []}

    if payload.question:
        _process_emojis(payload, tools, content_type, state)

    _process_attachments(db, payload, tools, content_type, state)

    return state, tools, content_type


def _send_init_chunk(payload: PredictionRequest, chat_id: str) -> tuple[str, str, dict]:
    return ("main", "init", {"sessionId": payload.sessionId, "chatId": chat_id})


def _send_summary_chunk(
    agent_message: list,
    tools: list,
    agent_reasoning: list,
    state: dict,
    elapsed: Timer,
) -> tuple[str, str, dict]:
    return (
        "main",
        "summary",
        {
            "message": "".join(agent_message).strip(),
            "tools": tools,
            "agentReasoning": agent_reasoning,
            "state": state,
            "elapsed": float(elapsed),
        },
    )


def _send_chunk_error(
    e: Exception,
    chunk_transform: AIMessageChunkTransformer,
    session_id: str,
) -> tuple[str, str, dict]:
    """Handle prediction errors by logging and creating error chunks."""
    logger.error(f"An error occurred {e.__dict__}", exc_info=True, extra={"session_id": session_id})
    err_chunk = {"name": "exception", "type": "error", "message": str(e)}
    chunk_transform.append("error", [err_chunk])
    return (("main"), "error", err_chunk)


def _handle_agent_message(message: dict, eol_chunk: bool, agent_message: list) -> bool:
    """Process a single AI message from agent updates."""
    if message.get("type") == "ai":
        if not message.get("content", ""):
            return True
        elif eol_chunk:
            agent_message.clear()
            eol_chunk = False

        agent_message.append(message.get("content"))
    return eol_chunk


def _process_agent_tools(messages: list, agent_message: list) -> None:
    """Process messages when tools are called."""
    agent_message.clear()
    for message in reversed(messages):
        if message.get("type") != "ai":
            break
        agent_message.insert(0, message.get("content"))


def _process_non_agent_updates(names: list, updates: dict, agent_message: list) -> None:
    """Process updates that don't come from the agent."""
    for name in names:
        update_entry = updates.get(name, {})
        update_list = update_entry if isinstance(update_entry, list) else [update_entry]
        for update_item in update_list:
            messages = update_item.get("messages", [])
            for message in reversed(messages):
                if message.get("type") == "ai" and (not message.get("usage_metadata") or not message.get("name", {})):
                    # Clear the agent message array to avoid duplicates
                    agent_message.clear()
                    agent_message.append(message.get("content"))
                    break


def _process_updates(chunk: dict, eol_chunk: bool, tool_calls: list, agent_message: list) -> bool:
    """Process updates from the stream and extract AI messages."""
    updates = deserialize_stream(chunk)
    names = updates.keys()
    if updates.get("agent"):
        messages = updates.get("agent", {}).get("messages", [])
        if len(messages) == 1:
            eol_chunk = _handle_agent_message(messages[-1], eol_chunk, agent_message)
        elif len(tool_calls):
            _process_agent_tools(messages, agent_message)
    else:
        _process_non_agent_updates(names, updates, agent_message)

    return eol_chunk


def _prepare_prediction_context(
    db: Session | None,
    payload: PredictionRequest,
) -> tuple[dict, list, list, dict, RunnableConfig]:
    """Initialize prediction context and prepare the initial state."""
    if isinstance(payload.config, PredictionConfig):
        payload.config = payload.config.__dict__

    state, tools, content_type = _bind_attachment_and_tools(db, payload)

    attachment_refs = _normalize_attachment_refs(payload.attachments)
    files_count = len(attachment_refs)
    if files_count > 0:
        logger.info(f"Attachments {files_count} download... ")

    reasoning = {
        "messages": [payload.question] if payload.question else [],
        "attachments": [{"type": attachment_type, "url": url} for attachment_type, url in attachment_refs],
        "usedTools": tools,
        "meta": {
            # "agentic": f"{_config.project_name}@{_config.project_version}",
            "userAgent": payload.config.get("userAgent")
            if payload.config and payload.config.get("userAgent")
            else "N/A",
        },
    }

    logger.info(
        {
            "event": "prediction_context_prepared",
            "question": payload.question,
            "attachments": files_count,
            "content_type": [str(item) for item in content_type],
            "streaming": payload.streaming,
            "reasoning": payload.reasoning,
        },
        extra={"session_id": payload.sessionId},
    )

    config = create_config(session_id=str(payload.sessionId), config=payload.config or {}, content_type=content_type)

    # Remove userAgent before using invoke
    if payload.config:
        payload.config.pop("userAgent")

    return state, tools, content_type, reasoning, config


async def _handle_stream_processing(
    astream: AsyncIterator[Any],
    chunk_transform: AIMessageChunkTransformer,
    agent_message: list,
    payload: PredictionRequest,
) -> AsyncGenerator[tuple[str, str, dict]]:
    """Process the entire stream of chunks."""
    n_chunk = 0
    eol_chunk = False
    tool_calls = []

    async for node, mode, chunk in astream:
        n_chunk += 1

        chunk_transform.append(mode, chunk)
        updates = deserialize_stream(chunk)

        if mode == "messages":
            if updates[0].get("tool_calls"):
                tool_calls.append(updates[0].get("id"))
            if payload.format != FormatType.RAW:
                yield (node, mode, chunk)

        elif mode == "updates":
            eol_chunk = True
            _process_updates(chunk, eol_chunk, tool_calls, agent_message)

        if payload.format == FormatType.RAW:
            yield (node, mode, chunk)


async def prediction_stream(
    db: Session | None,
    payload: PredictionRequest,
    chat_type: ChatType,
) -> AsyncGenerator[tuple[str, str, dict]]:
    """Stream predictions based on the request payload."""
    state, tools, content_type, reasoning, config = _prepare_prediction_context(db, payload)
    chat = BaseChatHistory(db)
    history_state = payload.config if isinstance(payload.config, dict) else payload.config.__dict__ if payload.config else {}
    chat_id = chat.extract_human_message(
        session_id=str(payload.sessionId),
        chat_type=chat_type,
        state=history_state,
        content=payload.question or "",
        reasoning=reasoning,
    )

    if payload.format != FormatType.RAW:
        yield _send_init_chunk(payload, chat_id)

    elapsed = Timer()
    chunk_transform = AIMessageChunkTransformer()
    agent_message = []

    try:
        graph = get_graph()
        if not is_setup() or not graph:
            raise ValueError("Graph is None. Failed to initialize graph.")

        astream = graph.astream(state, config=config, stream_mode=stream_mode, subgraphs=True)
        n_chunk = 0

        async for result in _handle_stream_processing(astream, chunk_transform, agent_message, payload):
            n_chunk += 1
            yield result

        elapsed.stop()
        logger.info(
            f"predicted {n_chunk} msgs ({float(elapsed)}s).",
            extra={"session_id": payload.sessionId},
        )

    except Exception as e:
        elapsed.stop()
        yield _send_chunk_error(e, chunk_transform, str(payload.sessionId or ""))

    state, agent_reasoning, tools = chunk_transform.extract_reasoning_tools()
    chat.extract_ai_message(
        chat_id=chat_id,
        session_id=str(payload.sessionId),
        chat_type=chat_type,
        content=" ".join(agent_message).strip(),
        state=state,
        reasoning=agent_reasoning,
        tools=tools,
    )
    chat.save()

    if payload.format != FormatType.RAW:
        yield _send_summary_chunk(agent_message, tools, agent_reasoning, state, elapsed)

    del chunk_transform, chat
