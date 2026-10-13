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


async def run_benchmark_workflow(
    run_id: UUID,
) -> None:

    snapshots = None

    async with AsyncSessionLocal() as db:

        try:
            # Load run
            run = await get_run(
                db=db,
                run_id=run_id,
            )

            if run is None:
                return

            state = dict(
                run.state_json
            )

            # Correctness must have passed first
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
                        "Benchmarking cannot start "
                        "because correctness "
                        "validation did not pass."
                    ),
                )
                return

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
                state["workspace_ref"]
            )

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
            # Baseline benchmark
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
            # Candidate benchmark
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
                    baseline.median_seconds,

                "mean_seconds":
                    baseline.mean_seconds,

                "stdev_seconds":
                    baseline.stdev_seconds,

                "values_count":
                    baseline.values_count,

                "duration_ms":
                    baseline.duration_ms,
            }

            candidate_data = {
                "median_seconds":
                    candidate.median_seconds,

                "mean_seconds":
                    candidate.mean_seconds,

                "stdev_seconds":
                    candidate.stdev_seconds,

                "values_count":
                    candidate.values_count,

                "duration_ms":
                    candidate.duration_ms,
            }

            await save_benchmark_result(
                db=db,
                run_id=run_id,
                iteration=1,
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

            # Next milestone:
            # deterministic verifier

        except BenchmarkError as exc:

            await fail_run(
                db=db,
                run_id=run_id,
                message=(
                    "Benchmarking failed: "
                    f"{exc}"
                ),
            )

        except Exception as exc:

            traceback.print_exc()

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

        finally:

            if snapshots is not None:
                cleanup_validation_snapshots(
                    snapshots
                )