import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class MyModelMixin:
    """
    Adds id, created_at, updated_at, deleted to any model that inherits this.
    `server_default=func.now()` means PostgreSQL itself sets the timestamp
    — not Python. More reliable: no timezone mismatch between app and DB.

    `deleted` is for soft delete — instead of removing rows from the DB,
    we mark them deleted=True. This preserves history (important for invoices,
    audit trails) and makes accidental deletions recoverable.
    """

    # Primary key as UUID — PostgreSQL stores this natively and efficiently
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,         # Python generates the UUID before INSERT
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),  # DB sets this on INSERT
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),        # DB updates this on every UPDATE
        nullable=False,
    )

    # -----------------------------------------------------------------------------
    # SOFT DELETE — why index=True matters here
    #
    # Almost every query will have WHERE deleted = false in it.
    # Without an index, PostgreSQL scans EVERY row to check this condition.
    # With index=True, it uses a B-tree index — much faster on large tables.
    #
    # In services, we'll always filter: .where(Model.deleted == False)
    # Never expose deleted records to the API.
    # -----------------------------------------------------------------------------
    deleted: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
    )


__all__ = ["MyModelMixin"]