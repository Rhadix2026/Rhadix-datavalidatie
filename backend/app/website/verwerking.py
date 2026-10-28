"""
verwerking.py — De stappen achter een website-aanvraag, en het opnieuw proberen.

Volgorde in het verzoek zelf:

1. de router valideert en legt de aanvraag vast (`opslag.leg_vast`);
2. `verwerk()` probeert meteen alle stappen, zodat de bezoeker even snel zijn
   rapport heeft als voorheen;
3. wat mislukt of geblokkeerd is, pakt de herhaaltaak later op.

De stappen zijn onafhankelijk van elkaar. Mislukt de mail aan de bezoeker, dan
gaan de melding aan ons en de CRM-registratie gewoon door — anders weten we
niet eens dat er iemand een rapport heeft aangevraagd.

Herhaaltaak
-----------
Een draad in het backendproces (`start()`), elke `WEBSITE_VERWERK_INTERVAL`
seconden. Wachttijd tussen pogingen loopt op van 1 minuut tot een dag; na
`WEBSITE_MAX_POGINGEN` pogingen wordt een stap opgegeven en gemeld. Een
geblokkeerde stap (instelling ontbreekt) telt niet als poging: die wacht tot de
instelling er is en gaat dan alsnog de deur uit.

Eén keer per `WEBSITE_OVERZICHT_UREN` gaat er een overzicht naar het interne
adres, alleen als er iets openstaat. Daarin staan aantallen en aanvraag-id's,
geen persoonsgegevens.

Zonder opslag
-------------
Is de opslag niet beschikbaar of staat `WEBSITE_OPSLAG=uit`, dan verwerkt
`verwerk_direct()` de stappen in het geheugen, precies zoals vóór deze
wijziging. Dat is ook de terugvaloptie zonder nieuwe image.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import timedelta

from app.services import contact_mail
from app.services import readiness_crm as crm
from app.services import readiness_mail
from app.services.mailer import send_email
from app.services.readiness_pdf import bouw_pdf
from app.services.readiness_rapport import bouw
from app.services.readiness_scoring import bereken
from app.website import instellingen
from app.website import opslag

log = logging.getLogger("rhadix.website")

RAPPORT = "rapport"
CONTACT = "contact"

STAPPEN = {
    RAPPORT: [opslag.MAIL_BEZOEKER, opslag.MAIL_INTERN, opslag.CRM],
    CONTACT: [opslag.MAIL_INTERN, opslag.CRM],
}

# Minuten tot de volgende poging, per mislukte poging.
WACHTTIJDEN = (1, 5, 15, 60, 180, 360, 720, 1440)
GEBLOKKEERD_OPNIEUW = timedelta(minutes=5)


def opslag_aan() -> bool:
    return (os.getenv("WEBSITE_OPSLAG") or "aan").strip().lower() not in ("uit", "off", "0", "false")


def max_pogingen() -> int:
    return int(os.getenv("WEBSITE_MAX_POGINGEN", str(len(WACHTTIJDEN))))


@dataclass
class Uitkomst:
    status: str
    fout: str | None = None
    extern_id: str | None = None


# ── De stappen ────────────────────────────────────────────────────────────────

def _rapport(g: dict):
    uitslag = bereken(g["check"], g["antwoorden"])
    return uitslag, bouw(uitslag, naam=g["naam"], organisatie=g["organisatie"])


def _mail_bezoeker(g: dict, _id: str | None, _poging: int) -> Uitkomst:
    if not instellingen.mail_aan():
        return Uitkomst(opslag.GEBLOKKEERD, "mail staat uit")
    _, opzet = _rapport(g)
    pdf = bouw_pdf(opzet)
    if readiness_mail.verstuur_rapport(opzet, g["email"], pdf):
        return Uitkomst(opslag.GELUKT)
    return Uitkomst(opslag.MISLUKT, "rapport niet verzonden (SMTP)")


def _mail_intern(soort: str):
    def stap(g: dict, aanvraag_id: str | None, _poging: int) -> Uitkomst:
        if not instellingen.mail_aan():
            return Uitkomst(opslag.GEBLOKKEERD, "mail staat uit")
        sleutel = instellingen.READINESS if soort == RAPPORT else instellingen.CONTACT
        adres = instellingen.intern_adres(sleutel)
        if not adres:
            return Uitkomst(opslag.GEBLOKKEERD, "geen intern adres ingesteld")
        if not instellingen.geldig(adres):
            return Uitkomst(opslag.GEBLOKKEERD, "intern adres is ongeldig")
        if soort == RAPPORT:
            _, opzet = _rapport(g)
            gelukt = readiness_mail.verstuur_signaal(opzet, g["email"], aanvraag_id=aanvraag_id)
        else:
            gelukt = contact_mail.verstuur(
                naam=g["naam"], email=g["email"], organisatie=g.get("organisatie", ""),
                telefoon=g.get("telefoon", ""), bericht=g.get("bericht", ""),
                onderwerp=g.get("onderwerp", ""), aanvraag_id=aanvraag_id)
        return Uitkomst(opslag.GELUKT) if gelukt else Uitkomst(opslag.MISLUKT, "melding niet verzonden (SMTP)")
    return stap


def _crm(soort: str):
    def stap(g: dict, aanvraag_id: str | None, poging: int) -> Uitkomst:
        if not crm.ingeschakeld():
            return Uitkomst(opslag.OVERGESLAGEN, "geen CRM-koppeling ingesteld")
        # Een eerdere poging kan de activiteit wél hebben aangemaakt en pas
        # daarna zijn afgebroken (timeout). Eerst kijken, dan pas opnieuw.
        if poging > 0 and aanvraag_id:
            bestaand = crm.zoek_activiteit(aanvraag_id)
            if bestaand:
                return Uitkomst(opslag.GELUKT, extern_id=bestaand.get("id"))
        if soort == RAPPORT:
            uitslag, _ = _rapport(g)
            activiteit = crm.registreer(
                uitslag, naam=g["naam"], organisatie=g["organisatie"], email=g["email"],
                campagne=g.get("campagne"), aanvraag_id=aanvraag_id)
        else:
            activiteit = crm.registreer_bericht(
                naam=g["naam"], email=g["email"], organisatie=g.get("organisatie", ""),
                telefoon=g.get("telefoon", ""), onderwerp=g.get("onderwerp", ""),
                bericht=g.get("bericht", ""), van=g.get("van", ""), cta_code=g.get("cta", ""),
                campagne=g.get("campagne"), aanvraag_id=aanvraag_id)
        if activiteit:
            return Uitkomst(opslag.GELUKT, extern_id=activiteit.get("id"))
        return Uitkomst(opslag.MISLUKT, "CRM-registratie mislukt")
    return stap


UITVOERDERS = {
    (RAPPORT, opslag.MAIL_BEZOEKER): _mail_bezoeker,
    (RAPPORT, opslag.MAIL_INTERN): _mail_intern(RAPPORT),
    (RAPPORT, opslag.CRM): _crm(RAPPORT),
    (CONTACT, opslag.MAIL_INTERN): _mail_intern(CONTACT),
    (CONTACT, opslag.CRM): _crm(CONTACT),
}


def _voer(soort: str, stap: str, gegevens: dict, aanvraag_id: str | None, poging: int) -> Uitkomst:
    try:
        return UITVOERDERS[(soort, stap)](gegevens, aanvraag_id, poging)
    except Exception as fout:
        log.exception("Website: stap %s van aanvraag %s wierp een fout", stap, aanvraag_id)
        return Uitkomst(opslag.MISLUKT, f"{type(fout).__name__}")


# ── Met opslag ────────────────────────────────────────────────────────────────

def _na_poging(aanvraag_id: str, stap: str, pogingen: int, uitkomst: Uitkomst) -> None:
    if uitkomst.status == opslag.GEBLOKKEERD:
        opslag.werk_bij(aanvraag_id, stap, opslag.GEBLOKKEERD, uitkomst.fout,
                        volgende=opslag.nu() + GEBLOKKEERD_OPNIEUW, telt_als_poging=False)
        return
    if uitkomst.status != opslag.MISLUKT:
        opslag.werk_bij(aanvraag_id, stap, uitkomst.status, uitkomst.fout, uitkomst.extern_id)
        return
    gedaan = pogingen + 1
    if gedaan >= max_pogingen():
        log.error("Website: stap %s van aanvraag %s opgegeven na %d pogingen (%s) — "
                  "handmatig afhandelen", stap, aanvraag_id, gedaan, uitkomst.fout)
        opslag.werk_bij(aanvraag_id, stap, opslag.OPGEGEVEN, uitkomst.fout)
        return
    wacht = WACHTTIJDEN[min(gedaan - 1, len(WACHTTIJDEN) - 1)]
    log.warning("Website: stap %s van aanvraag %s mislukt (poging %d, %s); opnieuw over %d min",
                stap, aanvraag_id, gedaan, uitkomst.fout, wacht)
    opslag.werk_bij(aanvraag_id, stap, opslag.MISLUKT, uitkomst.fout,
                    volgende=opslag.nu() + timedelta(minutes=wacht))


def voer_stap_uit(aanvraag_id: str, stap: str, geclaimd: bool = False) -> str | None:
    """Voert één opgeslagen stap uit en legt de uitkomst vast. Geeft de nieuwe
    status terug, of None als de stap niet (meer) te doen was."""
    aanvraag, stappen = opslag.haal(aanvraag_id)
    rij = stappen.get(stap)
    if aanvraag is None or rij is None or rij.status not in opslag.OPEN:
        return None
    if not geclaimd and not opslag.claim(aanvraag_id, stap, rij.volgende_poging_op):
        return None
    uitkomst = _voer(aanvraag.soort, stap, aanvraag.gegevens, aanvraag_id, rij.pogingen)
    _na_poging(aanvraag_id, stap, rij.pogingen, uitkomst)
    return uitkomst.status


def verwerk(aanvraag_id: str) -> dict[str, str]:
    """Eerste poging voor alle stappen van een zojuist vastgelegde aanvraag.
    Geeft per stap de status terug."""
    aanvraag, stappen = opslag.haal(aanvraag_id)
    if aanvraag is None:
        return {}
    uitslag: dict[str, str] = {}
    for stap in STAPPEN[aanvraag.soort]:
        rij = stappen.get(stap)
        if rij is None:
            continue
        nieuw = voer_stap_uit(aanvraag_id, stap) if rij.status in opslag.OPEN else None
        uitslag[stap] = nieuw or rij.status
    return uitslag


def verwerk_achterstand(limiet: int = 50) -> int:
    """Eén ronde van de herhaaltaak. Geeft het aantal behandelde stappen."""
    behandeld = 0
    for aanvraag_id, stap, gepland in opslag.te_verwerken(limiet):
        if opslag.claim(aanvraag_id, stap, gepland):
            voer_stap_uit(aanvraag_id, stap, geclaimd=True)
            behandeld += 1
    return behandeld


# ── Zonder opslag (terugval) ──────────────────────────────────────────────────

def verwerk_direct(soort: str, gegevens: dict) -> dict[str, str]:
    """Alle stappen in het geheugen, zonder vastlegging of herhaling."""
    return {stap: _voer(soort, stap, gegevens, None, 0).status for stap in STAPPEN[soort]}


# ── De ingang voor de routers ─────────────────────────────────────────────────

@dataclass
class Ontvangst:
    opgeslagen: bool              # duurzaam vastgelegd in de website-opslag
    aanvraag_id: str | None
    nieuw: bool                   # False: deze inzending was er al
    stappen: dict[str, str]       # stap -> status na de eerste poging

    def status(self, stap: str) -> str | None:
        return self.stappen.get(stap)

    def gelukt(self, stap: str) -> bool:
        return self.stappen.get(stap) == opslag.GELUKT

    def openstaand(self, stap: str) -> bool:
        return self.stappen.get(stap) in opslag.OPEN


def ontvang(soort: str, gegevens: dict, check_soort: str | None = None,
            aanvraag_id: str | None = None) -> Ontvangst:
    """Legt de aanvraag vast en doet de eerste verwerkingspoging.

    Lukt het vastleggen niet (database weg) of staat de opslag uit, dan wordt
    de aanvraag verwerkt zoals vóór deze wijziging: alles in één keer, zonder
    herhaling. `opgeslagen` is dan False.
    """
    if opslag_aan():
        try:
            sleutel, nieuw = opslag.leg_vast(soort, gegevens, STAPPEN[soort],
                                             check_soort=check_soort, aanvraag_id=aanvraag_id)
        except Exception:
            log.exception("Website: aanvraag kon niet worden vastgelegd — verwerking zonder opslag")
        else:
            if not nieuw:
                _, stappen = opslag.haal(sleutel)
                return Ontvangst(True, sleutel, False, {k: v.status for k, v in stappen.items()})
            try:
                return Ontvangst(True, sleutel, True, verwerk(sleutel))
            except Exception:
                # Vastgelegd is vastgelegd: de herhaaltaak pakt het op.
                log.exception("Website: eerste verwerking van aanvraag %s mislukt", sleutel)
                return Ontvangst(True, sleutel, True,
                                 {stap: opslag.WACHTEND for stap in STAPPEN[soort]})
    return Ontvangst(False, None, True, verwerk_direct(soort, gegevens))


# ── Overzicht en opruimen ─────────────────────────────────────────────────────

def overzicht_tekst(gevallen: list[dict]) -> str:
    regels = [f"<p>Er staan {len(gevallen)} verwerkingsstap(pen) van website-aanvragen open "
              "die aandacht vragen.</p>",
              '<table cellpadding="4" style="font-size:13px;border-collapse:collapse;">',
              "<tr><th align=left>Aanvraag</th><th align=left>Soort</th><th align=left>Stap</th>"
              "<th align=left>Status</th><th align=left>Pogingen</th><th align=left>Fout</th></tr>"]
    for g in gevallen:
        regels.append(f"<tr><td>{g['aanvraag_id']}</td><td>{g['soort']}</td><td>{g['stap']}</td>"
                      f"<td>{g['status']}</td><td>{g['pogingen']}</td>"
                      f"<td>{readiness_mail._esc(g['fout'] or '—')}</td></tr>")
    regels.append("</table><p style='font-size:12px;color:#7a8272;'>Geen persoonsgegevens in "
                  "deze mail. De aanvraag-id staat ook in de CRM-activiteit en in de melding.</p>")
    return "".join(regels)


def stuur_overzicht() -> bool:
    gevallen = opslag.probleemgevallen()
    if not gevallen:
        return False
    log.error("Website: %d verwerkingsstap(pen) vragen aandacht", len(gevallen))
    adres = instellingen.intern_adres(instellingen.CONTACT)
    if not adres or not instellingen.mail_aan():
        log.error("Website: overzicht niet verstuurd — geen intern adres of mail uit")
        return False
    return send_email(adres, f"Website-aanvragen: {len(gevallen)} stap(pen) vragen aandacht",
                      overzicht_tekst(gevallen), from_name=instellingen.afzendernaam())


# ── De herhaaltaak ────────────────────────────────────────────────────────────

_stop = threading.Event()
_draad: threading.Thread | None = None


def _lus() -> None:
    interval = int(os.getenv("WEBSITE_VERWERK_INTERVAL", "60"))
    overzicht_elke = float(os.getenv("WEBSITE_OVERZICHT_UREN", "24")) * 3600
    volgend_overzicht = time.monotonic() + 600       # eerste overzicht 10 min na start
    while not _stop.is_set():
        try:
            verwerk_achterstand()
            if time.monotonic() >= volgend_overzicht:
                volgend_overzicht = time.monotonic() + overzicht_elke
                stuur_overzicht()
                verwijderd = opslag.ruim_op()
                if verwijderd:
                    log.info("Website: %d aanvra(a)g(en) voorbij de bewaartermijn verwijderd", verwijderd)
        except Exception:
            log.exception("Website: ronde van de herhaaltaak mislukt")
        _stop.wait(interval)


def start() -> bool:
    global _draad
    if not opslag_aan() or (os.getenv("WEBSITE_VERWERKER") or "aan").lower() == "uit":
        log.info("Website: herhaaltaak niet gestart (opslag of verwerker uit)")
        return False
    if _draad is not None and _draad.is_alive():
        return True
    _stop.clear()
    _draad = threading.Thread(target=_lus, name="website-verwerker", daemon=True)
    _draad.start()
    log.info("Website: herhaaltaak gestart")
    return True


def stop() -> None:
    _stop.set()
