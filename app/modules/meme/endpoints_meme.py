import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import Depends, File, HTTPException
from fastapi.datastructures import UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core, schemas_core
from app.core.groups.groups_type import GroupType
from app.dependencies import (
    get_db,
    get_request_id,
    is_user_a_member,
    is_user_in,
)
from app.modules.meme import cruds_meme, models_meme, schemas_meme, types_meme
from app.types.content_type import ContentType
from app.types.module import Module
from app.utils.tools import (
    delete_file_from_data,
    get_file_from_data,
    save_file_as_data,
)

if TYPE_CHECKING:
    from app.types.floors_type import FloorsType

module = Module(
    root="meme",
    tag="Centrale Mega Meme",
)


async def is_allowed_meme_user(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
) -> models_core.CoreUser:
    """
    Overloads the is_user() dependency injection to verify if the user is in the banned table
    """
    user_current_ban = await cruds_meme.get_user_current_ban(db=db, user_id=user.id)
    if user_current_ban is not None:
        raise HTTPException(status_code=403, detail="You are currently banned")
    return user


@module.router.get(
    "/meme/memes/",
    response_model=list[schemas_meme.ShownMeme],
    status_code=200,
)
async def get_memes(
    sort_by: str = "best",
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get memes according to the asked sort
    """

    match sort_by:
        case types_meme.MemeSort.best:
            meme_page = await cruds_meme.get_memes_by_votes(
                db=db,
                descending=True,
                user_id=user.id,
            )
        case types_meme.MemeSort.worst:
            meme_page = await cruds_meme.get_memes_by_votes(
                db=db,
                descending=False,
                user_id=user.id,
            )
        case types_meme.MemeSort.trending:
            meme_page = await cruds_meme.get_trending_memes(
                db=db,
                user_id=user.id,
            )
        case types_meme.MemeSort.newest:
            meme_page = await cruds_meme.get_memes_by_date(
                db=db,
                descending=True,
                user_id=user.id,
            )
        case types_meme.MemeSort.oldest:
            meme_page = await cruds_meme.get_memes_by_date(
                db=db,
                descending=False,
                user_id=user.id,
            )
        case _:
            raise HTTPException(status_code=404, detail="Invalid sort method")

    return [
        schemas_meme.ShownMeme(
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
    "/meme/memes/me",
    response_model=list[schemas_meme.ShownMeme],
    status_code=200,
)
async def get_my_memes(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    meme_page = await cruds_meme.get_my_memes(
        db=db,
        user_id=user.id,
    )

    return [
        schemas_meme.ShownMeme(
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
    "/meme/memes/{meme_id}/img/",
    status_code=200,
    response_class=FileResponse,
)
async def get_meme_image_by_id(
    meme_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_allowed_meme_user),
):
    """
    Get a meme image using its id
    """
    meme = await cruds_meme.get_meme_by_id(db=db, meme_id=meme_id, user_id=user.id)
    if meme is None:
        raise HTTPException(status_code=404, detail="The meme does not exist")

    return get_file_from_data(
        default_asset="assets/images/default_meme.png",
        directory="memes",
        filename=str(meme_id),
    )


@module.router.post(
    "/meme/memes/{meme_id}/hide/",
    status_code=201,
)
async def hide_meme_by_id(
    meme_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.meme)),
):
    """
    Hide a meme from db
    Must be admin
    """
    meme = await cruds_meme.get_meme_by_id(db=db, meme_id=meme_id, user_id=user.id)
    if meme is None:
        raise HTTPException(status_code=404, detail="The meme does not exist")

    try:
        await cruds_meme.update_meme_ban_status(
            db=db,
            ban_status=types_meme.MemeStatus.banned,
            meme_id=meme_id,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.post(
    "/meme/memes/{meme_id}/show/",
    status_code=201,
)
async def show_meme_by_id(
    meme_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.meme)),
):
    """
    Show a meme from db
    Must be admin
    """
    meme = await cruds_meme.get_meme_by_id(db=db, meme_id=meme_id, user_id=user.id)
    if meme is None:
        raise HTTPException(status_code=404, detail="The meme does not exist")

    try:
        await cruds_meme.update_meme_ban_status(
            db=db,
            ban_status=types_meme.MemeStatus.neutral,
            meme_id=meme_id,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.delete(
    "/meme/memes/{meme_id}/",
    status_code=204,
)
async def delete_meme_by_id(
    meme_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Remove a meme from db
    Must be author of meme if meme is not banned
    """
    meme = await cruds_meme.get_meme_by_id(db=db, meme_id=meme_id, user_id=user.id)
    if not meme:
        raise HTTPException(
            status_code=404,
            detail="Invalid meme_id",
        )
    if meme.status == types_meme.MemeStatus.banned:
        raise HTTPException(
            status_code=403,
            detail="You can't delete a banned meme",
        )
    if meme.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="You are not the author of this meme",
        )
    try:
        await cruds_meme.delete_meme_by_id(db=db, meme_id=meme_id)
        delete_file_from_data(directory="meme", filename=str(meme_id))
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.post(
    "/meme/memes/",
    response_model=schemas_meme.Meme,
    status_code=201,
)
async def add_meme(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_allowed_meme_user),
    image: UploadFile = File(...),
    request_id: str = Depends(get_request_id),
):
    """
    Add a new meme
    """
    try:
        meme_id = uuid.uuid4()
        meme = models_meme.Meme(
            id=meme_id,
            user_id=user.id,
            creation_time=datetime.now(UTC),
            vote_score=0,
            votes=[],
            status=types_meme.MemeStatus.neutral,
        )
        cruds_meme.add_meme(db=db, meme=meme)
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
    "/meme/memes/{meme_id}/vote/",
    status_code=200,
    response_model=schemas_meme.Vote,
)
async def get_vote(
    meme_id: uuid.UUID,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_allowed_meme_user),
):
    """
    Get a meme caracteristics using its id
    """
    vote = await cruds_meme.get_vote(db=db, meme_id=meme_id, user_id=user_id)
    if vote is None:
        raise HTTPException(
            status_code=404,
            detail="The meme has no vote from this user",
        )

    return vote


