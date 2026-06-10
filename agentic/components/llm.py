import logging
from pathlib import Path

from langchain.chat_models.base import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.runnables import RunnableSerializable
from pydantic import BaseModel

from agentic.components.provider import llm_provider
from chatapi.services.prompts import read_prompt_from_db

logger = logging.getLogger("agentic.llm")

PROMPT_ROOT = Path("./agentic/prompts")


class LLMNode:
    def __init__(self, fully_name: str = "", template_name: str = "", inputs: list[str] | None = None) -> None:
        if inputs is None:
            inputs = []
        self.fully_name = fully_name
        self.inputs = inputs
        self.template_name = template_name
        self.template = template_name if not template_name else ""

    def _read_prompt(self, path: Path, fallback: bool = False) -> str | None:
        try:
            if path.is_file():
                return path.read_text(encoding="utf-8")
        except Exception as ex:
            logger.warning(f"Unable to read prompt file {path}: {ex}")
            return None

        if not fallback:
            logger.warning(f"Configured prompt file not found: {path}")
        return None

    def create_node(self, output: type[BaseModel], meta: dict) -> object:
        streaming = meta.get("streaming", False)
        model_name = self.get_model_name()
        parser = PydanticOutputParser(pydantic_object=output)

        # Define Prompt Template
        return self.get_prompt_template() | llm_provider(model_name, streaming, meta) | parser

    def get_model_name(self, model_name: str | None = None) -> str:
        return model_name if model_name else self.fully_name

    def get_model(self, fully_name: str | None = None, meta: dict | None = None) -> BaseChatModel:
        if meta is None:
            meta = {}
        return llm_provider(self.get_model_name(fully_name), meta.get("streaming", False), meta)

    def get_prompt(self, config: dict | None = None) -> str:
        if not self.template_name:
            if not self.template:
                raise ValueError("Template is empty or not found")
            return self.template

        prompt = read_prompt_from_db(self.template_name)
        if prompt:
            logger.info("Prompt loaded from database: %s", self.template_name)
            return prompt

        default_path = PROMPT_ROOT / self.template_name
        prompt = self._read_prompt(default_path, fallback=True)
        if prompt:
            logger.info("Prompt loaded from default file fallback: %s", default_path)
            return prompt

        if not self.template:
            raise ValueError("Template is empty or not found")

        return self.template

    def get_prompt_template(self, inputs: list[str] | None = None, config: dict | None = None) -> PromptTemplate:
        return PromptTemplate(input_variables=inputs if inputs else [], validate_template=False, template=self.get_prompt(config))

    def get_prompt_template_output(self, output: type[BaseModel]) -> RunnableSerializable:
        model_name = self.get_model_name()
        parser = PydanticOutputParser(pydantic_object=output)
        # partial_variables = {"format_instructions": parser.get_format_instructions()}
        template = self.get_prompt() + f"\n{parser.get_format_instructions()}"

        return (
            ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=template),
                    MessagesPlaceholder("messages"),
                ],
            )
            | llm_provider(model_name, False, {})
            | parser
        )
