"""
Regressietest: de reconciliatie/cross-check-engine moet JSON-bronnen aankunnen.
Voorheen kende calculation_engine.load() alleen CSV/XML/Excel — JSON viel door
naar pd.read_csv en brak. Nu is er een JSON-tak, en de happy-flow-batch matcht
op bestandsstam zodat een JSON-bron óók meedoet.
"""
import io
import json
from pathlib import Path

from app.reconciliation.calculation_engine import CalculationEngine, DataLoader
from app.reconciliation.rule_engine import RuleEngine

RULES_DIR = Path(__file__).resolve().parent.parent / "app" / "reconciliation" / "rules"

RECS = [
    {"medewerker_id": "1", "contract_status": "actief", "dienstverband_fte": 0.8, "contract_einddatum": "2025-12-31"},
    {"medewerker_id": "2", "contract_status": "actief", "dienstverband_fte": 1.0, "contract_einddatum": "2025-12-31"},
    {"medewerker_id": "3", "contract_status": "uit",    "dienstverband_fte": 1.0, "contract_einddatum": "2025-12-31"},
    {"medewerker_id": "4", "contract_status": "actief", "dienstverband_fte": 0.0, "contract_einddatum": "2025-12-31"},
]


def _csv_bytes():
    cols = list(RECS[0].keys())
    return (",".join(cols) + "\n" + "\n".join(
        ",".join(str(r[c]) for c in cols) for r in RECS)).encode()


def test_dataloader_parses_json():
    df = DataLoader.load(json.dumps(RECS).encode())
    assert len(df) == 4
    assert "medewerker_id" in df.columns
    # kale lijst én envelope leveren hetzelfde
    df2 = DataLoader.load(json.dumps({"skip": 0, "take": 9, "rows": RECS}).encode())
    assert len(df2) == 4


def _rule(indicator_id):
    eng = RuleEngine()
    eng.load_directory(RULES_DIR)
    for r in eng.list_rules():
        if r.indicator_id == indicator_id:
            return r
    return None


def test_happyflow_calc_json_equals_csv():
    rule = _rule("medewerker_count")
    assert rule is not None
    eng = CalculationEngine()
    calc_csv = eng.calculate(rule, source=io.BytesIO(_csv_bytes()))
    calc_json = eng.calculate(rule, source=io.BytesIO(json.dumps(RECS).encode()))
    # 2 actieve medewerkers met fte > 0 (id 1 en 2)
    assert calc_csv.expected_value == calc_json.expected_value == 2
