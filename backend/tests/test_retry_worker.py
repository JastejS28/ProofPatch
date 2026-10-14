from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.workers import (
    retry_worker,
)


class FakeSession:

    async def __aenter__(
        self,
    ):
        return self

    async def __aexit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        return False


def fake_session_factory():

    return FakeSession()


@pytest.mark.asyncio
async def test_candidate_failure_retries_before_limit(
    tmp_path,
    monkeypatch,
):

    run_id = uuid4()

    run = SimpleNamespace(
        id=run_id,
        target_file="target.py",
        target_function="calculate",
        state_json={
            "iteration_count":
                1,

            "workspace_ref":
                str(
                    tmp_path
                ),

            "changes": {
                "original_function":
                    (
                        "def calculate("
                        "value: int) -> int:\n"
                        "    return value"
                    )
            },
        },
    )

    async def fake_get_run(
        db,
        run_id,
    ):
        return run

    async def fake_archive(
        **kwargs,
    ):
        return run

    restored = []

    def fake_restore(
        **kwargs,
    ):
        restored.append(
            True
        )

    transitions = []

    async def fake_transition(
        db,
        run_id,
        status,
        message,
    ):
        transitions.append(
            status.value
        )

        return run

    coder_called = []

    async def fake_coder(
        run_id,
    ):
        coder_called.append(
            True
        )

    monkeypatch.setattr(
        retry_worker,
        "AsyncSessionLocal",
        fake_session_factory,
    )

    monkeypatch.setattr(
        retry_worker,
        "get_run",
        fake_get_run,
    )

    monkeypatch.setattr(
        retry_worker,
        "archive_failed_attempt",
        fake_archive,
    )

    monkeypatch.setattr(
        retry_worker,
        "restore_original_function",
        fake_restore,
    )

    monkeypatch.setattr(
        retry_worker,
        "transition_run",
        fake_transition,
    )

    monkeypatch.setattr(
        retry_worker.settings,
        "max_coder_attempts",
        2,
    )

    # This import happens locally inside
    # retry_worker, so patch the actual module.
    from app.workers import coder_worker

    monkeypatch.setattr(
        coder_worker,
        "run_coder_workflow",
        fake_coder,
    )

    await retry_worker.handle_candidate_failure(
        run_id=run_id,
        failure_stage="CORRECTNESS",
        reason="Candidate failed tests.",
    )

    assert restored == [
        True
    ]

    assert "MODIFYING" in transitions

    assert coder_called == [
        True
    ]


@pytest.mark.asyncio
async def test_candidate_failure_stops_after_max_attempts(
    monkeypatch,
):

    run_id = uuid4()

    run = SimpleNamespace(
        id=run_id,
        target_file="target.py",
        target_function="calculate",
        state_json={
            "iteration_count":
                2,

            "workspace_ref":
                "unused",

            "changes": {
                "original_function":
                    (
                        "def calculate("
                        "value: int) -> int:\n"
                        "    return value"
                    )
            },
        },
    )

    async def fake_get_run(
        db,
        run_id,
    ):
        return run

    async def fake_archive(
        **kwargs,
    ):
        return run

    transitions = []

    async def fake_transition(
        db,
        run_id,
        status,
        message,
    ):
        transitions.append(
            status.value
        )

        return run

    monkeypatch.setattr(
        retry_worker,
        "AsyncSessionLocal",
        fake_session_factory,
    )

    monkeypatch.setattr(
        retry_worker,
        "get_run",
        fake_get_run,
    )

    monkeypatch.setattr(
        retry_worker,
        "archive_failed_attempt",
        fake_archive,
    )

    monkeypatch.setattr(
        retry_worker,
        "transition_run",
        fake_transition,
    )

    monkeypatch.setattr(
        retry_worker.settings,
        "max_coder_attempts",
        2,
    )

    await retry_worker.handle_candidate_failure(
        run_id=run_id,
        failure_stage="BENCHMARK",
        reason="Performance too low.",
    )

    assert transitions == [
        "UNVERIFIED"
    ]