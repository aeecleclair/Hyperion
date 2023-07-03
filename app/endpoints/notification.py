from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_notification
from app.dependencies import get_db, is_user_a_member
from app.models import models_core, models_notification
from app.schemas import schemas_notification
from app.utils.types.tags import Tags

router = APIRouter()


@router.post(
    "/notification/register-device",
    response_model=schemas_notification.FirebaseDevice,
    status_code=201,
    tags=[Tags.notifications],
)
async def register_firebase_device(
    firebase_token: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Register a new firebase device for the user

    **The user must be authenticated to use this endpoint**
    """
    firebase_device = models_notification.FirebaseDevice(
        user_id=user.id, firebase_device_token=firebase_token
    )

    try:
        result = await cruds_notification.create_firebase_devices(
            firebase_device=firebase_device, db=db
        )
        return result
    except IntegrityError as error:
        raise HTTPException(status_code=400, detail=str(error))
