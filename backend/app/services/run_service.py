import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.run_status import RunStatus
from app.models.approval import Approval
from app.models.benchmark import Benchmark
from app.models.hypothesis import Hypothesis
from app.models.run import Run
from app.models.run_event import RunEvent
from app.models.validation import Validation
from app.schemas.run import RunCreate


def build_initial_state(
    run_id: UUID,
    payload: RunCreate,
) -> dict:
    return {
        "run_id": str(run_id),
        "repo_url": str(payload.repo_url),
        "target_file": payload.target_file,
        "target_function": payload.target_function,
        "problem_description": (
            payload.problem_description
        ),

        "status": RunStatus.QUEUED.value,
        "current_step": RunStatus.QUEUED.value,

        "workspace_ref": "",

        "purity_check": {},
        "repository_summary": {},
        "hypotheses": [],

        "selected_hypothesis_id": None,

        # Coder retry state
        "iteration_count": 0,
        "attempt_history": [],
        "retry_feedback": None,

        # Current attempt evidence
        "changes": {},
        "validation": {},
        "benchmark": {},
        "verification": {},

        "review": {},
        "approvals": {},
        "pr": {},

        "budget": {
            "llm_calls": 0,
            "elapsed_sec": 0,
            "cost_usd": 0.0,
        },

        "errors": [],
    }


async def create_run(
    db: AsyncSession,
    payload: RunCreate,
) -> Run:

    run_id = uuid.uuid4()

    state = build_initial_state(
        run_id=run_id,
        payload=payload,
    )

    run = Run(
        id=run_id,
        repo_url=str(
            payload.repo_url
        ),
        target_file=(
            payload.target_file
        ),
        target_function=(
            payload.target_function
        ),
        problem_description=(
            payload.problem_description
        ),
        status=(
            RunStatus.QUEUED.value
        ),
        current_step=(
            RunStatus.QUEUED.value
        ),
        state_json=state,
    )

    event = RunEvent(
        run_id=run_id,
        event_type=(
            RunStatus.QUEUED.value
        ),
        payload_json={
            "message": "Run created",
        },
    )

    db.add(run)
    db.add(event)

    await db.commit()
    await db.refresh(run)

    return run


async def get_run(
    db: AsyncSession,
    run_id: UUID,
) -> Run | None:

    result = await db.execute(
        select(Run).where(
            Run.id == run_id
        )
    )

    return (
        result.scalar_one_or_none()
    )


async def transition_run(
    db: AsyncSession,
    run_id: UUID,
    status: RunStatus,
    message: str,
) -> Run | None:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        return None

    run.status = status.value
    run.current_step = (
        status.value
    )

    state = dict(
        run.state_json
    )

    state["status"] = (
        status.value
    )

    state["current_step"] = (
        status.value
    )

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type=status.value,
        payload_json={
            "message": message,
        },
    )

    db.add(event)

    await db.commit()
    await db.refresh(run)

    return run


async def list_run_events(
    db: AsyncSession,
    run_id: UUID,
) -> list[RunEvent]:

    result = await db.execute(
        select(RunEvent)
        .where(
            RunEvent.run_id
            == run_id
        )
        .order_by(
            RunEvent.timestamp.asc(),
            RunEvent.id.asc(),
        )
    )

    return list(
        result.scalars().all()
    )


async def save_repository_analysis(
    db: AsyncSession,
    run_id: UUID,
    workspace_ref: str,
    repository_summary: dict,
    purity_check: dict,
) -> Run | None:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        return None

    state = dict(
        run.state_json
    )

    state["workspace_ref"] = (
        workspace_ref
    )

    state["repository_summary"] = (
        repository_summary
    )

    state["purity_check"] = (
        purity_check
    )

    run.state_json = state

    await db.commit()
    await db.refresh(run)

    return run


