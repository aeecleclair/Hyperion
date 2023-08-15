import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_cinema
from app.dependencies import (
    get_db,
    get_notification_tool,
    get_request_id,
    is_user_a_member,
    is_user_a_member_of,
)
from app.models import models_core
from app.schemas import schemas_cinema
from app.schemas.schemas_notification import Message
from app.utils.communication.notifications import NotificationTool
from app.utils.tools import get_file_from_data, save_file_as_data
from app.utils.types import standard_responses
from app.utils.types.groups_type import GroupType
from app.utils.types.notification_types import Topic
from app.utils.types.tags import Tags

router = APIRouter()

hyperion_error_logger = logging.getLogger("hyperion.error")


@router.get(
    "/cinema/sessions",
    response_model=list[schemas_cinema.CineSessionComplete],
    status_code=200,
    tags=[Tags.cinema],
)
async def get_sessions(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    result = await cruds_cinema.get_sessions(db=db)
    return result


@router.post(
    "/cinema/sessions",
    response_model=schemas_cinema.CineSessionComplete,
    status_code=201,
    tags=[Tags.cinema],
)
async def create_session(
    session: schemas_cinema.CineSessionBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.cinema)),
    notification_tool: NotificationTool = Depends(get_notification_tool),
):
    db_session = schemas_cinema.CineSessionComplete(
        id=str(uuid.uuid4()), **session.dict()
    )
    try:
        result = await cruds_cinema.create_session(session=db_session, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    # Send a notification with the week recap
    try:
        today = datetime.now(timezone.utc)
        sunday = today.replace(
            day=today.day - today.weekday() + 6, hour=11, minute=0, second=0
        )
        next_week_sessions = await cruds_cinema.get_sessions_after_datetime(
            start_after=sunday, db=db
        )
        message_content = ""
        days = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        for next_session in next_week_sessions:
            message_content += (
                f"{next_session.name} - {days[next_session.start.weekday()]}\n"
            )
        message = Message(
            # We use sunday date as context to avoid sending the recap twice
            context=f"cinema-recap-{sunday}",
            is_visible=True,
            title="Le programme de la semaine",
            content=message_content,
            delivery_datetime=sunday,
            # The notification will expire the next sunday
            expire_on=sunday.replace(day=sunday.day + 7),
        )
        await notification_tool.send_notification_to_topic(
            topic=Topic.cinema, message=message
        )
    except Exception as error:
        hyperion_error_logger.error(
            f"Error while sending cinema recap notification, {error}"
        )

    return result


@router.patch("/cinema/sessions/{session_id}", status_code=200, tags=[Tags.cinema])
async def update_session(
    session_id: str,
    session_update: schemas_cinema.CineSessionUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.cinema)),
):
    await cruds_cinema.update_session(
        session_id=session_id, session_update=session_update, db=db
    )


@router.delete("/cinema/sessions/{session_id}", status_code=204, tags=[Tags.cinema])
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.cinema)),
):
    await cruds_cinema.delete_session(session_id=session_id, db=db)


@router.post(
    "/cinema/sessions/{session_id}/poster",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.users],
)
async def create_campaigns_logo(
    session_id: str,
    image: UploadFile = File(...),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.cinema)),
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    session = await cruds_cinema.get_session_by_id(db=db, session_id=session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="The session does not exist.",
        )

    await save_file_as_data(
        image=image,
        directory="cinemasessions",
        filename=str(session_id),
        request_id=request_id,
        max_file_size=4 * 1024 * 1024,
        accepted_content_types=["image/jpeg", "image/png", "image/webp"],
    )

    return standard_responses.Result(success=True)


@router.get(
    "/cinema/sessions/{session_id}/poster",
    response_class=FileResponse,
    status_code=200,
    tags=[Tags.users],
)
async def read_session_poster(
    session_id: str,
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return get_file_from_data(
        default_asset="assets/images/default_movie.png",
        directory="cinemasessions",
        filename=str(session_id),
    )
