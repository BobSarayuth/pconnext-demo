from langchain_core.messages import ToolMessage
from langchain_core.tools import ToolException, tool
from langgraph.types import Command
from typing_extensions import Annotated, Tuple

from agentic.tools.utils import ContentService, normalize_product_name, parse_product_response, tool_exception_tuple


def fetch_product_message(product_name: str, limit: int):
    api = ContentService()
    res = api.get_product_by_name(product_name, limit)

    if res.status_code != 200:
        return [], f"API error {res.status_code}: {res.text}"

    return parse_product_response(res.json())


def response_skim(msg: list, tool_call_id: str):
    return Command(update={"messages": [ToolMessage("\n".join(msg), tool_call_id=tool_call_id)]})


@tool(response_format="content_and_artifact")
def skim_products(
    search_term: Annotated[
        str,
        "Retrieve only the item name entered by the user — no interpretation or changes, including size, unit, or number.",
    ],
) -> Tuple[str, dict]:
    """
    Use skim_products immediately when the customer provides a product name, model, type, or color. It improves search accuracy by matching properties, attributes, characteristics, and synonyms, and should also be used to check product information. If the customer asks for more details, search with skim_products first before anything else.
    It then picks the response format:
    - Exact match (one result): return full product details.
    - Multiple or no exact matches: return a concise, skimmed list of candidate product names.
    It always uses the raw search term—no further user qualification is required.
    """
    try:
        synonyms = {
            "เครื่องแรงดันบวก": "เครื่องเติมอากาศดี SCG Active AIR Quality",
            "เครื่องเติมอากาศ": "เครื่องเติมอากาศดี SCG Active AIR Quality",
            "เครื่องเติมอากาศดี": "เครื่องเติมอากาศดี SCG Active AIR Quality",
            "ไม้พื้น t-clip": "พื้นตกแต่ง เอสซีจี รุ่น ที-คลิปชิลด์",
            "ไม้พื้นt-clip": "พื้นตกแต่ง เอสซีจี รุ่น ที-คลิปชิลด์",
            "ไม้พื้นtclip": "พื้นตกแต่ง เอสซีจี รุ่น ที-คลิปชิลด์",
        }
        synonyms_msg = ""
        if search_term in synonyms.keys():
            search_term_old = search_term
            search_term = synonyms[search_term_old]
            synonyms_msg += f"Found synonym for {search_term_old} as {search_term}"

        products, err = fetch_product_message(search_term, 40)
        if err:
            raise ToolException(err)

        if not products:
            raise ToolException(f"No products found for '{search_term}'.")

        # Prepare data structures
        previous_search_meta_data = {}
        skimmed = []

        normalized_search_term = normalize_product_name(search_term)

        for row in products:
            # Check for both possible fields
            product_name = row.get("displayNameTh") or row.get("display_name_th")
            row.pop("url", None)
            metadata = row.get("metadata", {})
            metadata.pop("score")
            # Normalize the product name
            normalized_name = normalize_product_name(product_name)

            # Store in meta-data
            previous_search_meta_data[normalized_name] = metadata

            # Keep track of skimmed list
            skimmed.append({"product_name": product_name, "metadata": metadata})

            # Check if this is an exact normalized match
            if normalized_name == normalized_search_term:
                matched_name = row.get("displayNameTh") or row.get("display_name_th") or "Unknown Product"
                # Instead of only metadata, we now want to return all product details.
                meta = row.pop("metadata")
                results = [
                    f"Found an exact match for '{search_term}' and summarize product details in a single line, clearly and concisely, with a maximum of 1800 characters (including spaces).",
                    f"- Product Name: '{matched_name}'",
                    f"- Full Product Details: {row} meta data: {str(meta).replace('\n', '')}",
                    "- Do not show URLs or links in the customer-facing answer.",
                ]

                return "\n".join(results), {"data": products}

        # Otherwise, no “single exact match” found, so list all skimmed products.
        results = [
            "### Guidelines",
            "- Never show barcode, matNo, or any metadata to customers.",
            "- Default: display only the single most relevant product from this result.",
            "- Do not call `skim_products` again with the same or similar keyword in this turn.",
            "- Do not call `search_specific_product` for multiple products in the same turn.",
            "- If the user asks for recommendations, show 2-3 likely matches from this result and ask the customer to choose one before searching details.",
            "- Accessories are not the product. Exclude or separate from main results.",
            "- Same series with different colors = one group. Summarize the group and show up to 3 color options.",
            "- Total displayed items must not exceed 8.",
            "- If the user asks about color and the first skim is incomplete, ask whether they want to search further instead of calling another tool now.",
            "- If category is unclear, ask the customer to choose a category instead of calling another tool now.",
            "- Always filter out irrelevant products.",
            "- If data is insufficient or the case is complex, call `switch_agent_fasttrack` immediately.",
            "- Output format: one line per item, clear and concise. Do not show URLs or links. Keep total output ≤ 1,800 characters including spaces.",
        ]

        results.append(synonyms_msg)
        results.extend(
            [
                f"- '{product['product_name']}', meta data: {str(product['metadata']).replace('\n', '')}"
                for product in skimmed[:8]
            ]
        )

        return "\n".join(results), {"data": products}

    except Exception as e:
        return tool_exception_tuple(str(e))
