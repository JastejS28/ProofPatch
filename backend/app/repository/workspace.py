from pathlib import Path
from uuid import UUID

from app.core.config import (
    ROOT_DIR,
    settings,
)


def get_workspace_root() -> Path:
    configured_root = settings.workspace_root

    if configured_root.is_absolute():
        root = configured_root
    else:
        root = ROOT_DIR / configured_root

    root = root.resolve()

    root.mkdir(
        parents=True,
        exist_ok=True,
    )

    return root


def get_run_workspace(
    run_id: UUID,
) -> Path:
    return (
        get_workspace_root()
        / str(run_id)
    )


def prepare_run_workspace(
    run_id: UUID,
) -> Path:
    workspace = get_run_workspace(
        run_id
    )

    if workspace.exists():
        raise RuntimeError(
            f"Workspace already exists "
            f"for run {run_id}."
        )

    return workspace