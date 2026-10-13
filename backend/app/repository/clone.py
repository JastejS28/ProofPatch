import asyncio
import os
import subprocess
from pathlib import Path

from app.core.config import settings


class CloneError(Exception):
    pass


def _clone_repository_sync(
    clone_url: str,
    destination: Path,
) -> None:
    environment = os.environ.copy()

    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["GIT_LFS_SKIP_SMUDGE"] = "1"

    try:
        result = subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--no-tags",
                clone_url,
                str(destination),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
            timeout=settings.git_clone_timeout_seconds,
            check=False,
        )

    except subprocess.TimeoutExpired as exc:
        raise CloneError(
            "Repository clone exceeded the configured timeout."
        ) from exc

    except FileNotFoundError as exc:
        raise CloneError(
            "Git is not installed or is not available on PATH."
        ) from exc

    if result.returncode != 0:
        error_output = result.stderr.strip()

        raise CloneError(
            f"Git clone failed: {error_output}"
        )


async def clone_repository(
    clone_url: str,
    destination: Path,
) -> None:
    await asyncio.to_thread(
        _clone_repository_sync,
        clone_url,
        destination,
    )