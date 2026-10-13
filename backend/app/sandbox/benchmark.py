import ast
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.sandbox.runner import (
    run_benchmark_in_sandbox,
)


class BenchmarkError(Exception):
    pass


@dataclass
class BenchmarkMeasurement:
    median_seconds: float
    mean_seconds: float
    stdev_seconds: float
    values_count: int

    stdout: str
    stderr: str

    duration_ms: int


def _annotation_to_value(
    annotation: ast.expr | None,
) -> str:

    if annotation is None:
        raise BenchmarkError(
            "Benchmarking requires parameter "
            "type annotations."
        )

    # int
    if (
        isinstance(annotation, ast.Name)
        and annotation.id == "int"
    ):
        return "1000"

    # float
    if (
        isinstance(annotation, ast.Name)
        and annotation.id == "float"
    ):
        return "1234.5"

    # bool
    if (
        isinstance(annotation, ast.Name)
        and annotation.id == "bool"
    ):
        return "True"

    # str
    if (
        isinstance(annotation, ast.Name)
        and annotation.id == "str"
    ):
        return (
            '"proofpatch-" * 500'
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

        inner = annotation.slice

        if (
            isinstance(inner, ast.Name)
            and inner.id == "int"
        ):
            return (
                f"list(range("
                f"{settings.benchmark_input_size}"
                f"))"
            )

        if (
            isinstance(inner, ast.Name)
            and inner.id == "float"
        ):
            return (
                "[float(i) for i in "
                f"range({settings.benchmark_input_size})]"
            )

        if (
            isinstance(inner, ast.Name)
            and inner.id == "str"
        ):
            return (
                "[f'item_{i}' for i in "
                f"range({settings.benchmark_input_size})]"
            )

        if (
            isinstance(inner, ast.Name)
            and inner.id == "bool"
        ):
            return (
                "[i % 2 == 0 for i in "
                f"range({settings.benchmark_input_size})]"
            )

    raise BenchmarkError(
        "Unsupported benchmark parameter "
        "annotation: "
        f"{ast.unparse(annotation)}"
    )


def _build_argument_source(
    source: str,
    target_function: str,
) -> str:

    try:
        tree = ast.parse(
            source
        )

    except SyntaxError as exc:
        raise BenchmarkError(
            "Could not parse target function "
            "for benchmark input generation."
        ) from exc

    target_node = None

    # We intentionally expect the source snippet
    # itself to contain one target function.
    for node in tree.body:
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
        raise BenchmarkError(
            "Target function could not be found "
            "while preparing benchmark inputs."
        )

    if isinstance(
        target_node,
        ast.AsyncFunctionDef,
    ):
        raise BenchmarkError(
            "Async targets are not supported "
            "by V1 benchmarking."
        )

    if target_node.args.vararg is not None:
        raise BenchmarkError(
            "*args are not supported by "
            "V1 benchmarking."
        )

    if target_node.args.kwarg is not None:
        raise BenchmarkError(
            "**kwargs are not supported by "
            "V1 benchmarking."
        )

    if target_node.args.kwonlyargs:
        raise BenchmarkError(
            "Keyword-only parameters are not "
            "supported by V1 benchmarking."
        )

    arguments = [
        *target_node.args.posonlyargs,
        *target_node.args.args,
    ]

    values = [
        _annotation_to_value(
            argument.annotation
        )
        for argument in arguments
    ]

    if not values:
        return "()"

    if len(values) == 1:
        return (
            f"({values[0]},)"
        )

    return (
        "("
        + ", ".join(values)
        + ")"
    )


def _build_benchmark_script(
    target_file: str,
    target_function: str,
    source: str,
) -> str:

    arguments = (
        _build_argument_source(
            source=source,
            target_function=target_function,
        )
    )

    target_file_json = json.dumps(
        Path(target_file).as_posix()
    )

    target_function_json = json.dumps(
        target_function
    )

    return f'''
import importlib.util
import sys

import pyperf

from pathlib import Path


ROOT = Path("/workspace")

TARGET_FILE = {target_file_json}
TARGET_FUNCTION = {target_function_json}


sys.path.insert(
    0,
    str(ROOT),
)


file_path = (
    ROOT
    / TARGET_FILE
)


spec = (
    importlib.util
    .spec_from_file_location(
        "proofpatch_benchmark_target",
        file_path,
    )
)


if spec is None or spec.loader is None:
    raise RuntimeError(
        "Unable to load benchmark target."
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


target_function = getattr(
    module,
    TARGET_FUNCTION,
)


ARGS = {arguments}


def benchmark_target(
    loops,
):
    range_it = range(
        loops
    )

    start = (
        pyperf.perf_counter()
    )

    for _ in range_it:
        target_function(
            *ARGS
        )

    return (
        pyperf.perf_counter()
        - start
    )


runner = pyperf.Runner()


runner.bench_time_func(
    "target_function",
    benchmark_target,
)
'''.strip()


def _build_driver_script() -> str:

    return f'''
import json
import subprocess
import sys

import pyperf


command = [
    sys.executable,
    "/harness/benchmark_target.py",

    "--output",
    "/tmp/benchmark.json",

    "--processes",
    "{settings.benchmark_processes}",

    "--values",
    "{settings.benchmark_values}",

    "--warmups",
    "{settings.benchmark_warmups}",

    "--min-time",
    "{settings.benchmark_min_time_seconds}",

    "--quiet",
]


completed = subprocess.run(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    check=False,
)


if completed.returncode != 0:
    print(
        completed.stdout
    )

    print(
        completed.stderr,
        file=sys.stderr,
    )

    raise SystemExit(
        completed.returncode
    )


benchmark = pyperf.Benchmark.load(
    "/tmp/benchmark.json"
)


summary = {{
    "median_seconds":
        benchmark.median(),

    "mean_seconds":
        benchmark.mean(),

    "stdev_seconds":
        benchmark.stdev(),

    "values_count":
        len(
            benchmark.get_values()
        ),
}}


print(
    "PROOFPATCH_BENCHMARK_JSON="
    + json.dumps(summary)
)
'''.strip()


async def run_target_benchmark(
    workspace: Path,
    target_file: str,
    target_function: str,
    source: str,
) -> BenchmarkMeasurement:

    benchmark_script = (
        _build_benchmark_script(
            target_file=target_file,
            target_function=target_function,
            source=source,
        )
    )

    driver_script = (
        _build_driver_script()
    )

    with tempfile.TemporaryDirectory(
        prefix="proofpatch-benchmark-"
    ) as temp_directory:

        harness = Path(
            temp_directory
        )

        (
            harness
            / "benchmark_target.py"
        ).write_text(
            benchmark_script,
            encoding="utf-8",
        )

        (
            harness
            / "benchmark_driver.py"
        ).write_text(
            driver_script,
            encoding="utf-8",
        )

        sandbox_result = (
            await run_benchmark_in_sandbox(
                workspace=workspace,
                harness_workspace=harness,
                command=[
                    "python",
                    "/harness/benchmark_driver.py",
                ],
            )
        )

    if sandbox_result.timed_out:
        raise BenchmarkError(
            "Benchmark execution exceeded "
            f"{settings.benchmark_timeout_seconds} "
            "seconds."
        )

    if sandbox_result.exit_code != 0:
        raise BenchmarkError(
            "Benchmark process failed. "
            + sandbox_result.stderr[-4000:]
        )

    marker = (
        "PROOFPATCH_BENCHMARK_JSON="
    )

    summary_line = None

    for line in (
        sandbox_result
        .stdout
        .splitlines()
    ):
        if line.startswith(
            marker
        ):
            summary_line = line

    if summary_line is None:
        raise BenchmarkError(
            "Benchmark completed without "
            "returning benchmark statistics."
        )

    try:
        summary = json.loads(
            summary_line[
                len(marker):
            ]
        )

    except json.JSONDecodeError as exc:
        raise BenchmarkError(
            "Benchmark returned invalid "
            "statistics JSON."
        ) from exc

    return BenchmarkMeasurement(
        median_seconds=float(
            summary[
                "median_seconds"
            ]
        ),

        mean_seconds=float(
            summary[
                "mean_seconds"
            ]
        ),

        stdev_seconds=float(
            summary[
                "stdev_seconds"
            ]
        ),

        values_count=int(
            summary[
                "values_count"
            ]
        ),

        stdout=(
            sandbox_result.stdout
        ),

        stderr=(
            sandbox_result.stderr
        ),

        duration_ms=(
            sandbox_result.duration_ms
        ),
    )