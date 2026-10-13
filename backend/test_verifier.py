from app.verification.verifier import (
    verify_run_evidence,
)


good_state = {
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
        "improvement_percent": 40.0,
        "threshold_percent": 10.0,
    },
}


bad_performance_state = {
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
        "improvement_percent": 4.2,
        "threshold_percent": 10.0,
    },
}


print(
    verify_run_evidence(
        good_state
    )
)

print(
    verify_run_evidence(
        bad_performance_state
    )
)