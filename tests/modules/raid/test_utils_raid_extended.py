"""Extended tests for app/modules/raid/utils/utils_raid.py.

This file addresses the 0.8% test coverage gap in the raid module by covering
additional functions in utils_raid.py that were not previously tested.
"""

import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.payment import schemas_payment
from app.modules.raid import coredata_raid, schemas_raid
from app.modules.raid.raid_type import Difficulty, Situation, Size
from app.modules.raid.utils.utils_raid import (
    RaidPayementError,
    _participant_pdf_context,
    calculate_raid_payment,
    get_participant,
    set_team_number,
    validate_payment,
)

# --- Helper functions -----------------------------------------------------


async def _create_mock_db():
    """Create a mock async database session."""
    return AsyncMock(spec=AsyncSession)


def _create_mock_user():
    """Create a mock CoreUser for testing."""
    user = Mock()
    user.id = str(uuid4())
    user.name = "Test"
    user.firstname = "User"
    user.email = "test@example.com"
    user.phone = "+33123456789"
    user.birthday = datetime.date(1990, 1, 1)
    return user


# --- validate_payment tests -----------------------------------------------


@pytest.mark.asyncio
async def test_validate_payment_success_student():
    """Test validate_payment with student price."""
    db = AsyncMock()
    # Mock the checkout payment
    checkout_payment = schemas_payment.CheckoutPayment(
        id=uuid4(),
        checkout_id=uuid4(),
        paid_amount=50.0,
    )

    # Mock the participant checkout
    participant_checkout = Mock()
    participant_checkout.participant_user_id = "user_123"
    participant_checkout.edition_id = uuid4()

    # Mock prices
    prices = Mock()
    prices.student_price = 50.0
    prices.external_price = 90.0
    prices.t_shirt_price = 15.0

    # Mock dependencies
    with patch("app.modules.raid.utils.utils_raid.cruds_raid") as mock_cruds:
        mock_cruds.get_participant_checkout_by_checkout_id = AsyncMock(
            return_value=participant_checkout,
        )
        mock_cruds.confirm_payment = AsyncMock()

        with patch(
            "app.modules.raid.utils.utils_raid.get_core_data",
            new=AsyncMock(return_value=prices),
        ):
            await validate_payment(checkout_payment, db)

            # Verify payment confirmation
            mock_cruds.confirm_payment.assert_called_once_with(
                "user_123",
                participant_checkout.edition_id,
                db,
            )


@pytest.mark.asyncio
async def test_validate_payment_success_tshirt():
    """Test validate_payment with t-shirt price only."""
    db = AsyncMock()
    checkout_payment = schemas_payment.CheckoutPayment(
        id=uuid4(),
        checkout_id=uuid4(),
        paid_amount=15.0,
    )

    participant_checkout = Mock()
    participant_checkout.participant_user_id = "user_456"
    participant_checkout.edition_id = uuid4()

    prices = Mock()
    prices.student_price = 50.0
    prices.external_price = 90.0
    prices.t_shirt_price = 15.0

    with patch("app.modules.raid.utils.utils_raid.cruds_raid") as mock_cruds:
        mock_cruds.get_participant_checkout_by_checkout_id = AsyncMock(
            return_value=participant_checkout,
        )
        mock_cruds.confirm_t_shirt_payment = AsyncMock()

        with patch(
            "app.modules.raid.utils.utils_raid.get_core_data",
            new=AsyncMock(return_value=prices),
        ):
            await validate_payment(checkout_payment, db)

            mock_cruds.confirm_t_shirt_payment.assert_called_once_with(
                "user_456",
                participant_checkout.edition_id,
                db,
            )


@pytest.mark.asyncio
async def test_validate_payment_raised_when_checkout_not_found():
    """Test validate_payment raises RaidPayementError when checkout not found."""
    checkout_payment = schemas_payment.CheckoutPayment(
        id=uuid4(),
        checkout_id=uuid4(),
        paid_amount=50.0,
    )

    with patch("app.modules.raid.utils.utils_raid.cruds_raid") as mock_cruds:
        mock_cruds.get_participant_checkout_by_checkout_id = AsyncMock(
            return_value=None,
        )

        with pytest.raises(RaidPayementError) as exc_info:
            await validate_payment(checkout_payment, AsyncMock())

        assert "not found" in str(exc_info.value)


