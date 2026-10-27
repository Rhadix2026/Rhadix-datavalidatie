"""
test_onvolledige_csv_rijen.py — B-17: een CSV-rij met te weinig kolommen.

Vóór deze wijziging liet `parse_csv_bytes` de upload crashen: `csv.DictReader`
vult een ontbrekend veld met `None` (restval), en de bewaking `if k` keek naar
de sleutel in plaats van de waarde, dus `None.strip()` gaf een AttributeError
die als HTTP 500 bij de gebruiker belandde.

Afgesproken gedrag: geen 500 en geen stilzwijgende acceptatie, maar een
duidelijke validatiefout met het regelnummer en het ontbrekende veld.

Drie vormen worden getoetst, want ze gedragen zich verschillend bij DictReader:
een rij met te weinig kolommen (restval → None), een rij met te veel kolommen
(restkey → een lijst onder sleutel None) en een lege rij.
"""
import io

import pytest

from app.routers.validate import (
    onvolledige_rijen_naar_meldingen,
    parse_csv_bytes,
    voeg_onvolledige_rijen_toe,
)

KOP = "EmployeeId;BSN;DateOfBirth;Gender"
VOLLEDIG = "1001;123456782;1975-11-02;M"
TE_KORT = "1002;123456782"                      # mist DateOfBirth en Gender
TE_LANG = "1003;123456782;1980-03-03;V;extra"   # één kolom te veel
LEEG = ";;;"


def _csv(*regels: str) -> bytes:
    return ("\n".join([KOP, *regels]) + "\n").encode("utf-8")


# ── de parser ───────────────────────────────────────────────────────────────

def test_te_korte_rij_geeft_geen_uitzondering():
    headers, rows, total = parse_csv_bytes(_csv(VOLLEDIG, TE_KORT), "f.csv")
    assert headers == ["EmployeeId", "BSN", "DateOfBirth", "Gender"]
    assert total == 2
    assert len(rows) == 2


def test_te_korte_rij_wordt_geregistreerd_met_regelnummer_en_velden():
    onvolledig: list = []
    parse_csv_bytes(_csv(VOLLEDIG, TE_KORT), "f.csv", onvolledig=onvolledig)
    assert len(onvolledig) == 1
    # kopregel = 1, eerste gegevensrij = 2, de te korte rij = 3
    assert onvolledig[0]["rij"] == 3
    assert onvolledig[0]["ontbrekend"] == ["DateOfBirth", "Gender"]


def test_ontbrekende_waarde_wordt_lege_string_niet_none():
    _, rows, _ = parse_csv_bytes(_csv(TE_KORT), "f.csv")
    assert rows[0]["DateOfBirth"] == ""
    assert rows[0]["Gender"] == ""
    assert None not in rows[0].values()


def test_te_lange_rij_blijft_geldig_en_wordt_niet_als_onvolledig_gemeld():
    onvolledig: list = []
    headers, rows, total = parse_csv_bytes(_csv(TE_LANG), "f.csv", onvolledig=onvolledig)
    assert total == 1
    # De overtollige kolom komt onder sleutel None en wordt overgeslagen
    assert set(rows[0]) == set(headers)
    assert onvolledig == []


def test_lege_rij_telt_niet_mee_en_meldt_niets():
    onvolledig: list = []
    _, rows, total = parse_csv_bytes(_csv(VOLLEDIG, LEEG), "f.csv", onvolledig=onvolledig)
    assert total == 1
    assert len(rows) == 1
    assert onvolledig == []


def test_volledig_bestand_levert_geen_enkele_melding():
    onvolledig: list = []
    parse_csv_bytes(_csv(VOLLEDIG, VOLLEDIG), "f.csv", onvolledig=onvolledig)
    assert onvolledig == []


def test_onvolledig_blijft_optioneel():
    """Bestaande aanroepers geven de lijst niet mee; dat mag niet breken."""
    headers, rows, total = parse_csv_bytes(_csv(TE_KORT), "f.csv")
    assert total == 1 and headers and rows


# ── de meldingen ────────────────────────────────────────────────────────────

VERPLICHTE_SLEUTELS = {"severity", "type", "field", "count", "message", "examples"}


def test_melding_volgt_het_contract_van_file_results_issues():
    onvolledig = [{"rij": 3, "ontbrekend": ["DateOfBirth", "Gender"]}]
    meldingen = onvolledige_rijen_naar_meldingen(onvolledig)
    assert len(meldingen) == 2          # één melding per ontbrekend veld
    for m in meldingen:
        assert VERPLICHTE_SLEUTELS.issubset(m.keys())
        assert m["severity"] == "error"
        assert m["type"] == "incomplete_row"
        assert m["count"] == 1
        assert m["examples"] == ["rij 3"]
    assert {m["field"] for m in meldingen} == {"DateOfBirth", "Gender"}


