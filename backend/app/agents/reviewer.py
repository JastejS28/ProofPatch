from app.llm.base import (
    LLMProvider,
)
from app.schemas.reviewer import (
    ReviewerOutput,
)


def build_reviewer_prompt(
    context: str,
) -> str:

    return f"""
You are the Reviewer component of ProofPatch.

The candidate has already passed deterministic
static policy checks, correctness validation,
performance benchmarking, and deterministic
verification.

Your role is to explain the evidence clearly
for a human reviewer.

Rules:

1. Do not claim new facts that are not present
   in the supplied evidence.

2. Do not override deterministic verification.

3. Do not independently decide whether tests
   passed or whether the benchmark passed.
   Use the provided evidence.

4. Explain what changed and why the change is
   expected to improve performance.

5. Summarize the correctness evidence.

6. Summarize the benchmark evidence.

7. Mention meaningful risks or trade-offs.

8. Give a concise recommendation about whether
   the verified patch appears reasonable to send
   for human PR approval.

CONTEXT:

{context}
""".strip()


async def review_candidate(
    provider: LLMProvider,
    context: str,
) -> ReviewerOutput:

    prompt = build_reviewer_prompt(
        context
    )

    return await provider.generate_structured(
        prompt=prompt,
        response_model=ReviewerOutput,
    )