"""empty message

Create Date: 2025-08-10 15:40:44.191402
"""

from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

from app.types.sqlalchemy import TZDateTime

# revision identifiers, used by Alembic.
revision: str = "ca44192be52b"
down_revision: str | None = "2ca210263c74"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class Status(str, Enum):
    WAITING_APPROVAL = "WAITING_APPROVAL"
    REJECTED = "REJECTED"
    PUBLISHED = "PUBLISHED"


def upgrade() -> None:
    op.create_table(
        "feed_news",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("start", TZDateTime(), nullable=False),
        sa.Column("end", TZDateTime(), nullable=True),
        sa.Column("entity", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("action_start", TZDateTime(), nullable=True),
        sa.Column("module", sa.String(), nullable=False),
        sa.Column("module_object_id", sa.Uuid(), nullable=False),
        sa.Column("image_directory", sa.String(), nullable=False),
        sa.Column("image_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(Status, name="newsstatus"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "advert_adverts",
        sa.Column(
            "post_to_feed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.false(),
        ),
    )
    op.drop_column("advert_adverts", "tags")


def downgrade() -> None:
    op.add_column(
        "advert_adverts",
        sa.Column("tags", sa.String(), nullable=False, server_default=""),
    )
    op.drop_column("advert_adverts", "post_to_feed")
    op.drop_table("feed_news")
    sa.Enum(Status, name="newsstatus").drop(
        op.get_bind(),
    )


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    pass


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    pass
