from datetime import datetime

from sqlalchemy import DateTime, Identity, Integer, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Explicit constraint names. Without this, PostgreSQL invents names and Alembic
# migrations that drop/alter constraints become fragile.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# Column order in a table = order of creation. Columns that come from mixins would
# otherwise be appended after the model's own columns, so `sort_order` pins them:
# the primary key first, audit timestamps last, everything else in declaration order.
_FIRST = -100
_LAST_CREATED = 9998
_LAST_UPDATED = 9999


class IntPrimaryKeyMixin:
    """Auto-incrementing integer primary key (PostgreSQL identity column, starts at 1).
    Short and readable in citations and logs ("document 3, page 2"). The id exists only
    after INSERT/flush, and ids are sequential (fine: there are no public/guessable ids)."""

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(),
        primary_key=True,
        sort_order=_FIRST,
        comment="Surrogate primary key (auto-increment from 1).",
    )


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        sort_order=_LAST_CREATED,
        comment="Row creation time (UTC).",
    )


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        sort_order=_LAST_UPDATED,
        comment="Time of the last update to this row (UTC).",
    )
