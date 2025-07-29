import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import TYPE_CHECKING

from app.core.core_endpoints import cruds_core

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.utils.config import Settings

hyperion_error_logger = logging.getLogger("hyperion.error")


def send_email(
    recipient: str | list[str],
    subject: str,
    content: str,
    settings: "Settings",
):
    """
    Send a html email using **starttls**.
    Use the SMTP settings defined in environments variables or the dotenv file.
    See [Settings class](app/core/settings.py) for more information
    """
    # Send email using
    # https://realpython.com/python-send-email/#option-1-setting-up-a-gmail-account-for-development
    # Prevent send email from going to spam
    # https://errorsfixing.com/why-do-some-python-smtplib-messages-deliver-to-gmail-spam-folder/

    if isinstance(recipient, str):
        if recipient == "":
            return
        recipient = [recipient]

    if len(recipient) == 0:
        return

    context = ssl.create_default_context()

    msg = EmailMessage()
    msg.set_content(content, subtype="html", charset="utf-8")
    msg["From"] = settings.SMTP_EMAIL
    msg["To"] = ";".join(recipient)
    msg["Subject"] = subject

    with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        try:
            server.send_message(msg, settings.SMTP_EMAIL, recipient)
        except smtplib.SMTPRecipientsRefused:
            hyperion_error_logger.warning(
                f'Bad email adress: "{", ".join(recipient)}" for mail with subject "{subject}".',
            )


async def send_emails_from_queue(db: "AsyncSession", settings: "Settings") -> None:
    """
    Send emails from the email queue. This function should be called by a cron scheduled task only once per hour.
    The task will only send 100 emails per hour to avoid being rate-limited by the email provider.
    """
    queued_emails = await cruds_core.get_queued_emails(
        db=db,
        limit=100,
    )

    send_emails_ids = [email.id for email in queued_emails]

    for email in queued_emails:
        try:
            await send_email(
                recipient=email.email,
                subject=email.subject,
                content=email.body,
                settings=settings,
            )
        except Exception:
            hyperion_error_logger.exception(
                f"Error while sending queued email to {email.email} with subject {email.subject}",
            )
            send_emails_ids.remove(email.id)

    await cruds_core.delete_queued_email(
        queued_email_ids=send_emails_ids,
        db=db,
    )
