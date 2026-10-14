import traceback
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.db.session import (
    AsyncSessionLocal,
)
from app.models.approval import (
    Approval,
)
from app.repository.github_pr import (
    GitHubPRCreationError,
    commit_candidate_file,
    create_pr_only,
    find_existing_pr,
    prepare_branch,
)
from app.services.run_service import (
    fail_run,
    get_run,
    mark_pr_attempt_started,
    save_pr_failure,
    save_pr_progress,
    save_pr_result,
)
from app.workers.cleanup_worker import (
    cleanup_run_workflow,
)


def _build_pr_title(
    target_function: str,
) -> str:

    return (
        "ProofPatch: optimize "
        f"{target_function}"
    )


def _build_pr_body(
    state: dict,
) -> str:

    review = state.get(
        "review",
        {},
    )

    benchmark = state.get(
        "benchmark",
        {},
    )

    improvement = (
        benchmark.get(
            "improvement_percent"
        )
    )

    threshold = (
        benchmark.get(
            "threshold_percent"
        )
    )

    summary = review.get(
        "summary",
        (
            "Verified performance "
            "optimization generated "
            "by ProofPatch."
        ),
    )

    correctness = review.get(
        "correctness_summary",
        (
            "Correctness validation "
            "passed."
        ),
    )

    performance = review.get(
        "performance_summary",
        "",
    )

    risks = review.get(
        "risks_and_tradeoffs",
        [],
    )

    risks_text = (
        "\n".join(
            f"- {item}"
            for item in risks
        )
        if risks
        else
        "- No additional risks reported."
    )

    improvement_text = (
        f"{improvement:.2f}%"
        if improvement is not None
        else "Unavailable"
    )

    threshold_text = (
        f"{threshold:.2f}%"
        if threshold is not None
        else "Unavailable"
    )

    return f"""
## ProofPatch optimization

{summary}

### Correctness

{correctness}

### Performance

{performance}

Measured improvement:
{improvement_text}

Required threshold:
{threshold_text}

### Risks and trade-offs

{risks_text}

---

This patch passed ProofPatch's static policy,
correctness validation, benchmark threshold,
deterministic verification, and human PR approval.
""".strip()


