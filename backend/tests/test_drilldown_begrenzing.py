"""
test_drilldown_begrenzing.py — detailrecords begrensd, berekening volledig.

Zodra de echte AFAS Profit-exports aan de regels werden gekoppeld, bleek de
drill-down onbegrensd: één verzuimbestand van 32.599 records leverde een antwoord van
ruim 100 MB en 139 seconden op, waarmee de aanroep in de gateway-timeout liep en er
dus helemaal géén resultaat meer terugkwam.

De begrenzing raakt uitsluitend de individuele voorbeeldrecords die naar de frontend
gaan. Wat NIET verandert:

  * elk record uit het bestand wordt verwerkt en beoordeeld;
  * aantallen, scores, afwijkingen en totalen gaan over de volledige dataset;
  * grenswaarden (tolerance) en inhoudelijke validatieregels zijn ongemoeid.

Bij een begrensd resultaat komt in de metadata terug: hoeveel records er zijn
gecontroleerd, hoeveel afwijkingen er in totaal zijn, hoeveel detailrecords er worden
getoond, en dát de weergave begrensd is.
"""
import io
import json

import pytest

from app.reconciliation.reconciliation_engine import (
    MAX_DRILL_DOWN,
    DifferenceAnalyzer,
    ReconciliationEngine,
)
from app.reconciliation.calculation_engine import CalcResult
from app.reconciliation.rule_engine import AggregationConfig, IndicatorRule


def _regel(**overrides) -> IndicatorRule:
    basis = dict(
        indicator_id="test_telling",
        name="Testtelling",
        source_dataset="test.csv",
        aggregation=AggregationConfig(function="count", field="EmployeeId"),
    )
    basis.update(overrides)
    return IndicatorRule(**basis)


def _records(n, vanaf=0):
    return [{"EmployeeId": f"{i:06d}", "AbsenceId": i} for i in range(vanaf, vanaf + n)]


# ── De analyzer zelf ────────────────────────────────────────────────────────

class TestBegrenzingVanDetailrecords:

    def test_32599_afwijkingen_blijven_32599(self):
        """De maat waar het om begonnen is: het echte verzuimbestand."""
        uitgesloten = _records(32_599)
        issues, totalen = DifferenceAnalyzer.analyze([], uitgesloten, _regel())

        assert totalen["afwijkingen_totaal"] == 32_599, "de telling is meebegrensd"
        assert totalen["records_gecontroleerd"] == 32_599
        assert len(issues) == 100, "er worden meer dan 100 detailrecords teruggegeven"
        assert totalen["drill_down_getoond"] == 100
        assert totalen["drill_down_begrensd"] is True
        assert totalen["drill_down_maximum"] == 100

    def test_onder_de_grens_wordt_niets_weggelaten(self):
        issues, totalen = DifferenceAnalyzer.analyze([], _records(42), _regel())
        assert totalen["afwijkingen_totaal"] == 42
        assert len(issues) == 42
        assert totalen["drill_down_begrensd"] is False

    def test_precies_op_de_grens_is_niet_begrensd(self):
        issues, totalen = DifferenceAnalyzer.analyze([], _records(MAX_DRILL_DOWN), _regel())
        assert len(issues) == MAX_DRILL_DOWN
        assert totalen["afwijkingen_totaal"] == MAX_DRILL_DOWN
        assert totalen["drill_down_begrensd"] is False

    def test_eentje_over_de_grens_is_wel_begrensd(self):
        issues, totalen = DifferenceAnalyzer.analyze([], _records(MAX_DRILL_DOWN + 1), _regel())
        assert len(issues) == MAX_DRILL_DOWN
        assert totalen["afwijkingen_totaal"] == MAX_DRILL_DOWN + 1
        assert totalen["drill_down_begrensd"] is True

    def test_zonder_afwijkingen_geen_detailrecords(self):
        issues, totalen = DifferenceAnalyzer.analyze(_records(500), [], _regel())
        assert issues == []
        assert totalen["afwijkingen_totaal"] == 0
        assert totalen["records_gecontroleerd"] == 500
        assert totalen["drill_down_begrensd"] is False

    def test_alle_records_worden_beoordeeld(self):
        """Ook records voorbij de grens tellen mee — alleen hun detail komt niet terug."""
        issues, totalen = DifferenceAnalyzer.analyze([], _records(5_000), _regel())
        assert totalen["records_gecontroleerd"] == 5_000
        assert totalen["afwijkingen_totaal"] == 5_000
        assert len(issues) == 100

    def test_de_grens_is_instelbaar_maar_verandert_de_telling_niet(self):
        issues, totalen = DifferenceAnalyzer.analyze([], _records(1_000), _regel(), maximum=10)
        assert len(issues) == 10
        assert totalen["afwijkingen_totaal"] == 1_000


# ── Via reconcile(): komt het in de metadata terecht? ───────────────────────

