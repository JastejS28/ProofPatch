import traceback
from pathlib import Path
from uuid import UUID

from app.context.planning_context import (
    ContextBudgetError,
    build_planning_context,
)
from app.core.config import settings
from app.db.session import (
    AsyncSessionLocal,
)
from app.domain.run_status import (
    RunStatus,
)
from app.graphs.planning_graph import (
    planning_graph,
)
from app.llm.errors import (
    LLMQuotaExceededError,
    LLMRequestError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.repository.analyzer import (
    RepositoryAnalysisError,
    analyze_target_function,
)
from app.repository.clone import (
    CloneError,
    clone_repository,
)
from app.repository.github import (
    RepositoryValidationError,
    validate_public_repository,
)
from app.repository.purity import (
    check_function_purity,
)
from app.repository.workspace import (
    prepare_run_workspace,
)
from app.services.run_service import (
    fail_run,
    get_run,
    save_hypotheses,
    save_repository_analysis,
    transition_run,
)


async def run_workflow(
    run_id: UUID,
) -> None:

    async with AsyncSessionLocal() as db:

        try:
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
            # 2. Initialization
            # -------------------------

            await transition_run(
                db=db,
                run_id=run_id,
                status=(
                    RunStatus.INITIALIZING
                ),
                message=(
                    "Repository initialization "
                    "started."
                ),
            )

            # -------------------------
            # 3. Validate GitHub repo
            # -------------------------

            repository = (
                await validate_public_repository(
                    run.repo_url
                )
            )

            # -------------------------
            # 4. Prepare workspace
            # -------------------------

            workspace = (
                prepare_run_workspace(
                    run_id
                )
            )

            # -------------------------
            # 5. Clone repo
            # -------------------------

            await clone_repository(
                clone_url=(
                    repository.clone_url
                ),
                destination=workspace,
            )

            # -------------------------
            # 6. Analysis stage
            # -------------------------

            await transition_run(
                db=db,
                run_id=run_id,
                status=(
                    RunStatus.ANALYZING
                ),
                message=(
                    "Repository cloned "
                    "successfully."
                ),
            )

            # -------------------------
            # 7. Static target analysis
            # -------------------------

            analysis = (
                analyze_target_function(
                    workspace=workspace,
                    target_file=(
                        run.target_file
                    ),
                    target_function=(
                        run.target_function
                    ),
                )
            )

            # -------------------------
            # 8. Purity pre-check
            # -------------------------

            purity = (
                check_function_purity(
                    analysis.node
                )
            )

            repository_summary = {
                "owner":
                    repository.owner,

                "repository":
                    repository.name,

                "target_function":
                    analysis.name,

                "signature":
                    analysis.signature,

                "source":
                    analysis.source,

                "line_start":
                    analysis.line_start,

                "line_end":
                    analysis.line_end,

                "imports":
                    analysis.imports,

                "related_test_files":
                    analysis.related_test_files,
            }

            purity_check = {
                "passed":
                    purity.passed,

                "reasons":
                    purity.reasons,
            }

            # -------------------------
            # 9. Persist analysis
            # -------------------------

            await save_repository_analysis(
                db=db,
                run_id=run_id,
                workspace_ref=str(
                    workspace
                ),
                repository_summary=(
                    repository_summary
                ),
                purity_check=(
                    purity_check
                ),
            )

            # -------------------------
            # 10. Stop if unsafe target
            # -------------------------

            if not purity.passed:
                await fail_run(
                    db=db,
                    run_id=run_id,
                    message=(
                        "Target function failed "
                        "the V1 purity pre-check: "
                        + "; ".join(
                            purity.reasons
                        )
                    ),
                )

                return

            # -------------------------
            # 11. Build Scientist context
            # -------------------------

            planning_context = (
                build_planning_context(
                    workspace=Path(
                        workspace
                    ),
                    repository_summary=(
                        repository_summary
                    ),
                    problem_description=(
                        run
                        .problem_description
                    ),
                    token_budget=(
                        settings
                        .planning_token_budget
                    ),
                )
            )

            # -------------------------
            # 12. Scientist / LLM call
            # -------------------------

            graph_result = (
                await planning_graph.ainvoke(
                    {
                        "context":
                            planning_context,

                        "hypotheses":
                            [],
                    }
                )
            )

            # -------------------------
            # 13. Read hypotheses
            # -------------------------

            hypotheses = (
                graph_result.get(
                    "hypotheses",
                    [],
                )
            )

            if not hypotheses:
                await fail_run(
                    db=db,
                    run_id=run_id,
                    message=(
                        "Scientist returned no "
                        "optimization hypotheses."
                    ),
                )

                return

            # -------------------------
            # 14. Save hypotheses
            # -------------------------

            await save_hypotheses(
                db=db,
                run_id=run_id,
                hypotheses=hypotheses,
            )

        # -------------------------
        # Repository / context errors
        # -------------------------

        except (
            RepositoryValidationError,
            CloneError,
            RepositoryAnalysisError,
            ContextBudgetError,
        ) as exc:

            await fail_run(
                db=db,
                run_id=run_id,
                message=str(exc),
            )

        # -------------------------
        # Gemini/free-tier quota
        # -------------------------

        except LLMQuotaExceededError as exc:

            await fail_run(
                db=db,
                run_id=run_id,
                message=str(exc),
            )

        # -------------------------
        # LLM timeout
        # -------------------------

        except LLMTimeoutError as exc:

            await fail_run(
                db=db,
                run_id=run_id,
                message=str(exc),
            )

        # -------------------------
        # Provider temporarily down
        # -------------------------

        except LLMUnavailableError as exc:

            await fail_run(
                db=db,
                run_id=run_id,
                message=str(exc),
            )

        # -------------------------
        # Bad LLM request / response
        # -------------------------

        except LLMRequestError as exc:

            await fail_run(
                db=db,
                run_id=run_id,
                message=str(exc),
            )

        # -------------------------
        # Unexpected failure
        # -------------------------

        except Exception as exc:

            traceback.print_exc()

            await fail_run(
                db=db,
                run_id=run_id,
                message=(
                    "Unexpected workflow error: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )