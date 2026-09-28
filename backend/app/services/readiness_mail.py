"""
readiness_mail.py — De twee e-mails rond een Readiness-rapport.

1. **Naar de bezoeker**: een korte HTML-mail met de kernuitslag en het volledige
   rapport als PDF-bijlage. Kort met opzet — de mail moet in één oogopslag
   duidelijk maken wat de uitslag is; de verdieping zit in de bijlage.
2. **Naar Rhoderlanden**: een korte signaalmail met naam, organisatie,
   e-mailadres, type check, totaalscore en de twee belangrijkste
   aandachtspunten. **Zonder bijlage** — het volledige rapport gaat intern niet
   standaard mee.

Afzender
--------
Het From-*adres* blijft het geverifieerde `SMTP_FROM` (noreply@rhadix.nl).
`rhadix.nl` publiceert DMARC met strikte alignment (`p=quarantine; adkim=s;
aspf=s`), dus het From-domein moet exact overeenkomen met wat de provider
ondertekent. Versturen namens `rhoderlandengroep.nl` zou bovendien hard falen op
hun SPF-record, dat op `-all` staat zonder deze provider.

Wat wél kan: de **weergavenaam** ("Rhoderlanden Groep") en **Reply-To** vallen
buiten DMARC-alignment. Een antwoord van de bezoeker komt daardoor gewoon in de
postbus van Rhoderlanden terecht.

Een eigen verzenddomein is later één configuratiestap — domein verifiëren, SPF
en DKIM publiceren — en vraagt geen wijziging in deze code.

Geen opslag
-----------
Naam, organisatie en e-mailadres worden uitsluitend gebruikt om deze twee mails
te versturen. Er wordt niets in een database of CRM vastgelegd.
"""
from __future__ import annotations

import os

from app.services.mailer import send_email
from app.services.readiness_rapport import Rapport

STANDAARD_ADRES = "info@rhoderlandengroep.nl"

# Huisstijl van de Rhoderlanden-site.
DONKER = "#0f1712"
PANEEL = "#17221b"
LIME = "#d0e6a5"
TEKST = "#3f463a"
LIJN = "#dfe4d4"
TINT = "#eef4e3"


def _uit_omgeving(sleutel: str, standaard: str) -> str:
    """Leest een instelling, maar behandelt een lege waarde als niet gezet.

    De compose-bestanden geven deze variabelen altijd door, desnoods leeg
    (`${READINESS_REPLY_TO:-}`). Zonder deze controle zou zo'n lege waarde de
    standaard overrulen en zouden er mails zonder ontvanger ontstaan.
    """
    return (os.getenv(sleutel) or "").strip() or standaard


def intern_adres() -> str:
    return _uit_omgeving("READINESS_INTERN_ADRES", STANDAARD_ADRES)


def antwoordadres() -> str:
    return _uit_omgeving("READINESS_REPLY_TO", STANDAARD_ADRES)


def afzendernaam() -> str:
    return _uit_omgeving("READINESS_AFZENDERNAAM", "Rhoderlanden Groep")


