import asyncio

from app.llm.ollama_provider import (
    OllamaProvider,
)
from app.schemas.hypothesis import (
    ScientistOutput,
)


async def main() -> None:

    provider = OllamaProvider()

    result = (
        await provider.generate_structured(
            prompt="""
Analyze this Python performance issue.

A function loops through values and repeatedly
checks whether each value exists in a list.

Return exactly one optimization hypothesis.
""".strip(),
            response_model=ScientistOutput,
        )
    )

    print(
        result.model_dump()
    )


asyncio.run(main())