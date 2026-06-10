import json
import logging
from typing import Any

from fastapi.exceptions import HTTPException
from uuid_extensions import uuid7str

logger = logging.getLogger("transfrom")


def deserialize_stream(data: dict | list | str):  # noqa: ANN201
    """
    Serializes and deserializes the streaming message to ensure proper structure.
    """
    return json.loads(
        json.dumps(data, default=lambda o: o.__dict__ if hasattr(o, "__dict__") else str(o), ensure_ascii=False),
    )


def find_messages_type(messages: list[dict[str, Any]], message_type: str) -> dict[str, Any]:
    """Find all messages in state that match the specified type."""
    for msg in reversed(messages):
        if msg.get("type") == message_type and msg.get("content"):
            return msg
    return messages[-1]


class AIMessageChunkTransformer:
    """
    This module provides the StreamingMessageTransformer class for transforming
    streaming messages into a structured format suitable for storing history messages in DB
    """

    def __init__(self) -> None:
        # self.raw = []
        self.streaming_data = {}
        self.latest_agent_id = None
        # self.ai_content = ""
        self.tools_messages = {}

    def append(self, mode: str, streaming_chunk: list) -> None:
        """
        Processes each message from a streaming source.
        """
        data = deserialize_stream(streaming_chunk)
        if mode == "updates":
            self._handle_data_from_updates_mode(data)
        elif mode == "messages":
            self._handle_data_from_messages_mode(data)
        elif mode == "error":
            message = {
                "id": self.latest_agent_id,
                "invalid_tool_calls": [
                    {
                        "id": uuid7str(),
                        "name": data.get("name", "exception"),
                        "type": data.get("type", "error"),
                        "message": data.get("message"),
                    },
                ],
            }
            self._handle_message_chunk(message, {})

    def _handle_data_from_messages_mode(self, data: list) -> None:
        """Handles MessageChunk mode:messages."""
        message, metadata = data[0], data[1]
        if message.get("type") in ["AIMessageChunk", "ai", "human"]:
            self._handle_message_chunk(message, metadata)
        elif message.get("type") == "tool":
            self._handle_tool_message(message)
        elif message.get("type") not in ["system"]:
            raise Exception(f"'_handle_data_from_messages_mode' unknow type: {message.get('type')}")

    def _handle_message_chunk(self, message: dict, metadata: dict) -> None:
        """Handles AIMessageChunk type messages."""
        self.latest_agent_id = message.get("id")
        agent_name = metadata.get("langgraph_node")

        messages = message.get("content") or ""
        tool_calls = message.get("tool_calls")
        invalid_tool_calls = [tc for tc in message.get("invalid_tool_calls", []) if tc.get("id")]
        usage_metadata = message.get("usage_metadata") or metadata.get("usage_metadata") or {}

        structured = message.get("structured_output_format", False) or message.get("additional_kwargs", {}).get(
            "parsed",
            False,
        )

        model_name = (
            metadata.get("ls_model_name")
            or message.get("response_metadata", {}).get("model_name")
            or ("directive" if message.get("type") == "ai" else "")
        )
        meta_data = {
            "step": metadata.get("langgraph_step"),
            "modelName": model_name,
            "modelType": metadata.get("ls_model_type", message.get("type")),
            "temperature": metadata.get("ls_temperature", 0),
            "usage": {},
        }

        # state = self._extract_relevant_state(metadata)
        if self.latest_agent_id not in self.streaming_data:
            self._initialize_streaming_data(agent_name or "unknown", meta_data)

        self._update_streaming_data(messages, usage_metadata, tool_calls or [], invalid_tool_calls, structured)

    def _initialize_streaming_data(self, agent_name: str, meta_data: dict) -> None:
        """Initializes streaming data for a new AIMessageChunk."""
        self.streaming_data[self.latest_agent_id] = {
            "nodeId": self.latest_agent_id,
            "agentName": agent_name,
            "messages": "",
            "state": {},
            "meta": meta_data,
        }

    def _extract_relevant_state(self, meta_data: dict) -> dict:
        excluded_keys = {
            "thread_id",
            "langgraph_step",
            "langgraph_node",
            "langgraph_triggers",
            "langgraph_path",
            "langgraph_checkpoint_ns",
            "checkpoint_ns",
            "ls_provider",
            "ls_model_name",
            "ls_model_type",
            "ls_temperature",
            "structured_output_format",
        }
        return {k: meta_data[k] for k in meta_data.keys() - excluded_keys}

    def _update_streaming_data(
        self,
        messages: str,
        usage_metadata: dict,
        tool_calls: list,
        invalid_tool_calls: list,
        structured: bool,
    ) -> None:
        """Updates existing streaming data with new messages and tool calls."""

        self.streaming_data[self.latest_agent_id]["messages"] += f"{messages}"

        if structured:
            self.streaming_data[self.latest_agent_id]["structured"] = structured

        if usage_metadata:
            self.streaming_data[self.latest_agent_id]["meta"]["usage"] = usage_metadata

        if tool_calls:
            self.streaming_data[self.latest_agent_id].setdefault("tool_calls", []).extend(tool_calls)
        if invalid_tool_calls:
            self.streaming_data[self.latest_agent_id].setdefault("invalid_calls", []).extend(invalid_tool_calls)

    def _handle_tool_message(self, message: dict) -> None:
        """Handles tool type messages."""

        tool_id = message.get("tool_call_id")

        if not tool_id:
            raise HTTPException(status_code=500, detail="Tool call ID is missing from tool message")

        # latest_agent_id = self._find_latest_agent_id(tool_id)
        # if not latest_agent_id:
        #     raise HTTPException(status_code=500, detail=f"Tool ID not found in streaming data: {tool_id}")
        # self.latest_agent_id = latest_agent_id
        list_of_tools = self.streaming_data[self.latest_agent_id].get("tool_calls", [])
        for tool in list_of_tools:
            if tool["id"] == tool_id:
                tool["tool_messages"] = message.get("content")
                tool["tool_artifact"] = message.get("artifacts", {}).get("artifacts") or {}
                break

        if self.latest_agent_id is None:
            raise HTTPException(status_code=500, detail="No AIMessageChunk ID found before tool message.")
        if "tool_calls" in self.streaming_data[self.latest_agent_id]:
            self._update_tool_calls(message)
        else:
            logger.warning(f"'tool_calls' missing for the latest agent ID: {self.latest_agent_id}")

    # def _find_latest_agent_id(self, tool_id: str) -> str | None:
    #     """Updates tool calls with the corresponding tool messages."""
    #     for k, v in self.streaming_data.items():
    #         if "tool_calls" in v:
    #             for tool in v["tool_calls"]:
    #                 if tool["id"] == tool_id:
    #                     return k
    #     return None

    def _update_tool_calls(self, message: dict) -> None:
        """Updates tool calls with the corresponding tool messages."""
        list_of_tools = self.streaming_data[self.latest_agent_id]["tool_calls"]
        for tool in list_of_tools:
            tool_id = tool.get("id")
            if tool_id and tool_id == message.get("tool_call_id"):
                tool["tool_messages"] = message.get("content")
                tool["tool_artifact"] = message.get("artifact")
                return
        raise HTTPException(
            status_code=500,
            detail=f"tool ID does not match any tool in the latest agent ID: {self.latest_agent_id}",
        )

    def _construct_agent_reasoning_used_tools(self, messages: dict) -> tuple[dict, list[dict], list[dict]]:
        """
        Constructs lists of agent reasoning and tools used from provided messages.
        This method parses through each message to extract reasoning and tools
        used by the agent. The extracted information is collected into two lists:
        one for reasoning and one for tools.
        """
        agent_reasoning = []
        all_used_tools = []  # To collect tools for all used tools
        update_state = {}

        for msg in messages.values():
            # Construct agent_reasoning fields
            meta = msg.get("meta", {})
            update_state = msg.get("state", {})
            # structured = None
            # if meta["structured"]:
            #     # structured = json.loads(msg.get("messages"))
            # meta.pop("structured", None)
            agent = {
                "agentName": msg.get("agentName"),
                "messages": [msg.get("messages")] if msg.get("messages") else [],
                "structured": msg.get("structured"),
                "usedTools": [],
                "invalids": [],
                "sourceDocuments": [],
                "state": msg.get("state") or {},
                "nodeId": msg.get("nodeId"),
                "meta": meta,
            }

            if msg.get("invalid_calls"):
                agent["invalids"] = msg["invalid_calls"]

            if msg.get("tool_calls"):
                list_of_tools = msg["tool_calls"]
                tools = self._construct_used_tools_field([tc for tc in list_of_tools if tc.get("id")])

                all_used_tools.extend(tools)
                agent["usedTools"] = tools

            agent_reasoning.append(agent)

        return update_state, agent_reasoning, all_used_tools

    def _construct_used_tools_field(self, list_of_tools: list) -> list[dict[str, Any]]:
        """
        Constructs a consolidated list of tools used from the provided list.

        This method iterates through the provided list of tools to gather and aggregate
        unique instances of tool usage. The result is a collection of tools without duplication,
        suitable for displaying or logging the tools utilized by an agent.
        """
        tools = []  # To collect tools for each specific agent id
        for tool in list_of_tools:
            tool_id = tool.get("id")
            if tool_id and not tool.get("tool_messages"):
                tool["tool_messages"] = self.tools_messages.get(tool_id)

            structure = {
                # Construct used_tools fields
                "id": tool_id,
                "tool": tool.get("name"),
                "toolInput": tool.get("args", {}),
                "toolOutput": tool.get("tool_messages"),
                "artifact": tool.get("tool_artifact"),
            }
            tools.append(structure)

        return tools

    def _handle_data_from_updates_mode(self, data: dict) -> None:
        """Handles MessageChunk mode:updates."""
        name = self._get_name(data)

        message = data.get(name, {})
        # self._handle_last_content(message)
        # self._handle_all_contents_of_tool(message)
        messages = message if isinstance(message, list) else [message]
        for msg in messages:
            self._handle_last_content(msg)
            self._handle_all_contents_of_tool(msg)

    # response_metadata
    def _get_name(self, message: dict) -> str:
        name = "agent"
        if len(message.keys()) > 0:
            name = next(iter(message.keys()))
        return name

    def _handle_finish_reason(self, last_message: dict) -> None:
        """Retrieves the last message of agent response"""

        metadata = last_message.get("response_metadata", {})
        if metadata.get("finish_reason") and metadata.get("finish_reason").lower() != "stop":
            self.streaming_data[self.latest_agent_id].setdefault("invalid_calls", []).extend(
                [
                    {
                        "id": uuid7str(),
                        "name": metadata.get("model_name"),
                        "type": metadata.get("finish_reason"),
                        "message": metadata.get("finish_message"),
                    },
                ],
            )

    def _handle_last_content(self, updates: dict) -> None:
        """Retrieves the last message of agent response"""

        messages = updates.get("messages", [])
        state = updates.copy()
        state.pop("messages", None)
        if messages:
            last_message = find_messages_type(messages, "ai")
            self._handle_finish_reason(last_message)
            # self.ai_content = last_message.get("content", "")
            if state and self.latest_agent_id:
                self.streaming_data[self.latest_agent_id]["state"] = {
                    **self.streaming_data[self.latest_agent_id].get("state", {}),
                    **state,
                }

    def _handle_all_contents_of_tool(self, message: dict) -> None:
        """Retrieves the contents of all tools responses"""

        list_of_messages = message.get("messages", []) or []
        for tools_message in list_of_messages:
            if tools_message.get("type") == "tool":
                tool_id = tools_message.get("tool_call_id")
                tool_content = tools_message.get("content")
                if tool_id:
                    self.tools_messages[tool_id] = tool_content

    def extract_reasoning_tools(self) -> tuple[dict, list[dict], list[dict]]:
        """Retrieves and returns the content, agent reasoning, and used tools from message chunks"""
        state, agent_reasoning, used_tools = self._construct_agent_reasoning_used_tools(self.streaming_data)
        # content = self.ai_content

        # return content, state, agent_reasoning, used_tools
        return state, agent_reasoning, used_tools
