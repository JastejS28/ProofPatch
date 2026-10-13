from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.core.config import settings


class RepositoryValidationError(Exception):
    pass


@dataclass(frozen=True)
class GitHubRepository:
    owner: str
    name: str
    clone_url: str


def parse_github_repo_url(repo_url: str) -> GitHubRepository:
    parsed = urlparse(repo_url)

    if parsed.scheme not in {"http", "https"}:
        raise RepositoryValidationError(
            "Repository URL must use HTTP or HTTPS."
        )

    if parsed.netloc.lower() not in {
        "github.com",
        "www.github.com",
    }:
        raise RepositoryValidationError(
            "ProofPatch V1 only supports GitHub repositories."
        )

    parts = [
        part
        for part in parsed.path.strip("/").split("/")
        if part
    ]

    if len(parts) != 2:
        raise RepositoryValidationError(
            "Repository URL must look like "
            "https://github.com/owner/repository"
        )

    owner, name = parts

    if name.endswith(".git"):
        name = name[:-4]

    if not owner or not name:
        raise RepositoryValidationError(
            "Repository owner or name is missing."
        )

    return GitHubRepository(
        owner=owner,
        name=name,
        clone_url=f"https://github.com/{owner}/{name}.git",
    )


async def validate_public_repository(
    repo_url: str,
) -> GitHubRepository:
    repository = parse_github_repo_url(repo_url)

    api_url = (
        f"https://api.github.com/repos/"
        f"{repository.owner}/{repository.name}"
    )

    timeout = httpx.Timeout(
        settings.github_request_timeout_seconds
    )

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        try:
            response = await client.get(
                api_url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "ProofPatch",
                },
            )
        except httpx.HTTPError as exc:
            raise RepositoryValidationError(
                "Could not contact GitHub."
            ) from exc

    if response.status_code == 404:
        raise RepositoryValidationError(
            "Repository does not exist or is not public."
        )

    if response.status_code != 200:
        raise RepositoryValidationError(
            f"GitHub returned status "
            f"{response.status_code}."
        )

    payload = response.json()

    if payload.get("private") is True:
        raise RepositoryValidationError(
            "ProofPatch V1 only supports public repositories."
        )

    return repository

#validation of github repo