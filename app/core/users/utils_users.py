from app.core.groups import schemas_groups
from app.core.schools import schemas_schools
from app.core.users import models_users, schemas_users


def user_simple_model_to_schema(
    model: models_users.CoreUser,
) -> schemas_users.CoreUserSimple:
    """Convert a CoreUser model to a CoreUserSimple schema."""
    return schemas_users.CoreUserSimple(
        id=model.id,
        account_type=model.account_type,
        school_id=model.school_id,
        nickname=model.nickname,
        firstname=model.firstname,
        name=model.name,
    )


def user_model_to_schema(
    model: models_users.CoreUser,
) -> schemas_users.CoreUser:
    """Convert a CoreUser model to a CoreUser schema."""
    return schemas_users.CoreUser(
        id=model.id,
        account_type=model.account_type,
        school_id=model.school_id,
        nickname=model.nickname,
        firstname=model.firstname,
        name=model.name,
        email=model.email,
        birthday=model.birthday,
        promo=model.promo,
        floor=model.floor,
        phone=model.phone,
        created_on=model.created_on,
        groups=[
            schemas_groups.CoreGroupSimple(id=group.id, name=group.name)
            for group in model.groups
        ],
        school=schemas_schools.CoreSchool(
            id=model.school.id,
            name=model.school.name,
            email_regex=model.school.email_regex,
        ),
    )
