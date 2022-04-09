from fastapi import APIRouter
from app.utils.mail.mailworker import send_email
from starlette.responses import JSONResponse


router = APIRouter()


@router.post("/send-email/")
def send_email_backgroundtasks(email: str, subject: str, content: str):
    # TODO: WARNING this endpoint should be removed or restricted

    send_email(email, subject, content)
    return JSONResponse(status_code=200, content={"message": "email has been sent"})