class TestMetadataBijBegrenzing:

    def _resultaat(self, aantal):
        calc = CalcResult(
            indicator_id="test_telling",
            expected_value=float(aantal),
            record_count=aantal,
            included_records=[],
            excluded_records=_records(aantal),
            metadata={"total_rows": aantal, "peildatum": None, "source_dataset": "test.csv"},
        )
        return ReconciliationEngine().reconcile(_regel(), calc, actual_value=None)

    def test_metadata_bevat_de_vier_gevraagde_gegevens(self):
        res = self._resultaat(32_599).to_dict()
        m = res["metadata"]
        assert m["records_gecontroleerd"] == 32_599
        assert m["afwijkingen_totaal"] == 32_599
        assert m["drill_down_getoond"] == 100
        assert m["drill_down_begrensd"] is True

    def test_de_indicatorwaarde_blijft_de_volledige_dataset(self):
        res = self._resultaat(32_599).to_dict()
        assert res["expected_value"] == 32_599.0, "de waarde is meebegrensd"
        assert res["metadata"]["record_count"] == 32_599
        assert res["metadata"]["total_rows"] == 32_599

    def test_drill_down_in_de_response_is_begrensd(self):
        res = self._resultaat(32_599).to_dict()
        assert len(res["drill_down"]) == 100

    def test_grenswaarden_zijn_ongemoeid(self):
        res = self._resultaat(500).to_dict()
        assert "tolerance" in res["metadata"]
        assert res["metadata"]["tolerance"] == {"absolute": 0.0, "percentage": 0.0}


# ── End-to-end via de batch-endpoint ────────────────────────────────────────

class TestBatchEndpointBegrensd:
    """Met een verzuimbestand op ware grootte, via de echte endpoint."""

    AANTAL = 32_599

    def _bestand(self):
        # RecoveredCode is nodig omdat de regel 'lopende verzuimmeldingen' daarop
        # filtert (eq OPEN). Alles op 'GESLOTEN' zetten laat die regel elk record
        # uitsluiten — precies de situatie waarin de drill-down oploopt tot 32.599.
        records = [
            {"EmployeeId": f"{i % 2500:06d}", "AbsenceId": i,
             "StartDate": "2023-02-05T00:00:00Z", "EndDate": "2023-02-07T00:00:00Z",
             "RecoveredCode": "GESLOTEN"}
            for i in range(self.AANTAL)
        ]
        return json.dumps(records).encode("utf-8")

    _cache = {}

    @pytest.fixture()
    def antwoord(self, client):
        """Eén keer uitvoeren; het bestand van 32.599 records is te zwaar per test."""
        if "data" not in self._cache:
            files = [("files", ("Profit_Illness.json", io.BytesIO(self._bestand()), "application/json"))]
            res = client.post("/api/reconciliation/happy-flow/batch", files=files)
            assert res.status_code == 200, res.text[:400]
            self._cache["data"] = res.json()
        return self._cache["data"]

    def test_bestand_wordt_niet_overgeslagen(self, antwoord):
        assert antwoord["skipped_files"] == []

    def test_telling_gaat_over_de_volledige_dataset(self, antwoord):
        tel = [r for r in antwoord["all_results"] if r["indicator_id"] == "hf_profit_illness_count"]
        assert tel, "de telregel is niet gedraaid"
        assert tel[0]["expected_value"] == self.AANTAL
        assert tel[0]["record_count"] == self.AANTAL
        assert tel[0]["total_rows"] == self.AANTAL

    def test_unieke_medewerkers_klopt_over_de_volledige_dataset(self, antwoord):
        uniek = [r for r in antwoord["all_results"]
                 if r["indicator_id"] == "hf_profit_illness_unieke_medewerkers"]
        assert uniek and uniek[0]["expected_value"] == 2500

    def test_geen_enkele_indicator_geeft_meer_dan_honderd_detailrecords(self, antwoord):
        for r in antwoord["all_results"]:
            assert len(r.get("drill_down") or []) <= MAX_DRILL_DOWN, r["indicator_id"]

    def test_begrensde_indicator_meldt_het_volledige_aantal(self, antwoord):
        begrensd = [r for r in antwoord["all_results"]
                    if (r.get("metadata") or {}).get("drill_down_begrensd")]
        assert begrensd, "geen enkele indicator meldt begrenzing bij 32.599 records"
        for r in begrensd:
            m = r["metadata"]
            assert m["afwijkingen_totaal"] > m["drill_down_getoond"]
            assert m["drill_down_getoond"] == MAX_DRILL_DOWN
            assert m["records_gecontroleerd"] == self.AANTAL

    def test_het_antwoord_blijft_klein(self, antwoord):
        """Zonder begrenzing liep dit op tot ruim 100 MB en een gateway-timeout."""
        omvang = len(json.dumps(antwoord).encode("utf-8"))
        assert omvang < 2_000_000, f"antwoord is {omvang} bytes"
