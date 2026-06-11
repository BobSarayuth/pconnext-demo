from langchain_core.tools import tool
from typing_extensions import Annotated, Optional, Tuple

from agentic.models.responsed import ActionType


@tool(response_format="content_and_artifact")
def switch_agent_fasttrack(
    fasttrack: Annotated[
        bool,
        "Set fasttrack to True only for supported urgent operator handoff cases. Do not set True for price, quotation, purchase, checkout, payment, or order-placement requests because this system does not support them.",
    ],
    negative: Annotated[
        Optional[bool],
        "Set negative to True if the user input contains profanity, negative word or inappropriate language.",
    ] = None,
    situation_summary: Annotated[
        Optional[str],
        "A brief summary of the user's supported help request, written in Thai. Do not use this tool only for price, quotation, purchase, checkout, payment, or order-placement requests.",
    ] = None,
) -> Tuple[str, dict]:
    """
    Tool that instantly connects users to an SCG Digital Online operator without confirmation. The system automatically activates `switch_agent_fasttrack` when:
     - The user searches for information, locations, or products at any branch.
     - The user explicitly requests to speak with an operator
     - The user inquires about technicians or service staff
     - The user asks about product delivery, complaint, expresses dissatisfaction, negative sentiment toward, or reports system issues such as slowness or errors.
     - The user input is in a language other than Thai or English.
     - The user input the exact same message twice in a row.
    Do not call this tool only because the user asks for price, quotation, purchase, checkout, payment, or order placement.
    """

    notified = 'Always inform the customer that you have already contacted an SCG Digital ONLINE operator to assist them. Politely ask them to wait a moment for the operator to join and help, Example as: \n"บ๊อบบี๊ ขออนุญาตส่งต่อพี่ๆ เจ้าหน้าที่เพื่อช่วยเหลือดูเเลคุณลูกค้าเพิ่มเติม กรุณารอสักครู่ครับ"'

    if negative:
        notified = 'Always politely apologize to the customer first. Then inform them that you have already contacted an SCG Digital ONLINE operator to assist them, and kindly ask them to wait a moment for the operator to join and help, Example as: \n"ขออภัยหากลูกค้าได้รับความไม่สะดวกในการสนทนา อย่างไรแล้ว บ๊อบบี๊ ขออนุญาตส่งต่อพี่ๆ เจ้าหน้าที่เพื่อให้บริการข้อมูลต่อนะครับ กรุณารอสักครู่ครับ"'

    elif fasttrack:
        notified = f'Always inform the customer that you have already contacted an SCG Digital ONLINE operator to assist them regarding the following situation: "{situation_summary}". Politely ask them to wait a moment for the operator to join and help.'

    return notified, {
        "situation": situation_summary,
        "mode": ActionType.FASTTRACK if fasttrack else ActionType.AGENT,
    }
