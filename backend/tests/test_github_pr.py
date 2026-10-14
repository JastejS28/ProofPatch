import base64
from uuid import uuid4

import pytest

from app.repository import (
    github_pr,
)
from app.repository.github_pr import (
    CreatedPullRequest,
    GitHubPRCreationError,
)


# =====================================================
# FAKE HTTPX SUPPORT
# =====================================================


class FakeResponse:

    def __init__(
        self,
        status_code: int,
        json_data=None,
        headers=None,
    ):

        self.status_code = (
            status_code
        )

        self._json_data = (
            json_data
            if json_data is not None
            else {}
        )

        self.headers = (
            headers
            or {}
        )

        self.text = str(
            self._json_data
        )

        self.content = (
            b"content"
            if self._json_data
            else b""
        )

    def json(
        self,
    ):

        return self._json_data


class FakeAsyncClient:

    def __init__(
        self,
        responses,
    ):

        self.responses = list(
            responses
        )

        self.requests = []

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

    async def request(
        self,
        method,
        url,
        **kwargs,
    ):

        self.requests.append(
            {
                "method":
                    method,

                "url":
                    url,

                "kwargs":
                    kwargs,
            }
        )

        if not self.responses:

            raise AssertionError(
                "No fake response "
                "configured."
            )

        return self.responses.pop(
            0
        )


def install_fake_client(
    monkeypatch,
    responses,
):

    fake_client = FakeAsyncClient(
        responses
    )

    monkeypatch.setattr(
        github_pr.settings,
        "github_token",
        "fake-test-token",
    )

    monkeypatch.setattr(
        github_pr.httpx,
        "AsyncClient",
        lambda *args, **kwargs:
            fake_client,
    )

    return fake_client


# =====================================================
# PREPARE BRANCH
# =====================================================


@pytest.mark.asyncio
async def test_prepare_branch_reuses_existing_branch(
    monkeypatch,
):

    run_id = uuid4()

    branch = (
        "proofpatch/"
        f"{str(run_id)[:8]}"
    )

    fake_client = (
        install_fake_client(
            monkeypatch,
            [
                FakeResponse(
                    200,
                    {
                        "default_branch":
                            "main",
                    },
                ),
                FakeResponse(
                    200,
                    {
                        "ref":
                            (
                                "refs/heads/"
                                f"{branch}"
                            ),
                    },
                ),
            ],
        )
    )

    result = (
        await github_pr
        .prepare_branch(
            repo_url=(
                "https://github.com/"
                "JastejS28/"
                "proofpatch_testing"
            ),
            run_id=run_id,
        )
    )

    assert (
        result.branch
        == branch
    )

    assert (
        result.base_branch
        == "main"
    )

    methods = [
        request["method"]
        for request
        in fake_client.requests
    ]

    assert methods == [
        "GET",
        "GET",
    ]


@pytest.mark.asyncio
async def test_prepare_branch_creates_missing_branch(
    monkeypatch,
):

    run_id = uuid4()

    fake_client = (
        install_fake_client(
            monkeypatch,
            [
                # Repository metadata
                FakeResponse(
                    200,
                    {
                        "default_branch":
                            "main",
                    },
                ),

                # ProofPatch branch missing
                FakeResponse(
                    404,
                    {
                        "message":
                            "Not Found",
                    },
                ),

                # Base branch SHA
                FakeResponse(
                    200,
                    {
                        "object": {
                            "sha":
                                "abc123",
                        }
                    },
                ),

                # Create branch
                FakeResponse(
                    201,
                    {
                        "ref":
                            "refs/heads/"
                            "proofpatch/test",
                    },
                ),
            ],
        )
    )

    result = (
        await github_pr
        .prepare_branch(
            repo_url=(
                "https://github.com/"
                "JastejS28/"
                "proofpatch_testing"
            ),
            run_id=run_id,
        )
    )

    assert (
        result.base_branch
        == "main"
    )

    methods = [
        request["method"]
        for request
        in fake_client.requests
    ]

    assert methods == [
        "GET",
        "GET",
        "GET",
        "POST",
    ]

    create_request = (
        fake_client.requests[
            -1
        ]
    )

    assert (
        create_request[
            "kwargs"
        ][
            "json"
        ][
            "sha"
        ]
        == "abc123"
    )


