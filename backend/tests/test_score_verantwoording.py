"""
test_score_verantwoording.py — B-22 richting 1: verantwoording bij een score.

Legt drie dingen vast:

  1. Geen enkele bestaande scoreformule verandert. Dat is de harde eis: dit is
     transparantie, geen oplossing van B-22.
  2. Controles en bevindingen zijn gescheiden en worden niet verward. Eén
     bevinding kan meerdere afgekeurde controles bundelen, en een ontbrekend
     veld geeft een bevinding zonder uitgevoerde controles.
  3. De toelichting is neutraal en feitelijk: nergens de suggestie dat een score
     van 100 betekent dat de gegevens foutloos zijn.
"""
import io

import pytest

from app.services import score_accounting as acc
from app.services.algemeen_validator import validate_algemeen
from app.services.validator import validate_files

KOP = ["EmployeeId", "BSN", "DateOfBirth", "FirstName", "BirthName",
       "Gender", "EmploymentStart", "Mail"]
GOED = ["1001", "123456782", "1975-11-02", "Jeroen", "Bakker", "M", "2018-06-15", "j@example.org"]
KOP4 = ["EmployeeId", "BSN", "DateOfBirth", "Gender"]


def _inzet(kop, rijen, naam="Profit_Employees.csv"):
    return [{"filename": naam, "headers": kop, "rows": [dict(zip(kop, r)) for r in rijen]}]


# ── 1. de formules blijven ongemoeid ───────────────────────────────────────

def test_formules_onveranderd_alles_goed():
    r = validate_algemeen(_inzet(KOP, [GOED]))
    s = r["summary"]
    assert (s["completeness"], s["quality"], s["rhadix_index"]) == (100, 100, 100)


def test_formules_onveranderd_vier_van_acht_velden():
    """Het B-17-geval: vier verplichte velden ontbreken."""
    r = validate_algemeen(_inzet(KOP4, [["1001", "123456782", "1975-11-02", "M"]]))
    s = r["summary"]
    assert (s["completeness"], s["quality"], s["rhadix_index"]) == (50, 100, 50)


def test_formules_onveranderd_ongeldige_bsn():
    slecht = list(GOED); slecht[1] = "1234567"
    r = validate_algemeen(_inzet(KOP, [GOED, slecht]))
    assert r["summary"]["quality"] == 94


# ── 2. het contract ────────────────────────────────────────────────────────

def test_score_version_noemt_versie_route_en_formule():
    r = validate_algemeen(_inzet(KOP, [GOED]))
    v = r["score_version"]
    assert v["version"] == acc.SCORE_VERSION
    assert v["path"] == "algemeen"
    assert "completeness" in v["formula"] and "quality" in v["formula"]


def test_contract_heeft_dezelfde_sleutels_op_elke_route():
    verwacht = {"checks", "findings", "score_covers_all_findings", "explanation"}
    a = validate_algemeen(_inzet(KOP, [GOED]))["score_accounting"]
    k = validate_files([{"filename": "x.csv", "headers": ["a"], "rows": [{"a": "1"}]}])["score_accounting"]
    assert verwacht.issubset(a)
    assert verwacht.issubset(k)
    assert set(a["checks"]) == set(k["checks"])
    assert set(a["findings"]) == set(k["findings"])


def test_kikv_route_telt_geen_controles_maar_wel_bevindingen():
    r = validate_files([{"filename": "x.csv", "headers": ["a"], "rows": [{"a": "1"}]}])
    a = r["score_accounting"]
    assert a["checks"]["executed"] is None          # deze route telt geen waardecontroles
    assert a["checks"]["failed"] is None
    assert r["score_version"]["path"] == "kikv"
    assert "fouten x 5" in r["score_version"]["formula"]


# ── 3. controles en bevindingen zijn niet hetzelfde getal ──────────────────

def test_een_bevinding_bundelt_meerdere_afgekeurde_controles():
    """Vijf rijen met dezelfde fout: één bevinding, vijf afgekeurde controles."""
    slecht = list(GOED); slecht[1] = "1234567"
    r = validate_algemeen(_inzet(KOP, [slecht] * 5))
    a = r["score_accounting"]
    bevindingen = a["findings"]["in_score"]["errors"]
    assert bevindingen == 1                          # één bevinding
    assert a["checks"]["failed"] == 5                # vijf afgekeurde controles
    assert bevindingen != a["checks"]["failed"]


def test_ontbrekend_veld_geeft_bevinding_zonder_uitgevoerde_controles():
    r = validate_algemeen(_inzet(KOP4, [["1001", "123456782", "1975-11-02", "M"]]))
    a = r["score_accounting"]
    assert a["findings"]["outside_score"]["errors"] == 4
    assert a["findings"]["outside_score"]["by_type"] == {"missing_field": 4}
    assert a["checks"]["skipped"]["fields_absent"] == 4
    # op die vier velden is niets gecontroleerd
    assert a["checks"]["executed"] == 4              # alleen de vier aanwezige velden
    assert a["checks"]["failed"] == 0


def test_de_toelichting_waarschuwt_tegen_verwarring():
    a = validate_algemeen(_inzet(KOP, [GOED]))["score_accounting"]
    assert "geen vergelijkbare aantallen" in a["checks"]["note"]


def test_lege_waarden_worden_geteld_als_overgeslagen():
    leeg = list(GOED); leeg[7] = ""
    a = validate_algemeen(_inzet(KOP, [leeg]))["score_accounting"]
    assert a["checks"]["skipped"]["empty_values"] == 1
    # en veranderen de score niet
    assert validate_algemeen(_inzet(KOP, [leeg]))["summary"]["quality"] == 100


def test_bestanden_zonder_sjabloon_worden_geteld():
    inzet = _inzet(KOP, [GOED]) + [{"filename": "Onbekend.csv", "headers": ["a"], "rows": [{"a": "1"}]}]
    a = validate_algemeen(inzet)["score_accounting"]
    assert a["checks"]["skipped"]["files_without_template"] == 1


# ── 4. de toelichting is neutraal en feitelijk ─────────────────────────────

def test_toelichting_bij_bevindingen_buiten_de_score():
    r = validate_algemeen(_inzet(KOP4, [["1001", "123456782", "1975-11-02", "M"]]))
    a = r["score_accounting"]
    assert a["score_covers_all_findings"] is False
    assert a["explanation"] == (
        "Kwaliteitsscore 100 volgens berekening 2026.10. Daarnaast zijn 4 bevindingen "
        "vastgesteld die niet in deze score zijn verwerkt."
    )


def test_toelichting_bij_een_enkele_bevinding_is_enkelvoud():
    assert acc.toelichting("Kwaliteitsscore", 100, 1) == (
        "Kwaliteitsscore 100 volgens berekening 2026.10. Daarnaast is 1 bevinding "
        "vastgesteld die niet in deze score is verwerkt."
    )


def test_toelichting_belooft_nooit_foutloosheid():
    """De kern van de aanscherping: geen suggestie dat 100 'foutloos' betekent."""
    verboden = ["foutloos", "geen fouten", "volledig correct", "alles klopt", "perfect"]
    for buiten in (0, 1, 6):
        tekst = acc.toelichting("Kwaliteitsscore", 100, buiten).lower()
        for w in verboden:
            assert w not in tekst, f"{w!r} staat in: {tekst}"


def test_toelichting_zonder_bevindingen_buiten_de_score():
    a = validate_algemeen(_inzet(KOP, [GOED]))["score_accounting"]
    assert a["score_covers_all_findings"] is True
    assert "Alle vastgestelde bevindingen zijn in deze score verwerkt." in a["explanation"]


# ── 5. de route end-to-end, inclusief de meldingen van B-17 ───────────────

def _csv(*regels):
    return ("\n".join([";".join(KOP), *regels]) + "\n").encode("utf-8")


def test_route_verwerkt_onvolledige_rij_in_de_verantwoording(client):
    volledig = ";".join(GOED)
    te_kort = "1002;123456782"
    res = client.post(
        "/api/validate/upload",
        files=[("files", ("Profit_Employees.csv", io.BytesIO(_csv(volledig, te_kort)), "text/csv"))],
        data={"source": "afas", "standard": "algemeen"},
    )
    assert res.status_code == 200, res.text[:300]
    d = res.json()
    a = d["score_accounting"]
    buiten = a["findings"]["outside_score"]
    assert "incomplete_row" in buiten["by_type"], a
    assert a["score_covers_all_findings"] is False
    assert d["score_version"]["path"] == "algemeen"


def test_route_geeft_verantwoording_bij_een_volledig_bestand(client):
    res = client.post(
        "/api/validate/upload",
        files=[("files", ("Profit_Employees.csv", io.BytesIO(_csv(";".join(GOED))), "text/csv"))],
        data={"source": "afas", "standard": "algemeen"},
    )
    assert res.status_code == 200, res.text[:300]
    d = res.json()
    assert d["score_accounting"]["score_covers_all_findings"] is True
    assert d["summary"]["quality"] == 100
