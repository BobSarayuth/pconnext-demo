from typing import Annotated

from langchain_core.messages import ToolMessage
from langchain_core.tools import ToolException, tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.types import Command

from agentic.tools.utils import ContentService, normalize_product_name, parse_product_response, tool_exception_react


def fetch_product_by_name(search_term: str, limit: int) -> tuple[list[dict], str | None]:
    api = ContentService()
    res = api.get_product_by_name(search_term, limit)

    if res.status_code != 200:
        return [], f"API error {res.status_code}: {res.text}"

    return parse_product_response(res.json())


@tool
def search_specific_product(
    product_name: Annotated[str, 'The EXACT name of the product as returned by "skim_products".'],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    This function is used to 'search' for a specific product from the content service once you already have the exact product name.
    You must use tool "skim_products" first to determine the actual product name from the database (it must match exactly).
    Use this tool when the user wants to know more detailed information about a specific product, or
    when the user is asking about something that is supposed to be already included in the product.
    Call this tool at most once per user turn. If multiple products are possible, ask the customer to choose one first.

    """
    try:
        product_name = product_name.strip()
        data, err = fetch_product_by_name(product_name, 5)
        if err:
            raise ToolException(err)

        if not data:
            raise ToolException(f"Not found an exact match for '{product_name}'.")

        normalized_input = normalize_product_name(product_name)
        exact_matches = []
        all_products = []

        for prod in data:
            prod.pop("url", None)
            display_name = prod.get("displayNameTh") or prod.get("display_name_th", "")
            if normalize_product_name(display_name) == normalized_input:
                exact_matches.append(prod)

            all_products.append(prod)

        if len(exact_matches) == 1:
            match = exact_matches[0]
            message = (
                "- Avoid using markdown formatting entirely, including symbols like * for bold or \\n for line breaks."
                "- Do not show URLs or links in the customer-facing answer.\n"
                + f"Found an exact match for '{product_name}'.\nHere is the detailed product:\n\n{match}\n"
            )
            return Command(
                update={
                    "messages": [ToolMessage(message, tool_call_id=tool_call_id)],
                }
            )

        message = (
            "- Avoid using markdown formatting entirely, including symbols like * for bold or \\n for line breaks."
            "- Do not show URLs or links in the customer-facing answer.\n"
            "- You do not have to answer every answer yourself, if it too complicated or no information please consider switch to agent.\n"
            f"Search returned {len(all_products)} products for '{product_name}', "
            ".\n"
            "Here are the details for all returned products:\n\n"
        )
        for prod_info in all_products:
            message += f"{prod_info}\n\n"

        return Command(update={"messages": [ToolMessage(message, tool_call_id=tool_call_id)]})

    except Exception as e:
        return tool_exception_react(str(e), tool_call_id)
