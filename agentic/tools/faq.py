import re
from typing import Any

from langchain_core.tools import tool
from typing_extensions import Annotated, Tuple


FAQ_ENTRIES: list[dict[str, Any]] = [
    {
        "question": "SCG คืออะไร",
        "answer": (
            "SCG หรือ บริษัท ปูนซิเมนต์ไทย จำกัด (มหาชน) เป็นกลุ่มธุรกิจไทยที่มีหลายธุรกิจ "
            "โดยเว็บไซต์ SCG ระบุว่าธุรกิจของ SCG มุ่งส่งมอบนวัตกรรมกรีนเพื่อคุณภาพชีวิตที่ดีและโลกที่ยั่งยืน"
        ),
        "keywords": ["scg", "เอสซีจี", "ปูนซิเมนต์ไทย", "บริษัท", "คืออะไร"],
        "sources": ["https://www.scg.com/"],
    },
    {
        "question": "SCG มีธุรกิจอะไรบ้าง",
        "answer": (
            "เว็บไซต์ SCG แสดงกลุ่มธุรกิจหลัก เช่น ซีเมนต์แอนด์กรีนโซลูชันส์, สมาร์ทลีฟวิง, "
            "ดิสทริบิวชั่นแอนด์รีเทล, เคมิคอลส์, SCGP, คลีนเนอร์ยี่, เดคคอร์, SCGJWD "
            "และการลงทุนในธุรกิจอื่น"
        ),
        "keywords": ["ธุรกิจ", "business", "scg", "เอสซีจี", "มีอะไรบ้าง"],
        "sources": ["https://www.scg.com/"],
    },
    {
        "question": "SCG ให้ความสำคัญกับเรื่องความยั่งยืนอย่างไร",
        "answer": (
            "SCG สื่อสารแนวทาง Inclusive Green Growth โดยเดินหน้าด้วยนวัตกรรมกรีน "
            "และทำงานร่วมกับภาคส่วนใน supply chain เพื่อสังคมคาร์บอนต่ำ"
        ),
        "keywords": ["ยั่งยืน", "sustainability", "green", "inclusive green growth", "คาร์บอนต่ำ"],
        "sources": ["https://www.scg.com/"],
    },
    {
        "question": "สมัครเป็นคู่ค้าหรือคู่ธุรกิจกับ SCG ได้ที่ไหน",
        "answer": (
            "เว็บไซต์ SCG มีเมนูสำหรับสมัครเป็นคู่ค้า/คู่ธุรกิจกับ SCG ผ่านช่องทาง supplier ของ SCG"
        ),
        "keywords": ["คู่ค้า", "คู่ธุรกิจ", "supplier", "vendor", "สมัคร", "จัดซื้อ"],
        "sources": ["https://www.scg.com/", "https://supplier.scg.com/"],
    },
    {
        "question": "P Connext คืออะไร",
        "answer": (
            "ในโปรเจกต์นี้ P Connext คือระบบ demo สำหรับผู้ช่วยสนทนาที่ช่วยค้นหาข้อมูลสินค้า "
            "โดยเชื่อมกับการค้นหา SKU, profile สินค้า และ FAQ ที่เกี่ยวข้อง "
            "ไม่พบหน้าเว็บสาธารณะที่ยืนยันคำอธิบาย P Connext โดยตรง จึงควรถือข้อมูลนี้เป็นข้อมูลจากระบบใน repo"
        ),
        "keywords": ["p connext", "pconnext", "p-connext", "พีคอนเนค", "คืออะไร", "ระบบ"],
        "sources": ["repo:pconnext-demo"],
    },
    {
        "question": "P Connext ช่วยเรื่องสินค้าอย่างไร",
        "answer": (
            "P Connext ใช้ skim_products เพื่อค้นหา SKU candidate จากดัชนีสินค้า แล้วใช้ search_specific_product "
            "ดึงรายละเอียดสินค้าจาก Content Service SKU endpoint ด้วย product_sku_id ที่ได้จากผลค้นหา"
        ),
        "keywords": ["p connext", "สินค้า", "product", "sku", "รายละเอียด", "ค้นหา"],
        "sources": ["repo:pconnext-demo"],
    },
    {
        "question": "ควรถาม FAQ เมื่อไร",
        "answer": (
            "ใช้ FAQ สำหรับคำถามทั่วไปเกี่ยวกับ SCG, P Connext, วิธีใช้งานระบบ, คู่ค้า หรือภาพรวมธุรกิจ "
            "ถ้าลูกค้าถามหาสินค้าเฉพาะรุ่น สี หรือสเปก ให้ใช้เครื่องมือค้นหาสินค้าแทน "
            "ระบบรองรับเฉพาะการค้นหาข้อมูลสินค้า ยังไม่รองรับการตอบราคา ใบเสนอราคา หรือการสั่งซื้อ"
        ),
        "keywords": ["faq", "ถามอะไรได้", "วิธีใช้", "คำถามทั่วไป", "ช่วยอะไร"],
        "sources": ["repo:pconnext-demo"],
    },
]


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _tokens(value: str) -> set[str]:
    normalized = _normalize(value)
    parts = set(re.findall(r"[a-z0-9_-]+|[ก-๙]+", normalized))
    if "p connext" in normalized:
        parts.add("p connext")
    if "p-connext" in normalized or "pconnext" in normalized:
        parts.add("p connext")
    return parts


def _score(entry: dict[str, Any], query: str) -> int:
    query_text = _normalize(query)
    entry_text = _normalize(" ".join([entry["question"], " ".join(entry["keywords"])]))
    score = 0
    for token in _tokens(query):
        if token in entry_text:
            score += 2
    for keyword in entry["keywords"]:
        if _normalize(keyword) in query_text:
            score += 3
    if _normalize(entry["question"]) in query_text:
        score += 5
    return score


@tool(response_format="content_and_artifact")
def faq(
    query: Annotated[
        str,
        "The user's FAQ question about SCG, P Connext, suppliers, system usage, or general non-product information.",
    ],
) -> Tuple[str, dict]:
    """
    Use this for general FAQ questions about SCG, P Connext, supplier/business overview, or how the assistant works.
    Do not use this for specific product names, colors, sizes, manuals, or availability. Do not answer prices, quotations, or ordering because they are not supported.
    """
    ranked = sorted(
        ((entry, _score(entry, query)) for entry in FAQ_ENTRIES),
        key=lambda item: item[1],
        reverse=True,
    )
    matches = [entry for entry, score in ranked if score > 0][:3]
    if not matches:
        return (
            "ไม่พบ FAQ ที่ตรงกับคำถามนี้ หากเป็นคำถามเกี่ยวกับสินค้าให้ใช้เครื่องมือค้นหาสินค้า หากเป็นเรื่องซับซ้อนให้ส่งต่อเจ้าหน้าที่",
            {"query": query, "matches": []},
        )

    lines = ["FAQ result:"]
    for index, entry in enumerate(matches, start=1):
        lines.append(f"{index}. {entry['question']}")
        lines.append(entry["answer"])

    return "\n".join(lines), {"query": query, "matches": matches}
