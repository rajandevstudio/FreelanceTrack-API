from __future__ import annotations


import uuid
from enum import Enum

from sqlalchemy import String, Text, ForeignKey, Numeric, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import MyModelMixin

 
from typing import TYPE_CHECKING
 

if TYPE_CHECKING:
    # This block ONLY runs for static analysers (Pylance, mypy) — never at runtime.
    # So there's no circular import. Python skips this entire block when actually running.
    from app.models.timelog import TimeLog
    from app.models.user import User



# -----------------------------------------------------------------------------
# WHY ENUM FOR STATUS?
#
# We could store status as a plain string — "active", "completed", etc.
# But enums give us two advantages:
#   1. Python-side: our editor autocompletes valid values, typos are caught
#   2. DB-side: PostgreSQL creates a real ENUM type, invalid values are rejected
#      at the database level — not just the app level
#
# This is defense in depth — validation at multiple layers.
# -----------------------------------------------------------------------------


class ProjectStatus(str, Enum):
    """
    Inheriting from both `str` and `Enum` means:
    - It behaves like a string (can be serialized to JSON directly)
    - It behaves like an enum (only valid values allowed)
    Pydantic v2 handles `str` Enums natively — no extra config needed.
    """
    ACTIVE = "active"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class Project(Base, MyModelMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Text is unlimited length — good for descriptions, notes
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ProjectStatus enum — maps to a PostgreSQL ENUM column
    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(ProjectStatus, name="project_status"),  # name= is the PG type name
        default=ProjectStatus.ACTIVE,
        nullable=False,
    )

    # -----------------------------------------------------------------------------
    # NUMERIC vs FLOAT for money
    #
    # hourly_rate is Numeric(10, 2) — this means:
    #   - Up to 10 digits total
    #   - Exactly 2 decimal places
    #   - NO floating point errors (0.1 + 0.2 == 0.30, not 0.30000000004)
    #
    # Always use Numeric (not Float) when storing money. Float is approximate.
    # This is a common junior developer mistake.
    # -----------------------------------------------------------------------------
    hourly_rate: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0.0,
    )

    # Optional fixed budget — some projects are fixed price, not hourly
    budget: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Client name — simple string for now, could be a FK to a Clients table later
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # -----------------------------------------------------------------------------
    # FOREIGN KEY
    # ForeignKey("users.id") links this column to the `id` column in the `users` table
    # ondelete="CASCADE" — if the user is deleted, their projects are deleted too
    # (this is the DB-level cascade; SQLAlchemy's cascade handles the ORM level)
    # index=True — we'll often query "projects WHERE owner_id = ?" so index it
    # -----------------------------------------------------------------------------
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="projects")

    time_logs: Mapped[list["TimeLog"]] = relationship(
        "TimeLog",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def total_hours(self) -> float:
        """Sum of all logged hours — computed in Python, not SQL."""
        return sum(log.hours for log in self.time_logs)

    @property
    def total_earned(self) -> float:
        """Total earnings = hours × rate."""
        return round(self.total_hours * float(self.hourly_rate), 2)

    def __repr__(self) -> str:
        return f"<Project {self.name} ({self.status})>"