@module.router.get(
    "/meme/memes/votes/{vote_id}/",
    status_code=200,
    response_model=schemas_meme.Vote,
)
async def get_vote_by_id(
    vote_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_allowed_meme_user),
):
    """
    Get a meme caracteristics using its id
    """
    vote = await cruds_meme.get_vote_by_id(db=db, vote_id=vote_id)
    if vote is None:
        raise HTTPException(status_code=404, detail="The vote does not exist")

    return vote


@module.router.post(
    "/meme/memes/{meme_id}/vote/",
    response_model=schemas_meme.Vote,
    status_code=201,
)
async def add_vote(
    meme_id: uuid.UUID,
    positive: bool,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_allowed_meme_user),
):
    """
    Add a new vote for the user to a meme from its id
    """
    meme = await cruds_meme.get_meme_by_id(db=db, meme_id=meme_id, user_id=user.id)
    if meme is None:
        raise HTTPException(status_code=404, detail="The meme does not exist")
    vote = await cruds_meme.get_vote(db=db, meme_id=meme_id, user_id=user.id)
    if vote is not None:
        raise HTTPException(status_code=404, detail="Vote already created")

    try:
        vote_id = uuid.uuid4()
        vote = models_meme.Vote(
            id=vote_id,
            meme_id=meme_id,
            user_id=user.id,
            positive=positive,
        )
        await cruds_meme.update_meme_vote_score(
            db=db,
            meme_id=meme_id,
            old_positive=None,
            new_positive=positive,
        )
        cruds_meme.add_vote(db=db, vote=vote)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    else:
        return schemas_meme.Vote(
            meme_id=str(vote.meme_id),
            positive=vote.positive,
            user=vote.user,
        )


