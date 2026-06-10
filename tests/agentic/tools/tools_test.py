import os
from unittest.mock import patch

from agentic.tools import TOOLS, get_args


@patch.dict(
    os.environ, {"CAP_CONTENT_SERVICE_URL": "http://localhost:3080", "CAP_CONTENT_SERVICE_KEY": "valid-api-key"}
)
class TestExecuteTools:
    def test_skim_products(self):
        containText = "Here are the product names that were found"
        toolOutput = TOOLS["skim_products"].invoke(input=get_args({"search_term": "โซล่า"}))  # type: ignore
        messages = toolOutput.update.get("messages", [])
        assert len(messages) > 0
        assert containText in toolOutput.update.get("messages")[0].content

        toolOutput = TOOLS["skim_products"].invoke(input=get_args({"search_term": "บริการทาสีหลังคา"}))  # type: ignore
        messages = toolOutput.update.get("messages", [])
        assert len(messages) > 0
        assert containText in toolOutput.update.get("messages")[0].content

    def test_get_basic_knowledge(self):
        toolOutput = TOOLS["get_basic_knowledge"].invoke(  # type: ignore
            input=get_args({"building_material": ["ชุดครัวสำเร็จรูป"]})
        )
        messages = toolOutput.update.get("messages", [])
        assert len(messages) > 0

    def test_search_specific_product(self):
        toolOutput = TOOLS["search_specific_product"].invoke(  # type: ignore
            input=get_args({"product_name": "กระเบื้องมุงหลังคา เอสซีจี รุ่น เพรสทีจ"})
        )
        messages = toolOutput.update.get("messages", [])
        assert len(messages) > 0
        # Update assertion to accept new message format
        assert (
            "Found" in toolOutput.update.get("messages")[0].content
            or "Search returned" in toolOutput.update.get("messages")[0].content

    def test_calculator(self):
        toolOutput = TOOLS["calculator"].invoke(input=get_args({"expression": "10 + 15"}))  # type: ignore
        assert toolOutput.content == "25"

        toolOutput = TOOLS["calculator"].invoke(input=get_args({"expression": "sqrt(16)"}))  # type: ignore
        assert toolOutput.content == "4.0"

    def test_switch_agent_fasttrack(self):
        toolOutput = TOOLS["switch_agent_fasttrack"].invoke(  # type: ignore
            input=get_args({"situation_summary": "ต้องการสั่งซื้อสินค้า", "fasttrack": True})
        )
        assert "SCG Digital ONLINE" in toolOutput.content
        assert toolOutput.tool_call_id is not None
        assert isinstance(toolOutput.artifact, dict)
        assert toolOutput.artifact.get("mode") == "FASTTRACK"
