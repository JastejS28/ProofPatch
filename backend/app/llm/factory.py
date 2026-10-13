from app.core.config import settings
from app.llm.base import LLMProvider
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

    raise RuntimeError(
        f"Unsupported LLM provider: {provider}"
    )