async def fail_run(
    db: AsyncSession,
    run_id: UUID,
    message: str,
) -> Run | None:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        return None

    run.status = (
        RunStatus.FAILED.value
    )

    run.current_step = (
        RunStatus.FAILED.value
    )

    state = dict(
        run.state_json
    )

    errors = list(
        state.get(
            "errors",
            [],
        )
    )

    errors.append(
        {
            "message": message,
        }
    )

    state["status"] = (
        RunStatus.FAILED.value
    )

    state["current_step"] = (
        RunStatus.FAILED.value
    )

    state["errors"] = errors

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type=(
            RunStatus.FAILED.value
        ),
        payload_json={
            "message": message,
        },
    )

    db.add(event)

    await db.commit()
    await db.refresh(run)

    return run


async def save_hypotheses(
    db: AsyncSession,
    run_id: UUID,
    hypotheses: list[dict],
) -> Run | None:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        return None

    stored_hypotheses: list[
        dict
    ] = []

    for item in hypotheses:

        hypothesis = Hypothesis(
            run_id=run_id,
            summary=(
                item["summary"]
            ),
            mechanism=(
                item["mechanism"]
            ),
            expected_effect=(
                item[
                    "expected_effect"
                ]
            ),
            trade_offs=(
                item["trade_offs"]
            ),
            selected=False,
            status="PROPOSED",
        )

        db.add(hypothesis)

        await db.flush()

        stored_hypotheses.append(
            {
                "id": str(
                    hypothesis.id
                ),

                "summary":
                    hypothesis.summary,

                "mechanism":
                    hypothesis.mechanism,

                "expected_effect":
                    hypothesis
                    .expected_effect,

                "trade_offs":
                    hypothesis
                    .trade_offs,

                "selected":
                    False,

                "status":
                    "PROPOSED",
            }
        )

    run.status = (
        RunStatus
        .WAITING_FOR_CANDIDATE
        .value
    )

    run.current_step = (
        RunStatus
        .WAITING_FOR_CANDIDATE
        .value
    )

    state = dict(
        run.state_json
    )

    state["hypotheses"] = (
        stored_hypotheses
    )

    state["status"] = (
        RunStatus
        .WAITING_FOR_CANDIDATE
        .value
    )

    state["current_step"] = (
        RunStatus
        .WAITING_FOR_CANDIDATE
        .value
    )

    budget = dict(
        state.get(
            "budget",
            {},
        )
    )

    budget["llm_calls"] = (
        budget.get(
            "llm_calls",
            0,
        )
        + 1
    )

    state["budget"] = budget

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type=(
            RunStatus
            .WAITING_FOR_CANDIDATE
            .value
        ),
        payload_json={
            "message": (
                "Optimization hypotheses "
                "generated."
            ),
            "count": len(
                stored_hypotheses
            ),
        },
    )

    db.add(event)

    await db.commit()
    await db.refresh(run)

    return run


