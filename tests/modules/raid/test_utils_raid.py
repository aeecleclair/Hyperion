"""Unit tests for app/modules/raid/utils/utils_raid.py.

Covers:
- `will_birthday_be_minor_on` edge cases (no birthday, no raid date, on the
  exact cutoff day).
- `calculate_raid_payment` with the new Situation enum (no more `split(' : ')`).
- `set_team_number` via mocks — the CRUD-side `get_max_team_number_by_difficulty`
  now takes edition_id.
"""

import datetime
import uuid
from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pytest_mock import MockerFixture

from app.modules.raid import coredata_raid
from app.modules.raid.models_raid import RaidParticipant, RaidTeam
from app.modules.raid.raid_type import Difficulty, Situation, Size
from app.modules.raid.utils.utils_raid import (
    calculate_raid_payment,
    set_team_number,
    will_birthday_be_minor_on,
)

# -- will_birthday_be_minor_on ---------------------------------------------


def test_minor_when_birthday_unknown() -> None:
    assert will_birthday_be_minor_on(None, datetime.date(2026, 5, 1)) is True


def test_minor_without_raid_date_uses_next_year_jan_1() -> None:
    # A 16-year-old on today's year is still minor on Jan 1 next year.
    today = datetime.datetime.now(tz=datetime.UTC).date()
    assert (
        will_birthday_be_minor_on(
            datetime.date(today.year - 16, today.month, today.day),
            None,
        )
        is True
    )


def test_not_minor_if_birthday_18_years_before_raid() -> None:
    raid_date = datetime.date(2026, 5, 1)
    eighteenth_birthday_before_raid = datetime.date(2008, 4, 30)
    assert (
        will_birthday_be_minor_on(
            eighteenth_birthday_before_raid,
            raid_date,
        )
        is False
    )


def test_minor_if_birthday_after_raid() -> None:
    raid_date = datetime.date(2026, 5, 1)
    eighteenth_birthday_after_raid = datetime.date(2008, 5, 2)
    assert (
        will_birthday_be_minor_on(
            eighteenth_birthday_after_raid,
            raid_date,
        )
        is True
    )


# -- calculate_raid_payment (new enum semantics) ---------------------------


@pytest.fixture
def prices() -> coredata_raid.RaidPrice:
    return coredata_raid.RaidPrice(
        student_price=50,
        t_shirt_price=15,
        external_price=90,
    )


def _participant(**kwargs):
    defaults: dict[str, Any] = {
        "user_id": str(uuid4()),
        "edition_id": uuid4(),
        "payment": False,
        "t_shirt_payment": False,
        "t_shirt_size": None,
        "situation": None,
        "student_card_id": None,
    }
    defaults.update(kwargs)
    return RaidParticipant(**defaults)


def test_payment_centrale_with_student_card(prices) -> None:
    p = _participant(
        situation=Situation.centrale,
        student_card_id=str(uuid.uuid4()),
    )
    price, label = calculate_raid_payment(p, prices)
    assert price == 50
    assert "étudiant" in label


def test_payment_other_school_with_student_card(prices) -> None:
    p = _participant(
        situation=Situation.otherSchool,
        student_card_id=str(uuid.uuid4()),
    )
    price, label = calculate_raid_payment(p, prices)
    assert price == 50
    assert "étudiant" in label


def test_payment_centrale_without_student_card_falls_to_external(prices) -> None:
    p = _participant(situation=Situation.centrale, student_card_id=None)
    price, label = calculate_raid_payment(p, prices)
    assert price == 90
    assert "externe" in label


def test_payment_other_situation_is_external(prices) -> None:
    p = _participant(situation=Situation.other)
    price, _ = calculate_raid_payment(p, prices)
    assert price == 90


def test_payment_corporate_partner_is_external(prices) -> None:
    p = _participant(situation=Situation.corporatePartner)
    price, _ = calculate_raid_payment(p, prices)
    assert price == 90


def test_payment_adds_tshirt(prices) -> None:
    p = _participant(
        situation=Situation.centrale,
        student_card_id=str(uuid.uuid4()),
        t_shirt_size=Size.L,
    )
    price, _ = calculate_raid_payment(p, prices)
    assert price == 65  # 50 student + 15 t-shirt


def test_payment_none_size_tshirt_not_billed(prices) -> None:
    p = _participant(
        situation=Situation.centrale,
        student_card_id=str(uuid.uuid4()),
        t_shirt_size=Size.None_,
    )
    price, _ = calculate_raid_payment(p, prices)
    assert price == 50


