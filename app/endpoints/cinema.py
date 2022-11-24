import uuid

from fastapi import APIRouter, Depends, HTTPException
from imdb import Cinemagoer
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_cinema
from app.dependencies import get_db, is_user_a_member, is_user_a_member_of
from app.models import models_core
from app.schemas import schemas_cinema
from app.utils.types.groups_type import GroupType
from app.utils.types.tags import Tags

router = APIRouter()
moviedb = Cinemagoer()


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
):
    db_session = schemas_cinema.CineSessionComplete(
        id=str(uuid.uuid4()), **session.dict()
    )
    try:
        result = await cruds_cinema.create_session(session=db_session, db=db)
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.post(
    "cinema/sessions/{imdb_id}",
    response_model=schemas_cinema.CineSessionComplete,
    status_code=201,
    tags=[Tags.cinema],
)
async def create_session_with_id(
    imdb_id: str,
    session: schemas_cinema.CineSessionTime,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.cinema)),
):
    movie = moviedb.get_movie(imdb_id)
    db_session = schemas_cinema.CineSessionComplete(
        id=str(uuid.uuid4()),
        name=movie["localized title"],
        overview=movie["plot outline"],
        poster_url=movie["full size poster url"],
        genre=movie["genres"],
        **session.dict(),
    )
    try:
        result = await cruds_cinema.create_session(session=db_session, db=db)
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


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
