from app.llm.base import (
    LLMProvider,
    T,
)
from app.llm.errors import (
    LLMError,
    LLMQuotaExceededError,
    LLMRequestError,
    LLMTimeoutError,
    LLMUnavailableError,
)


class FallbackLLMProvider(LLMProvider):
    """
    Try the primary provider first.

    If the primary provider fails with a known
    recoverable LLM error, try the fallback provider.
    """

    def __init__(
        self,
        primary: LLMProvider,
        fallback: LLMProvider,
    ) -> None:
        self.primary = primary
        self.fallback = fallback

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
    ) -> T:

        try:
            print(
                "[LLM] Trying primary provider: "
                f"{type(self.primary).__name__}"
            )

            result = (
                await self.primary.generate_structured(
                    prompt=prompt,
                    response_model=response_model,
                )
            )

            print(
                "[LLM] Primary provider succeeded."
            )

            return result

        except (
            LLMQuotaExceededError,
            LLMUnavailableError,
            LLMTimeoutError,
            LLMRequestError,
        ) as primary_error:

            print(
                "[LLM] Primary provider failed: "
                f"{type(primary_error).__name__}: "
                f"{primary_error}"
            )

            print(
                "[LLM] Falling back to: "
                f"{type(self.fallback).__name__}"
            )

            try:
                result = (
                    await self.fallback
                    .generate_structured(
                        prompt=prompt,
                        response_model=response_model,
                    )
                )

                print(
                    "[LLM] Fallback provider succeeded."
                )

                return result

            except LLMError as fallback_error:

                raise LLMUnavailableError(
                    "Both LLM providers failed. "
                    "Primary error: "
                    f"{type(primary_error).__name__}: "
                    f"{primary_error}. "
                    "Fallback error: "
                    f"{type(fallback_error).__name__}: "
                    f"{fallback_error}"
                ) from fallback_error