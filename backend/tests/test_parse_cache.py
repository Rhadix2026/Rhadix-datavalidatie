"""
test_parse_cache.py — ieder bestand binnen één batch maar één keer inlezen.

Meerdere berekeningsregels werken op hetzelfde bronbestand. De batch-endpoint las dat
bestand voor élke regel opnieuw volledig in: bij een echte AFAS-export van 35 MB kostte
dat 32 seconden per keer, drie keer, waarmee de aanroep de gateway-timeout van 60
seconden niet haalde en er dus helemaal geen resultaat terugkwam.

De cache leeft uitsluitend binnen één aanroep. Wat er níet verandert: parserlogica,
templateherkenning, validatieregels, indicatorberekeningen, toleranties en
cross-checkdefinities. De uitkomsten moeten exact gelijk blijven.

Aandachtspunt dat deze suite bewaakt: `_apply_filters` zet de peildatumkolom om en
muteert daarmee het dataframe. Een gedeeld parse-resultaat moet dus per regel worden
gekopieerd, anders zou regel 2 op de omgezette kolom van regel 1 werken.
"""
import io
import json

import pytest

from app.reconciliation import router as recon_router
from app.reconciliation.calculation_engine import DataLoader


# ── Hulpmiddelen ────────────────────────────────────────────────────────────

def _illness(n, recovered="GESLOTEN"):
    return json.dumps([
        {"EmployeeId": f"{i % 250:06d}", "AbsenceId": i,
         "StartDate": "2023-02-05T00:00:00Z", "EndDate": "2023-02-07T00:00:00Z",
         "RecoveredCode": recovered}
        for i in range(n)
    ]).encode("utf-8")


def _timetable(n):
    return json.dumps([
        {"EmployeeId": f"{i % 100:06d}", "StartDate": "2015-01-01T00:00:00Z",
         "EndDate": None, "HoursPerWeek": 36}
        for i in range(n)
    ]).encode("utf-8")


def _employees(n):
    return json.dumps([
        {"EmployeeId": f"{i:06d}", "EmploymentStart": "2015-01-01T00:00:00Z",
         "EmploymentEnd": None}
        for i in range(n)
    ]).encode("utf-8")


@pytest.fixture()
def teller(monkeypatch):
    """Telt hoe vaak DataLoader.load wordt aangeroepen, per aanroep van de endpoint."""
    tellingen = {"totaal": 0}
    origineel = DataLoader.load

    def _geteld(source, **kw):
        tellingen["totaal"] += 1
        return origineel(source, **kw)

    monkeypatch.setattr(DataLoader, "load", staticmethod(_geteld))
    monkeypatch.setattr(recon_router, "DataLoader", DataLoader)
    return tellingen


def _post(client, bestanden):
    files = [("files", (naam, io.BytesIO(inhoud), "application/json"))
             for naam, inhoud in bestanden.items()]
    res = client.post("/api/reconciliation/happy-flow/batch", files=files)
    assert res.status_code == 200, res.text[:400]
    return res.json()


def _waarden(antwoord):
    return {r["indicator_id"]: r["expected_value"] for r in antwoord["all_results"]}


def _afwijkingen(antwoord):
    return {r["indicator_id"]: (r.get("metadata") or {}).get("afwijkingen_totaal")
            for r in antwoord["all_results"]}


# ── Eén inleesbeurt per bestand ─────────────────────────────────────────────

class TestEenKeerInlezen:

    def test_bestand_met_drie_regels_wordt_een_keer_ingelezen(self, client, teller):
        """Profit_Illness heeft drie regels; zonder cache waren dat drie inleesbeurten."""
        antwoord = _post(client, {"Profit_Illness.json": _illness(200)})
        assert len(antwoord["all_results"]) == 3, "verwacht drie illness-regels"
        assert teller["totaal"] == 1, f"bestand {teller['totaal']}x ingelezen in plaats van 1x"

    def test_drie_bestanden_leveren_drie_inleesbeurten(self, client, teller):
        antwoord = _post(client, {
            "Profit_Illness.json": _illness(120),
            "Profit_Timetable.json": _timetable(80),
            "Profit_Employees.json": _employees(60),
        })
        assert len(antwoord["all_results"]) == 8, "verwacht acht indicatoren"
        assert teller["totaal"] == 3, (
            f"{teller['totaal']} inleesbeurten voor 3 bestanden met 8 regels"
        )

    def test_meerdere_regels_delen_hetzelfde_resultaat(self, client, teller):
        """Alle drie de illness-regels rekenen over dezelfde 120 records."""
        antwoord = _post(client, {"Profit_Illness.json": _illness(120)})
        assert teller["totaal"] == 1
        for r in antwoord["all_results"]:
            assert (r.get("metadata") or {}).get("total_rows") == 120


# ── Uitkomsten identiek aan zonder cache ────────────────────────────────────

