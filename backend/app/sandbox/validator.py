from dataclasses import dataclass
from pathlib import Path


from app.sandbox.runner import (
    SandboxResult,
    run_in_sandbox,
)


@dataclass
class ValidationPair:
    baseline: SandboxResult
    candidate: SandboxResult

    @property
    def baseline_passed(self) -> bool:
        return (
            not self.baseline.timed_out
            and self.baseline.exit_code == 0
        )

    @property
    def candidate_passed(self) -> bool:
        return (
            not self.candidate.timed_out
            and self.candidate.exit_code == 0
        )

    @property
    def correctness_passed(self) -> bool:
        return (
            self.baseline_passed
            and self.candidate_passed
        )


async def run_existing_tests(
    baseline_workspace: Path,
    candidate_workspace: Path,
    test_files: list[str],
) -> ValidationPair:

    command = [
         "python",
    "-m",
    "pytest",
    "-q",
    "-p",
    "no:cacheprovider",
    *[
        Path(path).as_posix()
        for path in test_files
    ],
    ]

    baseline = await run_in_sandbox(
        workspace=baseline_workspace,
        command=command,
    )

    candidate = await run_in_sandbox(
        workspace=candidate_workspace,
        command=command,
    )

    return ValidationPair(
        baseline=baseline,
        candidate=candidate,
    )