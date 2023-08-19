from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from app.core.config import Settings
from app.dependencies import get_settings, is_user_a_member_of
from app.models import models_core
from app.utils.mail.mailworker import send_email
from app.utils.types.groups_type import GroupType

router = APIRouter()


@router.post("/send-email/")
def send_email_backgroundtasks(
    email: str,
    subject: str,
    content: str,
    settings: Settings = Depends(get_settings),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    send_email(email, subject, content, settings=settings)
    return JSONResponse(status_code=200, content={"message": "email has been sent"})
