import logging
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType, GroupType
from app.core.notification.notification_types import CustomTopic, Topic
from app.core.notification.schemas_notification import Message
from app.core.users import models_users
from app.core.utils.config import Settings
from app.dependencies import (
    get_db,
    get_notification_tool,
    get_request_id,
    get_scheduler,
    get_settings,
    is_user_a_member,
    is_user_in,
)
from app.modules.cinema import cruds_cinema, schemas_cinema
from app.types import standard_responses
from app.types.content_type import ContentType
from app.types.module import Module
from app.types.scheduler import Scheduler
from app.utils.communication.date_manager import (
    get_date_day,
    get_date_month,
    get_previous_sunday,
)
from app.utils.communication.notifications import NotificationTool
from app.utils.tools import get_file_from_data, save_file_as_data

module = Module(
    root="cinema",
    tag="Cinema",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
)

hyperion_error_logger = logging.getLogger("hyperion.error")


@module.router.get(
    "/cinema/themoviedb/{themoviedb_id}",
    response_model=schemas_cinema.TheMovieDB,
)
async def get_movie(
    themoviedb_id: str,
    settings: Settings = Depends(get_settings),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.cinema)),
):
    """
    Makes a HTTP request to The Movie Database (TMDB)
    using an API key and returns a TheMovieDB object
    * https://developer.themoviedb.org/reference/movie-details
    * https://developer.themoviedb.org/docs/errors
    """
    API_key = settings.THE_MOVIE_DB_API
    if API_key is None:
        hyperion_error_logger.error("No API key provided for module cinema")
        raise HTTPException(status_code=501, detail="No API key provided")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url=f"https://api.themoviedb.org/3/movie/{themoviedb_id}",
                params={
                    "api_key": API_key,
                    "language": "fr-FR",
                },
            )
        match response.status_code:
            case 200:
                return schemas_cinema.TheMovieDB(**response.json())
            case 401:
                hyperion_error_logger.error(
                    f"INVALID API KEY - Code 401 for TMDB request. JSON  response: {response.json()}",
                )
                raise HTTPException(
                    status_code=501,
                    detail="Invalid API key",
                )
            case 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Movie not found for TMDB movie ID {themoviedb_id} (code {response.status_code})",
                )
            case _:
                hyperion_error_logger.error(
                    f"Code {response.status_code} for TMDB request with movie ID {themoviedb_id}. JSON response: {response.json()}",
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Unknown error (code {response.status_code})",
                )
    except httpx.RequestError:
        hyperion_error_logger.exception("Could not reach the TMDB server")
        raise HTTPException(status_code=504, detail="Could not reach the TMDB server")


@module.router.get(
    "/cinema/sessions",
    response_model=list[schemas_cinema.CineSessionComplete],
    status_code=200,
)
async def get_sessions(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
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
    user: models_users.CoreUser = Depends(is_user_in(GroupType.cinema)),
    notification_tool: NotificationTool = Depends(get_notification_tool),
    scheduler: Scheduler = Depends(get_scheduler),
):
    db_session = schemas_cinema.CineSessionComplete(
        id=str(uuid.uuid4()),
        **session.model_dump(),
    )
    try:
        result = await cruds_cinema.create_session(session=db_session, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    session_date = result.start
    sunday = get_previous_sunday(session_date)
    if sunday > datetime.now(UTC):
        next_week_sessions = await cruds_cinema.get_sessions_in_time_frame(
            start_after=sunday,
            start_before=sunday + timedelta(days=7),
            db=db,
        )
        message_content = ""
        for next_session in next_week_sessions:
            message_content += f"{get_date_day(next_session.start)} {next_session.start.day} {get_date_month(next_session.start)} - {next_session.name}\n"
        message = Message(
            title="🎬 Cinéma - Programme de la semaine",
            content=message_content,
            action_module="cinema",
        )

        await notification_tool.cancel_notification(
            scheduler=scheduler,
            job_id=f"cinema_weekly_{sunday}",
        )

        await notification_tool.send_notification_to_topic(
            custom_topic=CustomTopic(topic=Topic.cinema),
            message=message,
            scheduler=scheduler,
            defer_date=sunday,
            job_id=f"cinema_weekly_{sunday}",
        )
    return result


@module.router.patch("/cinema/sessions/{session_id}", status_code=200)
async def update_session(
    session_id: str,
    session_update: schemas_cinema.CineSessionUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.cinema)),
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
    user: models_users.CoreUser = Depends(is_user_in(GroupType.cinema)),
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
    user: models_users.CoreUser = Depends(is_user_in(GroupType.cinema)),
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
    user: models_users.CoreUser = Depends(is_user_a_member),
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
