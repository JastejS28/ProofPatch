from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class DecisionType(StrEnum):
    CANDIDATE = "candidate"
    PR_APPROVAL = "pr_approval"
    REJECT = "reject"


class RunDecisionRequest(BaseModel):
    type: DecisionType
    value: UUID | None = None


class RunDecisionResponse(BaseModel):
    run_id: UUID
    status: str
    selected_hypothesis_id: UUID | None = None