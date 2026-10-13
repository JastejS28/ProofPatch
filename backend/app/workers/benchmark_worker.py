import traceback
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
from app.sandbox.benchmark import (
    BenchmarkError,
    run_target_benchmark,
)
from app.sandbox.snapshots import (
    cleanup_validation_snapshots,
    create_validation_snapshots,
)
from app.services.run_service import (
    fail_run,
    get_run,
    save_benchmark_result,
    transition_run,
)
from app.workers.verifier_worker import (
    run_verification_workflow,
)


async def run_benchmark_workflow(
    run_id: UUID,
) -> None:

    snapshots = None

    benchmark_succeeded = False

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

            # -------------------------
            # 2. Correctness gate
            # -------------------------

            validation = state.get(
                "validation",
                {},
            )

            if not validation.get(
                "correctness_passed",
                False,
            ):

                await fail_run(
                    db=db,
                    run_id=run_id,
                    message=(
                        "Benchmarking cannot "
                        "start because correctness "
                        "validation did not pass."
                    ),
                )

                return

            # -------------------------
            # 3. Load change evidence
            # -------------------------

            changes = state.get(
                "changes",
                {},
            )

            if not changes:

                await fail_run(
                    db=db,
                    run_id=run_id,
                    message=(
                        "Benchmarking could not "
                        "find candidate changes."
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
            # 4. Enter BENCHMARKING
            # -------------------------

            await transition_run(
                db=db,
                run_id=run_id,
                status=(
                    RunStatus.BENCHMARKING
                ),
                message=(
                    "Performance benchmarking "
                    "started."
                ),
            )

            workspace = Path(
                state[
                    "workspace_ref"
                ]
            )

            # -------------------------
            # 5. Fresh snapshots
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

            # -------------------------
            # 6. Baseline benchmark
            # -------------------------

            baseline = (
                await run_target_benchmark(
                    workspace=(
                        snapshots.baseline
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

            # -------------------------
            # 7. Candidate benchmark
            # -------------------------

            candidate = (
                await run_target_benchmark(
                    workspace=(
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

            baseline_data = {
                "median_seconds":
                    baseline
                    .median_seconds,

                "mean_seconds":
                    baseline
                    .mean_seconds,

                "stdev_seconds":
                    baseline
                    .stdev_seconds,

                "values_count":
                    baseline
                    .values_count,

                "duration_ms":
                    baseline
                    .duration_ms,
            }

            candidate_data = {
                "median_seconds":
                    candidate
                    .median_seconds,

                "mean_seconds":
                    candidate
                    .mean_seconds,

                "stdev_seconds":
                    candidate
                    .stdev_seconds,

                "values_count":
                    candidate
                    .values_count,

                "duration_ms":
                    candidate
                    .duration_ms,
            }

            # -------------------------
            # 8. Save benchmark
            # -------------------------

            await save_benchmark_result(
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
                threshold_percent=(
                    settings
                    .performance_threshold_percent
                ),
            )

            benchmark_succeeded = (
                True
            )

    except BenchmarkError as exc:

        async with AsyncSessionLocal() as db:

            await fail_run(
                db=db,
                run_id=run_id,
                message=(
                    "Benchmarking failed: "
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
                    "Unexpected benchmark "
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

    # Start verifier only after
    # benchmark session/snapshots close.
    if benchmark_succeeded:

        await run_verification_workflow(
            run_id
        )