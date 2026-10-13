import ast
import textwrap
from dataclasses import dataclass
from pathlib import Path

from app.repository.analyzer import (
    RepositoryAnalysisError,
    analyze_target_function,
)


class PatchError(Exception):
    pass


@dataclass
class PatchResult:
    original_function: str
    candidate_function: str
    target_file: str


def _parse_replacement_function(
    source: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef:

    try:
        tree = ast.parse(
            source
        )
    except SyntaxError as exc:
     raise PatchError(
        "Coder returned invalid Python syntax: "
        f"{exc.msg} at line {exc.lineno}."
    ) from exc

    function_nodes = [
        node
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    ]

    if len(function_nodes) != 1:
        raise PatchError(
            "Coder output must contain exactly "
            "one function definition."
        )

    if len(tree.body) != 1:
        raise PatchError(
            "Coder output may only contain "
            "the replacement function."
        )

    function = function_nodes[0]

    if function.decorator_list:
        raise PatchError(
            "Coder may not add decorators."
        )

    return function


def _signature_key(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple:
    return (
        isinstance(
            node,
            ast.AsyncFunctionDef,
        ),
        ast.dump(
            node.args,
            include_attributes=False,
        ),
        ast.dump(
            node.returns,
            include_attributes=False,
        )
        if node.returns is not None
        else None,
    )


def apply_function_replacement(
    workspace: Path,
    target_file: str,
    target_function: str,
    replacement_source: str,
) -> PatchResult:

    original_analysis = (
        analyze_target_function(
            workspace=workspace,
            target_file=target_file,
            target_function=target_function,
        )
    )

    original_node = (
        original_analysis.node
    )

    replacement_source = (
  _clean_replacement_source(
        replacement_source
    )    )

    replacement_node = (
        _parse_replacement_function(
            replacement_source
        )
    )

    if (
        replacement_node.name
        != original_node.name
    ):
        raise PatchError(
            "Coder changed the target "
            "function name."
        )

    if (
        _signature_key(replacement_node)
        != _signature_key(original_node)
    ):
        raise PatchError(
            "Coder changed the target "
            "function signature."
        )

    file_path = (
        workspace
        / target_file
    ).resolve()

    source = file_path.read_text(
        encoding="utf-8"
    )

    lines = source.splitlines(
        keepends=True
    )

    start_index = (
        original_node.lineno - 1
    )

    end_index = (
        original_node.end_lineno
        or original_node.lineno
    )

    indentation = " " * (
        original_node.col_offset
    )

    indented_replacement = (
        textwrap.indent(
            replacement_source,
            indentation,
        )
    )

    if not indented_replacement.endswith(
        "\n"
    ):
        indented_replacement += "\n"

    new_lines = (
        lines[:start_index]
        + [indented_replacement]
        + lines[end_index:]
    )

    candidate_source = "".join(
        new_lines
    )

    try:
        ast.parse(
            candidate_source
        )
    except SyntaxError as exc:
        raise PatchError(
            "Candidate file became invalid "
            "Python after replacement."
        ) from exc

    file_path.write_text(
        candidate_source,
        encoding="utf-8",
    )

    return PatchResult(
        original_function=(
            original_analysis.source
        ),
        candidate_function=(
            replacement_source
        ),
        target_file=target_file,
    )
import re


def _clean_replacement_source(
    source: str,
) -> str:
    cleaned = source.strip()

    fenced_match = re.search(
        r"```(?:python|py)?\s*(.*?)```",
        cleaned,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if fenced_match:
        cleaned = fenced_match.group(1).strip()

    lines = cleaned.splitlines()

    start_index = None

    for index, line in enumerate(lines):
        stripped = line.lstrip()

        if (
            stripped.startswith("def ")
            or stripped.startswith("async def ")
        ):
            start_index = index
            break

    if start_index is None:
        return cleaned

    cleaned = "\n".join(
        lines[start_index:]
    ).strip()

    return cleaned