import asyncio
import subprocess
from pathlib import Path


class GitDiffError(Exception):
    pass


def _run_git(
    workspace: Path,
    arguments: list[str],
) -> str:

    result = subprocess.run(
        [
            "git",
            "-C",
            str(workspace),
            *arguments,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise GitDiffError(
            result.stderr.strip()
            or "Git command failed."
        )

    return result.stdout


async def get_changed_files(
    workspace: Path,
) -> list[str]:

    output = await asyncio.to_thread(
        _run_git,
        workspace,
        [
            "diff",
            "--name-only",
        ],
    )

    return [
        line.strip()
        for line in output.splitlines()
        if line.strip()
    ]


async def get_diff(
    workspace: Path,
    target_file: str,
) -> str:

    return await asyncio.to_thread(
        _run_git,
        workspace,
        [
            "diff",
            "--",
            target_file,
        ],
    )

#After the function changes, Git tells us exactly what changed.