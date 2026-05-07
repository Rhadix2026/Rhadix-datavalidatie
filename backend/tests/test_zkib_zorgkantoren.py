"""
Tests voor het uitwisselprofiel Zorgkantoren (ZK-IB) — bronsystemen:
  - Exact Financial    (exact_fin)
  - AFAS PROFIT FIN    (afas_profit_fin)
  - Visma PUUR         (visma_puur)

Geteste scenario's:
  1.  Grootboekrubriek  — volledig geldige export
  2.  Grootboekrubriek  — rekeningNummer ontbreekt → error
  3.  Grootboekrubriek  — omschrijving ontbreekt → error
  4.  Grootboekrubriek  — startDatum ontbreekt → error
  5.  FinancieleBoeking — volledig geldige export
  6.  FinancieleBoeking — boekingsBedrag ontbreekt → error
  7.  FinancieleBoeking — boekingsBedrag geen getal → error
  8.  FinancieleBoeking — kostenPlaats ontbreekt → error
  9.  FinancieleBoeking — boekingsDatum ontbreekt → error
  10. FinancieleBoeking — grootBoekRekening ontbreekt → error
  11. Arrangement       — volledig geldig
  12. Arrangement       — Arrangement_ID ontbreekt → error
  13. Arrangement       — Client_ID ontbreekt → error
  14. Arrangement       — Begindatum ontbreekt → error
  15. Arrangement       — Einddatum voor Begindatum → warning
  16. ArrangemProductWLZ— volledig geldig
  17. ArrangemProductWLZ— BeginDatumDeclaratie ontbreekt → error
  18. ArrangemProductWLZ— EindDatumDeclaratie ontbreekt → error
  19. ArrangemProductWLZ— Zorgzwaartepakketcode ontbreekt → error
  20. ArrangemProductWLZ— EindDatum voor BeginDatum → error
  21. WLZProduct        — prestatiecode ontbreekt → error
  22. Bronsysteem-check — exact_fin aanwezig in SOURCE_SYSTEMS
  23. Bronsysteem-check — afas_profit_fin aanwezig in SOURCE_SYSTEMS
  24. Bronsysteem-check — visma_puur aanwezig in SOURCE_SYSTEMS
"""

import sys
import os
import re
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.source_systems import SOURCE_SYSTEMS

# ─── helpers ──────────────────────────────────────────────────────────────────

def parse_datum(s: str) -> datetime | None:
    """Parseer dd/mm/yyyy, geeft None bij lege of ongeldige waarde."""
    if not s or not s.strip():
        return None
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y")
    except ValueError:
        return None


def validate_grootboekrubriek(rows: list[dict]) -> list[dict]:
    """
    Valideert een lijst grootboekrubriek-records.
    Retourneert een lijst van gevonden issues:
      { "id": str, "severity": str, "count": int, "detail": str }
    """
    issues = []
    missing_nummer    = [r for r in rows if not r.get("grootboekRekeningNummer", "").strip()]
    missing_omschr    = [r for r in rows if not r.get("grootboekRekeningOmschrijving", "").strip()]
    missing_startdatum= [r for r in rows if not r.get("startDatum", "").strip()]
    ongeldige_datum   = [
        r for r in rows
        if r.get("startDatum", "").strip() and parse_datum(r["startDatum"]) is None
    ]

    if missing_nummer:
        issues.append({
            "id": "missing_rekeningnummer", "severity": "error",
            "count": len(missing_nummer),
            "detail": f"{len(missing_nummer)} record(s) zonder grootboekRekeningNummer",
        })
    if missing_omschr:
        issues.append({
            "id": "missing_omschrijving", "severity": "error",
            "count": len(missing_omschr),
            "detail": f"{len(missing_omschr)} record(s) zonder grootboekRekeningOmschrijving",
        })
    if missing_startdatum:
        issues.append({
            "id": "missing_startdatum", "severity": "error",
            "count": len(missing_startdatum),
            "detail": f"{len(missing_startdatum)} record(s) zonder startDatum",
        })
    if ongeldige_datum:
        nummers = ", ".join(r.get("grootboekRekeningNummer", "?") for r in ongeldige_datum)
        issues.append({
            "id": "ongeldige_startdatum", "severity": "error",
            "count": len(ongeldige_datum),
            "detail": f"Ongeldige startDatum voor: {nummers}",
        })
    return issues


def validate_financiele_boeking(rows: list[dict]) -> list[dict]:
    """Valideert financiële boekingsrecords voor ZK-IB."""
    issues = []
    missing_bedrag     = [r for r in rows if not str(r.get("boekingsBedrag", "")).strip()]
    geen_getal         = [
        r for r in rows
        if str(r.get("boekingsBedrag", "")).strip()
        and not _is_getal(str(r["boekingsBedrag"]))
    ]
    missing_datum      = [r for r in rows if not r.get("financieleBoekingsDatum", "").strip()]
    missing_rekening   = [r for r in rows if not r.get("grootBoekRekening", "").strip()]
    missing_kostenpl   = [r for r in rows if not r.get("kostenPlaats", "").strip()]

    if missing_bedrag:
        issues.append({"id": "missing_boekingsbedrag", "severity": "error",
                        "count": len(missing_bedrag), "detail": f"{len(missing_bedrag)} record(s) zonder boekingsBedrag"})
    if geen_getal:
        waarden = ", ".join(str(r["boekingsBedrag"]) for r in geen_getal)
        issues.append({"id": "ongeldig_boekingsbedrag", "severity": "error",
                        "count": len(geen_getal), "detail": f"Niet-numeriek boekingsBedrag: {waarden}"})
    if missing_datum:
        issues.append({"id": "missing_boekingsdatum", "severity": "error",
                        "count": len(missing_datum), "detail": f"{len(missing_datum)} record(s) zonder financieleBoekingsDatum"})
    if missing_rekening:
        issues.append({"id": "missing_grootboekrekening", "severity": "error",
                        "count": len(missing_rekening), "detail": f"{len(missing_rekening)} record(s) zonder grootBoekRekening"})
    if missing_kostenpl:
        issues.append({"id": "missing_kostenplaats", "severity": "error",
                        "count": len(missing_kostenpl), "detail": f"{len(missing_kostenpl)} record(s) zonder kostenPlaats"})
    return issues


def validate_arrangement(rows: list[dict]) -> list[dict]:
    """Valideert Arrangement-records (Visma PUUR) voor ZK-IB."""
    issues = []
    missing_id      = [r for r in rows if not r.get("Arrangement_ID", "").strip()]
    missing_client  = [r for r in rows if not r.get("Client_ID", "").strip()]
    missing_begin   = [r for r in rows if not r.get("Begindatum", "").strip()]
    einddatum_fouten = []
    for r in rows:
        begin = parse_datum(r.get("Begindatum", ""))
        eind  = parse_datum(r.get("Einddatum", ""))
        if begin and eind and eind < begin:
            einddatum_fouten.append(r)

    if missing_id:
        issues.append({"id": "missing_arrangement_id", "severity": "error",
                        "count": len(missing_id), "detail": f"{len(missing_id)} record(s) zonder Arrangement_ID"})
    if missing_client:
        issues.append({"id": "missing_client_id", "severity": "error",
                        "count": len(missing_client), "detail": f"{len(missing_client)} record(s) zonder Client_ID"})
    if missing_begin:
        issues.append({"id": "missing_begindatum", "severity": "error",
                        "count": len(missing_begin), "detail": f"{len(missing_begin)} record(s) zonder Begindatum"})
    if einddatum_fouten:
        ids = ", ".join(r.get("Arrangement_ID", "?") for r in einddatum_fouten)
        issues.append({"id": "einddatum_voor_begindatum", "severity": "warning",
                        "count": len(einddatum_fouten), "detail": f"Einddatum voor Begindatum: {ids}"})
    return issues


def validate_arrangement_product_wlz(rows: list[dict]) -> list[dict]:
    """Valideert ArrangementProductWLZ-records (Visma PUUR) voor ZK-IB."""
    issues = []
    missing_ap_id    = [r for r in rows if not r.get("ArrangementProduct_ID", "").strip()]
    missing_ind      = [r for r in rows if not r.get("IndicatieAanvraagnummer", "").strip()]
    missing_bslt     = [r for r in rows if not r.get("Besluitnummer", "").strip()]
    missing_begin    = [r for r in rows if not r.get("BeginDatumDeclaratie", "").strip()]
    missing_eind     = [r for r in rows if not r.get("EindDatumDeclaratie", "").strip()]
    missing_zzp      = [r for r in rows if not r.get("Zorgzwaartepakketcode", "").strip()]
    datum_fouten     = []
    for r in rows:
        begin = parse_datum(r.get("BeginDatumDeclaratie", ""))
        eind  = parse_datum(r.get("EindDatumDeclaratie", ""))
        if begin and eind and eind < begin:
            datum_fouten.append(r)

    if missing_ap_id:
        issues.append({"id": "missing_arrangementproduct_id", "severity": "error",
                        "count": len(missing_ap_id), "detail": f"{len(missing_ap_id)} record(s) zonder ArrangementProduct_ID"})
    if missing_ind:
        issues.append({"id": "missing_indicatie_aanvraagnummer", "severity": "error",
                        "count": len(missing_ind), "detail": f"{len(missing_ind)} record(s) zonder IndicatieAanvraagnummer"})
    if missing_bslt:
        issues.append({"id": "missing_besluitnummer", "severity": "error",
                        "count": len(missing_bslt), "detail": f"{len(missing_bslt)} record(s) zonder Besluitnummer"})
    if missing_begin:
        issues.append({"id": "missing_begindatum_declaratie", "severity": "error",
                        "count": len(missing_begin), "detail": f"{len(missing_begin)} record(s) zonder BeginDatumDeclaratie"})
    if missing_eind:
        issues.append({"id": "missing_einddatum_declaratie", "severity": "error",
                        "count": len(missing_eind), "detail": f"{len(missing_eind)} record(s) zonder EindDatumDeclaratie"})
    if missing_zzp:
        issues.append({"id": "missing_zorgzwaartepakketcode", "severity": "error",
                        "count": len(missing_zzp), "detail": f"{len(missing_zzp)} record(s) zonder Zorgzwaartepakketcode"})
    if datum_fouten:
        ids = ", ".join(r.get("ArrangementProduct_ID", "?") for r in datum_fouten)
        issues.append({"id": "einddatum_voor_begindatum_declaratie", "severity": "error",
                        "count": len(datum_fouten), "detail": f"EindDatum voor BeginDatum declaratie: {ids}"})
    return issues


def _is_getal(waarde: str) -> bool:
    try:
        float(waarde.replace(",", "."))
        return True
    except ValueError:
        return False


def issues_by_id(issues: list) -> dict:
    return {i["id"]: i for i in issues}


# ─── Scenario 1 — Grootboekrubriek: volledig geldige export ──────────────────

def test_grootboekrubriek_geldig_geen_errors():
    """Geldige grootboekrubriek export → geen errors."""
    rows = [
        {"grootboekRekeningNummer": "4100", "grootboekRekeningOmschrijving": "Personeelskosten", "startDatum": "01/01/2024", "eindDatum": ""},
        {"grootboekRekeningNummer": "8110", "grootboekRekeningOmschrijving": "WLZ VPT",          "startDatum": "01/01/2023", "eindDatum": ""},
    ]
    issues = validate_grootboekrubriek(rows)
    assert len(issues) == 0, f"Onverwachte issues: {issues}"
    print("✓  Scenario 1: Grootboekrubriek geldig → geen errors")


# ─── Scenario 2 — Grootboekrubriek: rekeningNummer ontbreekt ─────────────────

def test_grootboekrubriek_missing_rekeningnummer():
    """Rekeningnummer ontbreekt → error missing_rekeningnummer."""
    rows = [
        {"grootboekRekeningNummer": "",     "grootboekRekeningOmschrijving": "Personeelskosten", "startDatum": "01/01/2024", "eindDatum": ""},
        {"grootboekRekeningNummer": "4100", "grootboekRekeningOmschrijving": "WLZ VPT",          "startDatum": "01/01/2023", "eindDatum": ""},
    ]
    issues = issues_by_id(validate_grootboekrubriek(rows))
    assert "missing_rekeningnummer" in issues, "Verwachtte error 'missing_rekeningnummer'"
    assert issues["missing_rekeningnummer"]["count"] == 1
    print(f"✓  Scenario 2: Ontbrekend rekeningnummer → error (count=1)")


