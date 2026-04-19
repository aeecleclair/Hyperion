"""empty message

Create Date: 2026-03-27 23:23:07.797594
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

from app.types.sqlalchemy import TZDateTime

# revision identifiers, used by Alembic.
revision: str = "c052cfbe6d75"
down_revision: str | None = "46fbbcee7237"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tickets_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("open_datetime", TZDateTime(), nullable=False),
        sa.Column("close_datetime", TZDateTime(), nullable=True),
        sa.Column("quota", sa.Integer(), nullable=True),
        sa.Column("disabled", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["mypayment_store.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "tickets_category",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("quota", sa.Integer(), nullable=True),
        sa.Column("disabled", sa.Boolean(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("required_membership", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["tickets_event.id"],
        ),
        sa.ForeignKeyConstraint(
            ["required_membership"],
            ["core_association_membership.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "tickets_question",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.String(), nullable=False),
        sa.Column(
            "answer_type",
            sa.Enum("TEXT", "NUMBER", "BOOLEAN", name="answertype"),
            nullable=False,
        ),
        sa.Column("price", sa.Integer(), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("disabled", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["tickets_event.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "tickets_session",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("start_datetime", TZDateTime(), nullable=False),
        sa.Column("quota", sa.Integer(), nullable=True),
        sa.Column("disabled", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["tickets_event.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "tickets_checkout",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("expiration", TZDateTime(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("paid", sa.Boolean(), nullable=False),
        sa.Column("scanned", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["tickets_category.id"],
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["tickets_event.id"],
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["tickets_session.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["core_user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "tickets_answer",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("checkout_id", sa.Uuid(), nullable=False),
        sa.Column("answer", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["checkout_id"],
            ["tickets_checkout.id"],
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["tickets_question.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "calendar_events",
        sa.Column("ticket_event_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "calendar_events_ticket_event_id_fkey",
        "calendar_events",
        "tickets_event",
        ["ticket_event_id"],
        ["id"],
    )

    op.create_index(
        op.f("ix_tickets_answer_checkout_id"),
        "tickets_answer",
        ["checkout_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tickets_answer_question_id"),
        "tickets_answer",
        ["question_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tickets_category_event_id"),
        "tickets_category",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tickets_checkout_category_id"),
        "tickets_checkout",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tickets_checkout_event_id"),
        "tickets_checkout",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tickets_checkout_expiration"),
        "tickets_checkout",
        ["expiration"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tickets_checkout_paid"),
        "tickets_checkout",
        ["paid"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tickets_checkout_session_id"),
        "tickets_checkout",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tickets_checkout_user_id"),
        "tickets_checkout",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tickets_event_close_datetime"),
        "tickets_event",
        ["close_datetime"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tickets_event_disabled"),
        "tickets_event",
        ["disabled"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tickets_event_open_datetime"),
        "tickets_event",
        ["open_datetime"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tickets_event_store_id"),
        "tickets_event",
        ["store_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tickets_question_event_id"),
        "tickets_question",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tickets_session_event_id"),
        "tickets_session",
        ["event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_constraint(
        "calendar_events_ticket_event_id_fkey",
        "calendar_events",
        type_="foreignkey",
    )
    op.drop_table("tickets_answer")
    op.drop_table("tickets_question")
    op.drop_table("tickets_checkout")
    op.drop_table("tickets_session")
    op.drop_table("tickets_category")
    op.drop_table("tickets_event")
    sa.Enum("TEXT", "NUMBER", "BOOLEAN", name="answertype").drop(op.get_bind())


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
