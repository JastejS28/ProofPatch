from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api.routes import (
    runs as run_routes,
)
from app.domain.run_status import (
    RunStatus,
)


# =====================================================
# HELPERS
# =====================================================


def make_run(
    status: str,
):

    run_id = uuid4()

    return SimpleNamespace(
        id=run_id,
        status=status,
        current_step=status,
        state_json={},
    )


async def fake_coroutine(
    *args,
    **kwargs,
):

    return None


# =====================================================
# CANDIDATE SELECTION
# =====================================================


@pytest.mark.asyncio
async def test_candidate_selection_success(
    api_client,
    monkeypatch,
):

    run = make_run(
        RunStatus
        .WAITING_FOR_CANDIDATE
        .value
    )

    hypothesis_id = uuid4()

    async def fake_select_hypothesis(
        db,
        run_id,
        hypothesis_id,
    ):

        return run

    started = []

    def fake_start_background_task(
        coroutine,
    ):

        started.append(
            coroutine
        )

        coroutine.close()

    monkeypatch.setattr(
        run_routes,
        "select_hypothesis",
        fake_select_hypothesis,
    )

    monkeypatch.setattr(
        run_routes,
        "run_coder_workflow",
        fake_coroutine,
    )

    monkeypatch.setattr(
        run_routes,
        "start_background_task",
        fake_start_background_task,
    )

    response = await api_client.post(
        (
            f"/runs/"
            f"{run.id}"
            "/decision"
        ),
        json={
            "type":
                "candidate",

            "value":
                str(
                    hypothesis_id
                ),
        },
    )

    assert (
        response.status_code
        == 200
    )

    data = response.json()

    assert (
        data["run_id"]
        == str(
            run.id
        )
    )

    assert (
        data[
            "selected_hypothesis_id"
        ]
        == str(
            hypothesis_id
        )
    )

    assert len(
        started
    ) == 1


@pytest.mark.asyncio
async def test_candidate_requires_hypothesis_id(
    api_client,
):

    run_id = uuid4()

    response = await api_client.post(
        (
            f"/runs/"
            f"{run_id}"
            "/decision"
        ),
        json={
            "type":
                "candidate"
        },
    )

    assert (
        response.status_code
        == 422
    )

    assert (
        response.json()[
            "detail"
        ]
        ==
        (
            "Candidate decision "
            "requires a hypothesis ID."
        )
    )


@pytest.mark.asyncio
async def test_candidate_conflict_returns_409(
    api_client,
    monkeypatch,
):

    run_id = uuid4()
    hypothesis_id = uuid4()

    async def fake_select_hypothesis(
        db,
        run_id,
        hypothesis_id,
    ):

        raise ValueError(
            "Run is not waiting for "
            "candidate selection."
        )

    monkeypatch.setattr(
        run_routes,
        "select_hypothesis",
        fake_select_hypothesis,
    )

    response = await api_client.post(
        (
            f"/runs/"
            f"{run_id}"
            "/decision"
        ),
        json={
            "type":
                "candidate",

            "value":
                str(
                    hypothesis_id
                ),
        },
    )

    assert (
        response.status_code
        == 409
    )


# =====================================================
# PR APPROVAL
# =====================================================


@pytest.mark.asyncio
async def test_pr_approval_success(
    api_client,
    monkeypatch,
):

    run = make_run(
        RunStatus
        .CREATING_PR
        .value
    )

    async def fake_approve_pr_creation(
        db,
        run_id,
    ):

        return run

    started = []

    def fake_start_background_task(
        coroutine,
    ):

        started.append(
            coroutine
        )

        coroutine.close()

    monkeypatch.setattr(
        run_routes,
        "approve_pr_creation",
        fake_approve_pr_creation,
    )

    monkeypatch.setattr(
        run_routes,
        "run_pr_workflow",
        fake_coroutine,
    )

    monkeypatch.setattr(
        run_routes,
        "start_background_task",
        fake_start_background_task,
    )

    response = await api_client.post(
        (
            f"/runs/"
            f"{run.id}"
            "/decision"
        ),
        json={
            "type":
                "pr_approval"
        },
    )

    assert (
        response.status_code
        == 200
    )

    assert (
        response.json()[
            "status"
        ]
        ==
        RunStatus
        .CREATING_PR
        .value
    )

    assert len(
        started
    ) == 1


@pytest.mark.asyncio
async def test_duplicate_pr_approval_returns_409(
    api_client,
    monkeypatch,
):

    run_id = uuid4()

    async def fake_approve_pr_creation(
        db,
        run_id,
    ):

        raise ValueError(
            "Run is not waiting "
            "for PR approval."
        )

    monkeypatch.setattr(
        run_routes,
        "approve_pr_creation",
        fake_approve_pr_creation,
    )

    response = await api_client.post(
        (
            f"/runs/"
            f"{run_id}"
            "/decision"
        ),
        json={
            "type":
                "pr_approval"
        },
    )

    assert (
        response.status_code
        == 409
    )


# =====================================================
# PR REJECTION
# =====================================================


