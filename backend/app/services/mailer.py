"""
mailer.py — Generieke, env-gestuurde e-mailverzending voor het Rhadix-platform.

Bewust app-onafhankelijk en SMTP-gebaseerd zodat dezelfde mailer in alle vier de
apps kan worden hergebruikt en met elke EU-conforme SMTP-provider werkt
(standaard: Scaleway Transactional Email — EU-soeverein, ISO 27001, AVG/DPA).

Standaard UIT: zonder MAIL_ENABLED=true én SMTP_HOST gebeurt er niets (no-op),
zodat het inschakelen pas plaatsvindt als de provider + DNS (SPF/DKIM) staan.

Dataminimalisatie: notificaties bevatten uitsluitend de taaktitel, wie de taak
toewees en een inloglink — nooit cliënt-/zorgdata of validatie-inhoud.
"""
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

log = logging.getLogger("rhadix.mail")


def mail_enabled() -> bool:
    return os.getenv("MAIL_ENABLED", "false").lower() == "true" and bool(os.getenv("SMTP_HOST"))


def _public_url() -> str:
    return (os.getenv("PUBLIC_BASE_URL", "") or "").rstrip("/")


def send_email(to: str, subject: str, html: str, text: str | None = None) -> bool:
    """Verstuur één e-mail via SMTP. No-op (False) als mail uit/niet geconfigureerd is."""
    if not mail_enabled():
        log.info("Mail uit of niet geconfigureerd — overslaan (%s)", subject)
        return False
    if not to:
        return False

    host   = os.getenv("SMTP_HOST")
    port   = int(os.getenv("SMTP_PORT", "587"))
    user   = os.getenv("SMTP_USER")
    pw     = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM", "noreply@rhadix.nl")
    name   = os.getenv("SMTP_FROM_NAME", "Rhadix")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"]    = formataddr((name, sender))
    msg["To"]      = to
    msg.set_content(text or _html_to_text(html))
    msg.add_alternative(html, subtype="html")

    try:
        ctx = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=15) as s:
                if user:
                    s.login(user, pw)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as s:
                s.ehlo()
                s.starttls(context=ctx)
                if user:
                    s.login(user, pw)
                s.send_message(msg)
        log.info("Mail verzonden naar %s (%s)", to, subject)
        return True
    except Exception:
        import traceback
        log.error("Mail verzenden mislukt:\n%s", traceback.format_exc())
        return False


def _html_to_text(html: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", html).strip()


def _shell(title: str, body_html: str, cta_url: str | None) -> str:
    btn = ""
    if cta_url:
        btn = (f'<p style="margin:24px 0"><a href="{cta_url}" '
               f'style="background:#1d4ed8;color:#fff;text-decoration:none;padding:11px 20px;'
               f'border-radius:8px;font-weight:600;display:inline-block">Open in Rhadix</a></p>')
    return (
        f'<div style="font-family:Arial,Helvetica,sans-serif;max-width:520px;margin:0 auto;'
        f'color:#1f2937;line-height:1.5">'
        f'<h2 style="font-size:18px;color:#0f172a">{title}</h2>'
        f'{body_html}{btn}'
        f'<hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">'
        f'<p style="font-size:12px;color:#94a3b8">Je ontvangt deze melding omdat er in Rhadix '
        f'een taak aan je is toegewezen. De inhoud staat veilig achter je login.</p></div>'
    )


def notify_task_assigned(to_email: str, to_name: str | None, assigner: str | None, title: str) -> bool:
    who = assigner or "Een collega"
    body = (f'<p>{who} heeft je een taak toegewezen:</p>'
            f'<p style="background:#f1f5f9;border-radius:8px;padding:12px 14px;font-weight:600">{title}</p>')
    html = _shell("Nieuwe taak voor je", body, _public_url() or None)
    return send_email(to_email, f"Nieuwe taak: {title}", html)


def notify_tasks_assigned(to_email: str, to_name: str | None, assigner: str | None, count: int) -> bool:
    who = assigner or "Een collega"
    body = (f'<p>{who} heeft <strong>{count}</strong> taken aan je toegewezen '
            f'(o.a. uit een validatie-analyse).</p>')
    html = _shell("Nieuwe taken voor je", body, _public_url() or None)
    return send_email(to_email, f"{count} nieuwe taken toegewezen", html)
