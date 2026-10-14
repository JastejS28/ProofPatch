from app.core.config import (
    settings,
)
from app.llm.base import (
    LLMProvider,
)
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

4. Prefer explainable algorithmic, data-structure,
   allocation, lookup, loop, or repeated-work
   improvements.

5. Every hypothesis must explain:
   - what is slow,
   - why it is slow,
   - what mechanism could improve it,
   - expected effect,
   - trade-offs.

6. Return between 2 and
   {settings.max_hypotheses}
   genuinely distinct hypotheses.

7. The hypotheses must represent meaningfully
   different implementation strategies.
   Do not produce superficial rewrites of the
   same optimization.

8. Rank hypotheses from strongest to weakest
   expected optimization opportunity.

9. If one optimization is clearly strongest,
   still provide at least one reasonable
   alternative strategy when one exists.

10. Do not claim that an optimization works.
    It has not been benchmarked yet.

11. Existing tests may describe required behavior,
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