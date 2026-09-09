"""
test_profit_connector_matching.py — echte AFAS Profit-connectorbestanden koppelen.

De happy-flow-regels koppelen een bestand aan een berekeningsregel op de bestandsstam
(de naam zonder extensie). De AFAS Profit-regels droegen als bronnaam uitsluitend de
voorbeeldbestanden — `Profit_Employees_150_voorbeeld.xml` — terwijl een echte export van
de GET-connector `Profit_Employees.json` heet. Die stammen zijn ongelijk, dus alle echte
connectorbestanden belandden in `skipped_files` en de cross-checks kregen niets te
rekenen.

Een regel draagt nu naast `source_dataset` ook `source_aliases`. Omdat de match op de
stam gaat, dekt één alias zonder extensie de export als XML, JSON én CSV.

Deze suite bewaakt drie dingen:
  * de echte connectornamen koppelen aan de bestaande regels, in elk formaat;
  * de voorbeeldbestanden blijven koppelen — de herkenning mag niet verslechteren;
  * bestanden waarvoor geen regel bestaat blijven netjes in `skipped_files`.

De inhoudelijke cross-checks zijn hier bewust niet gewijzigd.
"""
import io
import json

import pytest

from app.reconciliation.rule_engine import RuleEngine

# De namen zoals de AFAS GET-connector ze uitlevert. Bewust géén extensie in de
# verwachting: de match hoort formaat-onafhankelijk te zijn.
CONNECTOR_MET_REGELS = ["Profit_Employees", "Profit_Illness", "Profit_Timetable"]

# Bestanden uit dezelfde export waarvoor (nog) geen berekeningsregels bestaan.
CONNECTOR_ZONDER_REGELS = ["Profit_Employers", "Profit_Functions", "Profit_OrganizationChart"]

VOORBEELDBESTANDEN = [
    "Profit_Employees_150_voorbeeld.xml",
    "Profit_Employees_basic_150_voorbeeld.xml",
    "Profit_Illness_150_voorbeeld.xml",
    "Profit_Timetable_150_voorbeeld.xml",
]


def _stem(naam: str) -> str:
    """Zelfde normalisatie als de batch-endpoint gebruikt."""
    return naam.rsplit(".", 1)[0].strip().lower()


@pytest.fixture(scope="module")
def happy_flow_regels():
    from pathlib import Path
    engine = RuleEngine()
    map_ = Path(__file__).resolve().parents[1] / "app" / "reconciliation" / "rules"
    for pad in sorted(map_.glob("*.yaml")):
        engine.load_file(pad)
    regels = [r for r in engine.list_rules() if "happy_flow" in r.tags]
    assert regels, "geen happy-flow-regels geladen"
    return regels


def _regels_voor(regels, bestandsnaam):
    """Welke regels matchen dit bestand, volgens dezelfde logica als de endpoint?"""
    doel = _stem(bestandsnaam)
    return [r for r in regels if any(_stem(n) == doel for n in r.bronnamen())]


# ── De echte connectornamen koppelen ────────────────────────────────────────

class TestEchteConnectorbestanden:

    @pytest.mark.parametrize("connector", CONNECTOR_MET_REGELS)
    @pytest.mark.parametrize("extensie", [".json", ".xml", ".csv"])
    def test_connectorbestand_koppelt_ongeacht_extensie(self, happy_flow_regels, connector, extensie):
        gevonden = _regels_voor(happy_flow_regels, connector + extensie)
        assert gevonden, f"{connector}{extensie} koppelt aan geen enkele regel"

    @pytest.mark.parametrize("connector", CONNECTOR_MET_REGELS)
    def test_koppeling_is_hoofdletterongevoelig(self, happy_flow_regels, connector):
        assert _regels_voor(happy_flow_regels, connector.lower() + ".json")
        assert _regels_voor(happy_flow_regels, connector.upper() + ".JSON")

    def test_de_zes_bestanden_uit_de_echte_export(self, happy_flow_regels):
        """Precies de set die de gebruiker aanbiedt: drie met regels, drie zonder."""
        met = [c for c in CONNECTOR_MET_REGELS if _regels_voor(happy_flow_regels, c + ".json")]
        zonder = [c for c in CONNECTOR_ZONDER_REGELS if not _regels_voor(happy_flow_regels, c + ".json")]
        assert met == CONNECTOR_MET_REGELS
        assert zonder == CONNECTOR_ZONDER_REGELS


# ── Bestaande herkenning blijft intact ──────────────────────────────────────

