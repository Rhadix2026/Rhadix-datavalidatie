"""
instellingen.py — Interne e-mailadressen van de website, op één plek.

Tot nu toe stonden de adressen als standaardwaarde in twee modules
(`contact_mail.py` en `readiness_mail.py`). Een opgeheven postvak bleef daardoor
onopgemerkt in gebruik: de code viel stil terug op een adres dat niet meer
bestond. Daarom is er hier **geen ingebouwde standaard** meer. Ontbreekt een
adres, dan wordt dat gemeld en blijft de melding in de wachtrij staan tot het
adres is ingesteld.

Centrale instellingen
---------------------
    WEBSITE_INTERN_ADRES   ontvanger van alle interne meldingen (contact,
                           Bespreek mijn uitslag, Readiness-signaal) en van het
                           dagoverzicht
    WEBSITE_REPLY_TO       antwoordadres in het rapport aan de bezoeker;
                           zonder waarde geldt het interne adres

Bestaande, specifiekere instellingen blijven werken en gaan vóór de centrale:

    CONTACT_ONTVANGER      alleen het contactformulier
    READINESS_INTERN_ADRES alleen de Readiness-signaalmail
    READINESS_REPLY_TO     alleen het antwoordadres van het rapport

Op staging wijzen die drie naar een testpostbus; dat blijft zo werken.
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger("rhadix.website")

CONTACT = "contact"
READINESS = "readiness"


def _env(sleutel: str) -> str:
    # Compose geeft deze variabelen altijd door, desnoods leeg; leeg telt als
    # niet gezet.
    return (os.getenv(sleutel) or "").strip()


def intern_adres(soort: str | None = None) -> str | None:
    """Ontvanger van de interne melding voor `soort`, of None als er geen is."""
    specifiek = {CONTACT: "CONTACT_ONTVANGER", READINESS: "READINESS_INTERN_ADRES"}.get(soort or "")
    return (_env(specifiek) if specifiek else "") or _env("WEBSITE_INTERN_ADRES") or None


def antwoordadres() -> str | None:
    """Reply-To van het rapport aan de bezoeker."""
    return (_env("READINESS_REPLY_TO") or _env("WEBSITE_REPLY_TO")
            or intern_adres(READINESS))


def afzendernaam() -> str:
    return _env("READINESS_AFZENDERNAAM") or "Rhoderlanden Groep"


def mail_aan() -> bool:
    from app.services.mailer import mail_enabled
    return mail_enabled()


def maskeer(email: str | None) -> str:
    """j***@voorbeeld.nl — genoeg om een regel in de log te herkennen, niet
    genoeg om er iemand mee te benaderen."""
    tekst = (email or "").strip()
    if "@" not in tekst:
        return "—"
    lokaal, domein = tekst.rsplit("@", 1)
    return f"{lokaal[:1]}***@{domein}"


# ── Controle ──────────────────────────────────────────────────────────────────

def geldig(adres: str | None) -> bool:
    """Is dit een bruikbaar adres (syntax, geen gereserveerd domein)? Zonder
    DNS: deze controle draait bij elke verzendpoging."""
    if not adres:
        return False
    from email_validator import EmailNotValidError, validate_email
    try:
        validate_email(adres, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def _controleer_adres(sleutel: str, waarde: str, dns: bool) -> str | None:
    from email_validator import EmailNotValidError, validate_email
    try:
        validate_email(waarde, check_deliverability=dns)
    except EmailNotValidError as fout:
        return f"{sleutel} is ongeldig: {fout}"
    except Exception as fout:              # DNS-storing: melden, niet afkeuren
        log.warning("Website: domein van %s niet te controleren (%s)", sleutel, fout)
    return None


def controleer(dns: bool = False) -> list[str]:
    """Wat er aan de mailconfiguratie van de website ontbreekt of niet klopt.

    Een lege lijst betekent: alle interne meldingen kunnen worden afgeleverd.
    Met `dns=True` wordt ook gecontroleerd of het domein mail kan ontvangen
    (MX). Dat vangt een tikfout in het domein, niet een opgeheven postvak op
    een bestaand domein; dat laatste komt pas via een bounce aan het licht.
    """
    problemen: list[str] = []
    if not mail_aan():
        problemen.append("MAIL_ENABLED staat uit of SMTP_HOST ontbreekt")

    for soort, naam in ((CONTACT, "contactformulier"), (READINESS, "Readiness-signaal")):
        if not intern_adres(soort):
            problemen.append(f"geen intern adres voor {naam} "
                             "(WEBSITE_INTERN_ADRES ontbreekt)")

    gecontroleerd: set[str] = set()
    for sleutel in ("WEBSITE_INTERN_ADRES", "WEBSITE_REPLY_TO", "CONTACT_ONTVANGER",
                    "READINESS_INTERN_ADRES", "READINESS_REPLY_TO"):
        waarde = _env(sleutel)
        if waarde and waarde.lower() not in gecontroleerd:
            gecontroleerd.add(waarde.lower())
            probleem = _controleer_adres(sleutel, waarde, dns)
            if probleem:
                problemen.append(probleem)
    return problemen


def meld_bij_start(dns: bool = True) -> list[str]:
    """Logt elk probleem als ERROR, zodat het in `docker logs` opvalt."""
    problemen = controleer(dns=dns)
    for probleem in problemen:
        log.error("Website-mailconfiguratie: %s — meldingen blijven in de wachtrij "
                  "tot dit is opgelost", probleem)
    if not problemen:
        log.info("Website-mailconfiguratie compleet")
    return problemen
