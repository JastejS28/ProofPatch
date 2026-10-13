from pathlib import Path


def _read_related_tests(
    workspace: Path,
    test_paths: list[str],
) -> str:

    sections: list[str] = []

    workspace_resolved = (
        workspace.resolve()
    )

    for relative_path in test_paths:

        path = (
            workspace
            / relative_path
        ).resolve()

        try:
            path.relative_to(
                workspace_resolved
            )

        except ValueError:
            continue

        if not path.is_file():
            continue

        try:
            content = (
                path.read_text(
                    encoding="utf-8"
                )
            )

        except (
            OSError,
            UnicodeDecodeError,
        ):
            continue

        sections.append(
            f"TEST FILE: "
            f"{relative_path}\n"
            f"{content}"
        )

    return "\n\n".join(
        sections
    )


def _build_retry_section(
    retry_feedback: dict | None,
) -> str:

    if not retry_feedback:
        return ""

    previous_iteration = (
        retry_feedback.get(
            "previous_iteration"
        )
    )

    failure_stage = (
        retry_feedback.get(
            "failure_stage",
            "UNKNOWN",
        )
    )

    reason = (
        retry_feedback.get(
            "reason",
            (
                "Previous candidate "
                "was rejected."
            ),
        )
    )

    previous_changes = (
        retry_feedback.get(
            "previous_changes",
            {},
        )
    )

    validation = (
        retry_feedback.get(
            "validation",
            {},
        )
    )

    benchmark = (
        retry_feedback.get(
            "benchmark",
            {},
        )
    )

    previous_candidate = (
        previous_changes.get(
            "candidate_function",
            "Unavailable",
        )
    )

    return f"""
PREVIOUS ATTEMPT FEEDBACK:

Previous iteration:
{previous_iteration}

Failure stage:
{failure_stage}

Reason:
{reason}

Previous implementation:
{previous_candidate}

Previous correctness evidence:
{validation}

Previous benchmark evidence:
{benchmark}

IMPORTANT RETRY INSTRUCTIONS:

This is a retry.

Do not simply reproduce the previous implementation.

Keep the selected optimization hypothesis unless the
failure evidence directly shows that a different
implementation of that hypothesis is required.

Produce a new implementation that addresses the
failure evidence.

The replacement must still preserve the exact function
name and signature.
""".strip()


def build_coder_context(
    workspace: Path,
    repository_summary: dict,
    problem_description: str,
    selected_hypothesis: dict,
    retry_feedback: dict | None = None,
) -> str:

    tests = _read_related_tests(
        workspace=workspace,
        test_paths=(
            repository_summary.get(
                "related_test_files",
                [],
            )
        ),
    )

    retry_section = (
        _build_retry_section(
            retry_feedback
        )
    )

    return f"""
USER PERFORMANCE CONCERN:
{problem_description}

TARGET SIGNATURE:
{repository_summary["signature"]}

CURRENT FUNCTION:
{repository_summary["source"]}

SELECTED OPTIMIZATION HYPOTHESIS:

Summary:
{selected_hypothesis["summary"]}

Mechanism:
{selected_hypothesis["mechanism"]}

Expected effect:
{selected_hypothesis["expected_effect"]}

Trade-offs:
{selected_hypothesis["trade_offs"]}

RELATED TESTS:
{tests if tests else "No directly related tests were found."}

{retry_section}
""".strip()