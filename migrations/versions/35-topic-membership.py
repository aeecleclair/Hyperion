"""topic-membership

Create Date: 2025-02-24 15:41:08.215026
"""

import uuid
from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

from app.core.groups.groups_type import GroupType
from app.types.sqlalchemy import TZDateTime

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

# revision identifiers, used by Alembic.
revision: str = "7da0e98a9e32"
down_revision: str | None = "d14266761430"
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
    op.create_table(
        "notification_topic",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("module_root", sa.String(), nullable=False),
        sa.Column("topic_identifier", sa.String(), nullable=True),
        sa.Column("restrict_to_group_id", sa.String(), nullable=True),
        sa.Column("restrict_to_members", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["restrict_to_group_id"],
            ["core_group.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # We completely changed how topics are stored in database. We can thus drop the content of existing tables
    op.drop_table("notification_topic_membership")

    op.create_table(
        "notification_topic_membership",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["core_user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["notification_topic.id"],
        ),
        sa.PrimaryKeyConstraint("user_id", "topic_id"),
    )

    op.drop_index("ix_notification_message_context", table_name="notification_message")
    op.drop_index(
        "ix_notification_message_firebase_device_token",
        table_name="notification_message",
    )
    # Message is not used anymore
    op.drop_table("notification_message")

    sa.Enum(Topic, name="topic").drop(op.get_bind())

    # We can manually create a topic for each advertisers
    # Define the advertiser table so we can query it
    advertiser_table = sa.table(
        "advert_advertisers",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
    )

    # Query all advertisers
    conn = op.get_bind()
    advertisers = conn.execute(
        sa.select(advertiser_table.c.id, advertiser_table.c.name),
    ).fetchall()

    # Define the notification_topic table to allow insertions
    notification_topic_table = sa.table(
        "notification_topic",
        sa.column("id", sa.Uuid),
        sa.column("name", sa.String),
        sa.column("module_root", sa.String),
        sa.column("topic_identifier", sa.String),
        sa.column("restrict_to_group_id", sa.String),
        sa.column("restrict_to_members", sa.Boolean),
    )

    # Insert a topic for each advertiser
    for advertiser_id, advertiser_name in advertisers:
        conn.execute(
            notification_topic_table.insert().values(
                id=uuid.uuid4(),
                name=f"📣 Annonce - {advertiser_name}",
                module_root="advert",
                topic_identifier=advertiser_id,
                restrict_to_group_id=None,
                restrict_to_members=True,
            ),
        )


def downgrade() -> None:
    op.drop_table("notification_topic_membership")

    op.create_table(
        "notification_topic_membership",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "topic",
            sa.Enum(
                "cinema",
                "advert",
                "amap",
                "booking",
                "event",
                "loan",
                "raffle",
                "vote",
                "ph",
                "test",
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

    op.drop_table("notification_topic")

    op.create_table(
        "notification_message",
        sa.Column("context", sa.String(), nullable=False),
        sa.Column("firebase_device_token", sa.String(), nullable=False),
        sa.Column("is_visible", sa.Boolean(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("content", sa.String(), nullable=True),
        sa.Column("action_module", sa.String(), nullable=True),
        sa.Column("action_table", sa.String(), nullable=True),
        sa.Column("delivery_datetime", TZDateTime(), nullable=True),
        sa.Column("expire_on", TZDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("context", "firebase_device_token"),
    )
    op.create_index(
        op.f("ix_notification_message_context"),
        "notification_message",
        ["context"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_message_firebase_device_token"),
        "notification_message",
        ["firebase_device_token"],
        unique=False,
    )


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    alembic_runner.insert_into(
        "advert_advertisers",
        {
            "id": uuid.uuid4(),
            "name": "test_advertiser",
            "group_manager_id": GroupType.admin.value,
        },
    )


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    memberships = alembic_connection.execute(
        sa.text("SELECT * FROM notification_topic"),
    ).all()
    assert len(memberships) == 1
    assert memberships[0][1] == "📣 Annonce - test_advertiser"
