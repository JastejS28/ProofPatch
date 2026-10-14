import asyncio
import traceback
from uuid import UUID

from app.db.session import (
    AsyncSessionLocal,
)
from app.repository.workspace import (
    WorkspaceCleanupError,
    cleanup_run_workspace,
)
from app.services.run_service import (
    get_run,
    save_workspace_cleanup,
)


TERMINAL_STATUSES = {
    "COMPLETED",
    "FAILED",
    "UNVERIFIED",
    "CANCELLED",
}


async def cleanup_run_workflow(
    run_id: UUID,
) -> None:
    """
    Delete the local workspace for a run
    after it reaches a terminal state.

    Cleanup is housekeeping only.

    A cleanup failure must never change
    the actual outcome of the run.
    """

    try:

        # ---------------------------------
        # 1. Verify that the run exists and
        #    is actually terminal.
        # ---------------------------------

        async with (
            AsyncSessionLocal()
        ) as db:

            run = await get_run(
                db=db,
                run_id=run_id,
            )

            if run is None:
                return

            if (
                run.status
                not in TERMINAL_STATUSES
            ):
                return

        # ---------------------------------
        # 2. Delete workspace outside the
        #    DB session.
        #
        # shutil.rmtree is blocking, so run
        # it in a thread.
        # ---------------------------------

        cleaned = (
            await asyncio.to_thread(
                cleanup_run_workspace,
                run_id,
            )
        )

        # ---------------------------------
        # 3. Persist cleanup evidence.
        # ---------------------------------

        async with (
            AsyncSessionLocal()
        ) as db:

            await save_workspace_cleanup(
                db=db,
                run_id=run_id,
                cleaned=cleaned,
            )

    except WorkspaceCleanupError as exc:

        # Cleanup failure must NOT convert
        # COMPLETED / FAILED / UNVERIFIED /
        # CANCELLED into another run status.
        print(
            "[WORKSPACE CLEANUP] "
            f"{run_id}: {exc}"
        )

    except Exception:

        # Again, cleanup is secondary.
        # Preserve the original run outcome.
        traceback.print_exc()