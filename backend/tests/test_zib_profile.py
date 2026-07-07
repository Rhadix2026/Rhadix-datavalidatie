"""
Tests voor Stap 2 slice 2.3: ZIB naar profiel. ZIB gebruikt eigen check-
implementaties met eigen meldingen, dus we tonen VERDICT-pariteit: de generieke
control keurt per waarde hetzelfde goed/af als ZIB's `_validate_value`
(bsn/date/code/numeric). Puur functioneel; geen DB of HTTP.
"""
from app.services.zib_validator import _validate_value
from app.services.zib_rules import ZIB_FIELD_RULES
from app.services.controls import check_value
from app.services.control_profiles import (profile_from_zib, run_profile,
                                           _ZIB_CHECK)
from app.services.ingest.pipeline import to_canonical

CASES = [
    ("bsn",     {"type": "bsn"},                                  None,
     ["123456782", "123456789", "12ab34", "999999990", "12345678"]),
    ("date",    {"type": "date"},                                 None,
     ["2026-01-01", "2026-02-30", "notadate", "20260101", "22-04-1990"]),
    ("code",    {"type": "code", "allowed_values": [{"value": "ja"}, {"value": "nee"}]},
     ["ja", "nee"], ["ja", "Nee", "misschien", "JA"]),
    ("numeric", {"type": "numeric"},                              None,
     ["36,0", "12", "x", "3.14"]),
]


def test_generic_controls_agree_with_zib_verdict():
    for vtype, rules, allowed, values in CASES:
        check = _ZIB_CHECK[vtype]
        for v in values:
            zib_valid = len(_validate_value("veld", v, rules)) == 0
            ctrl_valid = check_value(check, v, allowed=allowed)
            assert ctrl_valid == zib_valid, f"{vtype} «{v}»: control={ctrl_valid} zib={zib_valid}"


def test_profile_from_zib_patient():
    p = profile_from_zib("patient")
    assert p is not None and p.record_type == "patient"
    assert p.required.get("bsn") == "bsn"           # verplicht BSN-veld
    assert profile_from_zib("bestaat-niet") is None


def test_run_profile_zib_flags_invalid_bsn():
    p = profile_from_zib("patient")
    headers = ["BSN", "Voornaam", "Achternaam", "Geboortedatum"]
    rows = [{"BSN": "123456782", "Voornaam": "Jan", "Achternaam": "Jansen", "Geboortedatum": "1980-01-01"},
            {"BSN": "123456789", "Voornaam": "Piet", "Achternaam": "Peters", "Geboortedatum": "2026-02-30"}]
    cf = to_canonical("patienten.csv", headers, rows, total=2, standard="zib")
    assert cf.record_type == "patient"
    findings = run_profile(cf, p)
    bsn_finding = next((f for f in findings if f.concept == "bsn"), None)
    assert bsn_finding is not None and bsn_finding.check == "bsn" and bsn_finding.count == 1
