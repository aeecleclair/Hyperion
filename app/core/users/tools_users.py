import re
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType
from app.core.schools import cruds_schools
from app.core.schools.schools_type import SchoolType

ECL_STAFF_REGEX = r"^[\w\-.]*@(enise\.)?ec-lyon\.fr$"
ECL_STUDENT_REGEX = r"^[\w\-.]*@((etu(-enise)?)|(ecl\d{2}))\.ec-lyon\.fr$"
ECL_FORMER_STUDENT_REGEX = r"^[\w\-.]*@centraliens-lyon\.net$"


async def get_account_type_and_school_id_from_email(
    email: str,
    db: AsyncSession,
) -> tuple[AccountType, UUID]:
    """Return the account type from the email"""
    if re.match(ECL_STAFF_REGEX, email):
        return AccountType.staff, SchoolType.centrale_lyon.value
    if re.match(ECL_STUDENT_REGEX, email):
        return AccountType.student, SchoolType.centrale_lyon.value
    if re.match(ECL_FORMER_STUDENT_REGEX, email):
        return AccountType.former_student, SchoolType.centrale_lyon.value
    schools = await cruds_schools.get_schools(db)

    schools = [school for school in schools if school.id not in SchoolType.list()]
    school = next(
        (school for school in schools if re.match(school.email_regex, email)),
        None,
    )
    if school:
        return AccountType.other_school_student, school.id
    return AccountType.external, SchoolType.no_school.value
