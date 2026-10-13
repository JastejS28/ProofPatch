from app.core.config import settings
from app.llm.base import LLMProvider
from app.schemas.hypothesis import (
    ScientistOutput,
)


def build_scientist_prompt(
    context: str,
) -> str:
    return f"""
You are the Scientist component of ProofPatch.

Your task is to analyze one Python target function
and propose optimization hypotheses.

Rules:

1. Focus only on local function-level performance.
2. Preserve externally observable behavior.
3. Do not propose concurrency, multiprocessing,
   GPU/JIT, database tuning, network optimization,
   or large architectural refactors.
4. Prefer explainable algorithmic or data-structure
   improvements.
5. Every hypothesis must explain:
   - what is slow,
   - why it is slow,
   - what mechanism could improve it,
   - expected effect,
   - trade-offs.
6. Return at most {settings.max_hypotheses}
   genuinely distinct hypotheses.
7. Do not claim that an optimization works.
   It has not been benchmarked yet.
8. Existing tests may describe required behavior,
   but they are not proof of performance.

CONTEXT:

{context}
""".strip()


async def generate_hypotheses(
    provider: LLMProvider,
    context: str,
) -> ScientistOutput:
    prompt = build_scientist_prompt(
        context
    )

    return await provider.generate_structured(
        prompt=prompt,
        response_model=ScientistOutput,
    )