async def select_hypothesis(
    db: AsyncSession,
    run_id: UUID,
    hypothesis_id: UUID,
) -> Run:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        raise ValueError(
            "Run not found."
        )

    if (
        run.status
        != RunStatus
        .WAITING_FOR_CANDIDATE
        .value
    ):
        raise ValueError(
            "Run is not waiting for "
            "candidate selection."
        )

    state = dict(
        run.state_json
    )

    if state.get(
        "selected_hypothesis_id"
    ):
        raise ValueError(
            "A candidate hypothesis "
            "has already been selected."
        )

    result = await db.execute(
        select(Hypothesis).where(
            Hypothesis.id
            == hypothesis_id,

            Hypothesis.run_id
            == run_id,
        )
    )

    selected_hypothesis = (
        result.scalar_one_or_none()
    )

    if selected_hypothesis is None:
        raise ValueError(
            "Hypothesis does not "
            "belong to this run."
        )

    hypotheses_result = (
        await db.execute(
            select(Hypothesis).where(
                Hypothesis.run_id
                == run_id
            )
        )
    )

    hypotheses = list(
        hypotheses_result
        .scalars()
        .all()
    )

    for hypothesis in hypotheses:

        hypothesis.selected = (
            hypothesis.id
            == hypothesis_id
        )

        if hypothesis.selected:
            hypothesis.status = (
                "SELECTED"
            )
        else:
            hypothesis.status = (
                "NOT_SELECTED"
            )

    state[
        "selected_hypothesis_id"
    ] = str(
        hypothesis_id
    )

    state_hypotheses = []

    for hypothesis in hypotheses:

        state_hypotheses.append(
            {
                "id":
                    str(
                        hypothesis.id
                    ),

                "summary":
                    hypothesis.summary,

                "mechanism":
                    hypothesis.mechanism,

                "expected_effect":
                    hypothesis
                    .expected_effect,

                "trade_offs":
                    hypothesis
                    .trade_offs,

                "selected":
                    hypothesis.selected,

                "status":
                    hypothesis.status,
            }
        )

    state["hypotheses"] = (
        state_hypotheses
    )

    approvals = dict(
        state.get(
            "approvals",
            {},
        )
    )

    approvals["candidate"] = {
        "status":
            "APPROVED",

        "hypothesis_id":
            str(
                hypothesis_id
            ),
    }

    state["approvals"] = (
        approvals
    )

    run.state_json = state

    approval = Approval(
        run_id=run_id,
        approval_type="candidate",
        status="APPROVED",
    )

    event = RunEvent(
        run_id=run_id,
        event_type=(
            "CANDIDATE_SELECTED"
        ),
        payload_json={
            "hypothesis_id":
                str(
                    hypothesis_id
                ),

            "message":
                "Candidate hypothesis "
                "selected.",
        },
    )

    db.add(approval)
    db.add(event)

    await db.commit()
    await db.refresh(run)

    return run


async def get_selected_hypothesis(
    db: AsyncSession,
    run_id: UUID,
) -> Hypothesis | None:

    result = await db.execute(
        select(Hypothesis).where(
            Hypothesis.run_id
            == run_id,

            Hypothesis.selected
            .is_(True),
        )
    )

    return (
        result.scalar_one_or_none()
    )


# =====================================================
# CODER ATTEMPTS / RETRIES
# =====================================================


async def begin_coder_attempt(
    db: AsyncSession,
    run_id: UUID,
) -> int:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        raise ValueError(
            "Run not found."
        )

    state = dict(
        run.state_json
    )

    iteration = (
        int(
            state.get(
                "iteration_count",
                0,
            )
        )
        + 1
    )

    state["iteration_count"] = (
        iteration
    )

    # Clear evidence belonging to
    # the previous CURRENT attempt.
    #
    # attempt_history keeps old
    # evidence permanently.
    state["changes"] = {}
    state["validation"] = {}
    state["benchmark"] = {}
    state["verification"] = {}

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type=(
            "CODER_ATTEMPT_STARTED"
        ),
        payload_json={
            "iteration":
                iteration,

            "message":
                (
                    f"Coder attempt "
                    f"{iteration} started."
                ),
        },
    )

    db.add(event)

    await db.commit()
    await db.refresh(run)

    return iteration


async def archive_failed_attempt(
    db: AsyncSession,
    run_id: UUID,
    failure_stage: str,
    reason: str,
) -> Run | None:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        return None

    state = dict(
        run.state_json
    )

    iteration = int(
        state.get(
            "iteration_count",
            0,
        )
    )

    history = list(
        state.get(
            "attempt_history",
            [],
        )
    )

    changes = dict(
        state.get(
            "changes",
            {},
        )
    )

    validation = dict(
        state.get(
            "validation",
            {},
        )
    )

    benchmark = dict(
        state.get(
            "benchmark",
            {},
        )
    )

    verification = dict(
        state.get(
            "verification",
            {},
        )
    )

    history.append(
        {
            "iteration":
                iteration,

            "outcome":
                "REJECTED",

            "failure_stage":
                failure_stage,

            "reason":
                reason,

            "changes":
                changes,

            "validation":
                validation,

            "benchmark":
                benchmark,

            "verification":
                verification,
        }
    )

    state["attempt_history"] = (
        history
    )

    # This survives begin_coder_attempt()
    # and is included in retry prompt.
    state["retry_feedback"] = {
        "previous_iteration":
            iteration,

        "failure_stage":
            failure_stage,

        "reason":
            reason,

        "previous_changes":
            changes,

        "validation":
            validation,

        "benchmark":
            benchmark,

        "verification":
            verification,
    }

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type=(
            "CODER_ATTEMPT_REJECTED"
        ),
        payload_json={
            "iteration":
                iteration,

            "failure_stage":
                failure_stage,

            "reason":
                reason,
        },
    )

    db.add(event)

    await db.commit()
    await db.refresh(run)

    return run


