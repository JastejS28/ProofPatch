import base64
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import httpx

from app.core.config import (
    settings,
)
from app.repository.github import (
    parse_github_repo_url,
)


class GitHubPRCreationError(
    Exception
):
    pass


@dataclass
class CreatedPullRequest:
    number: int
    url: str
    branch: str
    base_branch: str


@dataclass
class PreparedGitHubBranch:
    branch: str
    base_branch: str


def _headers() -> dict[str, str]:

    if not settings.github_token:

        raise GitHubPRCreationError(
            "GitHub token is not configured."
        )

    return {
        "Authorization":
            f"Bearer {settings.github_token}",

        "Accept":
            "application/vnd.github+json",

        "X-GitHub-Api-Version":
            "2022-11-28",

        "User-Agent":
            "ProofPatch",
    }


async def _request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    allowed_statuses: set[int] | None = None,
    **kwargs,
) -> tuple[int, dict]:

    response = await client.request(
        method,
        url,
        **kwargs,
    )

    allowed = (
        allowed_statuses
        or set()
    )

    if (
        200
        <= response.status_code
        < 300
    ):

        if not response.content:
            return (
                response.status_code,
                {},
            )

        return (
            response.status_code,
            response.json(),
        )

    if (
        response.status_code
        in allowed
    ):

        try:
            payload = (
                response.json()
            )

        except Exception:
            payload = {}

        return (
            response.status_code,
            payload,
        )

    try:

        payload = (
            response.json()
        )

        message = payload.get(
            "message",
            response.text,
        )

    except Exception:

        message = (
            response.text
        )

    accepted_permissions = (
        response.headers.get(
            "X-Accepted-GitHub-Permissions",
            "not provided",
        )
    )

    raise GitHubPRCreationError(
        f"GitHub API {method} {url} "
        f"failed with status "
        f"{response.status_code}: "
        f"{message}. "
        "Required permissions: "
        f"{accepted_permissions}"
    )


async def prepare_branch(
    repo_url: str,
    run_id: UUID,
) -> PreparedGitHubBranch:

    repository = (
        parse_github_repo_url(
            repo_url
        )
    )

    owner = (
        repository.owner
    )

    repo = (
        repository.name
    )

    api_root = (
        f"{settings.github_api_base}"
        f"/repos/{owner}/{repo}"
    )

    branch = (
        "proofpatch/"
        f"{str(run_id)[:8]}"
    )

    timeout = httpx.Timeout(
        settings
        .github_request_timeout_seconds
    )

    async with httpx.AsyncClient(
        timeout=timeout,
        headers=_headers(),
    ) as client:

        # -------------------------
        # Repository metadata
        # -------------------------

        _, repo_data = (
            await _request(
                client,
                "GET",
                api_root,
            )
        )

        base_branch = (
            repo_data[
                "default_branch"
            ]
        )

        # -------------------------
        # Does ProofPatch branch exist?
        # -------------------------

        branch_ref_url = (
            f"{api_root}"
            f"/git/ref/heads/"
            f"{branch}"
        )

        status_code, _ = (
            await _request(
                client,
                "GET",
                branch_ref_url,
                allowed_statuses={
                    404,
                },
            )
        )

        if status_code == 200:

            return (
                PreparedGitHubBranch(
                    branch=branch,
                    base_branch=(
                        base_branch
                    ),
                )
            )

        # -------------------------
        # Read base SHA
        # -------------------------

        _, base_ref = (
            await _request(
                client,
                "GET",
                (
                    f"{api_root}"
                    f"/git/ref/heads/"
                    f"{base_branch}"
                ),
            )
        )

        base_sha = (
            base_ref[
                "object"
            ][
                "sha"
            ]
        )

        # -------------------------
        # Create branch
        # -------------------------

        await _request(
            client,
            "POST",
            (
                f"{api_root}"
                f"/git/refs"
            ),
            json={
                "ref":
                    f"refs/heads/{branch}",

                "sha":
                    base_sha,
            },
        )

    return PreparedGitHubBranch(
        branch=branch,
        base_branch=base_branch,
    )


