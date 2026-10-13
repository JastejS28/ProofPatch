import asyncio

from ollama import (
    Client,
    ResponseError,
)

from app.core.config import settings
from app.llm.base import (
    LLMProvider,
    T,
)
from app.llm.errors import (
    LLMRequestError,
    LLMTimeoutError,
    LLMUnavailableError,
)


class OllamaProvider(LLMProvider):

    def __init__(self) -> None:
        self.client = Client(
            host=settings.ollama_host
        )

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
    ) -> T:

        def _call() -> T:
            try:
                response = self.client.chat(
                    model=settings.ollama_model,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    format=(
                        response_model
                        .model_json_schema()
                    ),
                    options={
                        "temperature": 0,
                    },
                )

            except ResponseError as exc:
                raise LLMRequestError(
                    "Ollama rejected the request. "
                    f"{exc}"
                ) from exc

            except Exception as exc:
                raise LLMUnavailableError(
                    "Could not contact Ollama. "
                    "Make sure Ollama is running "
                    "and the configured model is "
                    "installed. "
                    f"Original error: {exc}"
                ) from exc

            content = (
                response.message.content
            )

            if not content:
                raise LLMRequestError(
                    "Ollama returned an empty "
                    "response."
                )

            try:
                return (
                    response_model
                    .model_validate_json(
                        content
                    )
                )

            except Exception as exc:
                raise LLMRequestError(
                    "Ollama returned output that "
                    "did not match the expected "
                    "structured schema."
                ) from exc

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    _call
                ),
                timeout=(
                    settings
                    .ollama_timeout_seconds
                ),
            )

        except asyncio.TimeoutError as exc:
            raise LLMTimeoutError(
                "Ollama request exceeded the "
                f"{settings.ollama_timeout_seconds}"
                "-second timeout."
            ) from exc