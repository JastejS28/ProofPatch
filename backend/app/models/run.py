import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    repo_url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )

    target_file: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )

    target_function: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    problem_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    current_step: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    state_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )



#     TABLE
#     runs
# ------------------------------------------------
# id
# repo_url
# target_file
# target_function
# problem_description
# status
# current_step
# state_json
# created_at
# updated_at