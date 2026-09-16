"""
test_validatiemeldingen_contract.py — het contract van de validatiemeldingen.

De frontend toont fouten en waarschuwingen per bestand: uitklapbaar, met de melding,
het veld, het aantal en scrollbare voorbeelden. Dat scherm leunt volledig op de vorm van
`file_results[].issues` in de respons van `/api/validate/upload`.

Deze suite legt die vorm vast. Verdwijnt er een sleutel of verandert de structuur, dan
valt de detailweergave stil zonder dat er iets zichtbaar stukgaat — precies wat er sinds
3 augustus gebeurde, alleen toen door een routewijziging in de frontend.

Belangrijk: de meldingen komen uit `validate_algemeen`, dat werkt op headers en rijen.
De vorm is daarmee gelijk voor JSON, XML en CSV; de parser bepaalt alleen hoe headers en
rijen worden verkregen. Die gelijkheid wordt hieronder per formaat getoetst.
"""
import io
import json

import pytest

# Twee medewerkers, waarvan de eerste een BSN dat de elfproef niet haalt en een
# onbestaande geboortedatum — dezelfde soort fouten als in de echte AFAS-export.
KOLOMMEN = ["EmployeeId", "BSN", "DateOfBirth", "FirstName", "BirthName",
            "Gender", "EmploymentStart", "Mail"]
RIJEN = [
    ["1001", "1234567", "199-02-23", "Anna", "de Vries", "V", "2015-01-01", "a@example.org"],
    ["1002", "123456782", "1975-11-02", "Jeroen", "Bakker", "M", "2018-06-15", "j@example.org"],
]

VERPLICHTE_SLEUTELS = {"severity", "type", "field", "count", "message", "examples"}


def _csv() -> bytes:
    regels = [",".join(KOLOMMEN)] + [",".join(r) for r in RIJEN]
    return ("\n".join(regels) + "\n").encode("utf-8")


def _json() -> bytes:
    return json.dumps([dict(zip(KOLOMMEN, r)) for r in RIJEN]).encode("utf-8")


def _xml() -> bytes:
    velden = "".join(
        "<Employee>" + "".join(f"<{k}>{v}</{k}>" for k, v in zip(KOLOMMEN, r)) + "</Employee>"
        for r in RIJEN
    )
    return f'<?xml version="1.0" encoding="utf-8"?><Profit_Employees>{velden}</Profit_Employees>'.encode("utf-8")


FORMATEN = {
    "csv": ("medewerker_afas_hrm.csv", _csv(), "text/csv"),
    "json": ("Profit_Employees.json", _json(), "application/json"),
    "xml": ("Profit_Employees.xml", _xml(), "application/xml"),
}


def _upload(client, formaat):
    naam, inhoud, mime = FORMATEN[formaat]
    res = client.post(
        "/api/validate/upload",
        files=[("files", (naam, io.BytesIO(inhoud), mime))],
        data={"source": "afas", "standard": "algemeen"},
    )
    assert res.status_code == 200, res.text[:400]
    return res.json()


def _meldingen(antwoord):
    uit = []
    for bestand in antwoord.get("file_results", []):
        uit.extend(bestand.get("issues") or [])
    return uit


# ── De vorm van een melding ─────────────────────────────────────────────────

