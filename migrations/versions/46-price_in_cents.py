"""empty message

Create Date: 2025-02-25 13:45:05.381491
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING
from uuid import uuid4

from app.core.schools.schools_type import SchoolType
from app.modules.raffle.types_raffle import RaffleStatusType

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4ae072a7e867"
down_revision: str | None = "91fadc90f892"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE amap_cash SET balance = balance * 100")
    op.execute("UPDATE amap_order SET amount = amount * 100")
    op.execute("UPDATE amap_product SET price = price * 100")
    op.execute("UPDATE raffle_cash SET balance = balance * 100")
    op.execute("UPDATE raffle_pack_ticket SET price = price * 100")

    op.alter_column(
        "amap_cash",
        "balance",
        existing_type=sa.FLOAT(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "amap_order",
        "amount",
        existing_type=sa.FLOAT(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "amap_product",
        "price",
        existing_type=sa.FLOAT(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "raffle_cash",
        "balance",
        existing_type=sa.FLOAT(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "raffle_pack_ticket",
        "price",
        existing_type=sa.FLOAT(),
        type_=sa.Integer(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "raffle_pack_ticket",
        "price",
        existing_type=sa.Integer(),
        type_=sa.FLOAT(),
        existing_nullable=False,
    )
    op.alter_column(
        "raffle_cash",
        "balance",
        existing_type=sa.Integer(),
        type_=sa.FLOAT(),
        existing_nullable=False,
    )
    op.alter_column(
        "amap_product",
        "price",
        existing_type=sa.Integer(),
        type_=sa.FLOAT(),
        existing_nullable=False,
    )
    op.alter_column(
        "amap_order",
        "amount",
        existing_type=sa.Integer(),
        type_=sa.FLOAT(),
        existing_nullable=False,
    )
    op.alter_column(
        "amap_cash",
        "balance",
        existing_type=sa.Integer(),
        type_=sa.FLOAT(),
        existing_nullable=False,
    )

    op.execute("UPDATE amap_cash SET balance = balance / 100")
    op.execute("UPDATE amap_order SET amount = amount / 100")
    op.execute("UPDATE amap_product SET price = price / 100")
    op.execute("UPDATE raffle_cash SET balance = balance / 100")
    op.execute("UPDATE raffle_pack_ticket SET price = price / 100")


user_id = uuid4()
group_id = uuid4()
raffle_id = uuid4()


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    alembic_runner.insert_into(
        "core_group",
        {
            "id": group_id,
            "name": "external",
        },
    )

    alembic_runner.insert_into(
        "core_user",
        {
            "id": user_id,
            "email": "dedftyugimo@myecl.fr",
            "account_type": "external",
            "school_id": SchoolType.no_school.value,
            "password_hash": "password_hash",
            "name": "name",
            "firstname": "firstname",
            "nickname": "nickname",
            "birthday": None,
            "promo": 21,
            "phone": "phone",
            "floor": "Autre",
            "created_on": None,
        },
    )
    alembic_runner.insert_into(
        "amap_cash",
        {
            "user_id": user_id,
            "balance": 3.3999999999999964,
        },
    )
    alembic_runner.insert_into(
        "amap_product",
        {
            "id": uuid4(),
            "name": "name",
            "price": 1.1000000000000014,
            "category": "category",
        },
    )
    alembic_runner.insert_into(
        "raffle_cash",
        {
            "user_id": user_id,
            "balance": 1.4210854715202004e-14,
        },
    )
    alembic_runner.insert_into(
        "raffle",
        {
            "id": raffle_id,
            "name": "name",
            "group_id": group_id,
            "status": RaffleStatusType.creation,
        },
    )
    alembic_runner.insert_into(
        "raffle_pack_ticket",
        {
            "id": uuid4(),
            "price": -3.552713678800501e-15,
            "pack_size": 5,
            "raffle_id": raffle_id,
        },
    )


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    amap_cash = alembic_connection.execute(
        sa.text(f"SELECT balance FROM amap_cash WHERE user_id = '{user_id}'"),
    ).fetchall()
    assert amap_cash[0][0] == 340

    amap_product = alembic_connection.execute(
        sa.text("SELECT price FROM amap_product WHERE name = 'name'"),
    ).fetchall()
    assert amap_product[0][0] == 110

    raffle_cash = alembic_connection.execute(
        sa.text(f"SELECT balance FROM raffle_cash WHERE user_id = '{user_id}'"),
    ).fetchall()
    assert raffle_cash[0][0] == 0

    raffle_pack_ticket = alembic_connection.execute(
        sa.text(
            f"SELECT price FROM raffle_pack_ticket WHERE raffle_id = '{raffle_id}'",
        ),
    ).fetchall()
    assert raffle_pack_ticket[0][0] == 0
