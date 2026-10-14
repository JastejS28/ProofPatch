import traceback
from uuid import UUID

from app.db.session import (
    AsyncSessionLocal,
)
from app.domain.run_status import (
    RunStatus,
)
from app.services.run_service import (
    archive_successful_attempt,
    fail_run,
    get_run,
    save_verification_result,
    transition_run,
)
from app.verification.verifier import (
    verify_run_evidence,
)
from app.workers.retry_worker import (
    handle_candidate_failure,
)


async def run_verification_workflow(
    run_id: UUID,
) -> None:

    retry_reason: str | None = None
    review_ready = False

    try:

        async with AsyncSessionLocal() as db:

            # -------------------------
            # 1. Load run
            # -------------------------

            run = await get_run(
                db=db,
                run_id=run_id,
            )

            if run is None:
                return

            # -------------------------
            # 2. Enter VERIFYING
            # -------------------------

            await transition_run(
                db=db,
                run_id=run_id,
                status=(
                    RunStatus.VERIFYING
                ),
                message=(
                    "Deterministic "
                    "verification started."
                ),
            )

            # -------------------------
            # 3. Reload state
            # -------------------------

            run = await get_run(
                db=db,
                run_id=run_id,
            )

            if run is None:
                return

            state = dict(
                run.state_json
            )

            # -------------------------
            # 4. Deterministic verifier
            # -------------------------

            verification = (
                verify_run_evidence(
                    state
                )
            )

            verification_data = {
                "passed":
                    verification.passed,

                "policy_passed":
                    verification
                    .policy_passed,

                "correctness_passed":
                    verification
                    .correctness_passed,

                "performance_passed":
                    verification
                    .performance_passed,

                "reasons":
                    verification.reasons,
            }

            # -------------------------
            # 5. Save evidence
            # -------------------------

            await save_verification_result(
                db=db,
                run_id=run_id,
                result=(
                    verification_data
                ),
            )

            # -------------------------
            # 6. Verification passed
            # -------------------------

            if verification.passed:

                await archive_successful_attempt(
                    db=db,
                    run_id=run_id,
                )

                await transition_run(
                    db=db,
                    run_id=run_id,
                    status=(
                        RunStatus.REVIEWING
                    ),
                    message=(
                        "Candidate passed "
                        "deterministic "
                        "verification."
                    ),
                )

                review_ready = True

            # -------------------------
            # 7. Verification failed
            # -------------------------

            else:

                retry_reason = (
                    "; ".join(
                        verification.reasons
                    )
                    or
                    (
                        "Candidate failed "
                        "deterministic "
                        "verification."
                    )
                )

        # ==================================
        # DB session closed here
        # ==================================

        # -------------------------
        # 8. Success → Reviewer
        # -------------------------

        if review_ready:

            # Local import avoids unnecessary
            # worker-level circular imports.
            from app.workers.reviewer_worker import (
                run_reviewer_workflow,
            )

            await run_reviewer_workflow(
                run_id
            )

            return

        # -------------------------
        # 9. Failure → retry handler
        # -------------------------

        if retry_reason is not None:

            await handle_candidate_failure(
                run_id=run_id,
                failure_stage=(
                    "VERIFICATION"
                ),
                reason=(
                    retry_reason
                ),
            )

    except Exception as exc:

        traceback.print_exc()

        async with AsyncSessionLocal() as db:

            await fail_run(
                db=db,
                run_id=run_id,
                message=(
                    "Unexpected verifier "
                    "workflow error: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )