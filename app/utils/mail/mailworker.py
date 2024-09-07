import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles

if TYPE_CHECKING:
    from app.core.config import Settings


async def send_email(
    recipient: str | list[str],
    subject: str,
    content: str,
    settings: "Settings",
    file_directory: str | None = None,
    file_name: str | None = None,
    main_type: str | None = None,
    sub_type: str | None = None,
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
        recipient = [recipient]

    context = ssl.create_default_context()

    msg = EmailMessage()
    msg.set_content(content, subtype="html", charset="utf-8")
    msg["From"] = settings.SMTP_EMAIL
    msg["To"] = ";".join(recipient)
    msg["Subject"] = subject

    if file_directory and file_name:
        async with aiofiles.open(Path(file_directory, file_name), "rb") as f:
            msg.add_attachment(
                f.read(),
                main_type=main_type,
                sub_type=sub_type,
                filename=file_name.split("/")[-1],
            )

    with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg, settings.SMTP_EMAIL, recipient)