async def archive_successful_attempt(
    db: AsyncSession,
    run_id: UUID,
) -> Run | None:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        return None

    state = dict(
        run.state_json
    )

    iteration = int(
        state.get(
            "iteration_count",
            0,
        )
    )

    history = list(
        state.get(
            "attempt_history",
            [],
        )
    )

    history.append(
        {
            "iteration":
                iteration,

            "outcome":
                "VERIFIED",

            "failure_stage":
                None,

            "reason":
                None,

            "changes":
                dict(
                    state.get(
                        "changes",
                        {},
                    )
                ),

            "validation":
                dict(
                    state.get(
                        "validation",
                        {},
                    )
                ),

            "benchmark":
                dict(
                    state.get(
                        "benchmark",
                        {},
                    )
                ),

            "verification":
                dict(
                    state.get(
                        "verification",
                        {},
                    )
                ),
        }
    )

    state["attempt_history"] = (
        history
    )

    # No more retry information needed.
    state["retry_feedback"] = None

    run.state_json = state

    await db.commit()
    await db.refresh(run)

    return run


# =====================================================
# PATCH EVIDENCE
# =====================================================


async def save_candidate_change(
    db: AsyncSession,
    run_id: UUID,
    selected_hypothesis_id: UUID,
    original_function: str,
    candidate_function: str,
    diff: str,
    policy_result: dict,
    change_summary: str,
    expected_mechanism: str,
) -> Run | None:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        return None

    state = dict(
        run.state_json
    )

    iteration = int(
        state.get(
            "iteration_count",
            0,
        )
    )

    if iteration <= 0:
        raise ValueError(
            "Coder attempt has not "
            "been started."
        )

    state["changes"] = {
        "iteration":
            iteration,

        "selected_hypothesis_id":
            str(
                selected_hypothesis_id
            ),

        "original_function":
            original_function,

        "candidate_function":
            candidate_function,

        "diff":
            diff,

        "change_summary":
            change_summary,

        "expected_mechanism":
            expected_mechanism,

        "policy":
            policy_result,
    }

    budget = dict(
        state.get(
            "budget",
            {},
        )
    )

    budget["llm_calls"] = (
        budget.get(
            "llm_calls",
            0,
        )
        + 1
    )

    state["budget"] = budget

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type=(
            "PATCH_PROPOSED"
        ),
        payload_json={
            "message":
                "Coder produced a "
                "candidate patch.",

            "iteration":
                iteration,

            "policy_passed":
                policy_result[
                    "passed"
                ],
        },
    )

    db.add(event)

    await db.commit()
    await db.refresh(run)

    return run


# =====================================================
# CORRECTNESS VALIDATION
# =====================================================


