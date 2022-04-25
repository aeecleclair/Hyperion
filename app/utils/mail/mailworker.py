import smtplib
import ssl
from email.message import EmailMessage

from app.core.settings import settings


def send_email(recipient: str, subject: str, content: str):
    """
    Send a plain text email using **starttls**.
    Use the SMTP settings defined in environments variables or the dotenv file.
    See [Settings class](app/core/settings.py) for more informations
    """
    # Send email using
    # https://realpython.com/python-send-email/#option-1-setting-up-a-gmail-account-for-development
    # Prevent send email from going to spam
    # https://errorsfixing.com/why-do-some-python-smtplib-messages-deliver-to-gmail-spam-folder/

    context = ssl.create_default_context()

    msg = EmailMessage()
    msg.set_content(content, subtype="plain", charset="us-ascii")
    msg["From"] = settings.SMTP_EMAIL
    msg["To"] = recipient
    msg["Subject"] = subject

    with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
