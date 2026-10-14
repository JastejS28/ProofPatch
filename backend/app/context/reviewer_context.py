def build_reviewer_context(
    state: dict,
    problem_description: str,
) -> str:

    changes = state.get(
        "changes",
        {},
    )

    validation = state.get(
        "validation",
        {},
    )

    benchmark = state.get(
        "benchmark",
        {},
    )

    verification = state.get(
        "verification",
        {},
    )

    return f"""
USER PERFORMANCE CONCERN:
{problem_description}

FINAL CANDIDATE CHANGE SUMMARY:
{changes.get("change_summary", "")}

EXPECTED MECHANISM:
{changes.get("expected_mechanism", "")}

DIFF:
{changes.get("diff", "")}

STATIC POLICY:
{changes.get("policy", {})}

CORRECTNESS EVIDENCE:
{validation}

BENCHMARK EVIDENCE:
{benchmark}

DETERMINISTIC VERIFICATION:
{verification}

REVIEW TASK:

Summarize the final verified candidate for a human reviewer.

Do not decide correctness yourself.
Do not override deterministic evidence.

Explain:
1. what changed
2. why it improves performance
3. what correctness evidence exists
4. what benchmark evidence exists
5. remaining risks or trade-offs
6. whether the patch is reasonable to approve for PR creation

Be concise and factual.
""".strip()