def _esc(tekst: str) -> str:
    return (str(tekst).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def bestandsnaam(rapport: Rapport) -> str:
    """Bestandsnaam van de bijlage, zonder spaties of rare tekens."""
    soort = "data" if rapport.check == "data" else "kikv"
    schoon = "".join(c if c.isalnum() else "-" for c in rapport.organisatie.lower())
    schoon = "-".join(deel for deel in schoon.split("-") if deel)[:40]
    return f"readiness-rapport-{soort}-{schoon or 'organisatie'}.pdf"


# ── Mail aan de bezoeker ──────────────────────────────────────────────────────

def _omhulsel(inhoud: str) -> str:
    """Eenvoudige, e-mailveilige opmaak in de huisstijl: tabellen en inline
    stijlen, geen externe fonts of afbeeldingen."""
    return (
        f'<div style="margin:0;padding:24px 12px;background:{TINT};">'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'style="max-width:560px;margin:0 auto;width:100%;font-family:Arial,Helvetica,sans-serif;'
        f'color:{TEKST};line-height:1.6;background:#ffffff;border:1px solid {LIJN};'
        f'border-radius:12px;overflow:hidden;">'
        f'<tr><td style="background:{DONKER};padding:18px 24px;">'
        f'<span style="color:#ffffff;font-size:16px;font-weight:bold;letter-spacing:0.04em;">'
        f'Rhoderlanden Groep</span></td></tr>'
        f'<tr><td style="padding:24px;">{inhoud}</td></tr>'
        f'</table></div>'
    )


def rapport_html(rapport: Rapport) -> str:
    """De HTML-mail voor de bezoeker."""
    punten = rapport.prioritering[0][1][:2] if rapport.prioritering else []
    lijst = "".join(
        f'<li style="margin-bottom:8px;"><b>{_esc(naam)}</b> ({score} van 100) — {_esc(tekst)}</li>'
        for naam, score, tekst, _antwoord in punten
    )
    rijen = "".join(
        f'<tr><td style="padding:6px 0;border-bottom:1px solid {LIJN};">{_esc(naam)}</td>'
        f'<td style="padding:6px 0;border-bottom:1px solid {LIJN};text-align:right;">'
        f'<b>{score}</b></td></tr>'
        for naam, score in rapport.dimensies
    )
    inhoud = (
        f'<p style="margin:0 0 16px;">Beste {_esc(rapport.naam)},</p>'
        f'<p style="margin:0 0 20px;">Hierbij uw <b>{_esc(rapport.titel.lower())}</b> '
        f'voor {_esc(rapport.organisatie)}. Het volledige rapport vindt u als PDF in de bijlage.</p>'

        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'style="width:100%;background:{PANEEL};border-radius:10px;margin-bottom:20px;">'
        f'<tr><td style="padding:18px 20px;text-align:center;">'
        f'<div style="color:{LIME};font-size:40px;font-weight:bold;line-height:1;">{rapport.totaal}</div>'
        f'<div style="color:#cfd8c9;font-size:12px;margin-top:2px;">van 100</div>'
        f'<div style="color:#ffffff;font-size:15px;font-weight:bold;margin-top:8px;">'
        f'{_esc(rapport.categorie)}</div></td></tr></table>'

        f'<p style="margin:0 0 18px;">{_esc(rapport.duiding)}</p>'

        f'<p style="margin:0 0 6px;font-weight:bold;">Uw vijf dimensies</p>'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'style="width:100%;font-size:14px;margin-bottom:20px;">{rijen}</table>'

        + (f'<p style="margin:0 0 6px;font-weight:bold;">Waar begint u?</p>'
           f'<ul style="margin:0 0 20px;padding-left:20px;font-size:14px;">{lijst}</ul>' if lijst else "")

        + f'<p style="margin:0 0 20px;font-size:14px;">In de bijlage staat de volledige analyse: '
          f'alle vijf de dimensies, uw sterke punten, de aandachtspunten per vraag, een '
          f'prioritering en een bijlage met uw eigen antwoorden.</p>'

        f'<div style="background:{TINT};border-radius:8px;padding:14px 16px;font-size:13px;">'
        f'{_esc(rapport.voorbehoud)}</div>'

        f'<p style="margin:20px 0 0;font-size:14px;">{_esc(rapport.vervolg)}</p>'
        f'<p style="margin:16px 0 0;font-size:14px;">Wilt u weten wat deze uitslag concreet '
        f'betekent voor uw organisatie? Antwoord gerust op deze mail, dan plannen we een '
        f'gesprek van 30 minuten.</p>'
        f'<p style="margin:20px 0 0;font-size:14px;">Met vriendelijke groet,<br>'
        f'<b>Rhoderlanden Groep</b></p>'

        f'<hr style="border:none;border-top:1px solid {LIJN};margin:24px 0 12px;">'
        f'<p style="margin:0;font-size:11px;color:#7a8272;">U ontvangt deze e-mail omdat u op '
        f'de website van Rhoderlanden Groep om dit rapport heeft gevraagd. Uw naam, organisatie '
        f'en e-mailadres zijn alleen gebruikt om deze mail te versturen en worden niet bewaard.</p>'
    )
    return _omhulsel(inhoud)


def verstuur_rapport(rapport: Rapport, email: str, pdf: bytes) -> bool:
    """Stuurt de bezoeker zijn rapport. Geeft terug of de verzending lukte."""
    onderwerp = f"Uw {rapport.soort} Readiness-rapport — {rapport.totaal} van 100"
    return send_email(
        to=email,
        subject=onderwerp,
        html=rapport_html(rapport),
        attachments=[(bestandsnaam(rapport), pdf, "application", "pdf")],
        from_name=afzendernaam(),
        reply_to=antwoordadres(),
    )


# ── Signaalmail aan Rhoderlanden ──────────────────────────────────────────────

def signaal_html(rapport: Rapport, email: str) -> str:
    punten = rapport.prioritering[0][1][:2] if rapport.prioritering else []
    lijst = "".join(
        f'<li style="margin-bottom:6px;"><b>{_esc(naam)}</b> ({score}) — {_esc(tekst)}</li>'
        for naam, score, tekst, _antwoord in punten
    )
    rijen = "".join(
        f'<tr><td style="padding:4px 12px 4px 0;color:#7a8272;">{k}</td>'
        f'<td style="padding:4px 0;"><b>{v}</b></td></tr>'
        for k, v in [
            ("Naam", _esc(rapport.naam)),
            ("Organisatie", _esc(rapport.organisatie)),
            ("E-mailadres", f'<a href="mailto:{_esc(email)}">{_esc(email)}</a>'),
            ("Check", _esc(rapport.check_titel)),
            ("Totaalscore", f"{rapport.totaal} van 100 · {_esc(rapport.categorie)}"),
        ]
    )
    return _omhulsel(
        f'<p style="margin:0 0 16px;"><b>Nieuwe aanvraag van een Readiness-rapport.</b></p>'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'style="width:100%;font-size:14px;margin-bottom:18px;">{rijen}</table>'
        + (f'<p style="margin:0 0 6px;font-weight:bold;">Belangrijkste aandachtspunten</p>'
           f'<ul style="margin:0 0 18px;padding-left:20px;font-size:14px;">{lijst}</ul>' if lijst else "")
        + f'<p style="margin:0;font-size:13px;color:#7a8272;">Het volledige rapport is naar de '
          f'aanvrager gestuurd en gaat hier bewust niet mee. Er is niets opgeslagen: deze mail '
          f'is de enige vastlegging.</p>'
    )


def verstuur_signaal(rapport: Rapport, email: str) -> bool:
    """Korte interne melding. Geen bijlage."""
    onderwerp = (f"Readiness-aanvraag: {rapport.organisatie} — "
                 f"{rapport.soort} {rapport.totaal}/100")
    return send_email(
        to=intern_adres(),
        subject=onderwerp,
        html=signaal_html(rapport, email),
        from_name=afzendernaam(),
        reply_to=email,          # antwoorden gaat rechtstreeks naar de aanvrager
    )
