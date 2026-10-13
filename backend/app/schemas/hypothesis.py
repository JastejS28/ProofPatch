from pydantic import BaseModel, Field


class OptimizationHypothesis(BaseModel):
    summary: str = Field(
        min_length=5,
        max_length=300,
    )

    mechanism: str = Field(
        min_length=10,
        max_length=1000,
    )

    expected_effect: str = Field(
        min_length=5,
        max_length=500,
    )

    trade_offs: str = Field(
        min_length=1,
        max_length=500,
    )


class ScientistOutput(BaseModel):
    hypotheses: list[OptimizationHypothesis] = Field(
        min_length=1,
        max_length=3,
    )