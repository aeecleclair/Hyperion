from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.flap import models_flappybird


async def get_flappybird_score_leaderboard(
    db: AsyncSession, skip: int, limit: int
) -> list[models_flappybird.FlappyBirdScore]:

    # On récupère tous les éléments FlappyBirdScore entre begin et end ordonnés par leur valeur
    result = await db.execute(
        select(models_flappybird.FlappyBirdScore)
        .order_by(
            models_flappybird.FlappyBirdScore.value.desc(),
        )
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_flappybird_score_by_user_id(
    db: AsyncSession, user_id: str
) -> list[models_flappybird.FlappyBirdScore]:

    # On récupère tous les éléments FlappyBirdScore dont le user_id correspond à celui que l'on recherche
    result = await db.execute(
        select(models_flappybird.FlappyBirdScore).where(
            models_flappybird.FlappyBirdScore.user_id == user_id
        )
    )
    return result.scalars().all()


async def create_flappybird_score(
    db: AsyncSession, flappybird_score: models_flappybird.FlappyBirdScore
) -> models_flappybird.FlappyBirdScore:

    # L'élément est placé tout seul dans la bonne table.
    # flappybird_score est en effet une instance du model : models_flappybird.FlappyBirdScore
    # qui contient le nom de la table
    db.add(flappybird_score)
    try:
        await db.commit()
        return flappybird_score
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)
