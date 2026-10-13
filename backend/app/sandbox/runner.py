import asyncio
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings


class SandboxError(Exception):
    pass


@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool


def _docker_run_sync(
    workspace: Path,
    command: list[str],
) -> SandboxResult:

    workspace = workspace.resolve()

    docker_command = [
       "docker",
    "run",
    "--rm",

    "--network",
    "none",

    "--cpus",
    str(settings.sandbox_cpu_limit),

    "--memory",
    f"{settings.sandbox_memory_mb}m",

    "--pids-limit",
    str(settings.sandbox_pids_limit),

    "--read-only",

    "--cap-drop",
    "ALL",

    "--security-opt",
    "no-new-privileges",

    "--user",
    "65534:65534",

    "--tmpfs",
    "/tmp:rw,noexec,nosuid,size=256m",

    "--mount",
    (
        "type=bind,"
        f"source={workspace},"
        "target=/workspace,"
        "readonly"
    ),

    "--workdir",
    "/workspace",

    settings.sandbox_image,

    *command,
    ]

    started = time.perf_counter()

    try:
        result = subprocess.run(
            docker_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=(
                settings.validation_timeout_seconds
            ),
            check=False,
        )

    except subprocess.TimeoutExpired as exc:

        duration_ms = int(
            (
                time.perf_counter()
                - started
            )
            * 1000
        )

        return SandboxResult(
            exit_code=-1,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            duration_ms=duration_ms,
            timed_out=True,
        )

    except FileNotFoundError as exc:
        raise SandboxError(
            "Docker is not installed or "
            "is not available on PATH."
        ) from exc

    duration_ms = int(
        (
            time.perf_counter()
            - started
        )
        * 1000
    )

    return SandboxResult(
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        duration_ms=duration_ms,
        timed_out=False,
    )


async def run_in_sandbox(
    workspace: Path,
    command: list[str],
) -> SandboxResult:

    return await asyncio.to_thread(
        _docker_run_sync,
        workspace,
        command,
    )