@pytest.mark.asyncio
async def test_pr_rejection_success(
    api_client,
    monkeypatch,
):

    run = make_run(
        RunStatus
        .CANCELLED
        .value
    )

    async def fake_reject_pr_creation(
        db,
        run_id,
    ):

        return run

    started = []

    def fake_start_background_task(
        coroutine,
    ):

        started.append(
            coroutine
        )

        coroutine.close()

    monkeypatch.setattr(
        run_routes,
        "reject_pr_creation",
        fake_reject_pr_creation,
    )

    if hasattr(
        run_routes,
        "cleanup_run_workflow",
    ):

        monkeypatch.setattr(
            run_routes,
            "cleanup_run_workflow",
            fake_coroutine,
        )

    monkeypatch.setattr(
        run_routes,
        "start_background_task",
        fake_start_background_task,
    )

    response = await api_client.post(
        (
            f"/runs/"
            f"{run.id}"
            "/decision"
        ),
        json={
            "type":
                "reject"
        },
    )

    assert (
        response.status_code
        == 200
    )

    assert (
        response.json()[
            "status"
        ]
        ==
        RunStatus
        .CANCELLED
        .value
    )


# =====================================================
# PR RETRY
# =====================================================


@pytest.mark.asyncio
async def test_pr_retry_success(
    api_client,
    monkeypatch,
):

    run = make_run(
        RunStatus
        .CREATING_PR
        .value
    )

    async def fake_prepare_pr_retry(
        db,
        run_id,
    ):

        return run

    started = []

    def fake_start_background_task(
        coroutine,
    ):

        started.append(
            coroutine
        )

        coroutine.close()

    monkeypatch.setattr(
        run_routes,
        "prepare_pr_retry",
        fake_prepare_pr_retry,
    )

    monkeypatch.setattr(
        run_routes,
        "run_pr_workflow",
        fake_coroutine,
    )

    monkeypatch.setattr(
        run_routes,
        "start_background_task",
        fake_start_background_task,
    )

    response = await api_client.post(
        (
            f"/runs/"
            f"{run.id}"
            "/retry-pr"
        )
    )

    assert (
        response.status_code
        == 200
    )

    assert (
        response.json()[
            "status"
        ]
        ==
        RunStatus
        .CREATING_PR
        .value
    )

    assert len(
        started
    ) == 1


@pytest.mark.asyncio
async def test_pr_retry_invalid_state_returns_409(
    api_client,
    monkeypatch,
):

    run_id = uuid4()

    async def fake_prepare_pr_retry(
        db,
        run_id,
    ):

        raise ValueError(
            "PR creation is not "
            "waiting for a retry."
        )

    monkeypatch.setattr(
        run_routes,
        "prepare_pr_retry",
        fake_prepare_pr_retry,
    )

    response = await api_client.post(
        (
            f"/runs/"
            f"{run_id}"
            "/retry-pr"
        )
    )

    assert (
        response.status_code
        == 409
    )


# =====================================================
# CANCEL
# =====================================================


@pytest.mark.asyncio
async def test_cancel_run_success(
    api_client,
    monkeypatch,
):

    # Skip cleanly only if your local
    # /cancel endpoint has not been added.
    if not hasattr(
        run_routes,
        "cancel_run",
    ):

        pytest.skip(
            "cancel_run not available"
        )

    run = make_run(
        RunStatus
        .CANCELLED
        .value
    )

    async def fake_cancel_run(
        db,
        run_id,
    ):

        return run

    started = []

    def fake_start_background_task(
        coroutine,
    ):

        started.append(
            coroutine
        )

        coroutine.close()

    monkeypatch.setattr(
        run_routes,
        "cancel_run",
        fake_cancel_run,
    )

    if hasattr(
        run_routes,
        "cleanup_run_workflow",
    ):

        monkeypatch.setattr(
            run_routes,
            "cleanup_run_workflow",
            fake_coroutine,
        )

    monkeypatch.setattr(
        run_routes,
        "start_background_task",
        fake_start_background_task,
    )

    response = await api_client.post(
        (
            f"/runs/"
            f"{run.id}"
            "/cancel"
        )
    )

    assert (
        response.status_code
        == 200
    )

    assert (
        response.json()[
            "status"
        ]
        ==
        RunStatus
        .CANCELLED
        .value
    )


@pytest.mark.asyncio
async def test_cancel_invalid_state_returns_409(
    api_client,
    monkeypatch,
):

    if not hasattr(
        run_routes,
        "cancel_run",
    ):

        pytest.skip(
            "cancel_run not available"
        )

    run_id = uuid4()

    async def fake_cancel_run(
        db,
        run_id,
    ):

        raise ValueError(
            "Run cannot be cancelled "
            "at its current stage."
        )

    monkeypatch.setattr(
        run_routes,
        "cancel_run",
        fake_cancel_run,
    )

    response = await api_client.post(
        (
            f"/runs/"
            f"{run_id}"
            "/cancel"
        )
    )

    assert (
        response.status_code
        == 409
    )


# =====================================================
# REQUEST VALIDATION
# =====================================================


@pytest.mark.asyncio
async def test_invalid_decision_type_returns_422(
    api_client,
):

    run_id = uuid4()

    response = await api_client.post(
        (
            f"/runs/"
            f"{run_id}"
            "/decision"
        ),
        json={
            "type":
                "something_invalid"
        },
    )

    assert (
        response.status_code
        == 422
    )