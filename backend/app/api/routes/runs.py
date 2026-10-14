from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)
from app.services.run_service import (
    approve_pr_creation,
    create_run,
    get_run,
    list_run_events,
    prepare_pr_retry,
    reject_pr_creation,
    select_hypothesis,
)

from app.db.session import (
    get_db,
)
from app.domain.run_status import (
    RunStatus,
)
from app.models.run import (
    Run,
)
from app.schemas.decision import (
    DecisionType,
    RunDecisionRequest,
    RunDecisionResponse,
)
from app.schemas.run import (
    RunCreate,
    RunCreateResponse,
    RunEventRead,
    RunRead,
)
from app.services.run_service import (
    approve_pr_creation,
    create_run,
    get_run,
    list_run_events,
    reject_pr_creation,
    select_hypothesis,
)
from app.workers.coder_worker import (
    run_coder_workflow,
)
from app.workers.pr_worker import (
    run_pr_workflow,
)
from app.workers.run_worker import (
    run_workflow,
)
from app.workers.task_registry import (
    start_background_task,
)


router = APIRouter(
    prefix="/runs",
)


# =====================================================
# CREATE RUN
# =====================================================


@router.post(
    "",
    response_model=RunCreateResponse,
    status_code=(
        status.HTTP_202_ACCEPTED
    ),
)
async def create_run_endpoint(
    payload: RunCreate,
    db: AsyncSession = Depends(
        get_db
    ),
) -> RunCreateResponse:

    run = await create_run(
        db=db,
        payload=payload,
    )

    start_background_task(
        run_workflow(
            run.id
        )
    )

    return RunCreateResponse(
        run_id=run.id,
        status=RunStatus(
            run.status
        ),
    )


# =====================================================
# GET RUN
# =====================================================


@router.get(
    "/{run_id}",
    response_model=RunRead,
)
async def get_run_endpoint(
    run_id: UUID,
    db: AsyncSession = Depends(
        get_db
    ),
) -> Run:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:

        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Run not found."
            ),
        )

    return run


# =====================================================
# GET RUN EVENTS
# =====================================================


@router.get(
    "/{run_id}/events",
    response_model=list[
        RunEventRead
    ],
)
async def get_run_events_endpoint(
    run_id: UUID,
    db: AsyncSession = Depends(
        get_db
    ),
) -> list:

    run = await get_run(
        db=db,
        run_id=run_id,
    )

    if run is None:

        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Run not found."
            ),
        )

    return await list_run_events(
        db=db,
        run_id=run_id,
    )


# =====================================================
# HUMAN DECISION ENDPOINT
# =====================================================


@router.post(
    "/{run_id}/decision",
    response_model=(
        RunDecisionResponse
    ),
)
async def make_run_decision(
    run_id: UUID,
    payload: RunDecisionRequest,
    db: AsyncSession = Depends(
        get_db
    ),
) -> RunDecisionResponse:

    # ==================================
    # 1. Candidate hypothesis selection
    # ==================================

    if (
        payload.type
        == DecisionType.CANDIDATE
    ):

        if payload.value is None:

            raise HTTPException(
                status_code=(
                    status
                    .HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    "Candidate decision "
                    "requires a hypothesis ID."
                ),
            )

        try:

            run = await select_hypothesis(
                db=db,
                run_id=run_id,
                hypothesis_id=(
                    payload.value
                ),
            )

        except ValueError as exc:

            raise HTTPException(
                status_code=(
                    status
                    .HTTP_409_CONFLICT
                ),
                detail=str(
                    exc
                ),
            ) from exc

        start_background_task(
            run_coder_workflow(
                run.id
            )
        )

        return RunDecisionResponse(
            run_id=run.id,
            status=run.status,
            selected_hypothesis_id=(
                payload.value
            ),
        )

    # ==================================
    # 2. Human approves PR creation
    # ==================================

    if (
        payload.type
        == DecisionType.PR_APPROVAL
    ):

        try:

            run = await approve_pr_creation(
                db=db,
                run_id=run_id,
            )

        except ValueError as exc:

            raise HTTPException(
                status_code=(
                    status
                    .HTTP_409_CONFLICT
                ),
                detail=str(
                    exc
                ),
            ) from exc

        # Actual GitHub work happens
        # asynchronously after approval.
        start_background_task(
            run_pr_workflow(
                run.id
            )
        )

        return RunDecisionResponse(
            run_id=run.id,
            status=run.status,
            selected_hypothesis_id=None,
        )

    # ==================================
    # 3. Human rejects PR creation
    # ==================================

    if (
        payload.type
        == DecisionType.REJECT
    ):

        try:

            run = await reject_pr_creation(
                db=db,
                run_id=run_id,
            )

        except ValueError as exc:

            raise HTTPException(
                status_code=(
                    status
                    .HTTP_409_CONFLICT
                ),
                detail=str(
                    exc
                ),
            ) from exc

        return RunDecisionResponse(
            run_id=run.id,
            status=run.status,
            selected_hypothesis_id=None,
        )

    # ==================================
    # 4. Unknown decision
    # ==================================

    raise HTTPException(
        status_code=(
            status
            .HTTP_501_NOT_IMPLEMENTED
        ),
        detail=(
            f"Decision type "
            f"'{payload.type.value}' "
            f"is not implemented."
        ),
    )


@router.post(
    "/{run_id}/retry-pr",
    response_model=(
        RunDecisionResponse
    ),
)
async def retry_pr_creation_endpoint(
    run_id: UUID,
    db: AsyncSession = Depends(
        get_db
    ),
) -> RunDecisionResponse:

    try:

        run = await prepare_pr_retry(
            db=db,
            run_id=run_id,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=(
                status
                .HTTP_409_CONFLICT
            ),
            detail=str(
                exc
            ),
        ) from exc

    start_background_task(
        run_pr_workflow(
            run.id
        )
    )

    return RunDecisionResponse(
        run_id=run.id,
        status=run.status,
        selected_hypothesis_id=None,
    )