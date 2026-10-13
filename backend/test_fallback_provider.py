import asyncio

from app.llm.factory import (
    get_llm_provider,
)
from app.schemas.hypothesis import (
    ScientistOutput,
)


async def main() -> None:

    provider = get_llm_provider()

    print(
        "Provider:",
        type(provider).__name__,
    )

    result = (
        await provider.generate_structured(
            prompt="""
Analyze this Python performance issue:

def count_members_slow(values, allowed):
    count = 0

    for value in values:
        if value in allowed:
            count += 1

    return count

Return one or more valid optimization
hypotheses.
""".strip(),
            response_model=ScientistOutput,
        )
    )

    print()
    print("SUCCESS")
    print(
        result.model_dump()
    )


asyncio.run(main())