# --- set_team_number tests -----------------------------------------------


@pytest.mark.asyncio
async def test_set_team_number_success():
    """Test set_team_number with a difficulty."""
    team = Mock(spec=schemas_raid.RaidTeam)
    team.id = "team_123"
    team.difficulty = Difficulty.sports

    edition_id = uuid4()
    db = AsyncMock()

    with patch("app.modules.raid.utils.utils_raid.cruds_raid") as mock_cruds:
        mock_cruds.get_max_team_number_by_difficulty = AsyncMock(return_value=0)
        mock_cruds.update_team = AsyncMock()

        await set_team_number(team, edition_id, db)

        # Verify max team number was retrieved and team updated
        mock_cruds.get_max_team_number_by_difficulty.assert_called_once_with(
            Difficulty.sports,
            edition_id,
            db,
        )
        mock_cruds.update_team.assert_called_once()


@pytest.mark.asyncio
async def test_set_team_number_with_existing_team():
    """Test set_team_number when teams already exist."""
    team = Mock(spec=schemas_raid.RaidTeam)
    team.id = "team_456"
    team.difficulty = Difficulty.expert

    edition_id = uuid4()
    db = AsyncMock()

    with patch("app.modules.raid.utils.utils_raid.cruds_raid") as mock_cruds:
        mock_cruds.get_max_team_number_by_difficulty = AsyncMock(return_value=205)
        mock_cruds.update_team = AsyncMock()

        await set_team_number(team, edition_id, db)

        # Should increment from existing max
        mock_cruds.update_team.assert_called_once()


# --- _participant_pdf_context tests --------------------------------------


def test_participant_pdf_context_with_user():
    """Test _participant_pdf_context when user is present."""
    participant = Mock(spec=schemas_raid.RaidParticipant)
    participant.model_dump.return_value = {
        "user_id": "test_user",
        "edition_id": uuid4(),
    }

    user = Mock()
    user.name = "Doe"
    user.firstname = "John"
    user.email = "john@example.com"
    user.phone = "+33123456789"
    user.birthday = datetime.date(1990, 1, 1)
    participant.user = user

    result = _participant_pdf_context(participant)

    assert result["user_id"] == "test_user"
    assert result["name"] == "Doe"
    assert result["firstname"] == "John"
    assert result["email"] == "john@example.com"
    assert result["phone"] == "+33123456789"
    assert result["birthday"] == datetime.date(1990, 1, 1)


def test_participant_pdf_context_without_user():
    """Test _participant_pdf_context when user is None."""
    participant = Mock(spec=schemas_raid.RaidParticipant)
    participant.model_dump.return_value = {
        "user_id": "test_user",
        "edition_id": uuid4(),
    }
    participant.user = None

    result = _participant_pdf_context(participant)

    assert result["user_id"] == "test_user"
    assert "name" not in result
    assert "firstname" not in result


# --- get_participant tests ------------------------------------------------


@pytest.mark.asyncio
async def test_get_participant_success():
    """Test get_participant when participant exists."""
    user_id = "user_123"
    edition_id = uuid4()
    db = AsyncMock()

    participant = Mock(spec=schemas_raid.RaidParticipant)
    participant.user_id = user_id
    participant.edition_id = edition_id

    with patch("app.modules.raid.utils.utils_raid.cruds_raid") as mock_cruds:
        mock_cruds.get_participant_by_user_id = AsyncMock(return_value=participant)

        result = await get_participant(user_id, edition_id, db)

        assert result is participant
        mock_cruds.get_participant_by_user_id.assert_called_once_with(
            user_id,
            edition_id,
            db,
        )


@pytest.mark.asyncio
async def test_get_participant_not_found():
    """Test get_participant when participant doesn't exist."""
    user_id = "non_existent_user"
    edition_id = uuid4()
    db = AsyncMock()

    with patch("app.modules.raid.utils.utils_raid.cruds_raid") as mock_cruds:
        mock_cruds.get_participant_by_user_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_participant(user_id, edition_id, db)

        assert exc_info.value.status_code == 404
        assert "Participant not found" in exc_info.value.detail


