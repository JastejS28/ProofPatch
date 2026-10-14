from app.verification.verifier import (
    VerificationResult,
    verify_run_evidence,
)


def test_verifier_passes_when_all_checks_pass():

    state = {
        "changes": {
            "policy": {
                "passed": True,
            }
        },
        "validation": {
            "correctness_passed": True,
        },
        "benchmark": {
            "passed": True,
        },
    }

    result = verify_run_evidence(
        state
    )

    assert isinstance(
        result,
        VerificationResult,
    )

    assert result.passed is True
    assert result.policy_passed is True

    assert (
        result.correctness_passed
        is True
    )

    assert (
        result.performance_passed
        is True
    )

    assert result.reasons == []


def test_verifier_fails_policy():

    state = {
        "changes": {
            "policy": {
                "passed": False,
            }
        },
        "validation": {
            "correctness_passed": True,
        },
        "benchmark": {
            "passed": True,
        },
    }

    result = verify_run_evidence(
        state
    )

    assert result.passed is False
    assert result.policy_passed is False

    assert (
        result.correctness_passed
        is True
    )

    assert (
        result.performance_passed
        is True
    )

    assert (
        "Static policy checks "
        "did not pass."
        in result.reasons
    )


def test_verifier_fails_correctness():

    state = {
        "changes": {
            "policy": {
                "passed": True,
            }
        },
        "validation": {
            "correctness_passed": False,
        },
        "benchmark": {
            "passed": True,
        },
    }

    result = verify_run_evidence(
        state
    )

    assert result.passed is False

    assert (
        result.policy_passed
        is True
    )

    assert (
        result.correctness_passed
        is False
    )

    assert (
        result.performance_passed
        is True
    )

    assert (
        "Correctness validation "
        "did not pass."
        in result.reasons
    )


def test_verifier_fails_benchmark():

    state = {
        "changes": {
            "policy": {
                "passed": True,
            }
        },
        "validation": {
            "correctness_passed": True,
        },
        "benchmark": {
            "passed": False,
            "improvement_percent": 5.0,
            "threshold_percent": 10.0,
        },
    }

    result = verify_run_evidence(
        state
    )

    assert result.passed is False

    assert (
        result.policy_passed
        is True
    )

    assert (
        result.correctness_passed
        is True
    )

    assert (
        result.performance_passed
        is False
    )

    assert len(
        result.reasons
    ) == 1

    assert (
        "5.00%"
        in result.reasons[0]
    )

    assert (
        "10.00%"
        in result.reasons[0]
    )


def test_verifier_fails_when_evidence_missing():

    state = {}

    result = verify_run_evidence(
        state
    )

    assert result.passed is False

    assert (
        result.policy_passed
        is False
    )

    assert (
        result.correctness_passed
        is False
    )

    assert (
        result.performance_passed
        is False
    )

    assert len(
        result.reasons
    ) == 3