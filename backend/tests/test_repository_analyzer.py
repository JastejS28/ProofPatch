import pytest

from app.repository.analyzer import (
    RepositoryAnalysisError,
    analyze_target_function,
)


def test_analyzer_supports_nested_target_file(
    tmp_path,
):

    package = (
        tmp_path
        / "src"
        / "utils"
    )

    package.mkdir(
        parents=True,
    )

    target = (
        package
        / "math_utils.py"
    )

    target.write_text(
        """
def calculate(values: list[int]) -> int:
    return sum(values)
""".strip(),
        encoding="utf-8",
    )

    result = analyze_target_function(
        workspace=tmp_path,
        target_file=(
            "src/utils/math_utils.py"
        ),
        target_function=(
            "calculate"
        ),
    )

    assert (
        result.name
        == "calculate"
    )

    assert (
        result.related_test_files
        == []
    )


def test_analyzer_discovers_related_test(
    tmp_path,
):

    target = (
        tmp_path
        / "logic.py"
    )

    target.write_text(
        """
def calculate(values: list[int]) -> int:
    return sum(values)
""".strip(),
        encoding="utf-8",
    )

    tests_dir = (
        tmp_path
        / "tests"
    )

    tests_dir.mkdir()

    (
        tests_dir
        / "test_logic.py"
    ).write_text(
        """
from logic import calculate

def test_calculate():
    assert calculate([1, 2]) == 3
""".strip(),
        encoding="utf-8",
    )

    result = analyze_target_function(
        workspace=tmp_path,
        target_file="logic.py",
        target_function="calculate",
    )

    assert len(
        result.related_test_files
    ) == 1

    assert (
        "test_logic.py"
        in result.related_test_files[
            0
        ]
    )


def test_analyzer_reports_no_related_tests(
    tmp_path,
):

    (
        tmp_path
        / "logic.py"
    ).write_text(
        """
def calculate(values: list[int]) -> int:
    return sum(values)
""".strip(),
        encoding="utf-8",
    )

    result = analyze_target_function(
        workspace=tmp_path,
        target_file="logic.py",
        target_function="calculate",
    )

    assert (
        result.related_test_files
        == []
    )


def test_analyzer_missing_target_file(
    tmp_path,
):

    with pytest.raises(
        RepositoryAnalysisError,
        match="does not exist",
    ):

        analyze_target_function(
            workspace=tmp_path,
            target_file="missing.py",
            target_function="calculate",
        )


def test_analyzer_missing_function(
    tmp_path,
):

    (
        tmp_path
        / "logic.py"
    ).write_text(
        """
def something_else() -> int:
    return 1
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(
        RepositoryAnalysisError,
        match="was not found",
    ):

        analyze_target_function(
            workspace=tmp_path,
            target_file="logic.py",
            target_function="calculate",
        )


def test_analyzer_rejects_non_python_file(
    tmp_path,
):

    (
        tmp_path
        / "logic.txt"
    ).write_text(
        "hello",
        encoding="utf-8",
    )

    with pytest.raises(
        RepositoryAnalysisError,
        match=(
            "only supports Python"
        ),
    ):

        analyze_target_function(
            workspace=tmp_path,
            target_file="logic.txt",
            target_function="calculate",
        )


def test_analyzer_rejects_path_escape(
    tmp_path,
):

    with pytest.raises(
        RepositoryAnalysisError,
        match="escapes",
    ):

        analyze_target_function(
            workspace=tmp_path,
            target_file="../outside.py",
            target_function="calculate",
        )