"""
Stap 2 — pariteitssweep KIK-V profiel vs. oude validator (gate vóór omschakelen).

Legt vast welke bespoke KIK-V-regels nu verdict-pariteit hebben in de profiel-laag.
De nog-openstaande legacy-only meldingen staan onderaan gedocumenteerd; die moeten
eerst geport worden vóór het endpoint op de profiel-laag mag draaien (slice 2.4).
"""
from app.services.validator import run_file_checks, auto_map, KIKV_REFERENCE
from app.services.control_profiles import profile_from_kikv, run_profile
from app.services.ingest.pipeline import to_canonical


def _run(rt, headers, rows):
    mapping = auto_map(headers, KIKV_REFERENCE[rt]["col_aliases"])
    legacy = {i["id"]: i["count"] for i in run_file_checks(rt, rows, mapping)}
    cf = to_canonical("x.csv", headers, rows, total=len(rows), standard="kikv")
    prof = {f"{f.concept}:{f.check}": f.count for f in run_profile(cf, profile_from_kikv(rt))}
    return legacy, prof, cf


def test_medewerker_ported_parity():
    legacy, prof, cf = _run("medewerker", ["personeelsnummer", "geboortedatum"], [
        {"personeelsnummer": "1", "geboortedatum": "1980-01-01"},
        {"personeelsnummer": "1", "geboortedatum": ""},
        {"personeelsnummer": "", "geboortedatum": "fout"},
        {"personeelsnummer": "99999", "geboortedatum": "1990-13-40"},
    ])
    assert cf.record_type == "medewerker"
    assert prof["personeelsnummer:unique"] == legacy["dup_id"]
    assert prof["personeelsnummer:forbidden"] == legacy["placeholder"]
    assert prof["geboortedatum:date"] == legacy["bad_dob"]


def test_werkovereenkomst_ported_parity():
    legacy, prof, cf = _run("werkovereenkomst",
        ["dienstverbandnummer", "personeelsnummer", "overeenkomsttype", "startdatum", "einddatum"], [
        {"dienstverbandnummer": "1", "personeelsnummer": "1", "overeenkomsttype": "bepaalde tijd", "startdatum": "2024-01-01", "einddatum": ""},
        {"dienstverbandnummer": "2", "personeelsnummer": "5", "overeenkomsttype": "onzin", "startdatum": "2024-01-01", "einddatum": ""},
        {"dienstverbandnummer": "3", "personeelsnummer": "6", "overeenkomsttype": "onbepaalde tijd", "startdatum": "2024-01-01", "einddatum": ""},
    ])
    assert prof["overeenkomsttype:codelist"] == legacy["invalid_type"]
    assert prof["einddatum:conditional_required"] == legacy["missing_einddatum_temp"]


def test_verzuim_ported_parity():
    legacy, prof, cf = _run("verzuim",
        ["personeelsnummer", "soortverzuim", "startmoment", "eindmoment", "verzuimpercentage"], [
        {"personeelsnummer": "1", "soortverzuim": "ziek", "startmoment": "2024-02-10", "eindmoment": "2024-02-05", "verzuimpercentage": "50"},
        {"personeelsnummer": "2", "soortverzuim": "ziek", "startmoment": "2024-01-01", "eindmoment": "", "verzuimpercentage": "150"},
    ])
    assert prof["eindmoment:date_order"] == legacy["end_before_start"]
    assert prof["verzuimpercentage:range"] == legacy["invalid_pct"]


# ── Nog te porten vóór slice 2.4 (endpoint-omschakeling) ──────────────────────
# - per-rij leeg-verplicht: empty_id, empty_dob, missing_start, missing_niveau
# - verzuim soortverzuim-codelijst (profiel bedraadt nu alleen overeenkomsttype)
# - dup_functie (waarschuwing), werkovereenkomst placeholder (99999 + leeg), open_contracts (info)
