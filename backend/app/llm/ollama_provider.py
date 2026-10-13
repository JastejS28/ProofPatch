import asyncio

from ollama import Client
from pydantic import BaseModel

from app.core.config import settings
from app.llm.base import LLMProvider, T


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
            response = self.client.chat(
                model=settings.ollama_model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                format=response_model.model_json_schema(),
                options={
                    "temperature": 0,
                },
            )

            return response_model.model_validate_json(
                response.message.content
            )

        return await asyncio.to_thread(
            _call
        )