def test_payment_already_paid_zero(prices) -> None:
    p = _participant(
        situation=Situation.centrale,
        student_card_id=str(uuid.uuid4()),
        payment=True,
    )
    price, _ = calculate_raid_payment(p, prices)
    assert price == 0


def test_payment_already_paid_but_tshirt_outstanding(prices) -> None:
    p = _participant(
        situation=Situation.centrale,
        student_card_id=str(uuid.uuid4()),
        payment=True,
        t_shirt_size=Size.L,
        t_shirt_payment=False,
    )
    price, _ = calculate_raid_payment(p, prices)
    assert price == 15


def test_payment_fully_settled_zero(prices) -> None:
    p = _participant(
        situation=Situation.centrale,
        student_card_id=str(uuid.uuid4()),
        payment=True,
        t_shirt_size=Size.L,
        t_shirt_payment=True,
    )
    price, _ = calculate_raid_payment(p, prices)
    assert price == 0


def test_payment_raises_if_prices_missing() -> None:
    bad_prices = coredata_raid.RaidPrice(
        student_price=None,
        t_shirt_price=None,
        external_price=None,
    )
    p = _participant(situation=Situation.other)
    with pytest.raises(HTTPException) as exc_info:
        calculate_raid_payment(p, bad_prices)
    assert exc_info.value.status_code == 404


# -- set_team_number -------------------------------------------------------


@pytest.mark.asyncio
async def test_set_team_number_noop_without_difficulty(mocker: MockerFixture) -> None:
    db = AsyncMock()
    team = Mock(spec=RaidTeam, id="tid", difficulty=None)
    mock_max = mocker.patch(
        "app.modules.raid.cruds_raid.get_max_team_number_by_difficulty",
        return_value=0,
    )
    mock_update = mocker.patch("app.modules.raid.cruds_raid.update_team")
    await set_team_number(team, uuid4(), db)
    mock_max.assert_not_called()
    mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_set_team_number_discovery_empty(mocker: MockerFixture) -> None:
    db = AsyncMock()
    team = Mock(spec=RaidTeam, id="tid", difficulty=Difficulty.discovery)
    mocker.patch(
        "app.modules.raid.cruds_raid.get_max_team_number_by_difficulty",
        return_value=0,
    )
    mock_update = mocker.patch("app.modules.raid.cruds_raid.update_team")
    await set_team_number(team, uuid4(), db)
    args, _ = mock_update.call_args
    assert args[1].number == 1


@pytest.mark.asyncio
async def test_set_team_number_sports_empty(mocker: MockerFixture) -> None:
    db = AsyncMock()
    team = Mock(spec=RaidTeam, id="tid", difficulty=Difficulty.sports)
    mocker.patch(
        "app.modules.raid.cruds_raid.get_max_team_number_by_difficulty",
        return_value=0,
    )
    mock_update = mocker.patch("app.modules.raid.cruds_raid.update_team")
    await set_team_number(team, uuid4(), db)
    args, _ = mock_update.call_args
    assert args[1].number == 101


@pytest.mark.asyncio
async def test_set_team_number_expert_with_existing(mocker: MockerFixture) -> None:
    db = AsyncMock()
    team = Mock(spec=RaidTeam, id="tid", difficulty=Difficulty.expert)
    mocker.patch(
        "app.modules.raid.cruds_raid.get_max_team_number_by_difficulty",
        return_value=205,
    )
    mock_update = mocker.patch("app.modules.raid.cruds_raid.update_team")
    await set_team_number(team, uuid4(), db)
    args, _ = mock_update.call_args
    assert args[1].number == 206


@pytest.mark.asyncio
async def test_set_team_number_passes_edition_to_crud(mocker: MockerFixture) -> None:
    db = AsyncMock()
    edition_id = uuid4()
    team = Mock(spec=RaidTeam, id="tid", difficulty=Difficulty.sports)
    mock_max = mocker.patch(
        "app.modules.raid.cruds_raid.get_max_team_number_by_difficulty",
        return_value=0,
    )
    mocker.patch("app.modules.raid.cruds_raid.update_team")
    await set_team_number(team, edition_id, db)
    args, _ = mock_max.call_args
    assert args[0] == Difficulty.sports
    assert args[1] == edition_id
