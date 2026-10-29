import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def send_email(to: str, subject: str, body: str) -> None:
    """Надсилає лист через SMTP (для Gmail: smtp.gmail.com:587 і пароль застосунку)."""
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM or settings.SMTP_USER
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(message)


def send_password_reset_email(to: str, link: str) -> None:
    """Надсилає посилання для скидання пароля. Без налаштованого SMTP посилання пишеться в лог сервера.

    Викликається як фонова задача: помилки не повинні впливати на відповідь API
    (інакше за відповіддю можна було б визначити, чи існує такий email).
    """
    if not smtp_configured():
        logger.warning("SMTP не налаштовано. Посилання для скидання пароля для %s: %s", to, link)
        return

    body = (
        "Вітаємо!\n\n"
        "Ви (або хтось інший) запросили скидання пароля в AI Code Reviewer.\n"
        f"Щоб задати новий пароль, перейдіть за посиланням (діє {settings.PASSWORD_RESET_MINUTES} хвилин):\n\n"
        f"{link}\n\n"
        "Якщо це були не ви, просто проігноруйте цей лист: пароль не зміниться."
    )
    try:
        send_email(to, "Скидання пароля AI Code Reviewer", body)
    except Exception:
        logger.exception("Не вдалося надіслати лист зі скиданням пароля")
        if settings.DEBUG:
            # Лише в режимі розробки: щоб можна було продовжити, поки пошта не налаштована правильно
            logger.warning("Посилання для скидання пароля для %s: %s", to, link)