def test_melding_noemt_veld_en_rij_in_de_tekst():
    meldingen = onvolledige_rijen_naar_meldingen([{"rij": 7, "ontbrekend": ["Gender"]}])
    assert "Gender" in meldingen[0]["message"]
    assert meldingen[0]["examples"] == ["rij 7"]


def test_meerdere_rijen_worden_per_veld_samengevoegd():
    onvolledig = [
        {"rij": 3, "ontbrekend": ["Gender"]},
        {"rij": 5, "ontbrekend": ["Gender"]},
        {"rij": 5, "ontbrekend": ["DateOfBirth"]},
    ]
    per_veld = {m["field"]: m for m in onvolledige_rijen_naar_meldingen(onvolledig)}
    assert per_veld["Gender"]["count"] == 2
    assert per_veld["Gender"]["examples"] == ["rij 3", "rij 5"]
    assert per_veld["DateOfBirth"]["count"] == 1


# ── de injectie in het validatieresultaat ───────────────────────────────────

def test_injectie_hangt_de_melding_aan_het_juiste_bestand():
    result = {
        "file_results": [
            {"filename": "a.csv", "issues": []},
            {"filename": "b.csv", "issues": []},
        ],
        "summary": {"error_count": 0, "quality": 100, "completeness": 100},
    }
    toegevoegd = voeg_onvolledige_rijen_toe(
        result, {"b.csv": [{"rij": 3, "ontbrekend": ["Gender"]}]}
    )
    assert toegevoegd == 1
    assert result["file_results"][0]["issues"] == []
    assert result["file_results"][1]["issues"][0]["field"] == "Gender"


def test_injectie_telt_mee_in_de_kop_en_haalt_de_volle_score_eraf():
    result = {
        "file_results": [{"filename": "a.csv", "issues": []}],
        "summary": {"error_count": 2, "quality": 100, "completeness": 100},
    }
    voeg_onvolledige_rijen_toe(result, {"a.csv": [{"rij": 3, "ontbrekend": ["Gender"]}]})
    assert result["summary"]["error_count"] == 3
    assert result["summary"]["quality"] == 99


def test_injectie_zonder_bevindingen_laat_alles_ongemoeid():
    result = {
        "file_results": [{"filename": "a.csv", "issues": []}],
        "summary": {"error_count": 0, "quality": 100, "completeness": 100},
    }
    assert voeg_onvolledige_rijen_toe(result, {}) == 0
    assert result["summary"] == {"error_count": 0, "quality": 100, "completeness": 100}
    assert result["file_results"][0]["issues"] == []


def test_injectie_werkt_zonder_summary_zib_pad():
    """Het ZIB-pad telt fouten uit file_results en heeft geen summary."""
    result = {"file_results": [{"filename": "a.csv", "issues": []}], "score": 100}
    assert voeg_onvolledige_rijen_toe(result, {"a.csv": [{"rij": 3, "ontbrekend": ["X"]}]}) == 1
    assert result["file_results"][0]["issues"][0]["severity"] == "error"


# ── de route, end to end ────────────────────────────────────────────────────

def test_upload_geeft_200_met_melding_in_plaats_van_500(client):
    res = client.post(
        "/api/validate/upload",
        files=[("files", ("Profit_Employees.csv", io.BytesIO(_csv(VOLLEDIG, TE_KORT)), "text/csv"))],
        data={"source": "afas", "standard": "algemeen"},
    )
    assert res.status_code == 200, res.text[:400]
    antwoord = res.json()
    meldingen = [
        m
        for fr in antwoord.get("file_results", [])
        for m in fr.get("issues", [])
        if m.get("type") == "incomplete_row"
    ]
    assert meldingen, "verwachtte een incomplete_row-melding"
    assert all(m["severity"] == "error" for m in meldingen)
    assert any("rij 3" in m["examples"] for m in meldingen)


def test_upload_van_een_volledig_bestand_meldt_niets_nieuws(client):
    res = client.post(
        "/api/validate/upload",
        files=[("files", ("Profit_Employees.csv", io.BytesIO(_csv(VOLLEDIG, VOLLEDIG)), "text/csv"))],
        data={"source": "afas", "standard": "algemeen"},
    )
    assert res.status_code == 200, res.text[:400]
    soorten = [
        m.get("type")
        for fr in res.json().get("file_results", [])
        for m in fr.get("issues", [])
    ]
    assert "incomplete_row" not in soorten
