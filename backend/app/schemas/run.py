from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.domain.run_status import RunStatus


class RunCreate(BaseModel):
    repo_url: HttpUrl

    target_file: str = Field(
        min_length=1,
        max_length=1024,
    )

    target_function: str = Field(
        min_length=1,
        max_length=255,
    )

    problem_description: str = Field(
        min_length=5,
        max_length=4000,
    )


class RunCreateResponse(BaseModel):
    run_id: UUID
    status: RunStatus


class RunRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    repo_url: str
    target_file: str
    target_function: str
    problem_description: str

    status: RunStatus
    current_step: str
    state_json: dict

    created_at: datetime
    updated_at: datetime


class RunEventRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    run_id: UUID
    timestamp: datetime
    event_type: str
    payload_json: dict


    # PYDNATIC SCHEMAS