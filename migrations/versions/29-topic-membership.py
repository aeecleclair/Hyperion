"""topic-membership

Create Date: 2025-02-24 15:41:08.215026
"""

from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

# revision identifiers, used by Alembic.
revision: str = "7da0e98a9e32"
down_revision: str | None = "c778706af06f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class Topic(str, Enum):
    cinema = "cinema"
    advert = "advert"
    amap = "amap"
    booking = "booking"
    event = "event"
    loan = "loan"
    raffle = "raffle"
    vote = "vote"
    ph = "ph"
    test = "test"


def upgrade() -> None:
    op.drop_table("notification_topic_membership")
    sa.Enum(Topic, name="topic").drop(op.get_bind())
    op.create_table(
        "notification_topic_membership",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "topic",
            sa.Enum(
                Topic,
                name="topic",
            ),
            nullable=False,
        ),
        sa.Column("topic_identifier", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["core_user.id"],
        ),
        sa.PrimaryKeyConstraint("user_id", "topic", "topic_identifier"),
    )
    op.create_index(
        op.f("ix_notification_topic_membership_topic"),
        "notification_topic_membership",
        ["topic"],
        unique=False,
    )

    notification_topic_membership_t = sa.Table(
        "notification_topic_membership",
        sa.MetaData(),
        sa.Column("user_id", sa.String),
        sa.Column("topic", sa.Enum(Topic, name="topic", nullable=False)),
        sa.Column("topic_identifier", sa.String),
    )

    bind = op.get_bind()

    users = bind.execute(sa.text("SELECT id FROM core_user")).fetchall()
    topics = [topic.value for topic in Topic]

    insert_values = [
        {"user_id": user_id, "topic": topic, "topic_identifier": ""}
        for (user_id,) in users
        for topic in topics
    ]

    if insert_values:
        bind.execute(
            sa.insert(notification_topic_membership_t).values(insert_values),
        )


def downgrade() -> None:
    pass


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    alembic_runner.insert_into(
        "core_user",
        {
            "id": "1356337e-d521-4910-889e-8bfa2c3c2f36",
            "email": "email54544326",
            "password_hash": "password_hash",
            "name": "name",
            "firstname": "firstname",
            "nickname": "nickname",
            "birthday": None,
            "promo": 21,
            "phone": None,
            "floor": "Autre",
            "created_on": None,
            "account_type": "student",
            "school_id": "dce19aa2-8863-4c93-861e-fb7be8f610ed",
        },
    )


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    table = alembic_connection.execute(
        sa.text("SELECT topic, user_id from notification_topic_membership"),
    ).fetchall()

    topics = [topic.value for topic in Topic]

    duos = {(topic, "a15e787d-e7ba-40b9-bfb4-d30de7c6aa28") for topic in topics}

    for duo in duos:
        assert duo in table
