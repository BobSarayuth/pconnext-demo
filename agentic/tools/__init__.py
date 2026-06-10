import importlib
import inspect
import logging
import os
from collections.abc import Callable

from langchain_core.messages import ToolMessage
from uuid_extensions import uuid7str

logger = logging.getLogger("workflow.tool")

TOOLS: dict[str, Callable] = {}


logger.info("Tools importing...")
_dir_tools = os.path.dirname(__file__)
for file in os.listdir(_dir_tools):
    if not file.endswith(".py") or file == "__init__.py":
        continue

    # Dynamically import each Python file in the tools directory as a module
    tool_object = importlib.import_module(f"agentic.tools.{inspect.getmodulename(file)}")

    for name, obj in inspect.getmembers(tool_object):
        # For LangChain Tools, check for a specific attribute, e.g. `_run`
        if hasattr(obj, "_run"):
            TOOLS[name] = obj


def get_args(arg: dict) -> dict:
    return {"id": uuid7str(), "type": "tool_call", "args": arg}


def execute_tool(name: str, args: dict) -> tuple[ToolMessage, dict]:
    """Check selected tools and return them."""
    if name not in TOOLS:
        raise ValueError(f"Tools are not registered: {name}. Please check the tool names and try again.")
    tool_input = get_args(args)
    return TOOLS[name].invoke(input=tool_input), {  # type: ignore
        "name": name,
        "args": args,
        "id": tool_input.get("id"),
        "type": "tool_call",
    }


def check_tools(tool_names: list) -> list:
    """Check selected tools and return them."""
    chosen_tools = []
    missing_tools = []

    # Find unused tools
    unused_tools = set(TOOLS.keys()) - set(tool_names)
    logger.info(f"Unused tools: {', '.join(unused_tools)}")

    for t in tool_names:
        if t in TOOLS:
            chosen_tools.append(TOOLS[t])
        else:
            missing_tools.append(t)
    if missing_tools:
        raise ValueError(
            f"Tools are not registered: {', '.join(missing_tools)}. Please check the tool names and try again.",
        )
    return chosen_tools  # Just return the selected tools
