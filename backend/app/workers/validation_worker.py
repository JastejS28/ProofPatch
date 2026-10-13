import traceback
from pathlib import Path
from uuid import UUID

from app.db.session import (
    AsyncSessionLocal,
)
from app.workers.benchmark_worker import (
    run_benchmark_workflow,
)
from app.domain.run_status import (
    RunStatus,
)
from app.sandbox.differential import (
    DifferentialTestError,
    run_differential_tests,
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
    save_differential_validation_result,
    save_validation_result,
    transition_run,
)


async def run_validation_workflow(
    run_id: UUID,
) -> None:

    snapshots = None

    async with AsyncSessionLocal() as db:

        try:
            # 1. Load run
            run = await get_run(
                db=db,
                run_id=run_id,
            )

            if run is None:
                return

            # 2. Read current state
            state = dict(
                run.state_json
            )

            changes = state.get(
                "changes",
                {},
            )

            # 3. Candidate patch must exist
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

            # 4. Candidate must have passed
            #    static policy first
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

            # 5. Enter VALIDATING stage
            await transition_run(
                db=db,
                run_id=run_id,
                status=RunStatus.VALIDATING,
                message=(
                    "Docker correctness "
                    "validation started."
                ),
            )

            # 6. Get workspace and analysis info
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

            # 7. Create isolated baseline and
            #    candidate snapshots BEFORE
            #    choosing validation strategy
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

            # ==================================
            # PATH A:
            # EXISTING REPOSITORY TESTS
            # ==================================

            if test_files:

                result = (
                    await run_existing_tests(
                        baseline_workspace=(
                            snapshots.baseline
                        ),
                        candidate_workspace=(
                            snapshots.candidate
                        ),
                        test_files=(
                            test_files
                        ),
                    )
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

                # Persist correctness evidence
                await save_validation_result(
                    db=db,
                    run_id=run_id,
                    iteration=1,
                    baseline_result=(
                        baseline_data
                    ),
                    candidate_result=(
                        candidate_data
                    ),
                )

                # Baseline itself must be healthy
                if not result.baseline_passed:
                    await fail_run(
                        db=db,
                        run_id=run_id,
                        message=(
                            "Baseline relevant "
                            "tests did not pass."
                        ),
                    )
                    return

                # Candidate must preserve tests
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

            # ==================================
            # PATH B:
            # NO TESTS → HYPOTHESIS FALLBACK
            # ==================================

            else:

                differential = (
                    await run_differential_tests(
                        baseline_workspace=(
                            snapshots.baseline
                        ),
                        candidate_workspace=(
                            snapshots.candidate
                        ),
                        target_file=(
                            run.target_file
                        ),
                        target_function=(
                            run.target_function
                        ),
                        source=(
                            changes[
                                "original_function"
                            ]
                        ),
                    )
                )

                differential_data = {
                    "exit_code":
                        differential
                        .result
                        .exit_code,

                    "stdout":
                        differential
                        .result
                        .stdout,

                    "stderr":
                        differential
                        .result
                        .stderr,

                    "duration_ms":
                        differential
                        .result
                        .duration_ms,

                    "timed_out":
                        differential
                        .result
                        .timed_out,
                }

                # Persist generated-test evidence
                await (
                    save_differential_validation_result(
                        db=db,
                        run_id=run_id,
                        iteration=1,
                        result=(
                            differential_data
                        ),
                    )
                )

                if not differential.passed:
                    await fail_run(
                        db=db,
                        run_id=run_id,
                        message=(
                            "Candidate failed "
                            "Hypothesis differential "
                            "testing."
                        ),
                    )
                    return

                await run_benchmark_workflow(
          run_id
             )

        except DifferentialTestError as exc:

            await fail_run(
                db=db,
                run_id=run_id,
                message=(
                    "Differential testing could "
                    "not be constructed: "
                    f"{exc}"
                ),
            )

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