# ─── Scenario 3 — Grootboekrubriek: omschrijving ontbreekt ───────────────────

def test_grootboekrubriek_missing_omschrijving():
    """Omschrijving ontbreekt → error missing_omschrijving."""
    rows = [
        {"grootboekRekeningNummer": "4100", "grootboekRekeningOmschrijving": "",  "startDatum": "01/01/2024", "eindDatum": ""},
    ]
    issues = issues_by_id(validate_grootboekrubriek(rows))
    assert "missing_omschrijving" in issues
    print(f"✓  Scenario 3: Ontbrekende omschrijving → error")


# ─── Scenario 4 — Grootboekrubriek: startDatum ontbreekt ─────────────────────

def test_grootboekrubriek_missing_startdatum():
    """startDatum ontbreekt → error missing_startdatum."""
    rows = [
        {"grootboekRekeningNummer": "4999", "grootboekRekeningOmschrijving": "Test", "startDatum": "", "eindDatum": ""},
    ]
    issues = issues_by_id(validate_grootboekrubriek(rows))
    assert "missing_startdatum" in issues
    print(f"✓  Scenario 4: Ontbrekende startDatum → error")


# ─── Scenario 5 — FinancieleBoeking: volledig geldig ─────────────────────────

def test_financiele_boeking_geldig_geen_errors():
    """Geldige financiële boekingen → geen errors."""
    rows = [
        {"boekingsBedrag": "125430.50", "financieleBoekingsDatum": "31/01/2024", "grootBoekRekening": "4100", "kostenPlaats": "KP-WLZ-001"},
        {"boekingsBedrag": "-2500.00",  "financieleBoekingsDatum": "29/02/2024", "grootBoekRekening": "4100", "kostenPlaats": "KP-WLZ-001"},
        {"boekingsBedrag": "0.00",      "financieleBoekingsDatum": "31/03/2024", "grootBoekRekening": "4400", "kostenPlaats": "KP-WLZ-002"},
    ]
    issues = validate_financiele_boeking(rows)
    assert len(issues) == 0, f"Onverwachte issues: {issues}"
    print("✓  Scenario 5: FinancieleBoeking geldig → geen errors")


# ─── Scenario 6 — FinancieleBoeking: boekingsBedrag ontbreekt ────────────────

def test_financiele_boeking_missing_bedrag():
    """boekingsBedrag ontbreekt → error missing_boekingsbedrag."""
    rows = [
        {"boekingsBedrag": "", "financieleBoekingsDatum": "31/01/2024", "grootBoekRekening": "4100", "kostenPlaats": "KP-001"},
    ]
    issues = issues_by_id(validate_financiele_boeking(rows))
    assert "missing_boekingsbedrag" in issues
    print("✓  Scenario 6: Ontbrekend boekingsBedrag → error")


# ─── Scenario 7 — FinancieleBoeking: boekingsBedrag geen getal ───────────────

def test_financiele_boeking_ongeldig_bedrag():
    """Niet-numeriek boekingsBedrag → error ongeldig_boekingsbedrag."""
    rows = [
        {"boekingsBedrag": "GEEN_GETAL", "financieleBoekingsDatum": "31/01/2024", "grootBoekRekening": "4100", "kostenPlaats": "KP-001"},
    ]
    issues = issues_by_id(validate_financiele_boeking(rows))
    assert "ongeldig_boekingsbedrag" in issues
    assert "GEEN_GETAL" in issues["ongeldig_boekingsbedrag"]["detail"]
    print(f"✓  Scenario 7: Niet-numeriek boekingsBedrag → error (detail bevat waarde)")


# ─── Scenario 8 — FinancieleBoeking: kostenPlaats ontbreekt ──────────────────

def test_financiele_boeking_missing_kostenplaats():
    """kostenPlaats ontbreekt → error missing_kostenplaats."""
    rows = [
        {"boekingsBedrag": "1000.00", "financieleBoekingsDatum": "31/01/2024", "grootBoekRekening": "4100", "kostenPlaats": ""},
    ]
    issues = issues_by_id(validate_financiele_boeking(rows))
    assert "missing_kostenplaats" in issues
    print("✓  Scenario 8: Ontbrekende kostenPlaats → error")


