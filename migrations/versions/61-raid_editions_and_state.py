"""raid_editions_and_state

Create Date: 2026-04-21 00:00:00.000000
"""

import contextlib
import json
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
down_revision: str | None = "84ee3296cc58"
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


DEFAULT_EDITION_ID = uuid.UUID("fc155c64-46ea-4acd-a941-a31999b5a719")


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
    """Seed data that exercises the migration's UPDATEs and FK creations.

    We insert a minimal raid_edition row plus a few raid_participant rows with
    varied situation/status combos so the migration's data-backfill logic runs
    against real data.

    Note: raid_edition is CREATED by this migration, so we can't seed it here.
    The migration itself inserts the default edition (lines 78-97). We only
    seed the tables that already exist: core_user, raid_participant, raid_team,
    raid_document, raid_security_file, raid_invite.
    """
    # Core users referenced by participants
    # First add a school for the FK
    alembic_runner.insert_into(
        "core_school",
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "Test School",
            "email_regex": "@example\\.com$",
        },
    )
    alembic_runner.insert_into(
        "core_school",
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "name": "Test School 2",
            "email_regex": "@example\\.com$",
        },
    )

    alembic_runner.insert_into(
        "core_user",
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "email": "user1@example.com",
            "password_hash": "hash",
            "school_id": "11111111-1111-1111-1111-111111111111",
            "account_type": "student",
            "name": "Doe",
            "firstname": "John",
            "nickname": "john",
            "birthday": None,
            "promo": 2026,
            "phone": "0102030405",
            "floor": "Autre",
            "created_on": None,
            "make_user_external": False,
        },
    )
    alembic_runner.insert_into(
        "core_user",
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "email": "user2@example.com",
            "password_hash": "hash",
            "school_id": "22222222-2222-2222-2222-222222222222",
            "account_type": "student",
            "name": "Smith",
            "firstname": "Jane",
            "nickname": "jane",
            "birthday": None,
            "promo": 2026,
            "phone": "0607080910",
            "floor": "Autre",
            "created_on": None,
            "make_user_external": False,
        },
    )

    # raid_participant rows BEFORE migration renames `id` -> `user_id`
    # and adds edition_id + status columns.
    # Use legacy 'situation' column values that the migration parses.
    alembic_runner.insert_into(
        "raid_participant",
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "Doe",
            "firstname": "John",
            "email": "user1@example.com",
            "birthday": "1990-01-01",
            "phone": "0102030405",
            "situation": "centrale",
            "other_school": None,
            "address": "1 rue Test",
            "bike_size": "M",
            "t_shirt_size": "M",
            "payment": True,
            "attestation_on_honour": True,
            "is_minor": False,
        },
    )
    alembic_runner.insert_into(
        "raid_participant",
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "name": "Smith",
            "firstname": "Jane",
            "email": "user2@example.com",
            "birthday": "1990-01-01",
            "phone": "0607080910",
            "situation": "otherschool : CentraleSupélec",
            "other_school": None,
            "address": "2 rue Test",
            "bike_size": "L",
            "t_shirt_size": "L",
            "payment": False,
            "attestation_on_honour": True,
            "is_minor": False,
        },
    )

    # raid_team row referencing the participants
    alembic_runner.insert_into(
        "raid_team",
        {
            "id": "team-001",
            "name": "Team Alpha",
            "difficulty": "discovery",
            "captain_id": "11111111-1111-1111-1111-111111111111",
            "second_id": "22222222-2222-2222-2222-222222222222",
            "number": 1,
            "meeting_place": "centrale",
            "file_id": None,
        },
    )

    # raid_document, raid_security_file, raid_invite rows
    alembic_runner.insert_into(
        "raid_document",
        {
            "id": "doc-001",
            "name": "ID Card",
            "uploaded_at": "2024-01-01",
            "type": "idCard",
            "validation": "accepted",
        },
    )
    alembic_runner.insert_into(
        "raid_security_file",
        {
            "id": "sec-001",
            "allergy": None,
            "asthma": False,
            "intensive_care_unit": False,
            "intensive_care_unit_when": None,
            "ongoing_treatment": None,
            "sicknesses": None,
            "hospitalization": None,
            "surgical_operation": None,
            "trauma": None,
            "family": None,
            "emergency_person_firstname": "Contact",
            "emergency_person_name": "Emergency",
            "emergency_person_phone": "0102030405",
            "file_id": None,
        },
    )
    alembic_runner.insert_into(
        "raid_invite",
        {
            "id": "inv-001",
            "team_id": "team-001",
            "token": "test-token",
        },
    )


def test_upgrade(
    alembic_runner: "MigrationContext",
    alembic_connection: sa.Connection,
) -> None:
    """Verify the migration produced the expected schema + data state."""
    # raid_edition exists and has our seeded row
    edition_rows = alembic_connection.execute(
        sa.text(
            "SELECT id, year, name, active, inscription_enabled FROM raid_edition"
        ),
    ).fetchall()
    assert len(edition_rows) == 1
    assert str(edition_rows[0][0]) == str(DEFAULT_EDITION_ID)
    assert edition_rows[0][1] == 2026
    assert edition_rows[0][2] == "Raid"
    assert edition_rows[0][3] is True
    assert edition_rows[0][4] is True

    # raid_participant: PK is now composite (user_id, edition_id)
    participant_rows = alembic_connection.execute(
        sa.text(
            "SELECT user_id, edition_id, situation, other_school, status "
            "FROM raid_participant ORDER BY user_id"
        ),
    ).fetchall()
    assert len(participant_rows) == 2

    # User 1: centrale -> status should become 'validated' (payment + attestation)
    p1 = next(r for r in participant_rows if r[0] == "11111111-1111-1111-1111-111111111111")
    assert str(p1[1]) == str(DEFAULT_EDITION_ID)
    assert p1[2] == "centrale"
    assert p1[3] is None
    assert p1[4] == "validated"

    # User 2: otherschool : CentraleSupélec -> other_school populated, status 'submitted'
    p2 = next(r for r in participant_rows if r[0] == "22222222-2222-2222-2222-222222222222")
    assert str(p2[1]) == str(DEFAULT_EDITION_ID)
    assert p2[2] == "otherSchool"
    assert p2[3] == "CentraleSupélec"
    assert p2[4] == "submitted"

    # raid_team got edition_id backfilled and composite FKs created
    team_rows = alembic_connection.execute(
        sa.text("SELECT id, edition_id, captain_id, second_id FROM raid_team"),
    ).fetchall()
    assert len(team_rows) == 1
    assert str(team_rows[0][1]) == str(DEFAULT_EDITION_ID)
    assert team_rows[0][2] == "11111111-1111-1111-1111-111111111111"
    assert team_rows[0][3] == "22222222-2222-2222-2222-222222222222"

    # raid_participant_checkout: participant_id -> participant_user_id + edition_id
    alembic_connection.execute(
        sa.text(
            "SELECT participant_user_id, edition_id FROM raid_participant_checkout"
        ),
    ).fetchall()
    # No checkout rows were seeded, but the column + FK should exist
    # (pytest-alembic will error if the FK creation fails)

    # raid_document, raid_security_file, raid_invite got edition_id + FKs
    for table in ("raid_document", "raid_security_file", "raid_invite"):
        rows = alembic_connection.execute(
            sa.text(f"SELECT edition_id FROM {table}"),
        ).fetchall()
        assert len(rows) >= 1
        assert all(str(r[0]) == str(DEFAULT_EDITION_ID) for r in rows)
