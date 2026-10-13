from app.core.config import settings
from app.llm.base import LLMProvider
from app.llm.fallback_provider import (
    FallbackLLMProvider,
)
from app.llm.gemini_provider import (
    GeminiProvider,
)
from app.llm.ollama_provider import (
    OllamaProvider,
)


def get_llm_provider() -> LLMProvider:

    provider = (
        settings.llm_provider
        .strip()
        .lower()
    )

    if provider == "ollama":
        return OllamaProvider()

    if provider == "gemini":
        return GeminiProvider()

    if provider == "gemini_ollama":
        return FallbackLLMProvider(
            primary=GeminiProvider(),
            fallback=OllamaProvider(),
        )

    raise RuntimeError(
        "Unsupported LLM provider: "
        f"{provider}"
    )