# --- calculate_raid_payment tests (NEW) -----------------------------------


def test_calculate_raid_payment_student_with_card():
    """Test calculate_raid_payment for student with student card."""
    participant = Mock(spec=schemas_raid.RaidParticipant)
    participant.situation = Situation.centrale
    participant.student_card_id = "card_123"
    participant.payment = False
    participant.t_shirt_size = None
    participant.t_shirt_payment = False

    prices = coredata_raid.RaidPrice(
        student_price=50.0,
        t_shirt_price=15.0,
        external_price=90.0,
    )

    price, checkout_name = calculate_raid_payment(participant, prices)

    assert price == 50.0
    assert "étudiant" in checkout_name


def test_calculate_raid_payment_student_without_card():
    """Test calculate_raid_payment falls back to external without student card."""
    participant = Mock(spec=schemas_raid.RaidParticipant)
    participant.situation = Situation.centrale
    participant.student_card_id = None
    participant.payment = False
    participant.t_shirt_size = None
    participant.t_shirt_payment = False

    prices = coredata_raid.RaidPrice(
        student_price=50.0,
        t_shirt_price=15.0,
        external_price=90.0,
    )

    price, checkout_name = calculate_raid_payment(participant, prices)

    assert price == 90.0
    assert "externe" in checkout_name


def test_calculate_raid_payment_other_school():
    """Test calculate_raid_payment for otherSchool situation."""
    participant = Mock(spec=schemas_raid.RaidParticipant)
    participant.situation = Situation.otherSchool
    participant.student_card_id = "card_123"
    participant.payment = False
    participant.t_shirt_size = None
    participant.t_shirt_payment = False

    prices = coredata_raid.RaidPrice(
        student_price=50.0,
        t_shirt_price=15.0,
        external_price=90.0,
    )

    price, checkout_name = calculate_raid_payment(participant, prices)

    assert price == 50.0
    assert "étudiant" in checkout_name


def test_calculate_raid_payment_corporate_partner():
    """Test calculate_raid_payment for corporatePartner situation."""
    participant = Mock(spec=schemas_raid.RaidParticipant)
    participant.situation = Situation.corporatePartner
    participant.student_card_id = "card_123"
    participant.payment = False
    participant.t_shirt_size = None
    participant.t_shirt_payment = False

    prices = coredata_raid.RaidPrice(
        student_price=50.0,
        t_shirt_price=15.0,
        external_price=90.0,
    )

    price, _ = calculate_raid_payment(participant, prices)

    assert price == 90.0  # Corporate partner is always external


def test_calculate_raid_payment_with_tshirt():
    """Test calculate_raid_payment includes t-shirt when applicable."""
    participant = Mock(spec=schemas_raid.RaidParticipant)
    participant.situation = Situation.centrale
    participant.student_card_id = "card_123"
    participant.payment = False
    participant.t_shirt_size = Size.L
    participant.t_shirt_payment = False

    prices = coredata_raid.RaidPrice(
        student_price=50.0,
        t_shirt_price=15.0,
        external_price=90.0,
    )

    price, _ = calculate_raid_payment(participant, prices)

    assert price == 65.0  # 50 student + 15 t-shirt


def test_calculate_raid_payment_already_paid():
    """Test calculate_raid_payment returns 0 when already paid."""
    participant = Mock(spec=schemas_raid.RaidParticipant)
    participant.situation = Situation.centrale
    participant.student_card_id = "card_123"
    participant.payment = True
    participant.t_shirt_size = None
    participant.t_shirt_payment = False

    prices = coredata_raid.RaidPrice(
        student_price=50.0,
        t_shirt_price=15.0,
        external_price=90.0,
    )

    price, _ = calculate_raid_payment(participant, prices)

    assert price == 0


def test_calculate_raid_payment_tshirt_alone():
    """Test calculate_raid_payment with only t-shirt payment."""
    participant = Mock(spec=schemas_raid.RaidParticipant)
    participant.situation = Situation.centrale
    participant.student_card_id = "card_123"
    participant.payment = True
    participant.t_shirt_size = Size.L
    participant.t_shirt_payment = False

    prices = coredata_raid.RaidPrice(
        student_price=50.0,
        t_shirt_price=15.0,
        external_price=90.0,
    )

    price, _ = calculate_raid_payment(participant, prices)

    assert price == 15.0  # Only t-shirt


