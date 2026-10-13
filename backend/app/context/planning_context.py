from pathlib import Path

import tiktoken


class ContextBudgetError(Exception):
    pass


def _read_test_file(
    workspace: Path,
    relative_path: str,
) -> str:
    path = (
        workspace
        / relative_path
    ).resolve()

    path.relative_to(
        workspace.resolve()
    )

    return path.read_text(
        encoding="utf-8"
    )


def build_planning_context(
    workspace: Path,
    repository_summary: dict,
    problem_description: str,
    token_budget: int,
) -> str:
    target_source = repository_summary[
        "source"
    ]

    signature = repository_summary[
        "signature"
    ]

    imports = repository_summary.get(
        "imports",
        [],
    )

    test_paths = repository_summary.get(
        "related_test_files",
        [],
    )

    test_sections: list[str] = []

    for relative_path in test_paths:
        try:
            content = _read_test_file(
                workspace,
                relative_path,
            )
        except (
            OSError,
            UnicodeDecodeError,
            ValueError,
        ):
            continue

        test_sections.append(
            f"TEST FILE: {relative_path}\n"
            f"{content}"
        )

    tests_text = "\n\n".join(
        test_sections
    )

    context = f"""
USER PERFORMANCE CONCERN:
{problem_description}

TARGET SIGNATURE:
{signature}

TARGET FUNCTION:
{target_source}

MODULE IMPORTS:
{chr(10).join(imports) if imports else "None"}

RELATED TESTS:
{tests_text if tests_text else "No directly related tests were found."}
""".strip()

    encoding = tiktoken.get_encoding(
        "cl100k_base"
    )

    token_count = len(
        encoding.encode(context)
    )

    if token_count > token_budget:
        reduced_context = f"""
USER PERFORMANCE CONCERN:
{problem_description}

TARGET SIGNATURE:
{signature}

TARGET FUNCTION:
{target_source}

MODULE IMPORTS:
{chr(10).join(imports) if imports else "None"}
""".strip()

        reduced_token_count = len(
            encoding.encode(
                reduced_context
            )
        )

        if reduced_token_count > token_budget:
            raise ContextBudgetError(
                "Target function alone exceeds "
                "the planning token budget."
            )

        return reduced_context

    return context