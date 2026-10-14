import pytest

from app.policy.change_policy import (
    check_change_policy,
)


def write_target(
    tmp_path,
    source: str,
):

    target = (
        tmp_path
        / "target.py"
    )

    target.write_text(
        source,
        encoding="utf-8",
    )

    return target


@pytest.mark.asyncio
async def test_policy_accepts_safe_change(
    tmp_path,
):

    write_target(
        tmp_path,
        """
def compute(values: list[int]) -> int:
    return sum(values)
""".strip(),
    )

    result = await check_change_policy(
        workspace=tmp_path,
        target_file="target.py",
        target_function="compute",
        changed_files=[
            "target.py"
        ],
    )

    assert result.passed is True
    assert result.reasons == []


@pytest.mark.asyncio
async def test_policy_rejects_no_changes(
    tmp_path,
):

    write_target(
        tmp_path,
        """
def compute(values: list[int]) -> int:
    return sum(values)
""".strip(),
    )

    result = await check_change_policy(
        workspace=tmp_path,
        target_file="target.py",
        target_function="compute",
        changed_files=[],
    )

    assert result.passed is False

    assert (
        "Candidate produced no file changes."
        in result.reasons
    )


@pytest.mark.asyncio
async def test_policy_rejects_extra_file(
    tmp_path,
):

    write_target(
        tmp_path,
        """
def compute(values: list[int]) -> int:
    return sum(values)
""".strip(),
    )

    result = await check_change_policy(
        workspace=tmp_path,
        target_file="target.py",
        target_function="compute",
        changed_files=[
            "target.py",
            "another.py",
        ],
    )

    assert result.passed is False

    assert any(
        (
            "outside the target file"
            in reason
        )
        for reason in result.reasons
    )


@pytest.mark.asyncio
async def test_policy_rejects_forbidden_import(
    tmp_path,
):

    write_target(
        tmp_path,
        """
def compute(values: list[int]) -> int:
    import subprocess
    return sum(values)
""".strip(),
    )

    result = await check_change_policy(
        workspace=tmp_path,
        target_file="target.py",
        target_function="compute",
        changed_files=[
            "target.py"
        ],
    )

    assert result.passed is False

    assert any(
        "subprocess"
        in reason
        for reason in result.reasons
    )


@pytest.mark.asyncio
async def test_policy_rejects_forbidden_call(
    tmp_path,
):

    write_target(
        tmp_path,
        """
def compute(values: list[int]) -> int:
    eval("1 + 1")
    return sum(values)
""".strip(),
    )

    result = await check_change_policy(
        workspace=tmp_path,
        target_file="target.py",
        target_function="compute",
        changed_files=[
            "target.py"
        ],
    )

    assert result.passed is False

    assert any(
        "eval"
        in reason
        for reason in result.reasons
    )