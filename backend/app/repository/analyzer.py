import ast
from dataclasses import dataclass
from pathlib import Path


class RepositoryAnalysisError(Exception):
    pass


@dataclass
class FunctionAnalysis:
    name: str
    source: str
    signature: str

    line_start: int
    line_end: int

    imports: list[str]
    related_test_files: list[str]

    node: ast.FunctionDef | ast.AsyncFunctionDef


def _extract_imports(
    tree: ast.Module,
) -> list[str]:
    imports: list[str] = []

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(
                    f"import {alias.name}"
                )

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""

            names = ", ".join(
                alias.name
                for alias in node.names
            )

            imports.append(
                f"from {module} import {names}"
            )

    return imports


def _find_function(
    tree: ast.Module,
    function_name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
        and node.name == function_name
    ]

    if not matches:
        raise RepositoryAnalysisError(
            f"Function '{function_name}' was not found."
        )

    if len(matches) > 1:
        raise RepositoryAnalysisError(
            f"Multiple functions named "
            f"'{function_name}' were found."
        )

    return matches[0]


def _build_signature(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str:
    arguments = ast.unparse(node.args)

    prefix = (
        "async def"
        if isinstance(node, ast.AsyncFunctionDef)
        else "def"
    )

    return_annotation = ""

    if node.returns is not None:
        return_annotation = (
            f" -> {ast.unparse(node.returns)}"
        )

    return (
        f"{prefix} {node.name}"
        f"({arguments})"
        f"{return_annotation}"
    )


def _find_related_tests(
    workspace: Path,
    function_name: str,
) -> list[str]:
    matches: list[str] = []

    for path in workspace.rglob("*.py"):
        lowered_parts = {
            part.lower()
            for part in path.parts
        }

        file_name = path.name.lower()

        looks_like_test = (
            "tests" in lowered_parts
            or file_name.startswith("test_")
            or file_name.endswith("_test.py")
        )

        if not looks_like_test:
            continue

        try:
            content = path.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError:
            continue

        if function_name in content:
            matches.append(
                str(path.relative_to(workspace))
            )

    return sorted(matches)


def analyze_target_function(
    workspace: Path,
    target_file: str,
    target_function: str,
) -> FunctionAnalysis:
    file_path = (
        workspace / target_file
    ).resolve()

    workspace_resolved = workspace.resolve()

    try:
        file_path.relative_to(
            workspace_resolved
        )
    except ValueError as exc:
        raise RepositoryAnalysisError(
            "Target file escapes the run workspace."
        ) from exc

    if not file_path.exists():
        raise RepositoryAnalysisError(
            f"Target file '{target_file}' does not exist."
        )

    if not file_path.is_file():
        raise RepositoryAnalysisError(
            "Target path is not a file."
        )

    if file_path.suffix != ".py":
        raise RepositoryAnalysisError(
            "ProofPatch V1 only supports Python files."
        )

    try:
        source = file_path.read_text(
            encoding="utf-8"
        )
    except UnicodeDecodeError as exc:
        raise RepositoryAnalysisError(
            "Target Python file is not valid UTF-8."
        ) from exc

    try:
        tree = ast.parse(
            source,
            filename=str(file_path),
        )
    except SyntaxError as exc:
        raise RepositoryAnalysisError(
            "Target Python file could not be parsed."
        ) from exc

    function_node = _find_function(
        tree,
        target_function,
    )

    function_source = ast.get_source_segment(
        source,
        function_node,
    )

    if function_source is None:
        raise RepositoryAnalysisError(
            "Could not extract target function source."
        )

    return FunctionAnalysis(
        name=function_node.name,
        source=function_source,
        signature=_build_signature(
            function_node
        ),
        line_start=function_node.lineno,
        line_end=function_node.end_lineno
        or function_node.lineno,
        imports=_extract_imports(tree),
        related_test_files=_find_related_tests(
            workspace,
            target_function,
        ),
        node=function_node,
    )