@module.router.delete(
    "/meme/memes/{meme_id}/vote/",
    status_code=204,
)
async def delete_vote(
    meme_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_allowed_meme_user),
):
    """
    Remove the vote from the user if it exists
    """
    meme = await cruds_meme.get_meme_by_id(db=db, meme_id=meme_id, user_id=user.id)
    if meme is None:
        raise HTTPException(status_code=404, detail="The meme does not exist")
    vote = await cruds_meme.get_vote(db=db, meme_id=meme_id, user_id=user.id)
    if vote is None:
        raise HTTPException(status_code=404, detail="The vote does not exist")
    try:
        await cruds_meme.update_meme_vote_score(
            db=db,
            meme_id=meme_id,
            old_positive=meme.votes[0].positive if meme.votes else None,
            new_positive=None,
        )
        await cruds_meme.delete_vote(db=db, vote_id=vote.id)
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.patch(
    "/meme/memes/{meme_id}/vote/",
    status_code=204,
)
async def update_vote(
    meme_id: uuid.UUID,
    positive: bool,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_allowed_meme_user),
):
    """
    Update a vote from the user if it exists even if vote is already at the right positivity
    """
    meme = await cruds_meme.get_meme_by_id(db=db, meme_id=meme_id, user_id=user.id)
    if meme is None:
        raise HTTPException(status_code=404, detail="The meme does not exist")
    vote = await cruds_meme.get_vote(db=db, meme_id=meme_id, user_id=user.id)
    if vote is None:
        raise HTTPException(status_code=404, detail="The vote does not exist")
    try:
        await cruds_meme.update_meme_vote_score(
            db=db,
            meme_id=meme_id,
            old_positive=meme.votes[0].positive,  # should exist
            new_positive=positive,
        )
        await cruds_meme.update_vote(db=db, vote_id=vote.id, new_positive=positive)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    else:
        return schemas_meme.Vote(
            meme_id=str(vote.meme_id),
            positive=positive,
            user=user,
        )


@module.router.post(
    "/meme/users/{user_id}/ban/",
    status_code=201,
)
async def ban_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.meme)),
):
    """
    Ban a user and hide all of his memes
    Must be admin
    """

    current_ban = await cruds_meme.get_user_current_ban(db=db, user_id=user_id)
    if current_ban is not None:
        raise HTTPException(status_code=404, detail="User is already banned")

    ban = models_meme.Ban(
        id=uuid.uuid4(),
        user_id=user_id,
        admin_id=user.id,
        end_time=None,
        creation_time=datetime.now(UTC),
    )
    try:
        cruds_meme.add_user_ban(db=db, ban=ban)
        await cruds_meme.update_ban_status_of_memes_from_user(
            db=db,
            user_id=user_id,
            new_ban_status=types_meme.MemeStatus.banned,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.post(
    "/meme/users/{user_id}/unban/",
    status_code=201,
)
async def unban_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.meme)),
):
    """
    Unban a user and unhide all of his memes
    Must be admin
    """

    current_ban = await cruds_meme.get_user_current_ban(db=db, user_id=user_id)
    if current_ban is None:
        raise HTTPException(status_code=404, detail="User is not already banned")

    try:
        await cruds_meme.update_end_of_ban(
            db=db,
            ban_id=current_ban.id,
            end_time=datetime.now(UTC),
        )
        await cruds_meme.update_ban_status_of_memes_from_user(
            db=db,
            user_id=user_id,
            new_ban_status=types_meme.MemeStatus.neutral,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@module.router.get(
    "/meme/users/{user_id}/ban_history/",
    status_code=200,
    response_model=list[schemas_meme.Ban],
)
async def get_user_ban_history(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.meme)),
):
    """
    Get the ban history of an user
    """
    ban_history = await cruds_meme.get_user_ban_history(db=db, user_id=user_id)
    return ban_history


@module.router.get(
    "/meme/users/banned/",
    status_code=200,
    response_model=list[schemas_core.CoreUserSimple],
)
async def get_banned_users(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.meme)),
):
    banned_users = await cruds_meme.get_banned_users(db=db)
    return banned_users


@module.router.get(
    "/meme/memes/hidden/",
    status_code=200,
    response_model=list[schemas_meme.ShownMeme],
)
async def get_hidden_memes(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.meme)),
):
    hidden_memes = await cruds_meme.get_hidden_memes(
        db=db,
        descending=True,
        user_id=user.id,
    )
    return [
        schemas_meme.ShownMeme(
            id=str(meme.id),
            user=meme.user,
            creation_time=meme.creation_time,
            vote_score=meme.vote_score,
            status=meme.status,
            my_vote=meme.votes[0].positive if meme.votes else None,
        )
        for meme in hidden_memes
    ]


