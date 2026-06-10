import logging
import os

import litellm
from langchain.chat_models import init_chat_model
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.language_models import BaseChatModel

# Configure logging
logger = logging.getLogger("provider")
litellm.suppress_debug_info = True


def llm_provider(provider_model: str, streaming: bool = False, meta: dict | None = None) -> BaseChatModel:
    if not meta:
        meta = {}

    if "/" in provider_model:
        custom_provider, model_name = provider_model.split("/", maxsplit=1)

        if model_name:
            provider_model = model_name
    else:
        custom_provider = "default"

    temperature = meta.get("temperature", 0)
    top_p = meta.get("top_p", 0.7)
    maxtoken = meta.get("maxtoken", None)

    if custom_provider == "litellm":
        # Get environment variables for LiteLLM configuration
        base_url = os.environ.get("LITELLM_BASE_URL", "")
        api_key = os.environ.get("LITELLM_API_KEY", "")

        # Validate required parameters
        if not base_url or not api_key:
            raise ValueError("Missing required environment variables: 'LITELLM_BASE_URL' and 'LITELLM_API_KEY'.")

        # langchain_litellm is not support steaming chunk
        meta.pop("streaming", 0)
        meta.pop("temperature", 0)
        meta.setdefault("drop_params", True)

        return ChatLiteLLM(
            model=provider_model,
            api_key=api_key,
            api_base=base_url,
            model_kwargs={**meta},
            temperature=temperature,
            top_p=top_p,
            streaming=streaming,
            max_tokens=maxtoken,
        )
    else:
        # Support Other model
        # https://python.langchain.com/api_reference/langchain/chat_models/langchain.chat_models.base.init_chat_model.html
        logger.info(f"init_chat_model provider: {provider_model}")
        return init_chat_model(provider_model, temperature=temperature, top_p=top_p, cache=False)
