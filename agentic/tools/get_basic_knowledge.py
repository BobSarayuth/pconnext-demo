import html
import re
from typing import Annotated, List

from langchain_core.messages import ToolMessage
from langchain_core.tools import ToolException, tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.types import Command

from agentic.models.knowledge import AllowedBasicKnowledge
from agentic.tools.utils import ContentService, parse_knowledge_response, reply, tool_exception_react


MAX_KNOWLEDGE_CONTENT_CHARS = 1200


def fetch_basic_knowledge(name: str, limit: int = 3) -> tuple[list[dict], str | None]:
    api = ContentService()
    res = api.get_knowledge_by_name(name, limit)

    if res.status_code != 200:
        return [], f"API error {res.status_code}: {res.text}"

    return parse_knowledge_response(res.json())


def sanitize_knowledge_content(value: str) -> str:
    text = html.unescape(value)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)(?:\\\{[^}]+})?", r"\1", text)
    text = re.sub(r"<a\b[^>]*>(.*?)</a>", r"\1", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\{[^}]*\}", " ", text)
    text = re.sub(r"[*_`#]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def format_knowledge_result(name: str, rows: list[dict]) -> str:
    content = [f"Knowledge for {name}"]
    for row in rows:
        title = row.get("title") or name
        article = sanitize_knowledge_content(str(row.get("content") or ""))
        keywords = row.get("keywords")
        if len(article) > MAX_KNOWLEDGE_CONTENT_CHARS:
            article = article[:MAX_KNOWLEDGE_CONTENT_CHARS].rstrip() + "..."

        content.append(f"- Title: {title}")
        if keywords:
            content.append(f"- Keywords: {keywords}")
        content.append(f"- Content: {article}")
        content.append("")
    return "\n".join(content).strip()


@tool
def get_basic_knowledge(
    about: Annotated[List[AllowedBasicKnowledge], "List of basic knowledge "],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Use get_basic_knowledge when:
    - The user's message is unclear, vague, or shows hesitation.
    - The user is generally interested in a topic or product type but doesn’t mention a specific model or name.
    - You're not sure what exact product, service, or topic the user means.
    - You need to understand the topic better before using more specific tools.
    This tool helps you:
    - Provide general information about the topic or product type.
    - Offer suggestions and examples.
    - Help the user explore different product or service categories.
    - Give context for better understanding and more accurate recommendations.
    - Suggest other relevant options, even if the user hasn’t chosen a specific model or brand.
    """

    try:
        knowledge = []
        artifact = {"refer": [], "data": {}}
        for name in about:
            rows, err = fetch_basic_knowledge(str(name))
            if err:
                raise ToolException(err)

            artifact["refer"].append(str(name))
            artifact["data"][str(name)] = rows
            if not rows:
                knowledge.append(f"Knowledge for {name}")
                knowledge.append(f"No content service result found. Use skim_products for latest products in {name}.")
                knowledge.append("")
                continue

            knowledge.append(format_knowledge_result(str(name), rows))
            knowledge.append("")

    except Exception as e:
        return tool_exception_react(str(e), tool_call_id)

    return reply(
        [
            ToolMessage(
                content="\n".join(knowledge),
                artifact=artifact,
                tool_call_id=tool_call_id,
            ),
        ],
        instructions=[
            "**INSTRUCTIONS**",
            "- Describe the content briefly and provide options to choose or decide",
            "- Avoid using markdown formatting entirely",
            "- For more products, use `skim_products`.",
        ],
    )
