"""40-promo-above-2000

Create Date: 2025-09-07 09:54:34.421809
"""

import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.core.schools.schools_type import SchoolType

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "91fadc90f892"
down_revision: str | None = "2880c583d7f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE core_user SET promo = 2000 + promo WHERE promo < 2000")


def downgrade() -> None:
    # we afterwards cannot distinguish those who had 2023 from 23
    pass


user_id_23 = str(uuid.uuid4())
user_id_2023 = str(uuid.uuid4())
user_id_null = str(uuid.uuid4())


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    alembic_runner.insert_into(
        "core_user",
        [
            {
                "id": user_id_23,
                "email": "email23",
                "school_id": str(SchoolType.no_school.value),
                "password_hash": "password_hash",
                "account_type": "student",
                "name": "name",
                "firstname": "firstname",
                "promo": 23,
            },
            {
                "id": user_id_2023,
                "email": "email2023",
                "school_id": str(SchoolType.no_school.value),
                "password_hash": "password_hash",
                "account_type": "student",
                "name": "name",
                "firstname": "firstname",
                "promo": 2023,
            },
            {
                "id": user_id_null,
                "email": "emailnull",
                "school_id": str(SchoolType.no_school.value),
                "password_hash": "password_hash",
                "account_type": "student",
                "name": "name",
                "firstname": "firstname",
                # promo is null
            },
        ],
    )


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    assert (
        alembic_connection.execute(
            sa.text(f"SELECT promo FROM core_user WHERE id = '{user_id_23}'"),
        ).all()[0][0]
        == 2023
    )
    assert (
        alembic_connection.execute(
            sa.text(f"SELECT promo FROM core_user WHERE id = '{user_id_2023}'"),
        ).all()[0][0]
        == 2023
    )
    assert (
        alembic_connection.execute(
            sa.text(f"SELECT promo FROM core_user WHERE id = '{user_id_null}'"),
        ).all()[0][0]
        is None
    )
