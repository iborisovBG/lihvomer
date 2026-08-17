"""Изпращане на известията по имейл.

Ако SMTP не е конфигуриран, известията пак се записват и се виждат в
приложението — само доставката се пропуска. Това позволява цялата верига да
се тества, без да се разчита на външна услуга.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings
from app.models import Notification, NotificationSeverity

logger = logging.getLogger(__name__)
_settings = get_settings()

SEVERITY_PREFIX = {
    NotificationSeverity.WARNING: "Внимание",
    NotificationSeverity.OPPORTUNITY: "Възможност",
    NotificationSeverity.INFO: "Напомняне",
}


class EmailNotConfigured(RuntimeError):
    """Липсва SMTP конфигурация; доставката се пропуска съзнателно."""


def email_configured() -> bool:
    return bool(_settings.smtp_host and _settings.smtp_from)


def render_email(notification: Notification) -> tuple[str, str, str]:
    """Връща (тема, текстова версия, HTML версия)."""
    prefix = SEVERITY_PREFIX[notification.severity]
    subject = f"[Лихвомер] {prefix}: {notification.title_bg}"

    action = notification.action_bg or ""
    plain = (
        f"{notification.title_bg}\n\n"
        f"{notification.body_bg}\n\n"
        f"{action}\n\n"
        "---\n"
        "Изчисленията стъпват изцяло на публично достъпни официални данни от "
        "ЕЦБ, Евростат и Bundesbank. Те нямат за цел да плашат или да дават "
        "финансов съвет. Преди решение за кредит се консултирайте с вашата "
        "банка или с лицензиран консултант.\n"
        "Можете да спрете тези известия от настройките в профила си."
    )

    html = f"""<!doctype html>
<html lang="bg"><body style="margin:0;padding:24px;background:#f6f7f9;
font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#161a22;">
  <div style="max-width:520px;margin:0 auto;background:#fff;border-radius:12px;
  padding:28px;border:1px solid #dde2ea;">
    <p style="margin:0 0 6px;font-size:12px;letter-spacing:.08em;
    text-transform:uppercase;color:#8a93a3;">{prefix}</p>
    <h1 style="margin:0 0 16px;font-size:20px;line-height:1.3;">
      {notification.title_bg}</h1>
    <p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#374151;">
      {notification.body_bg}</p>
    {f'<p style="margin:0 0 20px;padding:12px 14px;background:#e8ecf7;border-radius:8px;font-size:14px;line-height:1.5;">{action}</p>' if action else ''}
    <hr style="border:none;border-top:1px solid #dde2ea;margin:20px 0;">
    <p style="margin:0;font-size:12px;line-height:1.55;color:#8a93a3;">
      Изчисленията стъпват изцяло на публично достъпни официални данни от ЕЦБ,
      Евростат и Bundesbank. Те нямат за цел да плашат или да дават финансов
      съвет. Преди решение за кредит се консултирайте с вашата банка или с
      лицензиран консултант. Можете да спрете тези известия от настройките в
      профила си.</p>
  </div>
</body></html>"""

    return subject, plain, html


def send_email(recipient: str, notification: Notification) -> None:
    if not email_configured():
        raise EmailNotConfigured(
            "SMTP не е конфигуриран (SMTP_HOST и SMTP_FROM в .env)."
        )

    subject, plain, html = render_email(notification)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = _settings.smtp_from
    message["To"] = recipient
    message.set_content(plain)
    message.add_alternative(html, subtype="html")

    if _settings.smtp_use_ssl:
        server = smtplib.SMTP_SSL(_settings.smtp_host, _settings.smtp_port, timeout=20)
    else:
        server = smtplib.SMTP(_settings.smtp_host, _settings.smtp_port, timeout=20)

    with server:
        if _settings.smtp_use_tls and not _settings.smtp_use_ssl:
            server.starttls()
        if _settings.smtp_user:
            server.login(_settings.smtp_user, _settings.smtp_password)
        server.send_message(message)

    logger.info("Известие %s изпратено до %s", notification.id, recipient)