def test_calculate_raid_payment_fully_paid():
    """Test calculate_raid_payment with everything paid."""
    participant = Mock(spec=schemas_raid.RaidParticipant)
    participant.situation = Situation.centrale
    participant.student_card_id = "card_123"
    participant.payment = True
    participant.t_shirt_size = Size.L
    participant.t_shirt_payment = True

    prices = coredata_raid.RaidPrice(
        student_price=50.0,
        t_shirt_price=15.0,
        external_price=90.0,
    )

    price, _ = calculate_raid_payment(participant, prices)

    assert price == 0  # Everything paid


def test_calculate_raid_payment_invalid_price():
    """Test calculate_raid_payment raises HTTPException when prices invalid."""
    participant = Mock(spec=schemas_raid.RaidParticipant)
    participant.situation = Situation.other
    participant.student_card_id = None
    participant.payment = False
    participant.t_shirt_size = None
    participant.t_shirt_payment = False

    prices = coredata_raid.RaidPrice(
        student_price=None,
        t_shirt_price=None,
        external_price=None,
    )

    with pytest.raises(HTTPException) as exc_info:
        calculate_raid_payment(participant, prices)

    assert exc_info.value.status_code == 404
    assert "Prices not set" in exc_info.value.detail


def test_calculate_raid_payment_no_participant():
    """Test calculate_raid_payment raises when participant is None."""
    prices = coredata_raid.RaidPrice(
        student_price=50.0,
        t_shirt_price=15.0,
        external_price=90.0,
    )

    with pytest.raises(HTTPException) as exc_info:
        calculate_raid_payment(None, prices)

    assert exc_info.value.status_code == 404
    assert "Participant not found" in exc_info.value.detail


# --- Test coverage for calculate_raid_payment with None situation ---------------------------


def test_calculate_raid_payment_situation_none():
    """Test calculate_raid_payment when situation is None."""
    participant = Mock(spec=schemas_raid.RaidParticipant)
    participant.situation = None
    participant.student_card_id = None
    participant.payment = False
    participant.t_shirt_size = None
    participant.t_shirt_payment = False

    prices = coredata_raid.RaidPrice(
        student_price=50.0,
        t_shirt_price=15.0,
        external_price=90.0,
    )

    price, _ = calculate_raid_payment(participant, prices)

    assert price == 90.0  # None falls back to external


# --- Additional edge cases -----------------------------------------------


@pytest.mark.asyncio
async def test_validate_payment_all_combinations():
    """Test various payment combinations."""
    # Test student + t-shirt combination
    db = AsyncMock()
    checkout_payment = schemas_payment.CheckoutPayment(
        id=uuid4(),
        checkout_id=uuid4(),
        paid_amount=65.0,  # student + t-shirt
    )

    participant_checkout = Mock()
    participant_checkout.participant_user_id = "user_789"
    participant_checkout.edition_id = uuid4()

    prices = Mock()
    prices.student_price = 50.0
    prices.external_price = 90.0
    prices.t_shirt_price = 15.0

    with patch("app.modules.raid.utils.utils_raid.cruds_raid") as mock_cruds:
        mock_cruds.get_participant_checkout_by_checkout_id = AsyncMock(
            return_value=participant_checkout,
        )
        mock_cruds.confirm_payment = AsyncMock()
        mock_cruds.confirm_t_shirt_payment = AsyncMock()

        with patch(
            "app.modules.raid.utils.utils_raid.get_core_data",
            new=AsyncMock(return_value=prices),
        ):
            await validate_payment(checkout_payment, db)

            # Both should be confirmed for student + t-shirt combination
            mock_cruds.confirm_payment.assert_called_once_with(
                "user_789",
                participant_checkout.edition_id,
                db,
            )
            mock_cruds.confirm_t_shirt_payment.assert_called_once_with(
                "user_789",
                participant_checkout.edition_id,
                db,
            )