async def save_validation_result(
    db: AsyncSession,
    run_id: UUID,
    iteration: int,
    baseline_result: dict,
    candidate_result: dict,
) -> Run | None:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        return None

    baseline_passed = (
        not baseline_result[
            "timed_out"
        ]
        and baseline_result[
            "exit_code"
        ] == 0
    )

    candidate_passed = (
        not candidate_result[
            "timed_out"
        ]
        and candidate_result[
            "exit_code"
        ] == 0
    )

    correctness_passed = (
        baseline_passed
        and candidate_passed
    )

    baseline_row = Validation(
        run_id=run_id,
        iteration=iteration,
        stage="baseline_tests",
        status=(
            "PASS"
            if baseline_passed
            else "FAIL"
        ),
        stdout_ref=(
            baseline_result[
                "stdout"
            ][-8000:]
        ),
        duration_ms=(
            baseline_result[
                "duration_ms"
            ]
        ),
    )

    candidate_row = Validation(
        run_id=run_id,
        iteration=iteration,
        stage="candidate_tests",
        status=(
            "PASS"
            if candidate_passed
            else "FAIL"
        ),
        stdout_ref=(
            candidate_result[
                "stdout"
            ][-8000:]
        ),
        duration_ms=(
            candidate_result[
                "duration_ms"
            ]
        ),
    )

    db.add(baseline_row)
    db.add(candidate_row)

    state = dict(
        run.state_json
    )

    state["validation"] = {
        "iteration":
            iteration,

        "strategy":
            "existing_tests",

        "baseline": {
            "passed":
                baseline_passed,

            **baseline_result,
        },

        "candidate": {
            "passed":
                candidate_passed,

            **candidate_result,
        },

        "correctness_passed":
            correctness_passed,
    }

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type=(
            "VALIDATION_COMPLETED"
        ),
        payload_json={
            "iteration":
                iteration,

            "correctness_passed":
                correctness_passed,

            "baseline_passed":
                baseline_passed,

            "candidate_passed":
                candidate_passed,
        },
    )

    db.add(event)

    await db.commit()
    await db.refresh(run)

    return run


async def save_differential_validation_result(
    db: AsyncSession,
    run_id: UUID,
    iteration: int,
    result: dict,
) -> Run | None:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        return None

    passed = (
        not result[
            "timed_out"
        ]
        and result[
            "exit_code"
        ] == 0
    )

    validation_row = Validation(
        run_id=run_id,
        iteration=iteration,
        stage="differential_tests",
        status=(
            "PASS"
            if passed
            else "FAIL"
        ),
        stdout_ref=(
            result[
                "stdout"
            ][-8000:]
        ),
        duration_ms=(
            result[
                "duration_ms"
            ]
        ),
    )

    db.add(
        validation_row
    )

    state = dict(
        run.state_json
    )

    state["validation"] = {
        "iteration":
            iteration,

        "strategy":
            "hypothesis_differential",

        "differential": {
            "passed":
                passed,

            **result,
        },

        "correctness_passed":
            passed,
    }

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type=(
            "VALIDATION_COMPLETED"
        ),
        payload_json={
            "iteration":
                iteration,

            "strategy":
                "hypothesis_differential",

            "correctness_passed":
                passed,
        },
    )

    db.add(event)

    await db.commit()
    await db.refresh(run)

    return run


# =====================================================
# BENCHMARKING
# =====================================================


async def save_benchmark_result(
    db: AsyncSession,
    run_id: UUID,
    iteration: int,
    baseline_result: dict,
    candidate_result: dict,
    threshold_percent: float,
) -> Run | None:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        return None

    baseline_median = float(
        baseline_result[
            "median_seconds"
        ]
    )

    candidate_median = float(
        candidate_result[
            "median_seconds"
        ]
    )

    if baseline_median <= 0:
        raise ValueError(
            "Baseline benchmark median "
            "must be greater than zero."
        )

    improvement_percent = (
        (
            baseline_median
            - candidate_median
        )
        / baseline_median
        * 100.0
    )

    passed = (
        improvement_percent
        >= threshold_percent
    )

    benchmark_row = Benchmark(
        run_id=run_id,
        iteration=iteration,
        baseline_median_seconds=(
            baseline_median
        ),
        candidate_median_seconds=(
            candidate_median
        ),
        improvement_percent=(
            improvement_percent
        ),
        threshold_percent=(
            threshold_percent
        ),
        passed=passed,
    )

    db.add(
        benchmark_row
    )

    state = dict(
        run.state_json
    )

    state["benchmark"] = {
        "iteration":
            iteration,

        "baseline": {
            **baseline_result,
        },

        "candidate": {
            **candidate_result,
        },

        "improvement_percent":
            improvement_percent,

        "threshold_percent":
            threshold_percent,

        "passed":
            passed,
    }

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type=(
            "BENCHMARK_COMPLETED"
        ),
        payload_json={
            "iteration":
                iteration,

            "baseline_median_seconds":
                baseline_median,

            "candidate_median_seconds":
                candidate_median,

            "improvement_percent":
                improvement_percent,

            "threshold_percent":
                threshold_percent,

            "passed":
                passed,
        },
    )

    db.add(event)

    await db.commit()
    await db.refresh(run)

    return run