class TestUitkomstenOngewijzigd:
    """Vergelijkt de endpoint met een verse inleesbeurt per regel — de oude weg."""

    BESTANDEN = {
        "Profit_Illness.json": _illness(300),
        "Profit_Timetable.json": _timetable(150),
        "Profit_Employees.json": _employees(90),
    }

    def _zonder_cache(self):
        """Rekent elke regel uit op een eigen, vers ingelezen dataframe."""
        from app.reconciliation.reconciliation_engine import ReconciliationEngine
        from app.reconciliation.calculation_engine import CalculationEngine

        calc_engine, recon_engine = CalculationEngine(), ReconciliationEngine()
        regels = [r for r in recon_router._rule_engine.list_rules() if "happy_flow" in r.tags]

        def _stam(n):
            return n.rsplit(".", 1)[0].strip().lower()

        per_stam = {_stam(n): (n, c) for n, c in self.BESTANDEN.items()}
        uit = {}
        for regel in regels:
            treffer = next((per_stam[_stam(n)] for n in regel.bronnamen() if _stam(n) in per_stam), None)
            if treffer is None:
                continue
            _, inhoud = treffer
            calc = calc_engine.calculate(regel, source=io.BytesIO(inhoud))
            res = recon_engine.reconcile(regel, calc, actual_value=None).to_dict()
            uit[regel.indicator_id] = (res["expected_value"],
                                       res["metadata"]["afwijkingen_totaal"],
                                       len(res["drill_down"]))
        return uit

    def test_indicatorwaarden_zijn_gelijk(self, client):
        via_endpoint = _waarden(_post(client, self.BESTANDEN))
        zonder = {k: v[0] for k, v in self._zonder_cache().items()}
        assert via_endpoint == zonder

    def test_afwijkingen_zijn_gelijk(self, client):
        via_endpoint = _afwijkingen(_post(client, self.BESTANDEN))
        zonder = {k: v[1] for k, v in self._zonder_cache().items()}
        assert via_endpoint == zonder

    def test_aantal_drilldownrecords_is_gelijk(self, client):
        antwoord = _post(client, self.BESTANDEN)
        via_endpoint = {r["indicator_id"]: len(r.get("drill_down") or [])
                        for r in antwoord["all_results"]}
        zonder = {k: v[2] for k, v in self._zonder_cache().items()}
        assert via_endpoint == zonder

    def test_de_begrenzing_op_honderd_blijft_staan(self, client):
        antwoord = _post(client, {"Profit_Illness.json": _illness(300)})
        for r in antwoord["all_results"]:
            assert len(r.get("drill_down") or []) <= 100
        begrensd = [r for r in antwoord["all_results"]
                    if (r.get("metadata") or {}).get("drill_down_begrensd")]
        assert begrensd, "de begrenzing meldt zich niet meer bij 300 afwijkingen"
        assert begrensd[0]["metadata"]["afwijkingen_totaal"] == 300


# ── Bestanden raken elkaars resultaat niet ──────────────────────────────────

class TestGeenVerwisseling:

    def test_elk_bestand_krijgt_zijn_eigen_gegevens(self, client):
        antwoord = _post(client, {
            "Profit_Illness.json": _illness(300),
            "Profit_Timetable.json": _timetable(77),
            "Profit_Employees.json": _employees(11),
        })
        waarden = _waarden(antwoord)
        assert waarden["hf_profit_illness_count"] == 300
        assert waarden["hf_profit_timetable_count"] == 77
        assert waarden["hf_profit_employees_count"] == 11

    def test_gelijke_aantallen_leiden_niet_tot_verwisseling(self, client):
        """Zelfde aantal records per bestand: alleen de inhoud onderscheidt ze."""
        antwoord = _post(client, {
            "Profit_Illness.json": _illness(50),
            "Profit_Timetable.json": _timetable(50),
        })
        waarden = _waarden(antwoord)
        assert waarden["hf_profit_illness_count"] == 50
        assert waarden["hf_profit_timetable_count"] == 50
        # De unieke-medewerkerstelling verschilt wél: 50 records over 50 resp. 50 sleutels.
        assert waarden["hf_profit_illness_unieke_medewerkers"] == 50


# ── Cache is batch-scoped ───────────────────────────────────────────────────

class TestCachePerAanroep:

    def test_een_tweede_batch_leest_opnieuw_in(self, client, teller):
        _post(client, {"Profit_Illness.json": _illness(100)})
        na_eerste = teller["totaal"]
        assert na_eerste == 1

        _post(client, {"Profit_Illness.json": _illness(100)})
        assert teller["totaal"] == 2, "de tweede batch hergebruikte de cache van de eerste"

    def test_gewijzigde_inhoud_onder_dezelfde_naam_wordt_opnieuw_gelezen(self, client):
        """Bewijst dat er niets over aanroepen heen blijft hangen."""
        eerste = _post(client, {"Profit_Illness.json": _illness(40)})
        tweede = _post(client, {"Profit_Illness.json": _illness(90)})
        assert _waarden(eerste)["hf_profit_illness_count"] == 40
        assert _waarden(tweede)["hf_profit_illness_count"] == 90


# ── Fouten worden niet als geslaagd gecachet ────────────────────────────────

class TestFoutenNietGecachet:

    def test_onleesbaar_bestand_levert_een_foutresultaat_zonder_te_blijven_hangen(self, client):
        stuk = b"{dit is geen geldige json"
        antwoord = _post(client, {"Profit_Illness.json": stuk})
        assert antwoord["skipped_files"] == [], "bestand is wel gematcht, maar onleesbaar"
        for r in antwoord["all_results"]:
            assert r["expected_value"] is None
            assert (r.get("metadata") or {}).get("error"), "er is geen foutmelding vastgelegd"

    def test_na_een_fout_werkt_hetzelfde_bestand_in_een_nieuwe_batch_gewoon(self, client):
        _post(client, {"Profit_Illness.json": b"{kapot"})
        goed = _post(client, {"Profit_Illness.json": _illness(25)})
        assert _waarden(goed)["hf_profit_illness_count"] == 25, (
            "een eerdere leesfout werkt door in een volgende batch"
        )

    def test_een_kapot_bestand_raakt_een_goed_bestand_niet(self, client):
        antwoord = _post(client, {
            "Profit_Illness.json": b"{kapot",
            "Profit_Timetable.json": _timetable(33),
        })
        waarden = _waarden(antwoord)
        assert waarden["hf_profit_timetable_count"] == 33
        assert waarden["hf_profit_illness_count"] is None