# =====================================================
# COMMIT CANDIDATE FILE
# =====================================================


@pytest.mark.asyncio
async def test_commit_candidate_file_skips_identical_content(
    tmp_path,
    monkeypatch,
):

    target_file = (
        "optimization_cases.py"
    )

    candidate = (
        b"def example():\n"
        b"    return 2\n"
    )

    (
        tmp_path
        / target_file
    ).write_bytes(
        candidate
    )

    encoded = (
        base64.b64encode(
            candidate
        ).decode(
            "ascii"
        )
    )

    fake_client = (
        install_fake_client(
            monkeypatch,
            [
                FakeResponse(
                    200,
                    {
                        "sha":
                            "existing-sha",

                        "content":
                            encoded,
                    },
                ),
            ],
        )
    )

    await (
        github_pr
        .commit_candidate_file(
            repo_url=(
                "https://github.com/"
                "JastejS28/"
                "proofpatch_testing"
            ),
            workspace=tmp_path,
            target_file=(
                target_file
            ),
            branch=(
                "proofpatch/test"
            ),
            base_branch="main",
        )
    )

    methods = [
        request["method"]
        for request
        in fake_client.requests
    ]

    # No PUT because contents match.
    assert methods == [
        "GET",
    ]


@pytest.mark.asyncio
async def test_commit_candidate_file_updates_changed_content(
    tmp_path,
    monkeypatch,
):

    target_file = (
        "optimization_cases.py"
    )

    candidate = (
        b"def example():\n"
        b"    return 2\n"
    )

    (
        tmp_path
        / target_file
    ).write_bytes(
        candidate
    )

    old_content = (
        base64.b64encode(
            b"def example():\n"
            b"    return 1\n"
        ).decode(
            "ascii"
        )
    )

    fake_client = (
        install_fake_client(
            monkeypatch,
            [
                FakeResponse(
                    200,
                    {
                        "sha":
                            "old-sha",

                        "content":
                            old_content,
                    },
                ),

                FakeResponse(
                    200,
                    {
                        "content": {
                            "sha":
                                "new-sha",
                        }
                    },
                ),
            ],
        )
    )

    await (
        github_pr
        .commit_candidate_file(
            repo_url=(
                "https://github.com/"
                "JastejS28/"
                "proofpatch_testing"
            ),
            workspace=tmp_path,
            target_file=(
                target_file
            ),
            branch=(
                "proofpatch/test"
            ),
            base_branch="main",
        )
    )

    methods = [
        request["method"]
        for request
        in fake_client.requests
    ]

    assert methods == [
        "GET",
        "PUT",
    ]

    put_request = (
        fake_client.requests[
            1
        ]
    )

    assert (
        put_request[
            "kwargs"
        ][
            "json"
        ][
            "sha"
        ]
        == "old-sha"
    )

    decoded = (
        base64.b64decode(
            put_request[
                "kwargs"
            ][
                "json"
            ][
                "content"
            ]
        )
    )

    assert (
        decoded
        == candidate
    )


# =====================================================
# EXISTING PR
# =====================================================


@pytest.mark.asyncio
async def test_create_pr_only_reuses_existing_pr(
    monkeypatch,
):

    existing = (
        CreatedPullRequest(
            number=42,
            url=(
                "https://github.com/"
                "example/repo/pull/42"
            ),
            branch=(
                "proofpatch/test"
            ),
            base_branch="main",
        )
    )

    async def fake_find_existing_pr(
        repo_url,
        branch,
    ):

        return existing

    monkeypatch.setattr(
        github_pr,
        "find_existing_pr",
        fake_find_existing_pr,
    )

    result = (
        await github_pr
        .create_pr_only(
            repo_url=(
                "https://github.com/"
                "example/repo"
            ),
            branch=(
                "proofpatch/test"
            ),
            base_branch="main",
            title="Test PR",
            body="Test body",
        )
    )

    assert result is existing

    assert (
        result.number
        == 42
    )


