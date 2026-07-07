"""
Tests voor Stap 2 slice 2.2: declaratief profiel + runner. Kern: `run_profile`
op het canonieke model levert dezelfde bevindingen (ontbrekend veld + ongeldige
formaten, met severity en count) als de bestaande `validate_algemeen` — pariteit.
Puur functioneel; geen DB of HTTP.
"""
from app.services.algemeen_validator import validate_algemeen
from app.services.ingest.sources import detect_source
from app.services.ingest.pipeline import to_canonical
from app.services.control_profiles import (Profile, profile_from_algemeen_template,
                                           run_profile)


def _legacy_tuples(file_result):
    out = set()
    for i in file_result["issues"]:
        if i["type"] == "missing_field":
            out.add(("missing", i["field"], i["severity"]))
        else:
            ftype = i["type"].replace("invalid_", "")
            out.add((ftype, i["field"], i["severity"], i["count"]))
    return out


def _new_tuples(findings):
    out = set()
    for f in findings:
        if f.check == "missing":
            out.add(("missing", f.concept, f.severity))
        else:
            out.add((f.check, f.concept, f.severity, f.count))
    return out


def test_profile_from_template():
    p = profile_from_algemeen_template("employees")
    assert isinstance(p, Profile) and p.record_type == "employees"
    assert p.required and isinstance(p.all_fields, dict)
    assert profile_from_algemeen_template("bestaat-niet") is None


def test_run_profile_parity_with_validate_algemeen():
    rt = detect_source("Profit_Employees.xml", [], "algemeen").record_type
    profile = profile_from_algemeen_template(rt)
    fields = profile.all_fields

    # Laat één verplicht veld weg (-> missing) en vul de rest met waarden die
    # diverse formaatchecks laten falen. Beide engines gebruiken dezelfde
    # VALIDATORS, dus de gekozen waarden hoeven alleen 'gelijk te falen'.
    dropped = next(iter(profile.required))
    headers = [f for f in fields if f != dropped]
    rows = [
        {h: "x" for h in headers},
        {h: "2026-02-30" for h in headers},
        {h: "" for h in headers},
    ]

    legacy = validate_algemeen([{"filename": "Profit_Employees.xml",
                                 "headers": headers, "rows": rows}])
    fr = legacy["file_results"][0]
    assert fr["template"] == rt

    cf = to_canonical("Profit_Employees.xml", headers, rows, total=len(rows), standard="algemeen")
    findings = run_profile(cf, profile)

    assert _new_tuples(findings) == _legacy_tuples(fr)
    # er is minstens één missing (weggelaten verplicht veld) en één formaatfout
    assert any(f.check == "missing" for f in findings)
    assert any(f.check != "missing" for f in findings)


def test_run_profile_clean_file_no_missing():
    rt = "employees"
    profile = profile_from_algemeen_template(rt)
    headers = list(profile.all_fields.keys())   # alle velden aanwezig
    cf = to_canonical("Profit_Employees.xml", headers, [{h: "" for h in headers}],
                      total=1, standard="algemeen")
    findings = run_profile(cf, profile)
    # geen ontbrekende verplichte velden (alles aanwezig); lege waarden -> geen formaatfout
    assert not any(f.check == "missing" for f in findings)
