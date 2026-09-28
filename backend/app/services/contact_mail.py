"""
contact_mail.py — De e-mail achter het contactformulier van de website.

Eén bericht, naar de postbus van Rhoderlanden Groep. Hergebruikt de platform-
mailer en dezelfde afzenderregels als het Readiness-rapport: het From-adres
blijft het geverifieerde `SMTP_FROM`, de weergavenaam is "Rhoderlanden Groep",
en **Reply-To is het adres van de bezoeker** zodat antwoorden rechtstreeks bij
hem uitkomt.

De ontvanger is instelbaar met `CONTACT_ONTVANGER`, zodat op staging naar een
testpostbus kan worden gestuurd zonder dat er iets bij Rhoderlanden binnenkomt.
Zonder die instelling geldt het echte adres.
"""
from __future__ import annotations

import os

from app.services.mailer import send_email
from app.services.readiness_mail import (
    LIJN, TINT, _esc, _omhulsel, afzendernaam,
)

STANDAARD_ONTVANGER = "info@rhoderlandengroep.nl"


def ontvanger() -> str:
    """Leeg of alleen spaties telt als niet gezet; compose geeft de variabele
    altijd door, desnoods leeg."""
    return (os.getenv("CONTACT_ONTVANGER") or "").strip() or STANDAARD_ONTVANGER


def _onderwerpregel(naam: str, organisatie: str, onderwerp: str) -> str:
    wie = f"{naam} ({organisatie})" if organisatie else naam
    return f"Website: {onderwerp or 'bericht'} van {wie}"


def opmaak(naam: str, email: str, organisatie: str, telefoon: str,
           bericht: str, onderwerp: str) -> str:
    rijen = "".join(
        f'<tr><td style="padding:4px 12px 4px 0;color:#7a8272;white-space:nowrap;">{kop}</td>'
        f'<td style="padding:4px 0;"><b>{waarde}</b></td></tr>'
        for kop, waarde in [
            ("Naam", _esc(naam)),
            ("Organisatie", _esc(organisatie) or "—"),
            ("E-mailadres", f'<a href="mailto:{_esc(email)}">{_esc(email)}</a>'),
            ("Telefoon", _esc(telefoon) or "—"),
        ]
    )
    # Regelovergangen uit een textarea moeten zichtbaar blijven; <br> na het
    # ontsnappen toevoegen, anders zou de inhoud alsnog als HTML gelden.
    tekst = _esc(bericht).replace("\n", "<br>") if bericht else "<em>Geen bericht ingevuld.</em>"
    return _omhulsel(
        f'<p style="margin:0 0 16px;"><b>Nieuw bericht via de website.</b></p>'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'style="width:100%;font-size:14px;margin-bottom:18px;">{rijen}</table>'
        + (f'<p style="margin:0 0 6px;font-weight:bold;">{_esc(onderwerp)}</p>' if onderwerp else "")
        + f'<div style="background:{TINT};border-radius:8px;padding:14px 16px;font-size:14px;'
          f'line-height:1.6;">{tekst}</div>'
        + f'<hr style="border:none;border-top:1px solid {LIJN};margin:24px 0 12px;">'
          f'<p style="margin:0;font-size:12px;color:#7a8272;">Antwoorden op deze mail gaat '
          f'rechtstreeks naar de afzender. Er is niets opgeslagen: dit bericht is de enige '
          f'vastlegging.</p>'
    )


def verstuur(naam: str, email: str, organisatie: str = "", telefoon: str = "",
             bericht: str = "", onderwerp: str = "") -> bool:
    """Stuurt het bericht door. Geeft terug of de verzending lukte."""
    return send_email(
        to=ontvanger(),
        subject=_onderwerpregel(naam, organisatie, onderwerp),
        html=opmaak(naam, email, organisatie, telefoon, bericht, onderwerp),
        from_name=afzendernaam(),
        reply_to=email,
    )
