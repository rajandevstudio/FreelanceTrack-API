import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, Text, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from .base import MyModelMixin
from .project import Project


class TimeLog(Base, MyModelMixin):
    """
    Represents one time entry — like a single row in a timesheet.

    Example: "I worked 3.5 hours on the BillBolo API integration on April 5th"
      → hours=3.5, description="API integration", work_date=2026-04-05
    """

    __tablename__ = "time_logs"



    # -----------------------------------------------------------------------------
    # Numeric(5, 2) for hours means: up to 999.99 hours
    # Why not just an integer? Freelancers often log 1.5h or 2.25h
    # Numeric ensures precision — no floating point errors in totals
    # -----------------------------------------------------------------------------
    hours: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    # What did we actually work on? Good for invoice line items.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Date the work was done — separate from created_at (we might log yesterday's work today)
    # `date` type stores only the date, not time — perfect for timesheets
    work_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Which project this log belongs to
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    project: Mapped["Project"] = relationship("Project", back_populates="time_logs")

    def __repr__(self) -> str:
        return f"<TimeLog {self.hours}h on {self.work_date}>"