from pydantic import BaseModel, Field


class CoderOutput(BaseModel):
    replacement_function_lines: list[str] = Field(
        min_length=2,
    )

    change_summary: str = Field(
        min_length=5,
        max_length=500,
    )

    expected_mechanism: str = Field(
        min_length=5,
        max_length=1000,
    )