# =====================================================
# VERIFICATION
# =====================================================


async def save_verification_result(
    db: AsyncSession,
    run_id: UUID,
    result: dict,
) -> Run | None:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        return None

    state = dict(
        run.state_json
    )

    iteration = int(
        state.get(
            "iteration_count",
            0,
        )
    )

    state["verification"] = {
        "iteration":
            iteration,

        "passed":
            result[
                "passed"
            ],

        "policy_passed":
            result[
                "policy_passed"
            ],

        "correctness_passed":
            result[
                "correctness_passed"
            ],

        "performance_passed":
            result[
                "performance_passed"
            ],

        "reasons":
            result[
                "reasons"
            ],
    }

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type=(
            "VERIFICATION_COMPLETED"
        ),
        payload_json={
            "iteration":
                iteration,

            "passed":
                result[
                    "passed"
                ],

            "policy_passed":
                result[
                    "policy_passed"
                ],

            "correctness_passed":
                result[
                    "correctness_passed"
                ],

            "performance_passed":
                result[
                    "performance_passed"
                ],

            "reasons":
                result[
                    "reasons"
                ],
        },
    )

    db.add(event)

    await db.commit()
    await db.refresh(run)

    return run



async def save_review_result(
    db: AsyncSession,
    run_id: UUID,
    review: dict,
) -> Run | None:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        return None

    state = dict(
        run.state_json
    )

    state["review"] = {
        **review,
    }

    state["status"] = (
        RunStatus
        .WAITING_FOR_PR_APPROVAL
        .value
    )

    state["current_step"] = (
        RunStatus
        .WAITING_FOR_PR_APPROVAL
        .value
    )

    run.status = (
        RunStatus
        .WAITING_FOR_PR_APPROVAL
        .value
    )

    run.current_step = (
        RunStatus
        .WAITING_FOR_PR_APPROVAL
        .value
    )

    event = RunEvent(
        run_id=run_id,
        event_type=(
            RunStatus
            .WAITING_FOR_PR_APPROVAL
            .value
        ),
        payload_json={
            "message":
                "Reviewer completed. "
                "Waiting for human PR approval."
        },
    )

    db.add(
        event
    )

    await db.commit()
    await db.refresh(
        run
    )

    return run

async def approve_pr_creation(
    db: AsyncSession,
    run_id: UUID,
) -> Run:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        raise ValueError(
            "Run not found."
        )

    if (
        run.status
        != RunStatus
        .WAITING_FOR_PR_APPROVAL
        .value
    ):
        raise ValueError(
            "Run is not waiting for "
            "PR approval."
        )

    state = dict(
    run.state_json
)

    existing_pr = dict(
    state.get(
        "pr",
        {},
    )
)

    if existing_pr.get(
    "url"
):
     raise ValueError(
        "A pull request already exists "
        "for this run."
    )

    approvals = dict(
        state.get(
            "approvals",
            {},
        )
    )

    approvals["pr"] = {
        "status": "APPROVED",
    }

    state["approvals"] = approvals

    state["status"] = (
        RunStatus.CREATING_PR.value
    )

    state["current_step"] = (
        RunStatus.CREATING_PR.value
    )

    run.status = (
        RunStatus.CREATING_PR.value
    )

    run.current_step = (
        RunStatus.CREATING_PR.value
    )

    # IMPORTANT:
    # reassign the full JSON object so
    # SQLAlchemy definitely persists it.
    run.state_json = state

    approval = Approval(
        run_id=run_id,
        approval_type="pr",
        status="APPROVED",
    )

    event = RunEvent(
        run_id=run_id,
        event_type=(
            RunStatus.CREATING_PR.value
        ),
        payload_json={
            "message":
                "Human approved PR creation."
        },
    )

    db.add(approval)
    db.add(event)

    await db.commit()
    await db.refresh(run)

    return run

async def reject_pr_creation(
    db: AsyncSession,
    run_id: UUID,
) -> Run:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        raise ValueError(
            "Run not found."
        )

    if (
        run.status
        != RunStatus
        .WAITING_FOR_PR_APPROVAL
        .value
    ):
        raise ValueError(
            "Run is not waiting for "
            "PR approval."
        )

    state = dict(
        run.state_json
    )

    approvals = dict(
        state.get(
            "approvals",
            {},
        )
    )

    approvals["pr"] = {
        "status":
            "REJECTED",
    }

    state["approvals"] = (
        approvals
    )

    state["status"] = (
        RunStatus.CANCELLED.value
    )

    state["current_step"] = (
        RunStatus.CANCELLED.value
    )

    run.status = (
        RunStatus.CANCELLED.value
    )

    run.current_step = (
        RunStatus.CANCELLED.value
    )

    approval = Approval(
        run_id=run_id,
        approval_type="pr",
        status="REJECTED",
    )

    event = RunEvent(
        run_id=run_id,
        event_type=(
            RunStatus.CANCELLED.value
        ),
        payload_json={
            "message":
                "Human rejected PR creation."
        },
    )

    db.add(
        approval
    )

    db.add(
        event
    )

    await db.commit()
    await db.refresh(
        run
    )

    return run


async def save_pr_result(
    db: AsyncSession,
    run_id: UUID,
    pr_data: dict,
) -> Run | None:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        return None

    state = dict(
        run.state_json
    )

    state["pr"] = {
        **pr_data,
    }

    state["status"] = (
        RunStatus.COMPLETED.value
    )

    state["current_step"] = (
        RunStatus.COMPLETED.value
    )

    run.status = (
        RunStatus.COMPLETED.value
    )

    run.current_step = (
        RunStatus.COMPLETED.value
    )

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type=(
            RunStatus.COMPLETED.value
        ),
        payload_json={
            "message":
                "GitHub pull request "
                "created successfully.",

            "pr_number":
                pr_data[
                    "number"
                ],

            "pr_url":
                pr_data[
                    "url"
                ],
        },
    )

    db.add(
        event
    )

    await db.commit()
    await db.refresh(
        run
    )

    return run

async def save_pr_progress(
    db: AsyncSession,
    run_id: UUID,
    pr_data: dict,
) -> Run | None:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        return None

    state = dict(
        run.state_json
    )

    current_pr = dict(
        state.get(
            "pr",
            {},
        )
    )

    current_pr.update(
        pr_data
    )

    state["pr"] = (
        current_pr
    )

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type="PR_PROGRESS",
        payload_json={
            **pr_data,
        },
    )

    db.add(
        event
    )

    await db.commit()
    await db.refresh(
        run
    )

    return run

async def mark_pr_attempt_started(
    db: AsyncSession,
    run_id: UUID,
) -> Run | None:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        return None

    state = dict(
        run.state_json
    )

    pr_state = dict(
        state.get(
            "pr",
            {},
        )
    )

    attempt_count = int(
        pr_state.get(
            "attempt_count",
            0,
        )
    ) + 1

    pr_state["status"] = (
        "IN_PROGRESS"
    )

    pr_state["attempt_count"] = (
        attempt_count
    )

    state["pr"] = pr_state

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type=(
            "PR_ATTEMPT_STARTED"
        ),
        payload_json={
            "attempt":
                attempt_count,

            "message":
                "GitHub PR creation "
                "attempt started.",
        },
    )

    db.add(event)

    await db.commit()
    await db.refresh(run)

    return run