class TestGeenAchteruitgang:

    @pytest.mark.parametrize("voorbeeld", VOORBEELDBESTANDEN)
    def test_voorbeeldbestanden_koppelen_nog_steeds(self, happy_flow_regels, voorbeeld):
        assert _regels_voor(happy_flow_regels, voorbeeld), f"{voorbeeld} koppelt niet meer"

    @pytest.mark.parametrize("csv_bron", [
        "medewerker_afas_hrm.csv", "werkovereenkomst_afas_hrm.csv", "verzuim_afas_hrm.csv",
        "medewerker_ons.csv", "financieleboeking_afas_fin.csv", "grootboekrubriek_afas_fin.csv",
    ])
    def test_bestaande_csv_bronnen_koppelen_nog_steeds(self, happy_flow_regels, csv_bron):
        assert _regels_voor(happy_flow_regels, csv_bron), f"{csv_bron} koppelt niet meer"

    def test_elke_regel_heeft_een_primaire_bronnaam(self, happy_flow_regels):
        for r in happy_flow_regels:
            assert r.source_dataset, f"{r.indicator_id} mist source_dataset"
            assert r.bronnamen()[0] == r.source_dataset

    def test_aliassen_botsen_niet_met_een_andere_bron(self, happy_flow_regels):
        """Een alias mag niet dezelfde stam krijgen als de primaire naam van een andere bron."""
        primair = {_stem(r.source_dataset) for r in happy_flow_regels}
        for r in happy_flow_regels:
            for alias in r.source_aliases:
                assert _stem(alias) not in primair, (
                    f"alias {alias} van {r.indicator_id} botst met een bestaande bronnaam"
                )


# ── De batch-endpoint end-to-end ────────────────────────────────────────────

def _profit_json(records):
    return json.dumps(records).encode("utf-8")


class TestBatchEndpoint:
    """Draait de echte endpoint met bestanden die de connectornamen dragen."""

    BESTANDEN = {
        "Profit_Employees.json": [
            {"EmployeeId": "000153", "EmploymentStart": "2015-01-01T00:00:00Z", "EmploymentEnd": None},
            {"EmployeeId": "000154", "EmploymentStart": "2018-06-15T00:00:00Z", "EmploymentEnd": None},
            {"EmployeeId": "000155", "EmploymentStart": "2012-03-01T00:00:00Z",
             "EmploymentEnd": "2024-01-01T00:00:00Z"},
        ],
        "Profit_Illness.json": [
            {"EmployeeId": "000153", "AbsenceId": 1, "StartDate": "2023-02-05T00:00:00Z",
             "EndDate": "2023-02-07T00:00:00Z"},
            {"EmployeeId": "000154", "AbsenceId": 2, "StartDate": "2024-05-01T00:00:00Z",
             "EndDate": None},
        ],
        "Profit_Timetable.json": [
            {"EmployeeId": "000153", "StartDate": "2015-01-01T00:00:00Z", "EndDate": None,
             "HoursPerWeek": 36},
            {"EmployeeId": "000154", "StartDate": "2018-06-15T00:00:00Z", "EndDate": None,
             "HoursPerWeek": 24},
        ],
    }

    def _post(self, client, namen):
        files = [("files", (n, io.BytesIO(_profit_json(self.BESTANDEN[n])), "application/json"))
                 for n in namen]
        res = client.post("/api/reconciliation/happy-flow/batch", files=files)
        assert res.status_code == 200, res.text
        return res.json()

    def test_geen_enkel_ondersteund_bestand_wordt_overgeslagen(self, client):
        data = self._post(client, list(self.BESTANDEN))
        assert data["skipped_files"] == [], (
            f"ondersteunde bestanden overgeslagen: {data['skipped_files']}"
        )

    def test_er_komen_indicatorwaarden_terug(self, client):
        data = self._post(client, list(self.BESTANDEN))
        assert data["total_indicators"] > 0
        assert data["all_results"], "all_results is leeg"

    def test_elk_bestand_levert_ten_minste_een_indicator(self, client):
        data = self._post(client, list(self.BESTANDEN))
        per_bron = {r["source_dataset"] for r in data["all_results"]}
        assert len(per_bron) >= 3, f"te weinig bronnen gerekend: {per_bron}"

    def test_records_worden_daadwerkelijk_geteld(self, client):
        data = self._post(client, ["Profit_Employees.json"])
        tellingen = [r for r in data["all_results"] if r["indicator_id"] == "hf_profit_employees_count"]
        assert tellingen, "de telregel voor Profit_Employees is niet gedraaid"
        assert tellingen[0]["expected_value"] == 3, tellingen[0]

    def test_bestand_zonder_regels_blijft_overgeslagen(self, client):
        """Verwacht gedrag: waar geen regel voor is, wordt netjes gemeld."""
        files = [
            ("files", ("Profit_Employees.json", io.BytesIO(_profit_json(self.BESTANDEN["Profit_Employees.json"])), "application/json")),
            ("files", ("Profit_Employers.json", io.BytesIO(_profit_json([{"EmployerId": "01"}])), "application/json")),
        ]
        res = client.post("/api/reconciliation/happy-flow/batch", files=files)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["skipped_files"] == ["Profit_Employers.json"]
        assert data["all_results"], "de wél ondersteunde bron leverde niets op"
