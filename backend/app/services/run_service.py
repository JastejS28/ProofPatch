import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import Approval
from app.models.hypothesis import Hypothesis
from app.domain.run_status import RunStatus
from app.models.run import Run
from app.models.run_event import RunEvent
from app.models.validation import Validation
from app.schemas.run import RunCreate
from app.models.hypothesis import (
    Hypothesis,
)


def build_initial_state(
    run_id: UUID,
    payload: RunCreate,
) -> dict:
    return {
        "run_id": str(run_id),
        "repo_url": str(payload.repo_url),
        "target_file": payload.target_file,
        "target_function": payload.target_function,
        "problem_description": payload.problem_description,

        "status": RunStatus.QUEUED.value,
        "current_step": RunStatus.QUEUED.value,

        "workspace_ref": "",

        "purity_check": {},
        "repository_summary": {},
        "hypotheses": [],

        "selected_hypothesis_id": None,
        "iteration_count": 0,

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
        repo_url=str(payload.repo_url),
        target_file=payload.target_file,
        target_function=payload.target_function,
        problem_description=payload.problem_description,
        status=RunStatus.QUEUED.value,
        current_step=RunStatus.QUEUED.value,
        state_json=state,
    )

    event = RunEvent(
        run_id=run_id,
        event_type=RunStatus.QUEUED.value,
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

    return result.scalar_one_or_none()


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
    run.current_step = status.value

    state = dict(run.state_json)

    state["status"] = status.value
    state["current_step"] = status.value

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
            RunEvent.run_id == run_id
        )
        .order_by(
            RunEvent.timestamp.asc(),
            RunEvent.id.asc(),
        )
    )

    return list(result.scalars().all())


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

    state = dict(run.state_json)

    state["workspace_ref"] = workspace_ref
    state["repository_summary"] = repository_summary
    state["purity_check"] = purity_check

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

    run.status = RunStatus.FAILED.value
    run.current_step = RunStatus.FAILED.value

    state = dict(run.state_json)

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

    state["status"] = RunStatus.FAILED.value
    state["current_step"] = RunStatus.FAILED.value
    state["errors"] = errors

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type=RunStatus.FAILED.value,
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

    stored_hypotheses: list[dict] = []

    for item in hypotheses:
        hypothesis = Hypothesis(
            run_id=run_id,
            summary=item["summary"],
            mechanism=item["mechanism"],
            expected_effect=item[
                "expected_effect"
            ],
            trade_offs=item[
                "trade_offs"
            ],
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
                    hypothesis.expected_effect,
                "trade_offs":
                    hypothesis.trade_offs,
                "selected": False,
                "status": "PROPOSED",
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
            "message":
                "Optimization hypotheses generated.",
            "count":
                len(stored_hypotheses),
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
        != RunStatus.WAITING_FOR_CANDIDATE.value
    ):
        raise ValueError(
            "Run is not waiting for candidate selection."
        )

    result = await db.execute(
        select(Hypothesis).where(
            Hypothesis.id == hypothesis_id,
            Hypothesis.run_id == run_id,
        )
    )

    selected_hypothesis = (
        result.scalar_one_or_none()
    )

    if selected_hypothesis is None:
        raise ValueError(
            "Hypothesis does not belong to this run."
        )

    hypotheses_result = await db.execute(
        select(Hypothesis).where(
            Hypothesis.run_id == run_id
        )
    )

    hypotheses = list(
        hypotheses_result.scalars().all()
    )

    for hypothesis in hypotheses:
        hypothesis.selected = (
            hypothesis.id == hypothesis_id
        )

        if hypothesis.selected:
            hypothesis.status = "SELECTED"
        else:
            hypothesis.status = "NOT_SELECTED"

    state = dict(
        run.state_json
    )

    state[
        "selected_hypothesis_id"
    ] = str(hypothesis_id)

    state_hypotheses = []

    for hypothesis in hypotheses:
        state_hypotheses.append(
            {
                "id": str(hypothesis.id),
                "summary": hypothesis.summary,
                "mechanism":
                    hypothesis.mechanism,
                "expected_effect":
                    hypothesis.expected_effect,
                "trade_offs":
                    hypothesis.trade_offs,
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
        "status": "APPROVED",
        "hypothesis_id": str(
            hypothesis_id
        ),
    }

    state["approvals"] = approvals

    run.state_json = state

    approval = Approval(
        run_id=run_id,
        approval_type="candidate",
        status="APPROVED",
    )

    event = RunEvent(
        run_id=run_id,
        event_type="CANDIDATE_SELECTED",
        payload_json={
            "hypothesis_id":
                str(hypothesis_id),
            "message":
                "Candidate hypothesis selected.",
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
            Hypothesis.run_id == run_id,
            Hypothesis.selected.is_(True),
        )
    )

    return (
        result.scalar_one_or_none()
    )



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

    state["changes"] = {
        "iteration": 1,
        "selected_hypothesis_id":
            str(selected_hypothesis_id),
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
        event_type="PATCH_PROPOSED",
        payload_json={
            "message":
                "Coder produced a candidate patch.",
            "policy_passed":
                policy_result["passed"],
        },
    )

    db.add(event)

    await db.commit()
    await db.refresh(run)

    return run


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
        not baseline_result["timed_out"]
        and baseline_result["exit_code"] == 0
    )

    candidate_passed = (
        not candidate_result["timed_out"]
        and candidate_result["exit_code"] == 0
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
            baseline_result["stdout"][-8000:]
        ),
        duration_ms=(
            baseline_result["duration_ms"]
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
            candidate_result["stdout"][-8000:]
        ),
        duration_ms=(
            candidate_result["duration_ms"]
        ),
    )

    db.add(baseline_row)
    db.add(candidate_row)

    state = dict(
        run.state_json
    )

    state["validation"] = {
        "strategy": "existing_tests",

        "baseline": {
            "passed": baseline_passed,
            **baseline_result,
        },

        "candidate": {
            "passed": candidate_passed,
            **candidate_result,
        },

        "correctness_passed":
            correctness_passed,
    }

    run.state_json = state

    event = RunEvent(
        run_id=run_id,
        event_type="VALIDATION_COMPLETED",
        payload_json={
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

#THIS IS CONTROLLER(FROM SPRINGBOOT) WHICH SEND DATA INTO SERVICE 