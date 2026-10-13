from dataclasses import dataclass


@dataclass
class VerificationResult:
    passed: bool

    policy_passed: bool
    correctness_passed: bool
    performance_passed: bool

    reasons: list[str]


def verify_run_evidence(
    state: dict,
) -> VerificationResult:
    """
    Deterministically verify the current
    optimization candidate.

    No LLM calls are allowed here.
    """

    reasons: list[str] = []

    # -------------------------
    # 1. Static policy
    # -------------------------

    changes = state.get(
        "changes",
        {},
    )

    policy = changes.get(
        "policy",
        {},
    )

    policy_passed = bool(
        policy.get(
            "passed",
            False,
        )
    )

    if not policy_passed:
        reasons.append(
            "Static policy checks "
            "did not pass."
        )

    # -------------------------
    # 2. Correctness
    # -------------------------

    validation = state.get(
        "validation",
        {},
    )

    correctness_passed = bool(
        validation.get(
            "correctness_passed",
            False,
        )
    )

    if not correctness_passed:
        reasons.append(
            "Correctness validation "
            "did not pass."
        )

    # -------------------------
    # 3. Performance
    # -------------------------

    benchmark = state.get(
        "benchmark",
        {},
    )

    performance_passed = bool(
        benchmark.get(
            "passed",
            False,
        )
    )

    if not performance_passed:

        improvement = benchmark.get(
            "improvement_percent"
        )

        threshold = benchmark.get(
            "threshold_percent"
        )

        if (
            improvement is not None
            and threshold is not None
        ):
            reasons.append(
                "Performance improvement "
                f"was {improvement:.2f}% "
                "but required at least "
                f"{threshold:.2f}%."
            )

        else:
            reasons.append(
                "Performance improvement "
                "did not meet the required "
                "threshold."
            )

    # -------------------------
    # Final decision
    # -------------------------

    passed = (
        policy_passed
        and correctness_passed
        and performance_passed
    )

    return VerificationResult(
        passed=passed,
        policy_passed=(
            policy_passed
        ),
        correctness_passed=(
            correctness_passed
        ),
        performance_passed=(
            performance_passed
        ),
        reasons=reasons,
    )