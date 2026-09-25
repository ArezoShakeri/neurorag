"""LLM provider — swappable via LLM_PROVIDER so agent nodes only ever depend on BaseChatModel,
never a concrete provider. Set LLM_PROVIDER=anthropic (+ ANTHROPIC_API_KEY) to switch from the
local free Ollama model to Claude without touching any node code."""

from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from settings import get_settings


@lru_cache
def get_chat_model() -> BaseChatModel:
    settings = get_settings()

    if settings.llm_provider == "ollama":
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.1,
            num_predict=settings.llm_max_output_tokens,
            # Thinking-capable models (e.g. qwen3) would otherwise spend the output budget on
            # hidden reasoning; the task is grounded extraction, which doesn't need it.
            reasoning=False,
        )

    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        from langchain_anthropic import ChatAnthropic  # optional dependency, only needed for this provider

        return ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            temperature=0.1,
            max_tokens=settings.llm_max_output_tokens,
        )

    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider!r}")
