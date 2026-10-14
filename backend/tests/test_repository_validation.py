import pytest

from app.repository.github import (
    RepositoryValidationError,
    parse_github_repo_url,
)


def test_valid_github_url():

    result = parse_github_repo_url(
        "https://github.com/"
        "JastejS28/ProofPatch"
    )

    assert (
        result.owner
        == "JastejS28"
    )

    assert (
        result.name
        == "ProofPatch"
    )


def test_git_suffix_is_removed():

    result = parse_github_repo_url(
        "https://github.com/"
        "JastejS28/ProofPatch.git"
    )

    assert (
        result.name
        == "ProofPatch"
    )


def test_rejects_non_github_domain():

    with pytest.raises(
        RepositoryValidationError,
        match=(
            "only supports GitHub"
        ),
    ):

        parse_github_repo_url(
            "https://gitlab.com/"
            "owner/repo"
        )


def test_rejects_invalid_repository_shape():

    with pytest.raises(
        RepositoryValidationError,
        match=(
            "must look like"
        ),
    ):

        parse_github_repo_url(
            "https://github.com/"
            "owner/repo/extra"
        )


def test_rejects_non_http_scheme():

    with pytest.raises(
        RepositoryValidationError,
        match=(
            "must use HTTP or HTTPS"
        ),
    ):

        parse_github_repo_url(
            "git://github.com/"
            "owner/repo"
        )