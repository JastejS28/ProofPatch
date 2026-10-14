from pydantic import BaseModel, Field


class ReviewerOutput(BaseModel):
    summary: str = Field(
        min_length=1,
    )

    change_explanation: str = Field(
        min_length=1,
    )

    correctness_summary: str = Field(
        min_length=1,
    )

    performance_summary: str = Field(
        min_length=1,
    )

    risks_and_tradeoffs: list[str] = Field(
        default_factory=list,
    )

    recommendation: str = Field(
        min_length=1,
    )