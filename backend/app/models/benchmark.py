import uuid

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Integer,
)
from sqlalchemy.dialects.postgresql import (
    UUID,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.db.base import Base


class Benchmark(Base):
    __tablename__ = "benchmarks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "runs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    iteration: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    baseline_median_seconds: Mapped[float] = (
        mapped_column(
            Float,
            nullable=False,
        )
    )

    candidate_median_seconds: Mapped[float] = (
        mapped_column(
            Float,
            nullable=False,
        )
    )

    improvement_percent: Mapped[float] = (
        mapped_column(
            Float,
            nullable=False,
        )
    )

    threshold_percent: Mapped[float] = (
        mapped_column(
            Float,
            nullable=False,
        )
    )

    passed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )