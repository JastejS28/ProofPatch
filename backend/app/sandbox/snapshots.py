import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.repository.patcher import (
    apply_function_replacement,
)


@dataclass
class ValidationSnapshots:
    root: Path
    baseline: Path
    candidate: Path


def _copy_repository(
    source: Path,
    destination: Path,
) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(
            ".git",
            "__pycache__",
            ".pytest_cache",
        ),
    )


def create_validation_snapshots(
    workspace: Path,
    target_file: str,
    target_function: str,
    original_function: str,
) -> ValidationSnapshots:

    root = Path(
        tempfile.mkdtemp(
            prefix="proofpatch-validation-"
        )
    )

    baseline = root / "baseline"
    candidate = root / "candidate"

    _copy_repository(
        workspace,
        baseline,
    )

    _copy_repository(
        workspace,
        candidate,
    )

    apply_function_replacement(
        workspace=baseline,
        target_file=target_file,
        target_function=target_function,
        replacement_source=original_function,
    )

    return ValidationSnapshots(
        root=root,
        baseline=baseline,
        candidate=candidate,
    )


def cleanup_validation_snapshots(
    snapshots: ValidationSnapshots,
) -> None:

    shutil.rmtree(
        snapshots.root,
        ignore_errors=True,
    )