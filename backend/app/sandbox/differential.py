import ast
import json
from dataclasses import dataclass
from pathlib import Path
import tempfile

from app.sandbox.runner import (
    SandboxResult,
    run_differential_in_sandbox,
)

class DifferentialTestError(Exception):
    pass


@dataclass
class DifferentialValidationResult:
    result: SandboxResult

    @property
    def passed(self) -> bool:
        return (
            not self.result.timed_out
            and self.result.exit_code == 0
        )


def _annotation_to_strategy(
    annotation: ast.expr | None,
) -> str:
    """
    Convert a small supported subset of Python
    type annotations into Hypothesis strategies.

    V1 intentionally supports only simple,
    predictable types.
    """

    if annotation is None:
        raise DifferentialTestError(
            "Differential testing requires "
            "parameter type annotations."
        )

    # int
    if (
        isinstance(annotation, ast.Name)
        and annotation.id == "int"
    ):
        return (
            "st.integers("
            "min_value=-1000, "
            "max_value=1000"
            ")"
        )

    # float
    if (
        isinstance(annotation, ast.Name)
        and annotation.id == "float"
    ):
        return (
            "st.floats("
            "min_value=-1000, "
            "max_value=1000, "
            "allow_nan=False, "
            "allow_infinity=False"
            ")"
        )

    # bool
    if (
        isinstance(annotation, ast.Name)
        and annotation.id == "bool"
    ):
        return "st.booleans()"

    # str
    if (
        isinstance(annotation, ast.Name)
        and annotation.id == "str"
    ):
        return (
            "st.text("
            "alphabet=st.characters("
            "blacklist_categories=('Cs',)"
            "), "
            "max_size=30"
            ")"
        )

    # list[T]
    if (
        isinstance(annotation, ast.Subscript)
        and isinstance(
            annotation.value,
            ast.Name,
        )
        and annotation.value.id == "list"
    ):
        element_strategy = (
            _annotation_to_strategy(
                annotation.slice
            )
        )

        return (
            f"st.lists("
            f"{element_strategy}, "
            f"max_size=50"
            f")"
        )

    raise DifferentialTestError(
        "Unsupported parameter annotation for "
        "V1 differential testing: "
        f"{ast.unparse(annotation)}"
    )


def build_differential_test(
    target_file: str,
    target_function: str,
    source: str,
) -> str:
    """
    Build a pytest/Hypothesis test that imports
    baseline and candidate modules independently,
    generates inputs, and compares results.
    """

    try:
        tree = ast.parse(
            source
        )

    except SyntaxError as exc:
        raise DifferentialTestError(
            "Could not parse target source for "
            "differential testing."
        ) from exc

    target_node = None

    for node in ast.walk(tree):
        if (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and node.name == target_function
        ):
            target_node = node
            break

    if target_node is None:
        raise DifferentialTestError(
            "Target function was not found while "
            "building differential tests."
        )

    if isinstance(
        target_node,
        ast.AsyncFunctionDef,
    ):
        raise DifferentialTestError(
            "Async target functions are not "
            "supported by V1 differential testing."
        )

    positional_args = [
        *target_node.args.posonlyargs,
        *target_node.args.args,
    ]

    if target_node.args.vararg is not None:
        raise DifferentialTestError(
            "*args are not supported by V1 "
            "differential testing."
        )

    if target_node.args.kwarg is not None:
        raise DifferentialTestError(
            "**kwargs are not supported by V1 "
            "differential testing."
        )

    if target_node.args.kwonlyargs:
        raise DifferentialTestError(
            "Keyword-only parameters are not "
            "supported by V1 differential testing."
        )

    if not positional_args:
        raise DifferentialTestError(
            "Target function has no parameters."
        )

    strategies: list[str] = []

    for argument in positional_args:
        strategy = _annotation_to_strategy(
            argument.annotation
        )

        strategies.append(
            f"{argument.arg}={strategy}"
        )

    argument_names = [
        arg.arg
        for arg in positional_args
    ]

    given_arguments = ",\n    ".join(
        strategies
    )

    call_arguments = ", ".join(
        argument_names
    )

    target_path_json = json.dumps(
        Path(target_file).as_posix()
    )

    function_json = json.dumps(
        target_function
    )

    return f'''
import importlib.util
from pathlib import Path

from hypothesis import (
    given,
    settings,
    strategies as st,
)


TARGET_FILE = {target_path_json}
TARGET_FUNCTION = {function_json}


def load_function(
    root: str,
):
    file_path = (
        Path(root)
        / TARGET_FILE
    )

    spec = (
        importlib.util
        .spec_from_file_location(
            f"proofpatch_{{root}}",
            file_path,
        )
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Could not load target module."
        )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    spec.loader.exec_module(
        module
    )

    return getattr(
        module,
        TARGET_FUNCTION,
    )


baseline_function = load_function(
    "/baseline"
)

candidate_function = load_function(
    "/candidate"
)


@settings(
    max_examples=200,
    deadline=None,
)
@given(
    {given_arguments}
)
def test_baseline_candidate_equivalence(
    {call_arguments}
):
    baseline_result = baseline_function(
        {call_arguments}
    )

    candidate_result = candidate_function(
        {call_arguments}
    )

    assert (
        baseline_result
        == candidate_result
    )
'''.strip()


async def run_differential_tests(
    baseline_workspace: Path,
    candidate_workspace: Path,
    target_file: str,
    target_function: str,
    source: str,
) -> DifferentialValidationResult:

    test_source = (
        build_differential_test(
            target_file=target_file,
            target_function=target_function,
            source=source,
        )
    )

    with tempfile.TemporaryDirectory(
        prefix="proofpatch-differential-"
    ) as temp_directory:

        test_workspace = Path(
            temp_directory
        )

        test_file = (
            test_workspace
            / "test_differential.py"
        )

        test_file.write_text(
            test_source,
            encoding="utf-8",
        )

        result = (
            await run_differential_in_sandbox(
                baseline_workspace=(
                    baseline_workspace
                ),
                candidate_workspace=(
                    candidate_workspace
                ),
                test_workspace=(
                    test_workspace
                ),
                command=[
                    "python",
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "test_differential.py",
                ],
            )
        )

    return DifferentialValidationResult(
        result=result
    )