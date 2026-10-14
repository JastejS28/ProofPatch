import shutil
from pathlib import Path
from uuid import UUID

from app.core.config import (
    ROOT_DIR,
    settings,
)


class WorkspaceCleanupError(
    Exception
):
    pass


def get_workspace_root() -> Path:

    configured_root = (
        settings.workspace_root
    )

    if configured_root.is_absolute():
        root = configured_root

    else:
        root = (
            ROOT_DIR
            / configured_root
        )

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

    workspace = (
        get_run_workspace(
            run_id
        )
    )

    if workspace.exists():

        raise RuntimeError(
            "Workspace already exists "
            f"for run {run_id}."
        )

    return workspace


def cleanup_run_workspace(
    run_id: UUID,
) -> bool:

    workspace_root = (
        get_workspace_root()
    )

    workspace = (
        get_run_workspace(
            run_id
        ).resolve()
    )

    # ---------------------------------
    # Safety:
    # workspace must remain underneath
    # configured workspace root.
    # ---------------------------------

    try:

        workspace.relative_to(
            workspace_root
        )

    except ValueError as exc:

        raise WorkspaceCleanupError(
            "Run workspace escaped "
            "the configured workspace root."
        ) from exc

    # Already deleted is fine.
    if not workspace.exists():
        return False

    try:

        shutil.rmtree(
            workspace
        )

    except OSError as exc:

        raise WorkspaceCleanupError(
            "Could not remove run "
            f"workspace: {exc}"
        ) from exc

    return True