async def commit_candidate_file(
    repo_url: str,
    workspace: Path,
    target_file: str,
    branch: str,
    base_branch: str,
) -> None:

    repository = (
        parse_github_repo_url(
            repo_url
        )
    )

    owner = repository.owner
    repo = repository.name

    api_root = (
        f"{settings.github_api_base}"
        f"/repos/{owner}/{repo}"
    )

    timeout = httpx.Timeout(
        settings
        .github_request_timeout_seconds
    )

    workspace_resolved = (
        workspace.resolve()
    )

    file_path = (
        workspace
        / target_file
    ).resolve()

    try:

        file_path.relative_to(
            workspace_resolved
        )

    except ValueError as exc:

        raise GitHubPRCreationError(
            "Target file escaped "
            "the run workspace."
        ) from exc

    if not file_path.is_file():

        raise GitHubPRCreationError(
            "Verified target file "
            "does not exist."
        )

    candidate_content = (
        file_path.read_bytes()
    )

    encoded_content = (
        base64.b64encode(
            candidate_content
        )
        .decode(
            "ascii"
        )
    )

    async with httpx.AsyncClient(
        timeout=timeout,
        headers=_headers(),
    ) as client:

        # -------------------------
        # Current file on branch
        # -------------------------

        _, branch_file = (
            await _request(
                client,
                "GET",
                (
                    f"{api_root}"
                    f"/contents/"
                    f"{target_file}"
                ),
                params={
                    "ref": branch,
                },
            )
        )

        existing_sha = (
            branch_file[
                "sha"
            ]
        )

        # -------------------------
        # Decode GitHub file content
        # -------------------------

        existing_content = (
            branch_file.get(
                "content"
            )
        )

        if existing_content:

            remote_bytes = (
                base64.b64decode(
                    existing_content
                )
            )

            # Already committed.
            if (
                remote_bytes
                == candidate_content
            ):

                return

        # -------------------------
        # Update file
        # -------------------------

        await _request(
            client,
            "PUT",
            (
                f"{api_root}"
                f"/contents/"
                f"{target_file}"
            ),
            json={
                "message":
                    (
                        "ProofPatch: optimize "
                        f"{target_file}"
                    ),

                "content":
                    encoded_content,

                "sha":
                    existing_sha,

                "branch":
                    branch,
            },
        )


async def find_existing_pr(
    repo_url: str,
    branch: str,
) -> CreatedPullRequest | None:

    repository = (
        parse_github_repo_url(
            repo_url
        )
    )

    owner = repository.owner
    repo = repository.name

    api_root = (
        f"{settings.github_api_base}"
        f"/repos/{owner}/{repo}"
    )

    timeout = httpx.Timeout(
        settings
        .github_request_timeout_seconds
    )

    async with httpx.AsyncClient(
        timeout=timeout,
        headers=_headers(),
    ) as client:

        _, pulls = (
            await _request(
                client,
                "GET",
                (
                    f"{api_root}/pulls"
                ),
                params={
                    "state": "open",
                    "head":
                        f"{owner}:{branch}",
                },
            )
        )

    if not pulls:
        return None

    pr = pulls[0]

    return CreatedPullRequest(
        number=int(
            pr["number"]
        ),
        url=(
            pr["html_url"]
        ),
        branch=branch,
        base_branch=(
            pr["base"]["ref"]
        ),
    )


async def create_pr_only(
    repo_url: str,
    branch: str,
    base_branch: str,
    title: str,
    body: str,
) -> CreatedPullRequest:

    # -------------------------
    # First check for existing PR
    # -------------------------

    existing = (
        await find_existing_pr(
            repo_url=repo_url,
            branch=branch,
        )
    )

    if existing is not None:
        return existing

    repository = (
        parse_github_repo_url(
            repo_url
        )
    )

    owner = repository.owner
    repo = repository.name

    api_root = (
        f"{settings.github_api_base}"
        f"/repos/{owner}/{repo}"
    )

    timeout = httpx.Timeout(
        settings
        .github_request_timeout_seconds
    )

    async with httpx.AsyncClient(
        timeout=timeout,
        headers=_headers(),
    ) as client:

        _, pr_data = (
            await _request(
                client,
                "POST",
                (
                    f"{api_root}/pulls"
                ),
                json={
                    "title":
                        title,

                    "head":
                        branch,

                    "base":
                        base_branch,

                    "body":
                        body,
                },
            )
        )

    return CreatedPullRequest(
        number=int(
            pr_data["number"]
        ),
        url=(
            pr_data["html_url"]
        ),
        branch=branch,
        base_branch=base_branch,
    )