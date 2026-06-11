from typing import Optional

from langchain_core.messages import ToolMessage
from langchain_core.tools import ToolException, tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.types import Command
from typing_extensions import Annotated

from agentic.tools.utils import ContentService, tool_exception_react


def resolve_sku_id(product_sku_id: str, product_name: str | None) -> str:
    sku_id = str(product_sku_id or "").strip()
    if sku_id:
        return sku_id

    name = str(product_name or "").strip()
    if not name:
        raise ToolException("product_sku_id is required. Use the product_sku_id from skim_products metadata.")

    products, err = ContentService().search_sku_products_by_name(name, 1)
    if err:
        raise ToolException(err)
    if not products:
        raise ToolException(f"Not found a SKU candidate for '{name}'.")

    metadata = products[0].get("metadata") or {}
    sku_id = str(metadata.get("product_sku_id") or "").strip()
    if not sku_id:
        raise ToolException(f"SKU candidate for '{name}' does not include product_sku_id.")
    return sku_id


@tool
def search_specific_product(
    product_sku_id: Annotated[str, 'The product_sku_id from "skim_products" metadata.'],
    tool_call_id: Annotated[str, InjectedToolCallId],
    product_name: Annotated[
        Optional[str],
        'Optional fallback: the exact product name from "skim_products" if product_sku_id is unavailable.',
    ] = None,
) -> Command:
    """
    Fetch detailed SKU product data once you already have product_sku_id from skim_products.
    You must use tool "skim_products" first to determine the product_sku_id from metadata.
    Use this tool when the user wants to know more detailed information about a specific product, or
    when the user asks a product-specific FAQ such as usage, installation, warranty, specs, colors,
    included items, compatibility, or anything that should be included in the product detail.
    Call this tool at most once per user turn. If multiple products are possible, ask the customer to choose one first.

    """
    try:
        sku_id = resolve_sku_id(product_sku_id, product_name)
        data, err = ContentService().search_sku_products_by_id(sku_id)
        if err:
            raise ToolException(err)

        if not data:
            raise ToolException(f"Not found SKU profile for '{sku_id}'.")

        message = (
            "- Avoid using markdown formatting entirely, including symbols like * for bold or \\n for line breaks."
            "- Do not show URLs or links in the customer-facing answer.\n"
            "- If product_faq is present and relevant, answer from product_faq first, then use the rest of the product fields only as supporting information.\n"
            "- You do not have to answer every answer yourself, if it too complicated or no information please consider switch to agent.\n"
            f"Found SKU profile for '{sku_id}'.\nHere is the detailed product:\n\n"
        )
        for prod_info in data:
            message += f"{prod_info}\n\n"

        return Command(update={"messages": [ToolMessage(message, tool_call_id=tool_call_id)]})

    except Exception as e:
        return tool_exception_react(str(e), tool_call_id)
