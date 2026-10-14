from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.repository.github_pr import (
    GitHubPRCreationError,
)
from app.workers import (
    pr_worker,
)


class FakeScalarResult:

    def first(
        self,
    ):

        return SimpleNamespace(
            status="APPROVED"
        )


class FakeExecuteResult:

    def scalars(
        self,
    ):

        return FakeScalarResult()


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

    async def execute(
        self,
        statement,
    ):

        return FakeExecuteResult()


def fake_session_factory():

    return FakeSession()


@pytest.mark.asyncio
async def test_github_failure_becomes_retryable(
    monkeypatch,
    tmp_path,
):

    run_id = uuid4()

    target_file = (
        "optimization_cases.py"
    )

    (
        tmp_path
        / target_file
    ).write_text(
        (
            "def example():\n"
            "    return 1\n"
        ),
        encoding="utf-8",
    )

    run = SimpleNamespace(
        id=run_id,
        status="CREATING_PR",
        repo_url=(
            "https://github.com/"
            "JastejS28/"
            "proofpatch_testing"
        ),
        target_file=(
            target_file
        ),
        target_function=(
            "example"
        ),
        state_json={
            "workspace_ref":
                str(
                    tmp_path
                ),

            "verification": {
                "passed":
                    True,
            },

            "benchmark": {
                "improvement_percent":
                    20.0,

                "threshold_percent":
                    10.0,
            },

            "review": {},

            "pr": {},
        },
    )

    async def fake_get_run(
        db,
        run_id,
    ):

        return run

    async def fake_mark_pr_attempt_started(
        db,
        run_id,
    ):

        run.state_json[
            "pr"
        ] = {
            "status":
                "IN_PROGRESS",

            "attempt_count":
                1,
        }

        return run

    async def fake_prepare_branch(
        repo_url,
        run_id,
    ):

        raise GitHubPRCreationError(
            "Simulated GitHub failure"
        )

    saved_failures = []

    async def fake_save_pr_failure(
        db,
        run_id,
        message,
    ):

        saved_failures.append(
            message
        )

        return run

    terminal_failures = []

    async def fake_fail_run(
        db,
        run_id,
        message,
    ):

        terminal_failures.append(
            message
        )

        return run

    monkeypatch.setattr(
        pr_worker,
        "AsyncSessionLocal",
        fake_session_factory,
    )

    monkeypatch.setattr(
        pr_worker,
        "get_run",
        fake_get_run,
    )

    monkeypatch.setattr(
        pr_worker,
        "mark_pr_attempt_started",
        fake_mark_pr_attempt_started,
    )

    monkeypatch.setattr(
        pr_worker,
        "prepare_branch",
        fake_prepare_branch,
    )

    monkeypatch.setattr(
        pr_worker,
        "save_pr_failure",
        fake_save_pr_failure,
    )

    monkeypatch.setattr(
        pr_worker,
        "fail_run",
        fake_fail_run,
    )

    await (
        pr_worker
        .run_pr_workflow(
            run_id
        )
    )

    assert (
        len(
            saved_failures
        )
        == 1
    )

    assert (
        "Simulated GitHub failure"
        in saved_failures[
            0
        ]
    )

    # Most important assertion:
    # external GitHub failure must
    # NOT terminally fail the run.
    assert terminal_failures == []