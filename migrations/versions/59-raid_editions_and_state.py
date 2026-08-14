"""raid_editions_and_state

Create Date: 2026-04-21 00:00:00.000000
"""

import contextlib
import uuid
from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_alembic import MigrationContext

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9e1a4b2d7f10"
down_revision: str | None = "e58ffcd6b9eb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class RaidRegistrationStatus(Enum):
    draft = "draft"
    submitted = "submitted"
    validated = "validated"
    cancelled = "cancelled"


class SituationEnum(Enum):
    centrale = "centrale"
    otherSchool = "otherSchool"
    corporatePartner = "corporatePartner"
    other = "other"


DEFAULT_EDITION_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def upgrade() -> None:
    conn = op.get_bind()

    op.create_table(
        "raid_edition",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("registering_end_date", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("inscription_enabled", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Seed the default active edition; copy start/end date from the
    # RaidInformation core_data blob if present.
    raid_start_date = None
    raid_end_date = None
    raid_registering_end_date = None
    raid_info_row = conn.execute(
        sa.text(
            "SELECT data FROM core_data WHERE schema = 'RaidInformation' LIMIT 1",
        ),
    ).first()
    if raid_info_row is not None:
        import json

        try:
            payload = json.loads(raid_info_row[0]) if raid_info_row[0] else {}
            raid_start_date = payload.get("raid_start_date")
            raid_end_date = payload.get("raid_end_date")
            raid_registering_end_date = payload.get("raid_registering_end_date")
        except (TypeError, ValueError):
            pass

    conn.execute(
        sa.text(
            """
            INSERT INTO raid_edition (
                id, year, name, start_date, end_date,
                registering_end_date, active, inscription_enabled
            ) VALUES (
                :id, :year, :name, :start_date, :end_date,
                :registering_end_date, TRUE, TRUE
            )
            """,
        ).bindparams(
            id=DEFAULT_EDITION_ID,
            year=2026,
            name="Raid",
            start_date=raid_start_date,
            end_date=raid_end_date,
            registering_end_date=raid_registering_end_date,
        ),
    )

    status_enum = sa.Enum(
        RaidRegistrationStatus,
        name="raidregistrationstatus",
    )
    status_enum.create(conn, checkfirst=True)
    situation_enum = sa.Enum(SituationEnum, name="situation")
    situation_enum.create(conn, checkfirst=True)

    # ---- raid_participant: rename id -> user_id, add edition_id + status ----
    # Drop FKs that point at raid_participant.id first.
    for fk_name, table in (
        ("raid_team_captain_id_fkey", "raid_team"),
        ("raid_team_second_id_fkey", "raid_team"),
        ("raid_participant_checkout_participant_id_fkey", "raid_participant_checkout"),
    ):
        with contextlib.suppress(Exception):
            op.drop_constraint(fk_name, table, type_="foreignkey")

    op.alter_column("raid_participant", "id", new_column_name="user_id")
    with contextlib.suppress(Exception):
        op.drop_index("ix_raid_participant_id", table_name="raid_participant")
    op.create_index(
        op.f("ix_raid_participant_user_id"),
        "raid_participant",
        ["user_id"],
        unique=False,
    )
    op.add_column(
        "raid_participant",
        sa.Column("edition_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "raid_participant",
        sa.Column(
            "status",
            status_enum,
            nullable=False,
            server_default="draft",
        ),
    )

    conn.execute(
        sa.text(
            "UPDATE raid_participant SET edition_id = :eid WHERE edition_id IS NULL",
        ).bindparams(eid=DEFAULT_EDITION_ID),
    )
    conn.execute(
        sa.text(
            """
            UPDATE raid_participant
            SET status = 'validated'
            WHERE payment = true AND attestation_on_honour = true
            """,
        ),
    )
    conn.execute(
        sa.text(
            """
            UPDATE raid_participant
            SET status = 'submitted'
            WHERE attestation_on_honour = true AND status = 'draft'
            """,
        ),
    )

    op.alter_column("raid_participant", "edition_id", nullable=False)

    # Rewrite situation: move " : <school>" suffix into other_school, then enum.
    op.add_column(
        "raid_participant",
        sa.Column("situation_new", situation_enum, nullable=True),
    )
    conn.execute(
        sa.text(
            """
            UPDATE raid_participant
            SET other_school = COALESCE(
                other_school,
                SUBSTRING(situation FROM POSITION(' : ' IN situation) + 3)
            )
            WHERE situation LIKE 'otherschool : %'
            """,
        ),
    )
    conn.execute(
        sa.text(
            """
            UPDATE raid_participant SET situation_new = 'otherSchool'
            WHERE situation LIKE 'otherschool%' OR situation = 'otherSchool'
            """,
        ),
    )
    for literal in ("centrale", "corporatePartner", "other"):
        conn.execute(
            sa.text(
                "UPDATE raid_participant SET situation_new = CAST(:val AS situation) WHERE situation = :val",
            ).bindparams(val=literal),
        )
    op.drop_column("raid_participant", "situation")
    op.alter_column("raid_participant", "situation_new", new_column_name="situation")

    # Drop duplicated-of-core-user columns. Copy phone over first if missing.
    conn.execute(
        sa.text(
            """
            UPDATE core_user
            SET phone = rp.phone
            FROM raid_participant rp
            WHERE core_user.id = rp.user_id
              AND core_user.phone IS NULL
              AND rp.phone IS NOT NULL
            """,
        ),
    )
    conn.execute(
        sa.text(
            """
            UPDATE core_user
            SET birthday = rp.birthday
            FROM raid_participant rp
            WHERE core_user.id = rp.user_id
              AND core_user.birthday IS NULL
              AND rp.birthday IS NOT NULL
            """,
        ),
    )
    op.drop_column("raid_participant", "name")
    op.drop_column("raid_participant", "firstname")
    op.drop_column("raid_participant", "email")
    op.drop_column("raid_participant", "birthday")
    op.drop_column("raid_participant", "phone")

    # Promote PK to composite + add FKs.
    with contextlib.suppress(Exception):
        op.drop_constraint("raid_participant_pkey", "raid_participant", type_="primary")
    op.create_primary_key(
        "raid_participant_pkey",
        "raid_participant",
        ["user_id", "edition_id"],
    )
    op.create_foreign_key(
        "fk_raid_participant_user",
        "raid_participant",
        "core_user",
        ["user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_raid_participant_edition",
        "raid_participant",
        "raid_edition",
        ["edition_id"],
        ["id"],
    )

    # ---- raid_team: edition_id + composite FKs ----
    op.add_column(
        "raid_team",
        sa.Column("edition_id", sa.Uuid(), nullable=True),
    )
    conn.execute(
        sa.text(
            "UPDATE raid_team SET edition_id = :eid WHERE edition_id IS NULL",
        ).bindparams(eid=DEFAULT_EDITION_ID),
    )
    op.alter_column("raid_team", "edition_id", nullable=False)
    op.create_foreign_key(
        "fk_raid_team_edition",
        "raid_team",
        "raid_edition",
        ["edition_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_raid_team_captain",
        "raid_team",
        "raid_participant",
        ["captain_id", "edition_id"],
        ["user_id", "edition_id"],
    )
    op.create_foreign_key(
        "fk_raid_team_second",
        "raid_team",
        "raid_participant",
        ["second_id", "edition_id"],
        ["user_id", "edition_id"],
    )

    # ---- raid_participant_checkout: rename + composite FK ----
    op.alter_column(
        "raid_participant_checkout",
        "participant_id",
        new_column_name="participant_user_id",
    )
    op.add_column(
        "raid_participant_checkout",
        sa.Column("edition_id", sa.Uuid(), nullable=True),
    )
    conn.execute(
        sa.text(
            "UPDATE raid_participant_checkout SET edition_id = :eid WHERE edition_id IS NULL",
        ).bindparams(eid=DEFAULT_EDITION_ID),
    )
    op.alter_column("raid_participant_checkout", "edition_id", nullable=False)
    op.create_foreign_key(
        "fk_raid_participant_checkout_participant",
        "raid_participant_checkout",
        "raid_participant",
        ["participant_user_id", "edition_id"],
        ["user_id", "edition_id"],
    )

    # ---- Remaining tables: just edition_id FK ----
    for table in ("raid_document", "raid_security_file", "raid_invite"):
        op.add_column(
            table,
            sa.Column("edition_id", sa.Uuid(), nullable=True),
        )
        conn.execute(
            sa.text(
                f"UPDATE {table} SET edition_id = :eid WHERE edition_id IS NULL",
            ).bindparams(eid=DEFAULT_EDITION_ID),
        )
        op.alter_column(table, "edition_id", nullable=False)
        op.create_foreign_key(
            f"fk_{table}_edition",
            table,
            "raid_edition",
            ["edition_id"],
            ["id"],
        )


def downgrade() -> None:
    conn = op.get_bind()

    for table in ("raid_invite", "raid_security_file", "raid_document"):
        op.drop_constraint(f"fk_{table}_edition", table, type_="foreignkey")
        op.drop_column(table, "edition_id")

    op.drop_constraint(
        "fk_raid_participant_checkout_participant",
        "raid_participant_checkout",
        type_="foreignkey",
    )
    op.drop_column("raid_participant_checkout", "edition_id")
    op.alter_column(
        "raid_participant_checkout",
        "participant_user_id",
        new_column_name="participant_id",
    )
    # The single-column FK is recreated at the end, once raid_participant.id
    # has been restored as a unique primary key.

    op.drop_constraint("fk_raid_team_captain", "raid_team", type_="foreignkey")
    op.drop_constraint("fk_raid_team_second", "raid_team", type_="foreignkey")
    op.drop_constraint("fk_raid_team_edition", "raid_team", type_="foreignkey")
    op.drop_column("raid_team", "edition_id")

    op.drop_constraint(
        "fk_raid_participant_edition",
        "raid_participant",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_raid_participant_user",
        "raid_participant",
        type_="foreignkey",
    )
    op.drop_constraint("raid_participant_pkey", "raid_participant", type_="primary")
    op.create_primary_key(
        "raid_participant_pkey",
        "raid_participant",
        ["user_id"],
    )

    # Restore the dropped identity columns.
    op.add_column("raid_participant", sa.Column("phone", sa.String(), nullable=True))
    op.add_column("raid_participant", sa.Column("birthday", sa.Date(), nullable=True))
    op.add_column("raid_participant", sa.Column("email", sa.String(), nullable=True))
    op.add_column(
        "raid_participant",
        sa.Column("firstname", sa.String(), nullable=True),
    )
    op.add_column("raid_participant", sa.Column("name", sa.String(), nullable=True))
    conn.execute(
        sa.text(
            """
            UPDATE raid_participant
            SET name = u.name, firstname = u.firstname, email = u.email,
                birthday = u.birthday, phone = u.phone
            FROM core_user u
            WHERE u.id = raid_participant.user_id
            """,
        ),
    )

    op.add_column(
        "raid_participant",
        sa.Column("situation_str", sa.String(), nullable=True),
    )
    conn.execute(
        sa.text(
            """
            UPDATE raid_participant
            SET situation_str = CASE
                WHEN situation = 'otherSchool' AND other_school IS NOT NULL
                    THEN 'otherschool : ' || other_school
                WHEN situation = 'otherSchool' THEN 'otherschool'
                ELSE situation::text
            END
            """,
        ),
    )
    op.drop_column("raid_participant", "situation")
    op.alter_column(
        "raid_participant",
        "situation_str",
        new_column_name="situation",
    )

    op.drop_column("raid_participant", "status")
    op.drop_column("raid_participant", "edition_id")
    with contextlib.suppress(Exception):
        op.drop_index(
            op.f("ix_raid_participant_user_id"),
            table_name="raid_participant",
        )
    op.alter_column("raid_participant", "user_id", new_column_name="id")
    op.create_index("ix_raid_participant_id", "raid_participant", ["id"], unique=False)
    op.create_foreign_key(
        "raid_team_captain_id_fkey",
        "raid_team",
        "raid_participant",
        ["captain_id"],
        ["id"],
    )
    op.create_foreign_key(
        "raid_team_second_id_fkey",
        "raid_team",
        "raid_participant",
        ["second_id"],
        ["id"],
    )
    op.create_foreign_key(
        "raid_participant_checkout_participant_id_fkey",
        "raid_participant_checkout",
        "raid_participant",
        ["participant_id"],
        ["id"],
    )

    sa.Enum(name="raidregistrationstatus").drop(conn, checkfirst=True)
    sa.Enum(name="situation").drop(conn, checkfirst=True)
    op.drop_table("raid_edition")


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
