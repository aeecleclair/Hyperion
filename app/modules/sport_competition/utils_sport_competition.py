from app.modules.sport_competition import (
    schemas_sport_competition,
    types_sport_competition,
)


def checksport_category_compatibility(
    sport_category1: types_sport_competition.SportCategory | None,
    sport_category2: types_sport_competition.SportCategory | None,
):
    """
    Check if two sport categories are compatible.
    If one of the categories is None, they are compatible.
    If both categories are the same, they are compatible.
    If both categories are different, they are not compatible.
    """
    if sport_category1 is None or sport_category2 is None:
        return True
    return sport_category1 == sport_category2


def get_public_type_from_user(
    user: schemas_sport_competition.CompetitionUser,
) -> list[types_sport_competition.ProductPublicType]:
    types = []
    if user.is_athlete:
        types.append(types_sport_competition.ProductPublicType.athlete)
    elif user.is_pompom:
        types.append(types_sport_competition.ProductPublicType.pompom)
    elif user.is_cameraman:
        types.append(types_sport_competition.ProductPublicType.cameraman)
    elif user.is_fanfare:
        types.append(types_sport_competition.ProductPublicType.fanfare)
    if user.is_volunteer:
        types.append(types_sport_competition.ProductPublicType.volunteer)
    return types
