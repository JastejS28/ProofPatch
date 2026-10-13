import traceback
from pathlib import Path
from uuid import UUID

from app.db.session import (
    AsyncSessionLocal,
)
from app.domain.run_status import (
    RunStatus,
)
from app.sandbox.snapshots import (
    cleanup_validation_snapshots,
    create_validation_snapshots,
)
from app.sandbox.validator import (
    run_existing_tests,
)
from app.services.run_service import (
    fail_run,
    get_run,
    save_validation_result,
    transition_run,
)


async def run_validation_workflow(
    run_id: UUID,
) -> None:

    snapshots = None

    async with AsyncSessionLocal() as db:

        try:
            run = await get_run(
                db=db,
                run_id=run_id,
            )

            if run is None:
                return

            state = dict(
                run.state_json
            )

            changes = state.get(
                "changes",
                {},
            )

            if not changes:
                await fail_run(
                    db=db,
                    run_id=run_id,
                    message=(
                        "No candidate change "
                        "exists for validation."
                    ),
                )
                return

            policy = changes.get(
                "policy",
                {},
            )

            if not policy.get(
                "passed",
                False,
            ):
                await fail_run(
                    db=db,
                    run_id=run_id,
                    message=(
                        "Candidate has not passed "
                        "static policy checks."
                    ),
                )
                return

            await transition_run(
                db=db,
                run_id=run_id,
                status=RunStatus.VALIDATING,
                message=(
                    "Docker correctness "
                    "validation started."
                ),
            )

            workspace = Path(
                state["workspace_ref"]
            )

            repository_summary = (
                state[
                    "repository_summary"
                ]
            )

            test_files = (
                repository_summary.get(
                    "related_test_files",
                    [],
                )
            )

            if not test_files:
                await fail_run(
                    db=db,
                    run_id=run_id,
                    message=(
                        "No relevant existing tests "
                        "were found. Differential "
                        "testing fallback is not "
                        "implemented yet."
                    ),
                )
                return

            snapshots = (
                create_validation_snapshots(
                    workspace=workspace,
                    target_file=(
                        run.target_file
                    ),
                    target_function=(
                        run.target_function
                    ),
                    original_function=(
                        changes[
                            "original_function"
                        ]
                    ),
                )
            )

            result = await run_existing_tests(
                baseline_workspace=(
                    snapshots.baseline
                ),
                candidate_workspace=(
                    snapshots.candidate
                ),
                test_files=test_files,
            )

            baseline_data = {
                "exit_code":
                    result.baseline.exit_code,
                "stdout":
                    result.baseline.stdout,
                "stderr":
                    result.baseline.stderr,
                "duration_ms":
                    result.baseline.duration_ms,
                "timed_out":
                    result.baseline.timed_out,
            }

            candidate_data = {
                "exit_code":
                    result.candidate.exit_code,
                "stdout":
                    result.candidate.stdout,
                "stderr":
                    result.candidate.stderr,
                "duration_ms":
                    result.candidate.duration_ms,
                "timed_out":
                    result.candidate.timed_out,
            }

            await save_validation_result(
                db=db,
                run_id=run_id,
                iteration=1,
                baseline_result=baseline_data,
                candidate_result=candidate_data,
            )

            if not result.baseline_passed:
                await fail_run(
                    db=db,
                    run_id=run_id,
                    message=(
                        "Baseline relevant tests "
                        "did not pass."
                    ),
                )
                return

            if not result.candidate_passed:
                await fail_run(
                    db=db,
                    run_id=run_id,
                    message=(
                        "Candidate failed "
                        "correctness validation."
                    ),
                )
                return

            # Next milestone:
            # BENCHMARKING.

        except Exception as exc:

            traceback.print_exc()

            await fail_run(
                db=db,
                run_id=run_id,
                message=(
                    "Unexpected validation "
                    "workflow error: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )

        finally:
            if snapshots is not None:
                cleanup_validation_snapshots(
                    snapshots
                )