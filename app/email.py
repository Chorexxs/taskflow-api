"""Email sending for verification (T-113).

``EMAIL_BACKEND=log`` is the development default and writes the message to the
application log. Production should use ``smtp`` with the ``SMTP_*`` settings;
``EMAIL_VERIFICATION_REQUIRED=true`` is rejected outside development/test when
the backend is still ``log``.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any
from urllib.parse import quote

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

VERIFICATION_SUBJECT = "Verify your TaskFlow email"


class LogEmailSender:
    """Development sender: the verification link is written to the log."""

    def send(self, *, to: str, subject: str, body: str) -> None:
        logger.info("email_sent", to=to, subject=subject, body=body)


class SMTPEmailSender:
    """SMTP sender using STARTTLS (or implicit SSL on port 465)."""

    def send(self, *, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = settings.SMTP_FROM
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        if settings.SMTP_USE_SSL:
            smtp: Any = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        else:
            smtp = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        try:
            if settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL:
                smtp.starttls()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        finally:
            try:
                smtp.quit()
            except smtplib.SMTPException:
                smtp.close()


_sender: LogEmailSender | SMTPEmailSender | None = None


def get_email_sender() -> LogEmailSender | SMTPEmailSender:
    global _sender
    if _sender is None:
        _sender = SMTPEmailSender() if settings.EMAIL_BACKEND == "smtp" else LogEmailSender()
    return _sender


def reset_email_sender() -> None:
    global _sender
    _sender = None


def send_verification_email(to: str, token: str) -> None:
    """Send the single-use verification link to the given address."""
    link = f"{settings.FRONTEND_URL.rstrip('/')}/verify-email?token={quote(token, safe='')}"
    body = (
        "Welcome to TaskFlow.\n\n"
        "Verify your email by opening this link:\n"
        f"{link}\n\n"
        f"The link expires in {settings.EMAIL_VERIFICATION_TTL_HOURS} hours.\n"
        "If you did not create an account, you can ignore this message."
    )
    get_email_sender().send(to=to, subject=VERIFICATION_SUBJECT, body=body)