class TestVormVanDeMeldingen:

    @pytest.mark.parametrize("formaat", ["csv", "json", "xml"])
    def test_elke_melding_draagt_de_verplichte_sleutels(self, client, formaat):
        for m in _meldingen(_upload(client, formaat)):
            ontbreekt = VERPLICHTE_SLEUTELS - set(m)
            assert not ontbreekt, f"{formaat}: melding mist {ontbreekt} — {m}"

    @pytest.mark.parametrize("formaat", ["csv", "json", "xml"])
    def test_voorbeelden_dragen_rij_en_waarde(self, client, formaat):
        for m in _meldingen(_upload(client, formaat)):
            for v in m["examples"]:
                assert "row" in v and "value" in v, f"{formaat}: voorbeeld mist row/value — {v}"

    @pytest.mark.parametrize("formaat", ["csv", "json", "xml"])
    def test_severity_is_error_of_warning(self, client, formaat):
        for m in _meldingen(_upload(client, formaat)):
            assert m["severity"] in ("error", "warning"), m["severity"]

    @pytest.mark.parametrize("formaat", ["csv", "json", "xml"])
    def test_count_is_een_getal_en_minstens_een(self, client, formaat):
        for m in _meldingen(_upload(client, formaat)):
            assert isinstance(m["count"], int) and m["count"] >= 1

    @pytest.mark.parametrize("formaat", ["csv", "json", "xml"])
    def test_message_is_gevuld(self, client, formaat):
        for m in _meldingen(_upload(client, formaat)):
            assert isinstance(m["message"], str) and m["message"].strip()


# ── Dezelfde uitkomst voor JSON, XML en CSV ─────────────────────────────────

class TestFormatenGelijk:

    def _kern(self, antwoord):
        """Wat de weergave gebruikt, los van bestandsnaam en volgorde."""
        return sorted((m["severity"], m["type"], m["field"], m["count"])
                      for m in _meldingen(antwoord))

    def test_json_en_csv_geven_dezelfde_meldingen(self, client):
        assert self._kern(_upload(client, "json")) == self._kern(_upload(client, "csv"))

    def test_xml_en_csv_geven_dezelfde_meldingen(self, client):
        assert self._kern(_upload(client, "xml")) == self._kern(_upload(client, "csv"))

    @pytest.mark.parametrize("formaat", ["csv", "json", "xml"])
    def test_de_verwachte_twee_fouten_komen_terug(self, client, formaat):
        soorten = {(m["type"], m["field"]) for m in _meldingen(_upload(client, formaat))
                   if m["severity"] == "error"}
        assert ("invalid_bsn", "BSN") in soorten, f"{formaat}: BSN-fout ontbreekt"
        assert ("invalid_date", "DateOfBirth") in soorten, f"{formaat}: datumfout ontbreekt"


# ── Bestanden zonder meldingen ──────────────────────────────────────────────

class TestZonderMeldingen:

    def test_een_schoon_bestand_levert_een_lege_lijst(self, client):
        schoon = [dict(zip(KOLOMMEN, RIJEN[1]))]
        res = client.post(
            "/api/validate/upload",
            files=[("files", ("Profit_Employees.json",
                              io.BytesIO(json.dumps(schoon).encode()), "application/json"))],
            data={"source": "afas", "standard": "algemeen"},
        )
        assert res.status_code == 200, res.text[:300]
        bestanden = res.json()["file_results"]
        assert len(bestanden) == 1
        assert bestanden[0].get("issues") == [], bestanden[0].get("issues")

    def test_de_sleutel_issues_bestaat_altijd(self, client):
        """De frontend leest `issues` rechtstreeks; die mag niet ontbreken."""
        for formaat in ("csv", "json", "xml"):
            for bestand in _upload(client, formaat)["file_results"]:
                assert "issues" in bestand, f"{formaat}: {bestand.get('filename')} mist 'issues'"


# ── Het bestandsresultaat zelf ──────────────────────────────────────────────

class TestBestandsresultaat:
    """De kaart per bestand toont naam, label, rijen en scores."""

    @pytest.mark.parametrize("sleutel", ["filename", "label", "rows",
                                         "completeness", "quality", "rhadix_index"])
    def test_bestandsresultaat_draagt_de_weergavevelden(self, client, sleutel):
        for bestand in _upload(client, "json")["file_results"]:
            assert sleutel in bestand, f"{sleutel} ontbreekt in {bestand.get('filename')}"

    def test_alle_aangeboden_bestanden_komen_terug(self, client):
        antwoord = _upload(client, "json")
        assert len(antwoord["file_results"]) == 1
        assert antwoord["file_results"][0]["filename"] == "Profit_Employees.json"