async def run_pr_workflow(
    run_id: UUID,
) -> None:

    try:

        async with (
            AsyncSessionLocal()
        ) as db:

            # -------------------------
            # 1. Load run
            # -------------------------

            run = await get_run(
                db=db,
                run_id=run_id,
            )

            if run is None:
                return

            # -------------------------
            # 2. Already completed
            # -------------------------

            if (
                run.status
                == "COMPLETED"
            ):
                return

            # -------------------------
            # 3. State gate
            # -------------------------

            if (
                run.status
                != "CREATING_PR"
            ):

                await fail_run(
                    db=db,
                    run_id=run_id,
                    message=(
                        "PR creation started "
                        "from an invalid state."
                    ),
                )

                return

            # -------------------------
            # 4. Human approval gate
            # -------------------------

            approval_result = (
                await db.execute(
                    select(Approval)
                    .where(
                        Approval.run_id
                        == run_id,

                        Approval.approval_type
                        == "pr",

                        Approval.status
                        == "APPROVED",
                    )
                    .order_by(
                        Approval
                        .decided_at
                        .desc()
                    )
                )
            )

            pr_approval = (
                approval_result
                .scalars()
                .first()
            )

            if pr_approval is None:

                await fail_run(
                    db=db,
                    run_id=run_id,
                    message=(
                        "PR creation requires "
                        "explicit human approval."
                    ),
                )

                return

            # -------------------------
            # 5. Verification gate
            # -------------------------

            state = dict(
                run.state_json
            )

            verification = (
                state.get(
                    "verification",
                    {},
                )
            )

            if not verification.get(
                "passed",
                False,
            ):

                await fail_run(
                    db=db,
                    run_id=run_id,
                    message=(
                        "PR creation requires "
                        "a verified candidate."
                    ),
                )

                return

            # -------------------------
            # 6. Record attempt
            # -------------------------

            await mark_pr_attempt_started(
                db=db,
                run_id=run_id,
            )

            run = await get_run(
                db=db,
                run_id=run_id,
            )

            if run is None:
                return

            state = dict(
                run.state_json
            )

            pr_state = dict(
                state.get(
                    "pr",
                    {},
                )
            )

            workspace = Path(
                state[
                    "workspace_ref"
                ]
            )

            repo_url = (
                run.repo_url
            )

            target_file = (
                run.target_file
            )

            title = (
                _build_pr_title(
                    run.target_function
                )
            )

            body = (
                _build_pr_body(
                    state
                )
            )

        # ==================================
        # DB session closed for GitHub I/O
        # ==================================

        branch = (
            pr_state.get(
                "branch"
            )
        )

        base_branch = (
            pr_state.get(
                "base_branch"
            )
        )

        # -------------------------
        # 7. Create/reuse branch
        # -------------------------

        if (
            not branch
            or not base_branch
        ):

            prepared = (
                await prepare_branch(
                    repo_url=repo_url,
                    run_id=run_id,
                )
            )

            branch = (
                prepared.branch
            )

            base_branch = (
                prepared.base_branch
            )

            async with (
                AsyncSessionLocal()
            ) as db:

                await save_pr_progress(
                    db=db,
                    run_id=run_id,
                    pr_data={
                        "status":
                            "BRANCH_CREATED",

                        "branch":
                            branch,

                        "base_branch":
                            base_branch,
                    },
                )

        # -------------------------
        # 8. Commit/reuse candidate
        # -------------------------

        await commit_candidate_file(
            repo_url=repo_url,
            workspace=workspace,
            target_file=target_file,
            branch=branch,
            base_branch=base_branch,
        )

        async with (
            AsyncSessionLocal()
        ) as db:

            await save_pr_progress(
                db=db,
                run_id=run_id,
                pr_data={
                    "status":
                        "COMMITTED",

                    "branch":
                        branch,

                    "base_branch":
                        base_branch,
                },
            )

        # -------------------------
        # 9. Existing PR check
        # -------------------------

        existing = (
            await find_existing_pr(
                repo_url=repo_url,
                branch=branch,
            )
        )

        if existing is not None:

            async with (
                AsyncSessionLocal()
            ) as db:

                await save_pr_result(
                    db=db,
                    run_id=run_id,
                    pr_data={
                        "status":
                            "CREATED",

                        "number":
                            existing.number,

                        "url":
                            existing.url,

                        "branch":
                            existing.branch,

                        "base_branch":
                            existing.base_branch,
                    },
                )

            await cleanup_run_workflow(
                run_id
            )

            return

        # -------------------------
        # 10. Create PR
        # -------------------------

        created = (
            await create_pr_only(
                repo_url=repo_url,
                branch=branch,
                base_branch=base_branch,
                title=title,
                body=body,
            )
        )

        # -------------------------
        # 11. Complete run
        # -------------------------

        async with (
            AsyncSessionLocal()
        ) as db:

            await save_pr_result(
                db=db,
                run_id=run_id,
                pr_data={
                    "status":
                        "CREATED",

                    "number":
                        created.number,

                    "url":
                        created.url,

                    "branch":
                        created.branch,

                    "base_branch":
                        created.base_branch,
                },
            )

        await cleanup_run_workflow(
            run_id
        )

    # ======================================
    # GitHub/external errors are retryable
    # ======================================

    except GitHubPRCreationError as exc:

        async with (
            AsyncSessionLocal()
        ) as db:

            await save_pr_failure(
                db=db,
                run_id=run_id,
                message=str(
                    exc
                ),
            )

    # ======================================
    # Internal ProofPatch failures
    # ======================================

    except Exception as exc:

        traceback.print_exc()

        async with (
            AsyncSessionLocal()
        ) as db:

            await fail_run(
                db=db,
                run_id=run_id,
                message=(
                    "Unexpected PR workflow "
                    "error: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )