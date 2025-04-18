"""booking-type

Create Date: 2025-02-03 02:56:24.302160
"""

from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c778706af06f"
down_revision: str | None = "a1e6e8b52103"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class Decision(str, Enum):
    approved = "approved"
    declined = "declined"
    pending = "pending"


old_booking_table = sa.Table(
    "booking",
    sa.MetaData(),
    sa.Column("id", sa.String(), primary_key=True, index=True),
    sa.Column("decision", sa.String(), nullable=False),
)
new_booking_table = sa.Table(
    "booking",
    sa.MetaData(),
    sa.Column("id", sa.String(), primary_key=True, index=True),
    sa.Column("decision", sa.Enum(Decision), nullable=False),
)


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    conn = op.get_bind()
    booking_content = conn.execute(sa.select(old_booking_table)).fetchall()
    op.drop_column("booking", "decision")

    sa.Enum(Decision, name="decision").create(op.get_bind())
    op.add_column(
        "booking",
        sa.Column(
            "decision",
            sa.Enum(Decision, name="decision"),
            nullable=False,
            server_default="pending",
        ),
    )
    for booking in booking_content:
        # print(booking)
        conn.execute(
            sa.update(new_booking_table)
            .where(new_booking_table.c.id == booking[0])
            .values(decision=Decision(booking[1])),
        )

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    conn = op.get_bind()
    booking_content = conn.execute(sa.select(new_booking_table))
    op.drop_column("booking", "decision")
    op.add_column("booking", sa.Column("decision", sa.String(), nullable=False))
    for booking in booking_content:
        conn.execute(
            sa.update(old_booking_table)
            .where(old_booking_table.c.id == booking[0])
            .values(decision=booking[1].value),
        )
    sa.Enum(name="decision").drop(op.get_bind())
    # ### end Alembic commands ###


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    alembic_runner.insert_into(
        "core_user",
        {
            "id": "a15e787d-e7ba-40b9-bfb4-d30de7c6aa28",
            "email": "email54546",
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
    alembic_runner.insert_into(
        "core_group",
        {
            "id": "4b1095b7-fd92-46bd-9113-3040f290ac15",
            "name": "name",
        },
    )
    alembic_runner.insert_into(
        "booking_manager",
        {
            "id": "377ed2df-ad0c-4730-b48d-d895e369f7e7",
            "name": "name",
            "group_id": "4b1095b7-fd92-46bd-9113-3040f290ac15",
        },
    )
    alembic_runner.insert_into(
        "booking_room",
        {
            "id": "d2e6d1f4-3f6d-4b6b-9c1e-0b0b1d0d1b2b",
            "name": "name",
            "manager_id": "377ed2df-ad0c-4730-b48d-d895e369f7e7",
        },
    )
    alembic_runner.insert_into(
        "booking",
        {
            "id": "669b61e9-4f95-403a-bef2-d567fd1ca335",
            "reason": "reason",
            "start": datetime.fromisoformat("2025-02-03T02:56:24.302160"),
            "end": datetime.fromisoformat("2025-02-03T03:56:24.302160"),
            "creation": datetime.fromisoformat("2025-02-03T02:56:24.302160"),
            "note": "note",
            "room_id": "d2e6d1f4-3f6d-4b6b-9c1e-0b0b1d0d1b2b",
            "key": True,
            "entity": "entity",
            "decision": "approved",
            "applicant_id": "a15e787d-e7ba-40b9-bfb4-d30de7c6aa28",
        },
    )
    alembic_runner.insert_into(
        "booking",
        {
            "id": "eee8c5d4-b8fc-4159-b249-1fcaa28066da",
            "reason": "reason",
            "start": datetime.fromisoformat("2025-02-04T02:56:24.302160"),
            "end": datetime.fromisoformat("2025-02-04T03:56:24.302160"),
            "creation": datetime.fromisoformat("2025-02-04T02:56:24.302160"),
            "note": "note",
            "room_id": "d2e6d1f4-3f6d-4b6b-9c1e-0b0b1d0d1b2b",
            "key": True,
            "entity": "entity",
            "decision": "pending",
            "applicant_id": "a15e787d-e7ba-40b9-bfb4-d30de7c6aa28",
        },
    )
    alembic_runner.insert_into(
        "booking",
        {
            "id": "ff24fe5c-ddf9-475a-98ac-ed82bcfef606",
            "reason": "reason",
            "start": datetime.fromisoformat("2025-02-05T02:56:24.302160"),
            "end": datetime.fromisoformat("2025-02-05T03:56:24.302160"),
            "creation": datetime.fromisoformat("2025-02-05T02:56:24.302160"),
            "note": "note",
            "room_id": "d2e6d1f4-3f6d-4b6b-9c1e-0b0b1d0d1b2b",
            "key": True,
            "entity": "entity",
            "decision": "declined",
            "applicant_id": "a15e787d-e7ba-40b9-bfb4-d30de7c6aa28",
        },
    )


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    booking = alembic_connection.execute(
        sa.select(new_booking_table),
    ).fetchall()
    assert len(booking) == 3
    assert booking[0][1] == Decision.approved
    assert booking[1][1] == Decision.pending
    assert booking[2][1] == Decision.declined
