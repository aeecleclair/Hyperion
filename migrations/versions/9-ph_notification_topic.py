"""empty message

Create Date: 2024-04-25 19:44:53.520776
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b2d2f884627"
down_revision: str | None = "44fc1e13f47a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("notification_topic_membership") as batch_op:
        batch_op.alter_column(
            "topic",
            existing_type=sa.VARCHAR(length=23),
            type_=sa.Enum(
                "cinema",
                "advert",
                "bookingadmin",
                "amap",
                "booking",
                "event",
                "loan",
                "raffle",
                "vote",
                "ph",
                name="topic",
            ),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("notification_topic_membership") as batch_op:
        batch_op.alter_column(
            "topic",
            existing_type=sa.VARCHAR(length=23),
            type_=sa.Enum(
                "cinema",
                "advert",
                "bookingadmin",
                "amap",
                "booking",
                "event",
                "loan",
                "raffle",
                "vote",
                name="topic",
            ),
            existing_nullable=False,
        )
