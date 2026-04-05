import uuid

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from .base import MyModelMixin
from .project import Project




# -----------------------------------------------------------------------------
# HOW SQLAlchemy 2.0 MODELS WORK
#
# Old SQLAlchemy style (you might see this in tutorials):
#   id = Column(Integer, primary_key=True)
#
# New SQLAlchemy 2.0 style (what we use):
#   id: Mapped[int] = mapped_column(primary_key=True)
#
# The `Mapped[type]` annotation gives you full type safety — your editor
# knows that `user.id` is a uuid.UUID, not "any value". This catches bugs
# before you even run the code.
# -----------------------------------------------------------------------------


class User(Base, MyModelMixin):
    __tablename__ = "users"

    

    # unique=True creates a DB-level unique constraint — faster than app-level checks
    # index=True creates a B-tree index — makes lookups by email O(log n) not O(n)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # We store the full name as one field — simpler for freelancer context
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # NEVER store plain text passwords. This stores the bcrypt hash.
    # bcrypt is intentionally slow — makes brute force attacks impractical.
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Soft account control — instead of deleting users, we deactivate them
    # Deactivated users can't log in but their data (projects, invoices) stays intact
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Default hourly rate — used in invoice calculations
    # Stored as float here; in a real billing system you'd use Numeric(10,2)
    hourly_rate: Mapped[float] = mapped_column(default=0.0, nullable=False)

    # -----------------------------------------------------------------------------
    # RELATIONSHIPS
    # This tells SQLAlchemy: "a User has many Projects"
    # `back_populates` creates the reverse: project.owner → the User
    # `cascade="all, delete-orphan"` means if you delete a User,
    # all their Projects are automatically deleted too (like Django's CASCADE)
    # `lazy="selectin"` is important for async — it pre-loads related data
    # in a separate SELECT rather than lazy-loading (which breaks in async)
    # -----------------------------------------------------------------------------
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"