# ─── Scenario 9 — FinancieleBoeking: datum ontbreekt ─────────────────────────

def test_financiele_boeking_missing_datum():
    """financieleBoekingsDatum ontbreekt → error missing_boekingsdatum."""
    rows = [
        {"boekingsBedrag": "1000.00", "financieleBoekingsDatum": "", "grootBoekRekening": "4100", "kostenPlaats": "KP-001"},
    ]
    issues = issues_by_id(validate_financiele_boeking(rows))
    assert "missing_boekingsdatum" in issues
    print("✓  Scenario 9: Ontbrekende boekingsDatum → error")


# ─── Scenario 10 — FinancieleBoeking: grootBoekRekening ontbreekt ────────────

def test_financiele_boeking_missing_rekening():
    """grootBoekRekening ontbreekt → error missing_grootboekrekening."""
    rows = [
        {"boekingsBedrag": "1000.00", "financieleBoekingsDatum": "31/01/2024", "grootBoekRekening": "", "kostenPlaats": "KP-001"},
    ]
    issues = issues_by_id(validate_financiele_boeking(rows))
    assert "missing_grootboekrekening" in issues
    print("✓  Scenario 10: Ontbrekende grootBoekRekening → error")


# ─── Scenario 11 — Arrangement: volledig geldig ──────────────────────────────

def test_arrangement_geldig_geen_errors():
    """Geldige arrangement-records → geen errors."""
    rows = [
        {"Arrangement_ID": "ARR-001", "Client_ID": "CLT-001", "Begindatum": "01/01/2024", "Einddatum": ""},
        {"Arrangement_ID": "ARR-002", "Client_ID": "CLT-002", "Begindatum": "01/03/2024", "Einddatum": "30/09/2024"},
    ]
    issues = validate_arrangement(rows)
    assert len(issues) == 0, f"Onverwachte issues: {issues}"
    print("✓  Scenario 11: Arrangement geldig → geen errors")


# ─── Scenario 12 — Arrangement: Arrangement_ID ontbreekt ─────────────────────

def test_arrangement_missing_id():
    rows = [{"Arrangement_ID": "", "Client_ID": "CLT-001", "Begindatum": "01/01/2024", "Einddatum": ""}]
    issues = issues_by_id(validate_arrangement(rows))
    assert "missing_arrangement_id" in issues
    print("✓  Scenario 12: Ontbrekend Arrangement_ID → error")


# ─── Scenario 13 — Arrangement: Client_ID ontbreekt ─────────────────────────

def test_arrangement_missing_client_id():
    rows = [{"Arrangement_ID": "ARR-001", "Client_ID": "", "Begindatum": "01/01/2024", "Einddatum": ""}]
    issues = issues_by_id(validate_arrangement(rows))
    assert "missing_client_id" in issues
    print("✓  Scenario 13: Ontbrekend Client_ID → error")


# ─── Scenario 14 — Arrangement: Begindatum ontbreekt ────────────────────────

def test_arrangement_missing_begindatum():
    rows = [{"Arrangement_ID": "ARR-001", "Client_ID": "CLT-001", "Begindatum": "", "Einddatum": ""}]
    issues = issues_by_id(validate_arrangement(rows))
    assert "missing_begindatum" in issues
    print("✓  Scenario 14: Ontbrekende Begindatum → error")


# ─── Scenario 15 — Arrangement: Einddatum voor Begindatum ────────────────────

def test_arrangement_einddatum_voor_begindatum():
    """Einddatum vóór Begindatum → warning einddatum_voor_begindatum."""
    rows = [
        {"Arrangement_ID": "ARR-006", "Client_ID": "CLT-006", "Begindatum": "01/04/2024", "Einddatum": "31/03/2024"},
    ]
    issues = issues_by_id(validate_arrangement(rows))
    assert "einddatum_voor_begindatum" in issues
    assert issues["einddatum_voor_begindatum"]["severity"] == "warning"
    assert "ARR-006" in issues["einddatum_voor_begindatum"]["detail"]
    print(f"✓  Scenario 15: Einddatum voor Begindatum → warning (ARR-006 in detail)")


