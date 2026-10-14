import traceback
from uuid import UUID

from app.context.reviewer_context import (
    build_reviewer_context,
)
from app.db.session import (
    AsyncSessionLocal,
)
from app.llm.factory import (
    get_llm_provider,
)
from app.services.run_service import (
    fail_run,
    get_run,
    save_review_result,
)
from app.agents.reviewer import (
    review_candidate,
)


async def run_reviewer_workflow(
    run_id: UUID,
) -> None:

    async with AsyncSessionLocal() as db:

        try:
            run = await get_run(
                db=db,
                run_id=run_id,
            )

            if run is None:
                return

            state = dict(
                run.state_json
            )

            verification = state.get(
                "verification",
                {},
            )

            if not verification.get(
                "passed",
                False,
            ):
                await fail_run(
                    db=db,
                    run_id=run_id,
                    message=(
                        "Reviewer cannot start "
                        "because deterministic "
                        "verification did not pass."
                    ),
                )
                return

            context = (
                build_reviewer_context(
                    state=state,
                    problem_description=(
                        run.problem_description
                    ),
                )
            )

            provider = (
                get_llm_provider()
            )

            reviewer_output = (
                await review_candidate(
                    provider=provider,
                    context=context,
                )
            )

            review_data = (
                reviewer_output
                .model_dump()
            )

            await save_review_result(
                db=db,
                run_id=run_id,
                review=review_data,
            )

        except Exception as exc:

            traceback.print_exc()

            await fail_run(
                db=db,
                run_id=run_id,
                message=(
                    "Unexpected reviewer "
                    "workflow error: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )