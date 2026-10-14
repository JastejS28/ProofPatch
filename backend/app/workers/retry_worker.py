from pathlib import Path
from uuid import UUID

from app.core.config import (
    settings,
)
from app.db.session import (
    AsyncSessionLocal,
)
from app.domain.run_status import (
    RunStatus,
)
from app.repository.patcher import (
    restore_original_function,
)
from app.services.run_service import (
    archive_failed_attempt,
    get_run,
    transition_run,
)


async def handle_candidate_failure(
    run_id: UUID,
    failure_stage: str,
    reason: str,
) -> None:

    should_retry = False
    should_cleanup = False

    async with (
        AsyncSessionLocal()
    ) as db:

        # =================================
        # 1. Load run
        # =================================

        run = await get_run(
            db=db,
            run_id=run_id,
        )

        if run is None:
            return

        state = dict(
            run.state_json
        )

        iteration = int(
            state.get(
                "iteration_count",
                0,
            )
        )

        changes = dict(
            state.get(
                "changes",
                {},
            )
        )

        # =================================
        # 2. Archive rejected attempt
        # =================================

        await archive_failed_attempt(
            db=db,
            run_id=run_id,
            failure_stage=(
                failure_stage
            ),
            reason=reason,
        )

        # =================================
        # 3. Maximum attempts exhausted
        # =================================

        if (
            iteration
            >= settings
            .max_coder_attempts
        ):

            await transition_run(
                db=db,
                run_id=run_id,
                status=(
                    RunStatus.UNVERIFIED
                ),
                message=(
                    "Candidate did not satisfy "
                    "verification requirements "
                    "after the maximum number "
                    "of Coder attempts."
                ),
            )

            should_cleanup = True

        # =================================
        # 4. Retry still available
        # =================================

        else:

            original_function = (
                changes.get(
                    "original_function"
                )
            )

            # -----------------------------
            # Cannot restore baseline
            # -----------------------------

            if not original_function:

                await transition_run(
                    db=db,
                    run_id=run_id,
                    status=(
                        RunStatus.UNVERIFIED
                    ),
                    message=(
                        "Retry could not continue "
                        "because the original "
                        "target function was "
                        "unavailable."
                    ),
                )

                should_cleanup = True

            # -----------------------------
            # Restore baseline and retry
            # -----------------------------

            else:

                workspace = Path(
                    state[
                        "workspace_ref"
                    ]
                )

                restore_original_function(
                    workspace=workspace,
                    target_file=(
                        run.target_file
                    ),
                    target_function=(
                        run.target_function
                    ),
                    original_function=(
                        original_function
                    ),
                )

                await transition_run(
                    db=db,
                    run_id=run_id,
                    status=(
                        RunStatus.MODIFYING
                    ),
                    message=(
                        f"Coder attempt "
                        f"{iteration} was rejected. "
                        "Original function restored "
                        "for retry."
                    ),
                )

                should_retry = True

    # =====================================
    # DB session closed here
    # =====================================

    # =====================================
    # 5. Terminal UNVERIFIED cleanup
    # =====================================

    if should_cleanup:

        # Local import avoids unnecessary
        # worker-level circular imports.
        from app.workers.cleanup_worker import (
            cleanup_run_workflow,
        )

        await cleanup_run_workflow(
            run_id
        )

        return

    # =====================================
    # 6. Start next Coder attempt
    # =====================================

    if should_retry:

        # Local import prevents:
        #
        # coder_worker
        # → retry_worker
        # → coder_worker
        #
        # circular import.
        from app.workers.coder_worker import (
            run_coder_workflow,
        )

        await run_coder_workflow(
            run_id
        )