# ─── Scenario 16 — ArrangementProductWLZ: volledig geldig ────────────────────

def test_arrangement_product_wlz_geldig():
    rows = [{
        "ArrangementProduct_ID": "AP-001-A",
        "IndicatieAanvraagnummer": "IND-2023-001",
        "Besluitnummer": "BSLT-2023-001",
        "BeginDatumDeclaratie": "01/01/2024",
        "EindDatumDeclaratie": "31/03/2024",
        "Zorgzwaartepakketcode": "VV10",
    }]
    issues = validate_arrangement_product_wlz(rows)
    assert len(issues) == 0, f"Onverwachte issues: {issues}"
    print("✓  Scenario 16: ArrangementProductWLZ geldig → geen errors")


# ─── Scenario 17 — ArrangementProductWLZ: BeginDatumDeclaratie ontbreekt ─────

def test_arrangement_product_wlz_missing_begin():
    rows = [{"ArrangementProduct_ID": "AP-ERR", "IndicatieAanvraagnummer": "IND-001",
             "Besluitnummer": "BSLT-001", "BeginDatumDeclaratie": "",
             "EindDatumDeclaratie": "31/08/2024", "Zorgzwaartepakketcode": "VV05"}]
    issues = issues_by_id(validate_arrangement_product_wlz(rows))
    assert "missing_begindatum_declaratie" in issues
    print("✓  Scenario 17: Ontbrekende BeginDatumDeclaratie → error")


# ─── Scenario 18 — ArrangementProductWLZ: EindDatumDeclaratie ontbreekt ──────

def test_arrangement_product_wlz_missing_eind():
    rows = [{"ArrangementProduct_ID": "AP-ERR", "IndicatieAanvraagnummer": "IND-001",
             "Besluitnummer": "BSLT-001", "BeginDatumDeclaratie": "01/06/2024",
             "EindDatumDeclaratie": "", "Zorgzwaartepakketcode": "VV05"}]
    issues = issues_by_id(validate_arrangement_product_wlz(rows))
    assert "missing_einddatum_declaratie" in issues
    print("✓  Scenario 18: Ontbrekende EindDatumDeclaratie → error")


# ─── Scenario 19 — ArrangementProductWLZ: ZZP-code ontbreekt ─────────────────

def test_arrangement_product_wlz_missing_zzp():
    rows = [{"ArrangementProduct_ID": "AP-ERR", "IndicatieAanvraagnummer": "IND-001",
             "Besluitnummer": "BSLT-001", "BeginDatumDeclaratie": "01/06/2024",
             "EindDatumDeclaratie": "31/08/2024", "Zorgzwaartepakketcode": ""}]
    issues = issues_by_id(validate_arrangement_product_wlz(rows))
    assert "missing_zorgzwaartepakketcode" in issues
    print("✓  Scenario 19: Ontbrekende Zorgzwaartepakketcode → error")


# ─── Scenario 20 — ArrangementProductWLZ: EindDatum voor BeginDatum ──────────

def test_arrangement_product_wlz_datum_volgorde():
    """EindDatumDeclaratie voor BeginDatumDeclaratie → error."""
    rows = [{"ArrangementProduct_ID": "AP-ERR-005", "IndicatieAanvraagnummer": "IND-001",
             "Besluitnummer": "BSLT-001", "BeginDatumDeclaratie": "01/09/2024",
             "EindDatumDeclaratie": "31/08/2024", "Zorgzwaartepakketcode": "VV05"}]
    issues = issues_by_id(validate_arrangement_product_wlz(rows))
    assert "einddatum_voor_begindatum_declaratie" in issues
    assert issues["einddatum_voor_begindatum_declaratie"]["severity"] == "error"
    assert "AP-ERR-005" in issues["einddatum_voor_begindatum_declaratie"]["detail"]
    print("✓  Scenario 20: EindDatum voor BeginDatum declaratie → error")


# ─── Scenario 21 — WLZProduct: prestatiecode ontbreekt ───────────────────────

