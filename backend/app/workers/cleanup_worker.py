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

    try:

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

        cleaned = (
            await asyncio.to_thread(
                cleanup_run_workspace,
                run_id,
            )
        )

        async with (
            AsyncSessionLocal()
        ) as db:

            await save_workspace_cleanup(
                db=db,
                run_id=run_id,
                cleaned=cleaned,
            )

    except WorkspaceCleanupError as exc:

        print(
            "[WORKSPACE CLEANUP] "
            f"{run_id}: {exc}"
        )

    except Exception:

        traceback.print_exc()