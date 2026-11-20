"""Sends emails over SMTP. With no SMTP_HOST set (local dev), emails are printed to the terminal."""
import logging
import smtplib
from email.message import EmailMessage

from .config import settings

log = logging.getLogger("jps.email")


def send_email(to: str, subject: str, body: str, reply_to: str | None = None) -> bool:
    if not to:
        return False
    msg = EmailMessage()
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)

    if not settings.SMTP_HOST:
        print("\n" + "=" * 70 + f"\n[EMAIL – not sent, SMTP not configured]\nTo: {to}\nSubject: {subject}\n\n{body}\n" + "=" * 70, flush=True)
        return False
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as s:
            s.starttls()
            if settings.SMTP_USER:
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.send_message(msg)
        return True
    except Exception:  # never break a page because email failed
        log.exception("Email to %s failed", to)
        return False
