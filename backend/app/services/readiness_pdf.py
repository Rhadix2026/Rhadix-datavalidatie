"""
readiness_pdf.py — Zet een Readiness-rapport om in een PDF.

Hergebruikt `RhadixRenderer` uit `report_pdf_template.py`: dezelfde opmaak,
typografie en tabellen als de bestaande Rhadix-rapporten. Dit bestand bevat
daarom **alleen de opbouw van de story**, geen stijlen en geen renderlogica.
`reportlab` stond al in `requirements.txt`; er komt niets bij.

Bewust niet gebruikt: `header_bar()`. Die zet het Rhadix-logo en de navy
titelbalk bovenaan, en dit rapport wordt door Rhoderlanden Groep uitgebracht.
De titel wordt daarom als gewone kop opgebouwd, zodat er geen merk in beeld
komt dat hier niet thuishoort.

De PDF volgt de indeling van `readiness_rapport.Rapport`, in deze volgorde:

    1  titel en voor wie het rapport is
    2  managementsamenvatting
    3  totaalscore en de vijf dimensies
    4  sterke punten
    5  analyse per dimensie, oplopend op score
    6  prioritering
    7  antwoordenbijlage
    8  voorbehoud en vervolgstap
"""
from __future__ import annotations

from datetime import date

from app.services.readiness_rapport import Rapport
from app.services.report_pdf_template import RhadixRenderer as R, score_color_name

AFZENDER = "Rhoderlanden Groep · rhoderlandengroep.nl"


def _esc(tekst: str) -> str:
    """ReportLab-paragrafen zijn mini-HTML; & < > moeten daarom ontsnappen.

    De inhoud bevat bijvoorbeeld "Standaardisatie & betekenis"; zonder deze
    stap breekt dat de opbouw van de PDF.
    """
    return (str(tekst).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _datum() -> str:
    maanden = ("januari", "februari", "maart", "april", "mei", "juni", "juli",
               "augustus", "september", "oktober", "november", "december")
    vandaag = date.today()
    return f"{vandaag.day} {maanden[vandaag.month - 1]} {vandaag.year}"


def bouw_pdf(rapport: Rapport) -> bytes:
    """Bouwt de PDF en geeft de bytes terug."""
    story: list = []

    # 1 — Titel
    story += R.text(f"<b>{_esc(rapport.titel)}</b>", "h2")
    story += R.text(
        f"{_esc(rapport.check_titel)} · opgesteld voor <b>{_esc(rapport.organisatie)}</b>"
        f" · {_datum()}", "small")
    story += R.text(f"Ter attentie van {_esc(rapport.naam)}.", "small")
    story += R.separator()

    # 2 — Managementsamenvatting
    story += R.text("Managementsamenvatting", "h3")
    story += R.text(_esc(rapport.samenvatting))
    story += R.separator()

    # 3 — Totaalscore en dimensies
    story += R.text("Uw score", "h3")
    story += R.kpi_hero(
        main_value=str(rapport.totaal),
        main_label=rapport.categorie,
        main_sublabel=f"{rapport.soort} Readiness",
        main_color=score_color_name(rapport.totaal),
        kpis=[],
    )
    story += R.text(_esc(rapport.duiding))
    story += R.text("De vijf dimensies", "h3")
    story += R.score_table(
        headers=[_esc(naam) for naam, _ in rapport.dimensies],
        values=[str(score) for _, score in rapport.dimensies],
        value_colors=[score_color_name(score) for _, score in rapport.dimensies],
    )
    story += R.separator()

    # 4 — Sterke punten
    story += R.text("Sterke punten", "h3")
    if rapport.sterke_punten:
        story += R.bullets([f"<b>{_esc(d)}:</b> {_esc(t)}" for d, t in rapport.sterke_punten])
    else:
        story += R.text(_esc(rapport.geen_sterke_punten or ""))
    story += R.separator()

    # 5 — Analyse per dimensie
    story += R.text("Analyse per dimensie", "h3")
    for blok in rapport.blokken:
        kop = f"{_esc(blok.naam)} — {blok.score} van 100"
        if blok.prioriteit:
            kop += f"  ({_esc(blok.prioriteit)})"
        story += R.text(f"<b>{kop}</b>")
        story += R.text(f"<b>Interpretatie.</b> {_esc(blok.interpretatie)}")
        if blok.wat_al_staat:
            story += R.text("<b>Wat al staat.</b> " + " ".join(_esc(t) for t in blok.wat_al_staat), "small")
        if blok.aandachtspunten:
            story += R.text("Concrete aandachtspunten", "small")
            story += R.bullets([_esc(t) for t in blok.aandachtspunten])
        if blok.deels_geregeld:
            for vraag, antwoord in blok.deels_geregeld:
                story += R.text(f'Deels geregeld: "{_esc(vraag)}" — <b>{_esc(antwoord)}</b>', "small")
        story += R.text(f"<b>Verbeteractie.</b> {_esc(blok.verbeteractie)}")
        story += R.separator(space_before=6, space_after=6)

    # 6 — Prioritering
    story += R.text("Prioritering", "h3")
    for kop, regels in rapport.prioritering:
        story += R.text(f"<b>{_esc(kop)}</b>")
        if regels:
            story += R.bullets([f"<b>{_esc(n)} ({s}).</b> {_esc(t)}<br/>"
                                f'<font size="7">Uw antwoord: {_esc(a)}</font>'
                                for n, s, t, a in regels])
        else:
            story += R.text("Geen dimensies in deze groep.", "small")
    story += R.separator()

    # 7 — Antwoordenbijlage
    story += R.text("Bijlage: uw antwoorden", "h3")
    story += R.text(
        "Deze bijlage laat zien waarop het rapport is gebaseerd, zodat u de uitkomst "
        "binnen uw organisatie kunt nalopen en bespreken.", "small")
    for dimensie, vragen in rapport.bijlage:
        story += R.text(f"<b>{_esc(dimensie)}</b>", "small")
        story += R.bullets([f"{_esc(v)} — <b>{_esc(a)}</b>" for v, a in vragen])
    story += R.separator()

    # 8 — Voorbehoud en vervolg
    story += R.text("Wat dit rapport wel en niet is", "h3")
    story += R.text(_esc(rapport.voorbehoud))
    story += R.text(_esc(rapport.vervolg))

    story += R.footer_bar(AFZENDER)

    return R.build_pdf(story, title=rapport.titel, author="Rhoderlanden Groep")
