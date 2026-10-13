import traceback
from pathlib import Path
from uuid import UUID

from app.agents.coder import (
    generate_candidate,
)
from app.context.coder_context import (
    build_coder_context,
)
from app.db.session import (
    AsyncSessionLocal,
)
from app.domain.run_status import (
    RunStatus,
)
from app.llm.factory import (
    get_llm_provider,
)
from app.policy.change_policy import (
    check_change_policy,
)
from app.repository.git_diff import (
    GitDiffError,
    get_changed_files,
    get_diff,
)
from app.repository.patcher import (
    PatchError,
    apply_function_replacement,
)
from app.services.run_service import (
    fail_run,
    get_run,
    get_selected_hypothesis,
    save_candidate_change,
    transition_run,
)
from app.workers.validation_worker import (
    run_validation_workflow,
)


async def run_coder_workflow(
    run_id: UUID,
) -> None:

    async with AsyncSessionLocal() as db:
        try:
            # 1. Load the run
            run = await get_run(
                db=db,
                run_id=run_id,
            )

            if run is None:
                return

            # 2. Find the hypothesis selected by the user
            selected_hypothesis = (
                await get_selected_hypothesis(
                    db=db,
                    run_id=run_id,
                )
            )

            if selected_hypothesis is None:
                await fail_run(
                    db=db,
                    run_id=run_id,
                    message=(
                        "No selected hypothesis "
                        "was found."
                    ),
                )
                return

            # 3. Move workflow into MODIFYING
            await transition_run(
                db=db,
                run_id=run_id,
                status=RunStatus.MODIFYING,
                message=(
                    "Coder implementation "
                    "started."
                ),
            )

            # 4. Read current run state
            state = dict(
                run.state_json
            )

            workspace = Path(
                state["workspace_ref"]
            )

            repository_summary = (
                state[
                    "repository_summary"
                ]
            )

            # 5. Convert selected hypothesis DB model
            #    into simple dict for prompt/context
            hypothesis_data = {
                "id": str(
                    selected_hypothesis.id
                ),
                "summary":
                    selected_hypothesis.summary,
                "mechanism":
                    selected_hypothesis.mechanism,
                "expected_effect":
                    selected_hypothesis.expected_effect,
                "trade_offs":
                    selected_hypothesis.trade_offs,
            }

            # 6. Build focused Coder context
            coder_context = (
                build_coder_context(
                    workspace=workspace,
                    repository_summary=(
                        repository_summary
                    ),
                    problem_description=(
                        run.problem_description
                    ),
                    selected_hypothesis=(
                        hypothesis_data
                    ),
                )
            )

            # 7. Select Ollama/Gemini provider
            provider = get_llm_provider()

            # 8. Ask Coder LLM for replacement function
            coder_output = (
                await generate_candidate(
                    provider=provider,
                    context=coder_context,
                )
            )

            # 9. Rebuild Python source from structured lines
            replacement_function = "\n".join(
                coder_output
                .replacement_function_lines
            )

            # Temporary development logging
            print(
                "\n========== CODER REPLACEMENT =========="
            )
            print(
                replacement_function
            )
            print(
                "========================================\n"
            )

            # 10. Replace only the target function
            patch_result = (
                apply_function_replacement(
                    workspace=workspace,
                    target_file=(
                        run.target_file
                    ),
                    target_function=(
                        run.target_function
                    ),
                    replacement_source=(
                        replacement_function
                    ),
                )
            )

            # 11. Ask Git what files changed
            changed_files = (
                await get_changed_files(
                    workspace
                )
            )

            # 12. Capture exact target-file diff
            diff = await get_diff(
                workspace=workspace,
                target_file=(
                    run.target_file
                ),
            )

            # 13. Run deterministic static policy checks
            policy = (
                await check_change_policy(
                    workspace=workspace,
                    target_file=(
                        run.target_file
                    ),
                    target_function=(
                        run.target_function
                    ),
                    changed_files=(
                        changed_files
                    ),
                )
            )

            policy_data = {
                "passed":
                    policy.passed,
                "reasons":
                    policy.reasons,
                "changed_files":
                    changed_files,
            }

            # 14. Save patch + diff + policy evidence
            #
            # We save even if policy failed because
            # the rejected patch is still useful evidence.
            await save_candidate_change(
                db=db,
                run_id=run_id,
                selected_hypothesis_id=(
                    selected_hypothesis.id
                ),
                original_function=(
                    patch_result
                    .original_function
                ),
                candidate_function=(
                    patch_result
                    .candidate_function
                ),
                diff=diff,
                policy_result=(
                    policy_data
                ),
                change_summary=(
                    coder_output
                    .change_summary
                ),
                expected_mechanism=(
                    coder_output
                    .expected_mechanism
                ),
            )

            # 15. STOP before execution if static policy fails
            if not policy.passed:
                await fail_run(
                    db=db,
                    run_id=run_id,
                    message=(
                        "Candidate failed static "
                        "policy checks: "
                        + "; ".join(
                            policy.reasons
                        )
                    ),
                )
                return

            # 16. Static checks passed.
            # Now execute baseline/candidate tests
            # inside the Docker sandbox.
            await run_validation_workflow(
                run_id
            )

        except (
            PatchError,
            GitDiffError,
        ) as exc:
            await fail_run(
                db=db,
                run_id=run_id,
                message=str(exc),
            )

        except Exception as exc:
            traceback.print_exc()

            await fail_run(
                db=db,
                run_id=run_id,
                message=(
                    "Unexpected coder workflow "
                    "error: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )