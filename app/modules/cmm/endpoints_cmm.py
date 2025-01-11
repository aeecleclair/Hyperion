import uuid
from datetime import UTC, datetime

from fastapi import Depends, File, HTTPException
from fastapi.datastructures import UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.groups.groups_type import AccountType, GroupType
from app.dependencies import (
    get_db,
    get_request_id,
    is_user,
)
from app.modules.cmm import cruds_cmm, models_cmm, schemas_cmm, types_cmm
from app.types.content_type import ContentType
from app.types.module import Module
from app.utils.tools import (
    delete_file_from_data,
    get_file_from_data,
    is_user_member_of_an_allowed_group,
    save_file_as_data,
)

module = Module(
    root="cmm",
    tag="Centrale Mega Meme",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
)


async def verify_ban_status(
    db,
    user,
):
    user_current_ban = await cruds_cmm.get_user_current_ban(db=db, user_id=user.id)
    if user_current_ban is not None:
        raise HTTPException(status_code=403, detail="You are currently banned")


@module.router.get(
    "/cmm/memes/",
    response_model=list[schemas_cmm.ShownMeme],
    status_code=200,
)
async def get_memes(
    sort_by: str = "best",
    n_page: int = 1,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Get a page of memes according to the asked sort
    """
    if n_page < 1:
        raise HTTPException(
            status_code=404,
            detail="Invalid page number",
        )

    match sort_by:
        case types_cmm.MemeSort.best:
            meme_page = await cruds_cmm.get_memes_by_votes(
                db=db,
                descending=True,
                n_page=n_page,
                user_id=user.id,
            )
        case types_cmm.MemeSort.worst:
            meme_page = await cruds_cmm.get_memes_by_votes(
                db=db,
                descending=False,
                n_page=n_page,
                user_id=user.id,
            )
        case types_cmm.MemeSort.trending:
            meme_page = await cruds_cmm.get_trending_memes(
                db=db,
                n_page=n_page,
                user_id=user.id,
            )
        case types_cmm.MemeSort.newest:
            meme_page = await cruds_cmm.get_memes_by_date(
                db=db,
                descending=True,
                n_page=n_page,
                user_id=user.id,
            )
        case types_cmm.MemeSort.oldest:
            meme_page = await cruds_cmm.get_memes_by_date(
                db=db,
                descending=False,
                n_page=n_page,
                user_id=user.id,
            )
        case _:
            raise HTTPException(status_code=404, detail="Invalid sort method")

    return [
        schemas_cmm.ShownMeme(
            id=str(meme.id),
            user=meme.user,
            creation_time=meme.creation_time,
            vote_score=meme.vote_score,
            status=meme.status,
            my_vote=meme.votes[0].positive if meme.votes else None,
        )
        for meme in meme_page
    ]


@module.router.get(
    "/cmm/memes/{meme_id}/",
    status_code=200,
    response_model=schemas_cmm.ShownMeme,
)
async def get_meme_by_id(
    meme_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Get a meme caracteristics using its id
    """
    shown_meme = await cruds_cmm.get_meme_by_id(db=db, meme_id=meme_id, user_id=user.id)
    if shown_meme is None:
        raise HTTPException(status_code=404, detail="The meme does not exist")

    return shown_meme


@module.router.get(
    "/cmm/memes/{meme_id}/img/",
    status_code=200,
    response_class=FileResponse,
)
async def get_meme_image_by_id(
    meme_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Get a meme image using its id
    """
    meme = await cruds_cmm.get_meme_by_id(db=db, meme_id=meme_id, user_id=user.id)
    if meme is None:
        raise HTTPException(status_code=404, detail="The meme does not exist")

    return get_file_from_data(
        default_asset="assets/images/default_meme.png",
        directory="memes",
        filename=str(meme_id),
    )


@module.router.delete(
    "/cmm/memes/{meme_id}/",
    status_code=204,
)
async def delete_meme_by_id(
    meme_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Remove a meme from db
    Must be author of meme if meme is not banned or admin
    """
    meme = await cruds_cmm.get_meme_by_id(db=db, meme_id=meme_id, user_id=user.id)
    if not meme:
        raise HTTPException(
            status_code=404,
            detail="Invalid meme_id",
        )
    if not is_user_member_of_an_allowed_group(user, [GroupType.admin]):
        if meme.user_id != user.id:
            raise HTTPException(
                status_code=403,
                detail="You cannot remove a meme from another user",
            )
        elif meme.status != types_cmm.MemeStatus.neutral:
            raise HTTPException(
                status_code=403,
                detail="You cannot remove your meme if it is banned ",
            )

    try:
        await cruds_cmm.delete_meme_by_id(db=db, meme_id=meme_id)
        await delete_file_from_data(directory="meme", filename=str(meme_id))
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.post(
    "/cmm/memes/",
    response_model=schemas_cmm.Meme,
    status_code=201,
)
async def add_meme(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
    image: UploadFile = File(...),
    request_id: str = Depends(get_request_id),
):
    """
    Add a new meme
    """
    try:
        meme_id = uuid.uuid4()
        meme = models_cmm.Meme(
            id=meme_id,
            user_id=user.id,
            creation_time=datetime.now(UTC),
            vote_score=0,
            votes=[],
            status=types_cmm.MemeStatus.neutral,
        )
        cruds_cmm.add_meme(db=db, meme=meme)
        await db.commit()
        await save_file_as_data(
            upload_file=image,
            directory="memes",
            filename=str(meme_id),
            request_id=request_id,
            max_file_size=4 * 1024 * 1024,
            accepted_content_types=[
                ContentType.jpg,
                ContentType.png,
                ContentType.webp,
            ],
        )

    except Exception:
        await db.rollback()
        raise
    else:
        return meme


@module.router.get(
    "/cmm/memes/{meme_id}/vote/",
    status_code=200,
    response_model=schemas_cmm.Vote,
)
async def get_vote(
    meme_id: uuid.UUID,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Get a meme caracteristics using its id
    """
    vote = await cruds_cmm.get_vote(db=db, meme_id=meme_id, user_id=user_id)
    if vote is None:
        raise HTTPException(
            status_code=404,
            detail="The meme has no vote from this user",
        )

    return vote


@module.router.get(
    "/cmm/memes/votes/{vote_id}/",
    status_code=200,
    response_model=schemas_cmm.Vote,
)
async def get_vote_by_id(
    vote_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Get a meme caracteristics using its id
    """
    vote = await cruds_cmm.get_vote_by_id(db=db, vote_id=vote_id)
    if vote is None:
        raise HTTPException(status_code=404, detail="The vote does not exist")

    return vote


@module.router.post(
    "/cmm/memes/{meme_id}/vote/",
    response_model=schemas_cmm.Vote,
    status_code=201,
)
async def add_vote(
    meme_id: uuid.UUID,
    positive: bool,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Add a new vote for the user to a meme from its id
    """
    meme = await cruds_cmm.get_meme_by_id(db=db, meme_id=meme_id, user_id=user.id)
    if meme is None:
        raise HTTPException(status_code=404, detail="The meme does not exist")
    try:
        vote_id = uuid.uuid4()
        vote = models_cmm.Vote(
            id=vote_id,
            meme_id=meme_id,
            user_id=user.id,
            positive=positive,
        )
        await cruds_cmm.update_meme_vote_score(
            db=db,
            meme_id=meme_id,
            old_positive=meme.votes[0].positive if meme.votes else None,
            new_positive=positive,
        )
        cruds_cmm.add_vote(db=db, vote=vote)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    else:
        return vote


@module.router.delete(
    "/cmm/memes/{meme_id}/vote/",
    status_code=201,
)
async def delete_vote(
    meme_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Remove the vote from the user if it exists
    """
    meme = await cruds_cmm.get_meme_by_id(db=db, meme_id=meme_id, user_id=user.id)
    if meme is None:
        raise HTTPException(status_code=404, detail="The meme does not exist")
    vote = await cruds_cmm.get_vote(db=db, meme_id=meme_id, user_id=user.id)
    if vote is None:
        raise HTTPException(status_code=404, detail="The vote does not exist")
    try:
        await cruds_cmm.update_meme_vote_score(
            db=db,
            meme_id=meme_id,
            old_positive=meme.votes[0].positive if meme.votes else None,
            new_positive=vote.positive,
        )
        await cruds_cmm.delete_vote(db=db, vote_id=vote.id)
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.patch(
    "/cmm/memes/{meme_id}/vote/",
    status_code=201,
)
async def update_vote(
    meme_id: uuid.UUID,
    positive: bool,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Update a vote from the user if it exists even if vote is already at the right positivity
    """
    meme = await cruds_cmm.get_meme_by_id(db=db, meme_id=meme_id, user_id=user.id)
    if meme is None:
        raise HTTPException(status_code=404, detail="The meme does not exist")
    vote = await cruds_cmm.get_vote(db=db, meme_id=meme_id, user_id=user.id)
    if vote is None:
        raise HTTPException(status_code=404, detail="The vote does not exist")
    try:
        await cruds_cmm.update_meme_vote_score(
            db=db,
            meme_id=meme_id,
            old_positive=meme.votes[0].positive if meme.votes else None,
            new_positive=vote.positive,
        )
        await cruds_cmm.update_vote(db=db, vote_id=vote.id, new_positive=positive)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    else:
        vote.positive = positive
        return vote


@module.router.post(
    "/cmm/users/{user_id}/ban/",
    status_code=201,
    response_model=models_cmm.Ban,
)
async def ban_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Ban a user and hide all of his memes
    Must be admin
    """
    if not is_user_member_of_an_allowed_group(user, [GroupType.admin]):
        raise HTTPException(
            status_code=401,
            detail="Cannot ban another user",
        )

    current_ban = await cruds_cmm.get_user_current_ban(db=db, user_id=user_id)
    if current_ban is not None:
        raise HTTPException(status_code=404, detail="User is already banned")

    ban = models_cmm.Ban(
        id=uuid.uuid4(),
        user_id=user_id,
        admin_id=user.id,
        end_time=None,
        creation_time=datetime.now(UTC),
    )
    try:
        cruds_cmm.add_user_ban(db=db, ban=ban)
        await cruds_cmm.update_ban_status_of_memes_from_user(
            db=db,
            user_id=user_id,
            new_ban_status=types_cmm.MemeStatus.banned,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    else:
        return ban


@module.router.post(
    "/cmm/users/{user_id}/unban/",
    status_code=201,
)
async def unban_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Unban a user and unhide all of his memes
    Must be admin
    """
    if not is_user_member_of_an_allowed_group(user, [GroupType.admin]):
        raise HTTPException(
            status_code=401,
            detail="Cannot unban another user",
        )

    current_ban = await cruds_cmm.get_user_current_ban(db=db, user_id=user_id)
    if current_ban is None:
        raise HTTPException(status_code=404, detail="User is not already banned")

    try:
        await cruds_cmm.update_end_of_ban(
            db=db,
            ban_id=current_ban.id,
            end_time=datetime.now(UTC),
        )
        await cruds_cmm.update_ban_status_of_memes_from_user(
            db=db,
            user_id=user_id,
            new_ban_status=types_cmm.MemeStatus.neutral,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.get(
    "/cmm/users/{user_id}/ban_history/",
    status_code=200,
    response_model=list[schemas_cmm.Ban],
)
async def get_user_ban_history(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Get the ban history of an user
    """
    ban_history = await cruds_cmm.get_user_ban_history(db=db, user_id=user_id)
    return ban_history
