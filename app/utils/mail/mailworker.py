import logging
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings

hyperion_error_logger = logging.getLogger("hyperion.error")


def send_email(
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

    hyperion_error_logger.debug(f"Sending email to {recipient}")

    if isinstance(recipient, str):
        recipient = [recipient]

    context = ssl.create_default_context()

    msg = EmailMessage()
    msg.set_content(content, subtype="html", charset="utf-8")
    msg["From"] = settings.SMTP_EMAIL
    msg["To"] = ";".join(recipient)
    msg["Subject"] = subject

    if file_directory and file_name:
        hyperion_error_logger.debug(
            f"Adding attachment {Path(file_directory, file_name)}",
        )
        file_path = Path(file_directory, file_name)
        hyperion_error_logger.debug(f"Reading file '{file_path}'")
        with Path.open(file_path, "rb") as file:
            hyperion_error_logger.debug(f"Reading file {file_name}")
            msg.add_attachment(
                file.read(),
                main_type=main_type,
                sub_type=sub_type,
                filename=file_name,
            )

    hyperion_error_logger.debug(f"Sending email to {recipient}")
    with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg, settings.SMTP_EMAIL, recipient)

    hyperion_error_logger.debug(f"Email sent to {recipient}")
