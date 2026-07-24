"""
Stap 2 slice 2.4: endpoint-omschakeling achter de env-vlag RHADIX_USE_PROFILES.
Vlag uit -> oude validator (huidig gedrag). Vlag aan -> profiel-laag levert de
per-bestand-meldingen, envelope (score/file_results) blijft intact.
"""
from app.services.validator import validate_files, use_profiles, profile_issues

FILES = [{
    "filename": "medewerker.csv",
    "schema_key": "medewerker",
    "headers": ["personeelsnummer", "geboortedatum"],
    "rows": [
        {"personeelsnummer": "1", "geboortedatum": "1980-01-01"},
        {"personeelsnummer": "1", "geboortedatum": "1981-01-01"},   # duplicaat
        {"personeelsnummer": "2", "geboortedatum": "fout"},         # bad dob
    ],
}]


def _ids(result):
    ids = set()
    for fr in result["file_results"]:
        ids |= {i["id"] for i in fr["issues"]}
    return ids


def test_flag_off_uses_legacy(monkeypatch):
    monkeypatch.delenv("RHADIX_USE_PROFILES", raising=False)
    assert use_profiles() is False
    result = validate_files(FILES)
    ids = _ids(result)
    assert "dup_id" in ids            # oude validator-ids
    assert "file_results" in result and "score" in result


def test_flag_on_uses_profiles(monkeypatch):
    monkeypatch.setenv("RHADIX_USE_PROFILES", "1")
    assert use_profiles() is True
    result = validate_files(FILES)
    ids = _ids(result)
    assert "personeelsnummer_unique" in ids     # profiel-laag-ids
    assert "geboortedatum_date" in ids
    # envelope intact
    assert "score" in result and result["file_results"][0]["error_count"] >= 1


def test_profile_issues_shape():
    issues = profile_issues("medewerker", FILES[0]["headers"], FILES[0]["rows"])
    assert issues and all({"id", "label", "severity", "count"} <= set(i) for i in issues)