# =====================================================
# CREATE NEW PR
# =====================================================


@pytest.mark.asyncio
async def test_create_pr_only_creates_new_pr(
    monkeypatch,
):

    async def fake_find_existing_pr(
        repo_url,
        branch,
    ):

        return None

    monkeypatch.setattr(
        github_pr,
        "find_existing_pr",
        fake_find_existing_pr,
    )

    fake_client = (
        install_fake_client(
            monkeypatch,
            [
                FakeResponse(
                    201,
                    {
                        "number":
                            7,

                        "html_url":
                            (
                                "https://github.com/"
                                "example/repo/"
                                "pull/7"
                            ),
                    },
                ),
            ],
        )
    )

    result = (
        await github_pr
        .create_pr_only(
            repo_url=(
                "https://github.com/"
                "example/repo"
            ),
            branch=(
                "proofpatch/test"
            ),
            base_branch="main",
            title=(
                "ProofPatch test"
            ),
            body="Body",
        )
    )

    assert (
        result.number
        == 7
    )

    assert (
        result.branch
        == "proofpatch/test"
    )

    assert (
        result.base_branch
        == "main"
    )

    assert (
        len(
            fake_client.requests
        )
        == 1
    )

    request = (
        fake_client.requests[
            0
        ]
    )

    assert (
        request["method"]
        == "POST"
    )

    assert (
        request[
            "kwargs"
        ][
            "json"
        ][
            "head"
        ]
        == "proofpatch/test"
    )


# =====================================================
# GITHUB API ERROR
# =====================================================


@pytest.mark.asyncio
async def test_request_raises_github_error_with_permissions():

    fake_client = (
        FakeAsyncClient(
            [
                FakeResponse(
                    403,
                    {
                        "message":
                            (
                                "Resource not "
                                "accessible by "
                                "personal access token"
                            ),
                    },
                    headers={
                        (
                            "X-Accepted-"
                            "GitHub-Permissions"
                        ):
                            (
                                "contents=write"
                            ),
                    },
                )
            ]
        )
    )

    with pytest.raises(
        GitHubPRCreationError,
    ) as exc_info:

        await github_pr._request(
            client=fake_client,
            method="POST",
            url=(
                "https://api.github.com/"
                "repos/example/repo/"
                "git/refs"
            ),
        )

    message = str(
        exc_info.value
    )

    assert "403" in message

    assert (
        "Resource not accessible"
        in message
    )

    assert (
        "contents=write"
        in message
    )



@pytest.mark.asyncio
async def test_prepare_branch_respects_non_main_default_branch(
    monkeypatch,
):

    run_id = uuid4()

    fake_client = (
        install_fake_client(
            monkeypatch,
            [
                # Repository says default branch
                # is develop, not main.
                FakeResponse(
                    200,
                    {
                        "default_branch":
                            "develop",
                    },
                ),

                # ProofPatch branch missing.
                FakeResponse(
                    404,
                    {
                        "message":
                            "Not Found",
                    },
                ),

                # Read develop SHA.
                FakeResponse(
                    200,
                    {
                        "object": {
                            "sha":
                                "develop-sha",
                        }
                    },
                ),

                # Branch creation.
                FakeResponse(
                    201,
                    {
                        "ref":
                            "refs/heads/"
                            "proofpatch/test",
                    },
                ),
            ],
        )
    )

    result = (
        await github_pr
        .prepare_branch(
            repo_url=(
                "https://github.com/"
                "JastejS28/"
                "proofpatch_testing"
            ),
            run_id=run_id,
        )
    )

    assert (
        result.base_branch
        == "develop"
    )

    base_request = (
        fake_client.requests[
            2
        ]
    )

    assert (
        "/git/ref/heads/develop"
        in base_request["url"]
    )