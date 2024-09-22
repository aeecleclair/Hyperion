"""empty message

Create Date: 2024-09-21 11:40:24.305070
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d24003cffdcd"
down_revision: str | None = "bccdd745730c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "google_api_oauth_flow_state",
        sa.Column("state", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("state"),
    )

    # We remove existing core data object, as it is replaced by `google_api_oauth_flow_state` table

    t_core_data = sa.Table(
        "core_data",
        sa.MetaData(),
        sa.Column("schema", sa.String(), nullable=False),
        sa.Column("data", sa.String(), nullable=False),
    )

    conn = op.get_bind()
    conn.execute(
        sa.delete(
            t_core_data,
        ).where(t_core_data.c.schema == "GoogleAPIOAuthFlow"),
    )


def downgrade() -> None:
    op.drop_table("google_api_oauth_flow_state")


def pre_test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    alembic_runner.insert_into(
        "core_data",
        {
            "schema": "GoogleAPIOAuthFlow",
            "data": '{"state":"state1"}',
        },
    )
    alembic_runner.insert_into(
        "core_data",
        {
            "schema": "GoogleAPICredentials",
            "data": '{"token":"token","refresh_token":"refresh","token_uri":"uri","client_id":"clientid","client_secret":"secret","scopes":[],"expiry":"2024-09-01T12:57:03.100953Z"}',
        },
    )


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    rows = alembic_connection.execute(
        sa.text("SELECT data FROM core_data WHERE schema='GoogleAPIOAuthFlow'"),
    ).fetchall()

    # We removed `GoogleAPIOAuthFlow` core data
    assert len(rows) == 0

    rows = alembic_connection.execute(
        sa.text("SELECT data FROM core_data WHERE schema='GoogleAPICredentials'"),
    ).fetchall()

    # Other Core data should remain
    assert len(rows) == 1
