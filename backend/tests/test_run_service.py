from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.run_status import (
    RunStatus,
)
from app.services import (
    run_service,
)


@pytest.mark.asyncio
async def test_cancel_waiting_candidate(
    fake_db,
    monkeypatch,
):

    run_id = uuid4()

    run = SimpleNamespace(
        id=run_id,
        status=(
            RunStatus
            .WAITING_FOR_CANDIDATE
            .value
        ),
        current_step=(
            RunStatus
            .WAITING_FOR_CANDIDATE
            .value
        ),
        state_json={
            "status":
                RunStatus
                .WAITING_FOR_CANDIDATE
                .value,

            "current_step":
                RunStatus
                .WAITING_FOR_CANDIDATE
                .value,

            "pr": {},
        },
    )

    async def fake_get_run(
        db,
        run_id,
    ):

        return run

    monkeypatch.setattr(
        run_service,
        "get_run",
        fake_get_run,
    )

    result = (
        await run_service
        .cancel_run(
            db=fake_db,
            run_id=run_id,
        )
    )

    assert (
        result.status
        == RunStatus.CANCELLED.value
    )

    assert (
        result.state_json[
            "cancellation"
        ][
            "completed"
        ]
        is True
    )


@pytest.mark.asyncio
async def test_cancel_waiting_pr_approval(
    fake_db,
    monkeypatch,
):

    run_id = uuid4()

    run = SimpleNamespace(
        id=run_id,
        status=(
            RunStatus
            .WAITING_FOR_PR_APPROVAL
            .value
        ),
        current_step=(
            RunStatus
            .WAITING_FOR_PR_APPROVAL
            .value
        ),
        state_json={
            "status":
                RunStatus
                .WAITING_FOR_PR_APPROVAL
                .value,

            "current_step":
                RunStatus
                .WAITING_FOR_PR_APPROVAL
                .value,

            "pr": {},
        },
    )

    async def fake_get_run(
        db,
        run_id,
    ):

        return run

    monkeypatch.setattr(
        run_service,
        "get_run",
        fake_get_run,
    )

    result = (
        await run_service
        .cancel_run(
            db=fake_db,
            run_id=run_id,
        )
    )

    assert (
        result.status
        == RunStatus.CANCELLED.value
    )


@pytest.mark.asyncio
async def test_cancel_completed_run_fails(
    fake_db,
    monkeypatch,
):

    run_id = uuid4()

    run = SimpleNamespace(
        id=run_id,
        status=(
            RunStatus
            .COMPLETED
            .value
        ),
        current_step=(
            RunStatus
            .COMPLETED
            .value
        ),
        state_json={
            "status":
                RunStatus
                .COMPLETED
                .value,

            "current_step":
                RunStatus
                .COMPLETED
                .value,

            "pr": {
                "status":
                    "CREATED",
            },
        },
    )

    async def fake_get_run(
        db,
        run_id,
    ):

        return run

    monkeypatch.setattr(
        run_service,
        "get_run",
        fake_get_run,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Run cannot be cancelled"
        ),
    ):

        await run_service.cancel_run(
            db=fake_db,
            run_id=run_id,
        )


@pytest.mark.asyncio
async def test_cancel_retryable_pr_failure(
    fake_db,
    monkeypatch,
):

    run_id = uuid4()

    run = SimpleNamespace(
        id=run_id,
        status=(
            RunStatus
            .CREATING_PR
            .value
        ),
        current_step=(
            RunStatus
            .CREATING_PR
            .value
        ),
        state_json={
            "status":
                RunStatus
                .CREATING_PR
                .value,

            "current_step":
                RunStatus
                .CREATING_PR
                .value,

            "pr": {
                "status":
                    "FAILED_RETRYABLE",
            },
        },
    )

    async def fake_get_run(
        db,
        run_id,
    ):

        return run

    monkeypatch.setattr(
        run_service,
        "get_run",
        fake_get_run,
    )

    result = (
        await run_service
        .cancel_run(
            db=fake_db,
            run_id=run_id,
        )
    )

    assert (
        result.status
        == RunStatus.CANCELLED.value
    )


@pytest.mark.asyncio
async def test_prepare_pr_retry(
    fake_db,
    monkeypatch,
):

    run_id = uuid4()

    run = SimpleNamespace(
        id=run_id,
        status=(
            RunStatus
            .CREATING_PR
            .value
        ),
        current_step=(
            RunStatus
            .CREATING_PR
            .value
        ),
        state_json={
            "pr": {
                "status":
                    "FAILED_RETRYABLE",

                "attempt_count":
                    1,
            }
        },
    )

    async def fake_get_run(
        db,
        run_id,
    ):

        return run

    monkeypatch.setattr(
        run_service,
        "get_run",
        fake_get_run,
    )

    result = (
        await run_service
        .prepare_pr_retry(
            db=fake_db,
            run_id=run_id,
        )
    )

    assert (
        result.state_json[
            "pr"
        ][
            "status"
        ]
        == "RETRYING"
    )


@pytest.mark.asyncio
async def test_prepare_pr_retry_requires_failure_state(
    fake_db,
    monkeypatch,
):

    run_id = uuid4()

    run = SimpleNamespace(
        id=run_id,
        status=(
            RunStatus
            .CREATING_PR
            .value
        ),
        current_step=(
            RunStatus
            .CREATING_PR
            .value
        ),
        state_json={
            "pr": {
                "status":
                    "IN_PROGRESS",
            }
        },
    )

    async def fake_get_run(
        db,
        run_id,
    ):

        return run

    monkeypatch.setattr(
        run_service,
        "get_run",
        fake_get_run,
    )

    with pytest.raises(
        ValueError,
        match=(
            "PR creation is not "
            "waiting for a retry"
        ),
    ):

        await (
            run_service
            .prepare_pr_retry(
                db=fake_db,
                run_id=run_id,
            )
        )