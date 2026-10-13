from pathlib import Path


def _read_related_tests(
    workspace: Path,
    test_paths: list[str],
) -> str:
    sections: list[str] = []

    workspace_resolved = workspace.resolve()

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
            content = path.read_text(
                encoding="utf-8"
            )
        except (
            OSError,
            UnicodeDecodeError,
        ):
            continue

        sections.append(
            f"TEST FILE: {relative_path}\n"
            f"{content}"
        )

    return "\n\n".join(
        sections
    )


def build_coder_context(
    workspace: Path,
    repository_summary: dict,
    problem_description: str,
    selected_hypothesis: dict,
) -> str:

    tests = _read_related_tests(
        workspace=workspace,
        test_paths=repository_summary.get(
            "related_test_files",
            [],
        ),
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
""".strip()