async def save_pr_failure(
    db: AsyncSession,
    run_id: UUID,
    message: str,
) -> Run | None:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        return None

    state = dict(
        run.state_json
    )

    pr_state = dict(
        state.get(
            "pr",
            {},
        )
    )

    pr_state["status"] = (
        "FAILED_RETRYABLE"
    )

    pr_state["last_error"] = (
        message
    )

    state["pr"] = pr_state

    # IMPORTANT:
    # We intentionally keep the run in
    # CREATING_PR instead of FAILED.
    state["status"] = (
        RunStatus.CREATING_PR.value
    )

    state["current_step"] = (
        RunStatus.CREATING_PR.value
    )

    run.status = (
        RunStatus.CREATING_PR.value
    )

    run.current_step = (
        RunStatus.CREATING_PR.value
    )

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type=(
            "PR_FAILED_RETRYABLE"
        ),
        payload_json={
            "message":
                message,
        },
    )

    db.add(event)

    await db.commit()
    await db.refresh(run)

    return run


async def prepare_pr_retry(
    db: AsyncSession,
    run_id: UUID,
) -> Run:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        raise ValueError(
            "Run not found."
        )

    if (
        run.status
        != RunStatus
        .CREATING_PR
        .value
    ):
        raise ValueError(
            "Run is not in the "
            "PR creation stage."
        )

    state = dict(
        run.state_json
    )

    pr_state = dict(
        state.get(
            "pr",
            {},
        )
    )

    if (
        pr_state.get(
            "status"
        )
        != "FAILED_RETRYABLE"
    ):
        raise ValueError(
            "PR creation is not "
            "waiting for a retry."
        )

    pr_state["status"] = (
        "RETRYING"
    )

    state["pr"] = pr_state

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type=(
            "PR_RETRY_REQUESTED"
        ),
        payload_json={
            "message":
                "Retry requested for "
                "GitHub PR creation.",
        },
    )

    db.add(event)

    await db.commit()
    await db.refresh(run)

    return run


async def save_workspace_cleanup(
    db: AsyncSession,
    run_id: UUID,
    cleaned: bool,
) -> Run | None:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:
        return None

    state = dict(
        run.state_json
    )

    state["workspace"] = {
        "cleaned": cleaned,
    }

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type=(
            "WORKSPACE_CLEANED"
        ),
        payload_json={
            "cleaned":
                cleaned,
        },
    )

    db.add(event)

    await db.commit()
    await db.refresh(run)

    return run



async def cancel_run(
    db: AsyncSession,
    run_id: UUID,
) -> Run:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:

        raise ValueError(
            "Run not found."
        )

    cancellable_statuses = {
        RunStatus
        .WAITING_FOR_CANDIDATE
        .value,

        RunStatus
        .WAITING_FOR_PR_APPROVAL
        .value,
    }

    state = dict(
        run.state_json
    )

    pr_state = dict(
        state.get(
            "pr",
            {},
        )
    )

    retryable_pr_failure = (
        run.status
        == RunStatus
        .CREATING_PR
        .value
        and pr_state.get(
            "status"
        )
        == "FAILED_RETRYABLE"
    )

    if (
        run.status
        not in cancellable_statuses
        and not retryable_pr_failure
    ):

        raise ValueError(
            "Run cannot be cancelled "
            "at its current stage."
        )

    run.status = (
        RunStatus.CANCELLED.value
    )

    run.current_step = (
        RunStatus.CANCELLED.value
    )

    state["status"] = (
        RunStatus.CANCELLED.value
    )

    state["current_step"] = (
        RunStatus.CANCELLED.value
    )

    state["cancellation"] = {
        "requested": True,
        "completed": True,
    }

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type=(
            RunStatus.CANCELLED.value
        ),
        payload_json={
            "message":
                "Run cancelled by user."
        },
    )

    db.add(event)

    await db.commit()
    await db.refresh(run)

    return run

#THIS IS CONTROLLER(FROM SPRINGBOOT) WHICH SEND DATA INTO SERVICE 