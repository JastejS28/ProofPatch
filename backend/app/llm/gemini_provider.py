import asyncio

from google import genai
from google.genai import (
    errors,
    types,
)

from app.core.config import settings
from app.llm.base import (
    LLMProvider,
    T,
)
from app.llm.errors import (
    LLMQuotaExceededError,
    LLMRequestError,
    LLMTimeoutError,
    LLMUnavailableError,
)


class GeminiProvider(LLMProvider):

    def __init__(self) -> None:

        if not settings.gemini_api_key:
            raise LLMRequestError(
                "GEMINI_API_KEY is not configured."
            )

        self.client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(
                timeout=(
                    settings
                    .gemini_timeout_seconds
                    * 1000
                ),
                retry_options=(
                    types.HttpRetryOptions(
                        attempts=(
                            settings
                            .gemini_retry_attempts
                        ),
                    )
                ),
            ),
        )

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
    ) -> T:

        def _call() -> T:

            try:
                response = (
                    self.client.models
                    .generate_content(
                        model=(
                            settings.gemini_model
                        ),
                        contents=prompt,
                        config={
                            "response_mime_type":
                                "application/json",
                            "response_schema":
                                response_model,
                        },
                    )
                )

            except errors.APIError as exc:

                code = getattr(
                    exc,
                    "code",
                    None,
                )

                message = getattr(
                    exc,
                    "message",
                    str(exc),
                )

                # -------------------------
                # Quota / rate-limit error
                # -------------------------
                if code == 429:
                    raise (
                        LLMQuotaExceededError(
                            "Gemini quota or rate "
                            "limit was exhausted. "
                            f"Provider message: "
                            f"{message}"
                        )
                    ) from exc

                # -------------------------
                # Temporary server failure
                # -------------------------
                if code in {
                    500,
                    502,
                    503,
                    504,
                }:
                    raise (
                        LLMUnavailableError(
                            "Gemini is temporarily "
                            "unavailable. "
                            f"Provider message: "
                            f"{message}"
                        )
                    ) from exc

                # -------------------------
                # Other Gemini API failure
                # -------------------------
                raise LLMRequestError(
                    "Gemini request failed. "
                    f"HTTP {code}: {message}"
                ) from exc

            # Best case:
            # SDK already converted JSON
            # into our Pydantic model.
            if response.parsed is not None:
                return response.parsed

            # Prevent vague JSON parsing errors
            # if Gemini returns no text.
            if not response.text:
                raise LLMRequestError(
                    "Gemini returned an empty "
                    "response."
                )

            try:
                return (
                    response_model
                    .model_validate_json(
                        response.text
                    )
                )

            except Exception as exc:
                raise LLMRequestError(
                    "Gemini returned a response "
                    "that did not match the "
                    "expected structured schema."
                ) from exc

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    _call
                ),
                timeout=(
                    settings
                    .gemini_timeout_seconds
                    + 5
                ),
            )

        except asyncio.TimeoutError as exc:
            raise LLMTimeoutError(
                "Gemini request exceeded the "
                f"{settings.gemini_timeout_seconds}"
                "-second timeout."
            ) from exc