@module.router.get(
    "/meme/leaderboard/",
    status_code=200,
    response_model=list[schemas_meme.UserScore]
    | list[schemas_meme.FloorScore]
    | list[schemas_meme.PromoScore],
)
async def get_user_leaderbord(
    period: types_meme.PeriodLeaderboard,
    entity: types_meme.EntityLeaderboard,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    match period:
        case types_meme.PeriodLeaderboard.week:
            n_jours = 7
        case types_meme.PeriodLeaderboard.month:
            n_jours = 30
        case types_meme.PeriodLeaderboard.year:
            n_jours = 365
        case types_meme.PeriodLeaderboard.always:
            n_jours = -1
        case _:
            raise HTTPException(status_code=404, detail="Invalid period")

    memes = await cruds_meme.get_all_memes(db=db, n_jours=n_jours)

    match entity:
        case types_meme.EntityLeaderboard.promo:
            promo_scores: dict[int, int] = {}

            for meme in memes:
                meme_author = meme.user
                meme_author_promo = meme_author.promo
                if meme_author_promo:
                    if meme_author_promo not in promo_scores:
                        promo_scores[meme_author_promo] = 0

                    promo_scores[meme_author_promo] += meme.vote_score

            sorted_promo_scores = sorted(
                promo_scores.items(),
                key=lambda item: item[1],
                reverse=True,
            )

            return [
                {
                    "promo": promo,
                    "score": total_score,
                    "position": i + 1,
                }
                for i, (promo, total_score) in enumerate(sorted_promo_scores)
            ]

        case types_meme.EntityLeaderboard.floor:
            floor_scores: dict[FloorsType, int] = {}

            for meme in memes:
                meme_author = meme.user
                meme_author_floor = meme_author.floor
                if meme_author_floor:
                    if meme_author_floor not in floor_scores:
                        floor_scores[meme_author_floor] = 0

                    floor_scores[meme_author_floor] += meme.vote_score

            sorted_floor_scores = sorted(
                floor_scores.items(),
                key=lambda item: item[1],
                reverse=True,
            )

            return [
                {
                    "floor": floor,
                    "score": total_score,
                    "position": i + 1,
                }
                for i, (floor, total_score) in enumerate(sorted_floor_scores)
            ]

        case types_meme.EntityLeaderboard.user:
            user_scores: dict[str, int] = {}
            users: dict[str, models_core.CoreUser] = {}

            for meme in memes:
                meme_author = meme.user
                meme_author_id = meme_author.id

                user_scores[meme_author_id] = (
                    user_scores.get(meme_author_id, 0) + meme.vote_score
                )
                users[meme_author_id] = meme_author

            sorted_user_scores = sorted(
                user_scores.items(),
                key=lambda item: item[1],
                reverse=True,
            )

            return [
                {"user": users[user_id], "score": score, "position": i + 1}
                for i, (user_id, score) in enumerate(sorted_user_scores)
            ]

        case _:
            raise HTTPException(status_code=404, detail="Invalid period")


@module.router.get(
    "/meme/leaderboard/me",
    status_code=200,
    response_model=schemas_meme.Score,
)
async def get_my_leaderbord(
    period: types_meme.PeriodLeaderboard,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    match period:
        case types_meme.PeriodLeaderboard.week:
            n_jours = 7
        case types_meme.PeriodLeaderboard.month:
            n_jours = 30
        case types_meme.PeriodLeaderboard.year:
            n_jours = 365
        case types_meme.PeriodLeaderboard.always:
            n_jours = -1
        case _:
            raise HTTPException(status_code=404, detail="Invalid period")

    memes = await cruds_meme.get_all_memes(db=db, n_jours=n_jours)

    my_score = sum(meme.vote_score for meme in memes if meme.user.id == user.id)

    user_scores: dict[str, int] = {}

    for meme in memes:
        user_id = meme.user.id
        user_scores[user_id] = user_scores.get(user_id, 0) + meme.vote_score

    sorted_scores = sorted(user_scores.items(), key=lambda item: item[1], reverse=True)

    my_position = next(
        (i + 1 for i, (user_id, _) in enumerate(sorted_scores) if user_id == user.id),
        None,
    )

    return {"score": my_score, "position": my_position}
