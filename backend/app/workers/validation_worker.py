import traceback
from pathlib import Path
from uuid import UUID

from app.db.session import (
    AsyncSessionLocal,
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
from app.workers.benchmark_worker import (
    run_benchmark_workflow,
)
from app.workers.retry_worker import (
    handle_candidate_failure,
)


async def run_validation_workflow(
    run_id: UUID,
) -> None:

    snapshots = None

    retry_request: (
        tuple[str, str]
        | None
    ) = None

    validation_succeeded = False

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

            state = dict(
                run.state_json
            )

            changes = state.get(
                "changes",
                {},
            )

            # -------------------------
            # 2. Candidate must exist
            # -------------------------

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

            iteration = int(
                changes.get(
                    "iteration",
                    state.get(
                        "iteration_count",
                        1,
                    ),
                )
            )

            # -------------------------
            # 3. Policy must have passed
            # -------------------------

            policy = changes.get(
                "policy",
                {},
            )

            if not policy.get(
                "passed",
                False,
            ):

                retry_request = (
                    "POLICY",
                    (
                        "Candidate entered "
                        "validation without "
                        "passing static policy."
                    ),
                )

            if retry_request is not None:
                pass

            else:
                # -------------------------
                # 4. Enter VALIDATING
                # -------------------------

                await transition_run(
                    db=db,
                    run_id=run_id,
                    status=(
                        RunStatus.VALIDATING
                    ),
                    message=(
                        "Docker correctness "
                        "validation started."
                    ),
                )

                workspace = Path(
                    state[
                        "workspace_ref"
                    ]
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

                # -------------------------
                # 5. Baseline/candidate snapshots
                # -------------------------

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

                # =========================
                # PATH A: existing tests
                # =========================

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
                            result
                            .baseline
                            .exit_code,

                        "stdout":
                            result
                            .baseline
                            .stdout,

                        "stderr":
                            result
                            .baseline
                            .stderr,

                        "duration_ms":
                            result
                            .baseline
                            .duration_ms,

                        "timed_out":
                            result
                            .baseline
                            .timed_out,
                    }

                    candidate_data = {
                        "exit_code":
                            result
                            .candidate
                            .exit_code,

                        "stdout":
                            result
                            .candidate
                            .stdout,

                        "stderr":
                            result
                            .candidate
                            .stderr,

                        "duration_ms":
                            result
                            .candidate
                            .duration_ms,

                        "timed_out":
                            result
                            .candidate
                            .timed_out,
                    }

                    await save_validation_result(
                        db=db,
                        run_id=run_id,
                        iteration=(
                            iteration
                        ),
                        baseline_result=(
                            baseline_data
                        ),
                        candidate_result=(
                            candidate_data
                        ),
                    )

                    # Original project failure
                    # is infrastructure / repo problem,
                    # not candidate problem.
                    if (
                        not result
                        .baseline_passed
                    ):

                        await fail_run(
                            db=db,
                            run_id=run_id,
                            message=(
                                "Baseline relevant "
                                "tests did not pass."
                            ),
                        )

                        return

                    if (
                        not result
                        .candidate_passed
                    ):

                        retry_request = (
                            "CORRECTNESS",
                            (
                                "Candidate failed "
                                "existing repository "
                                "correctness tests."
                            ),
                        )

                    else:
                        validation_succeeded = (
                            True
                        )

                # =========================
                # PATH B: generated tests
                # =========================

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

                    await (
                        save_differential_validation_result(
                            db=db,
                            run_id=run_id,
                            iteration=(
                                iteration
                            ),
                            result=(
                                differential_data
                            ),
                        )
                    )

                    if not differential.passed:

                        retry_request = (
                            "CORRECTNESS",
                            (
                                "Candidate failed "
                                "generated Hypothesis "
                                "differential tests."
                            ),
                        )

                    else:
                        validation_succeeded = (
                            True
                        )

    except DifferentialTestError as exc:

        async with AsyncSessionLocal() as db:

            await fail_run(
                db=db,
                run_id=run_id,
                message=(
                    "Differential testing "
                    "could not be constructed: "
                    f"{exc}"
                ),
            )

        return

    except Exception as exc:

        traceback.print_exc()

        async with AsyncSessionLocal() as db:

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

        return

    finally:

        if snapshots is not None:

            cleanup_validation_snapshots(
                snapshots
            )

    # DB session and validation
    # snapshots are closed here.

    if retry_request is not None:

        failure_stage, reason = (
            retry_request
        )

        await handle_candidate_failure(
            run_id=run_id,
            failure_stage=(
                failure_stage
            ),
            reason=reason,
        )

        return

    if validation_succeeded:

        await run_benchmark_workflow(
            run_id
        )