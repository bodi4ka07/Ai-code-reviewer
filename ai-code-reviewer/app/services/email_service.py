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


def _deliver(to: str, subject: str, body: str, link: str, what: str) -> None:
    """Надсилає лист із посиланням. Без налаштованого SMTP посилання пишеться в лог сервера.

    Викликається як фонова задача: помилки не повинні впливати на відповідь API
    (інакше за відповіддю можна було б визначити, чи існує такий email).
    """
    if not smtp_configured():
        logger.warning("SMTP не налаштовано. Посилання для %s для %s: %s", what, to, link)
        return

    try:
        send_email(to, subject, body)
    except Exception:
        logger.exception("Не вдалося надіслати лист (%s)", what)
        if settings.DEBUG:
            # Лише в режимі розробки: щоб можна було продовжити, поки пошта не налаштована правильно
            logger.warning("Посилання для %s для %s: %s", what, to, link)


def send_password_reset_email(to: str, link: str) -> None:
    body = (
        "Вітаємо!\n\n"
        "Ви (або хтось інший) запросили скидання пароля в AI Code Reviewer.\n"
        f"Щоб задати новий пароль, перейдіть за посиланням (діє {settings.PASSWORD_RESET_MINUTES} хвилин):\n\n"
        f"{link}\n\n"
        "Якщо це були не ви, просто проігноруйте цей лист: пароль не зміниться."
    )
    _deliver(to, "Скидання пароля AI Code Reviewer", body, link, "скидання пароля")


def send_verification_email(to: str, link: str) -> None:
    body = (
        "Вітаємо в AI Code Reviewer!\n\n"
        f"Щоб підтвердити email і завершити реєстрацію, перейдіть за посиланням (діє {settings.VERIFY_EMAIL_HOURS} годин):\n\n"
        f"{link}\n\n"
        "Якщо ви не реєструвались, просто проігноруйте цей лист."
    )
    _deliver(to, "Підтвердіть email в AI Code Reviewer", body, link, "підтвердження email")
