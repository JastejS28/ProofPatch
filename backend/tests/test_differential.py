import pytest

from app.sandbox.differential import (
    DifferentialTestError,
    build_differential_test,
)


def test_builds_differential_test_for_supported_function():

    source = """
def count_members(
    values: list[int],
    allowed: list[int],
) -> int:
    count = 0

    for value in values:
        if value in allowed:
            count += 1

    return count
""".strip()

    generated = build_differential_test(
        target_file=(
            "optimization_cases.py"
        ),
        target_function=(
            "count_members"
        ),
        source=source,
    )

    assert (
        "test_baseline_candidate_equivalence"
        in generated
    )

    assert (
        "@given("
        in generated
    )

    assert (
        "max_examples=200"
        in generated
    )

    assert (
        '"/baseline"'
        in generated
    )

    assert (
        '"/candidate"'
        in generated
    )


def test_differential_rejects_untyped_parameter():

    source = """
def calculate(value):
    return value
""".strip()

    with pytest.raises(
        DifferentialTestError,
        match=(
            "requires parameter "
            "type annotations"
        ),
    ):

        build_differential_test(
            target_file="target.py",
            target_function="calculate",
            source=source,
        )


def test_differential_rejects_async_function():

    source = """
async def calculate(
    value: int,
) -> int:
    return value
""".strip()

    with pytest.raises(
        DifferentialTestError,
        match=(
            "Async target functions"
        ),
    ):

        build_differential_test(
            target_file="target.py",
            target_function="calculate",
            source=source,
        )


def test_differential_rejects_unsupported_dict():

    source = """
def calculate(
    values: dict[str, int],
) -> int:
    return len(values)
""".strip()

    with pytest.raises(
        DifferentialTestError,
        match=(
            "Unsupported parameter "
            "annotation"
        ),
    ):

        build_differential_test(
            target_file="target.py",
            target_function="calculate",
            source=source,
        )


def test_differential_rejects_varargs():

    source = """
def calculate(
    *values: int,
) -> int:
    return sum(values)
""".strip()

    with pytest.raises(
        DifferentialTestError,
        match=r"\*args",
    ):

        build_differential_test(
            target_file="target.py",
            target_function="calculate",
            source=source,
        )