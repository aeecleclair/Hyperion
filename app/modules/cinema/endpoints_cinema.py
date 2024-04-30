import logging
import uuid
from zoneinfo import ZoneInfo

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core, standard_responses
from app.core.groups.groups_type import GroupType
from app.core.module import Module
from app.core.notification.notification_types import CustomTopic, Topic, TopicMessage
from app.dependencies import (
    get_db,
    get_notification_tool,
    get_request_id,
    is_user_a_member,
    is_user_a_member_of,
)
from app.modules.cinema import cruds_cinema, schemas_cinema
from app.types.content_type import ContentType
from app.utils.communication.notifications import NotificationTool
from app.utils.tools import get_file_from_data, save_file_as_data

module = Module(
    root="cinema",
    tag="Cinema",
    default_allowed_groups_ids=[GroupType.student, GroupType.staff],
)

hyperion_error_logger = logging.getLogger("hyperion.error")


@module.router.get(
    "/cinema/sessions",
    response_model=list[schemas_cinema.CineSessionComplete],
    status_code=200,
)
async def get_sessions(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    result = await cruds_cinema.get_sessions(db=db)
    return result


@module.router.post(
    "/cinema/sessions",
    response_model=schemas_cinema.CineSessionComplete,
    status_code=201,
)
async def create_session(
    session: schemas_cinema.CineSessionBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.cinema)),
    notification_tool: NotificationTool = Depends(get_notification_tool),
):
    db_session = schemas_cinema.CineSessionComplete(
        id=str(uuid.uuid4()),
        **session.model_dump(),
    )
    try:
        result = await cruds_cinema.create_session(session=db_session, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    try:
        days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        months = [
            "Janvier",
            "Février",
            "Mars",
            "Avril",
            "Mai",
            "Juin",
            "Juillet",
            "Août",
            "Septembre",
            "Octobre",
            "Novembre",
            "Décembre",
        ]
        french_hour = db_session.start.astimezone(ZoneInfo("Europe/Paris"))
        message_content = (
            db_session.name
            + " - "
            + days[db_session.start.weekday()]
            + " "
            + db_session.start.strftime("%d")
            + " "
            + months[db_session.start.month - 1]
            + " à "
            + french_hour.strftime("%H:%M")
        )
        message = TopicMessage(
            title="🎬 Cinéma - Nouvelle séance",
            content=message_content,
        )

        notification_tool.send_notification_to_topic(
            custom_topic=CustomTopic(Topic.cinema),
            message=message,
        )

    except Exception as error:
        hyperion_error_logger.error(f"Error while sending CINEMA notification, {error}")

    return result


@module.router.patch("/cinema/sessions/{session_id}", status_code=200)
async def update_session(
    session_id: str,
    session_update: schemas_cinema.CineSessionUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.cinema)),
):
    await cruds_cinema.update_session(
        session_id=session_id,
        session_update=session_update,
        db=db,
    )


@module.router.delete("/cinema/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.cinema)),
):
    await cruds_cinema.delete_session(session_id=session_id, db=db)


@module.router.post(
    "/cinema/sessions/{session_id}/poster",
    response_model=standard_responses.Result,
    status_code=201,
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
        upload_file=image,
        directory="cinemasessions",
        filename=str(session_id),
        request_id=request_id,
        max_file_size=4 * 1024 * 1024,
        accepted_content_types=[
            ContentType.jpg,
            ContentType.png,
            ContentType.webp,
        ],
    )

    return standard_responses.Result(success=True)


@module.router.get(
    "/cinema/sessions/{session_id}/poster",
    response_class=FileResponse,
    status_code=200,
)
async def read_session_poster(
    session_id: str,
    user: models_core.CoreUser = Depends(is_user_a_member),
    db: AsyncSession = Depends(get_db),
):
    session = await cruds_cinema.get_session_by_id(db=db, session_id=session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="The session does not exist.",
        )

    return get_file_from_data(
        default_asset="assets/images/default_movie.png",
        directory="cinemasessions",
        filename=str(session_id),
    )