def test_wlz_product_missing_prestatiecode():
    """WLZProduct zonder prestatiecode is ongeldig."""
    rows = [
        {"prestatiecode": "VV10", "Product_ID": "PRD-001"},
        {"prestatiecode": "",     "Product_ID": "PRD-999"},
    ]
    missing = [r for r in rows if not r.get("prestatiecode", "").strip()]
    assert len(missing) == 1
    print("✓  Scenario 21: WLZProduct zonder prestatiecode → gedetecteerd")


# ─── Scenario 22-24 — Bronsystemen aanwezig in SOURCE_SYSTEMS ────────────────

def test_exact_fin_in_source_systems():
    """exact_fin moet aanwezig zijn in SOURCE_SYSTEMS."""
    assert "exact_fin" in SOURCE_SYSTEMS, "exact_fin ontbreekt in SOURCE_SYSTEMS"
    s = SOURCE_SYSTEMS["exact_fin"]
    assert s["vendor"] == "Exact Software"
    assert "grootboekrubriek"   in s["schemas"]
    assert "financiele_boeking" in s["schemas"]
    assert "wlz_kostenplaats"   in s["schemas"]
    print(f"✓  Scenario 22: exact_fin aanwezig — {len(s['schemas'])} schema's")


def test_afas_profit_fin_in_source_systems():
    """afas_profit_fin moet aanwezig zijn in SOURCE_SYSTEMS."""
    assert "afas_profit_fin" in SOURCE_SYSTEMS, "afas_profit_fin ontbreekt in SOURCE_SYSTEMS"
    s = SOURCE_SYSTEMS["afas_profit_fin"]
    assert s["vendor"] == "AFAS Software"
    assert "grootboekrubriek"   in s["schemas"]
    assert "financiele_boeking" in s["schemas"]
    assert "wlz_kostenplaats"   in s["schemas"]
    print(f"✓  Scenario 23: afas_profit_fin aanwezig — {len(s['schemas'])} schema's")


def test_visma_puur_in_source_systems():
    """visma_puur moet aanwezig zijn in SOURCE_SYSTEMS."""
    assert "visma_puur" in SOURCE_SYSTEMS, "visma_puur ontbreekt in SOURCE_SYSTEMS"
    s = SOURCE_SYSTEMS["visma_puur"]
    assert s["vendor"] == "Visma"
    assert "arrangement"              in s["schemas"]
    assert "arrangement_product"      in s["schemas"]
    assert "arrangement_product_wlz"  in s["schemas"]
    assert "team"                     in s["schemas"]
    assert "wlz_product"              in s["schemas"]
    print(f"✓  Scenario 24: visma_puur aanwezig — {len(s['schemas'])} schema's")


# ─── runner ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_grootboekrubriek_geldig_geen_errors,
        test_grootboekrubriek_missing_rekeningnummer,
        test_grootboekrubriek_missing_omschrijving,
        test_grootboekrubriek_missing_startdatum,
        test_financiele_boeking_geldig_geen_errors,
        test_financiele_boeking_missing_bedrag,
        test_financiele_boeking_ongeldig_bedrag,
        test_financiele_boeking_missing_kostenplaats,
        test_financiele_boeking_missing_datum,
        test_financiele_boeking_missing_rekening,
        test_arrangement_geldig_geen_errors,
        test_arrangement_missing_id,
        test_arrangement_missing_client_id,
        test_arrangement_missing_begindatum,
        test_arrangement_einddatum_voor_begindatum,
        test_arrangement_product_wlz_geldig,
        test_arrangement_product_wlz_missing_begin,
        test_arrangement_product_wlz_missing_eind,
        test_arrangement_product_wlz_missing_zzp,
        test_arrangement_product_wlz_datum_volgorde,
        test_wlz_product_missing_prestatiecode,
        test_exact_fin_in_source_systems,
        test_afas_profit_fin_in_source_systems,
        test_visma_puur_in_source_systems,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"✗  {t.__name__} GEFAALD: {e}")
            failed += 1
        except Exception as e:
            print(f"✗  {t.__name__} EXCEPTION: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"ZK-IB Testset — Resultaat: {passed}/{passed+failed} geslaagd")
    if failed:
        sys.exit(1)
