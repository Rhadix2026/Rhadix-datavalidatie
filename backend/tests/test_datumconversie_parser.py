"""
test_datumconversie_parser.py — snellere datumconversie, identieke uitkomst.

De AFAS-parsers riepen `pd.to_datetime` aan per lósse waarde. Dat is een vectorised
functie: per scalaire aanroep zet pandas een array op, bouwt een Index en raadt bij een
ISO-datum het formaat met dateutil. Gemeten op een echte export kostte dat 260 µs per
ISO-waarde; 194.614 datumwaarden in één bestand werden zo 31,9 van de 32,6 seconden
parsetijd.

Nu: `pd.Timestamp` (scalair, ~1,8 µs) met een memo per parse-aanroep, omdat datumwaarden
sterk herhalen.

Deze suite bewaakt de enige eis die telt: **dezelfde invoer levert exact dezelfde
genormaliseerde data op**. De oude conversie staat hieronder als referentie, zodat oud en
nieuw regel voor regel vergeleken kunnen worden.
"""
import io
import json

import pandas as pd
import pytest

from app.reconciliation.calculation_engine import (
    _AFAS_DATE_COMPACT,
    _AFAS_DATETIME_ISO,
    _datumomzetters,
    _parse_afas_json,
    _parse_afas_xml,
)


# ── De oude implementatie, letterlijk, als referentie ───────────────────────

def _oud_compact(s):
    try:
        return pd.to_datetime(s, format="%Y%m%d")
    except Exception:
        return s


def _oud_iso(s):
    try:
        return pd.to_datetime(s)
    except Exception:
        return s


def _oud_json(source: io.BytesIO) -> pd.DataFrame:
    """De normalisatielus zoals hij was, met pd.to_datetime per waarde."""
    source.seek(0)
    data = json.loads(source.read().decode("utf-8-sig", errors="replace"))
    records = data if isinstance(data, list) else (data.get("rows") or [data])
    rows = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        row = {}
        for k, v in rec.items():
            if v is None or (isinstance(v, str) and v.strip() == ""):
                row[k] = None
            elif isinstance(v, str):
                s = v.strip()
                if _AFAS_DATE_COMPACT.match(s):
                    row[k] = _oud_compact(s)
                elif _AFAS_DATETIME_ISO.match(s):
                    row[k] = _oud_iso(s)
                else:
                    row[k] = s
            else:
                row[k] = v
        if row:
            rows.append(row)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ── Waarde-voor-waarde gelijk ───────────────────────────────────────────────

# Representatieve waarden uit de echte AFAS Profit-exports, plus de randgevallen.
COMPACTE_WAARDEN = ["20200303", "19750102", "20240229", "20261231", "18000101"]
ISO_WAARDEN = [
    "2023-02-05T00:00:00Z", "2023-02-07T23:59:00Z", "2015-01-01T00:00:00Z",
    "2026-04-19T00:00:00", "1975-11-02T00:00:00Z", "2024-05-01T12:34:56Z",
]
ONPARSEERBAAR_COMPACT = ["99999999", "00000000", "20261332"]
ONPARSEERBAAR_ISO = ["2026-13-45T00:00:00", "2026-02-30T00:00:00Z"]


class TestWaardeVoorWaarde:

    @pytest.mark.parametrize("waarde", COMPACTE_WAARDEN)
    def test_compacte_datum_identiek(self, waarde):
        compact, _ = _datumomzetters()
        nieuw, oud = compact(waarde), _oud_compact(waarde)
        assert nieuw == oud
        assert type(nieuw) is type(oud)

    @pytest.mark.parametrize("waarde", ISO_WAARDEN)
    def test_iso_datum_identiek(self, waarde):
        _, iso = _datumomzetters()
        nieuw, oud = iso(waarde), _oud_iso(waarde)
        assert nieuw == oud
        assert type(nieuw) is type(oud)

    @pytest.mark.parametrize("waarde", ONPARSEERBAAR_COMPACT)
    def test_onparseerbare_compacte_waarde_valt_terug_op_de_tekst(self, waarde):
        compact, _ = _datumomzetters()
        nieuw, oud = compact(waarde), _oud_compact(waarde)
        assert nieuw == oud == waarde
        assert isinstance(nieuw, str)

    @pytest.mark.parametrize("waarde", ONPARSEERBAAR_ISO)
    def test_onparseerbare_iso_waarde_valt_terug_op_de_tekst(self, waarde):
        _, iso = _datumomzetters()
        nieuw, oud = iso(waarde), _oud_iso(waarde)
        assert nieuw == oud == waarde
        assert isinstance(nieuw, str)

    def test_herhaalde_waarde_geeft_hetzelfde_resultaat(self):
        """De memo mag de uitkomst niet veranderen bij de tweede aanroep."""
        _, iso = _datumomzetters()
        eerste = iso("2023-02-05T00:00:00Z")
        tweede = iso("2023-02-05T00:00:00Z")
        assert eerste == tweede == _oud_iso("2023-02-05T00:00:00Z")

    def test_onparseerbare_waarde_wordt_ook_onthouden(self):
        compact, _ = _datumomzetters()
        assert compact("99999999") == "99999999"
        assert compact("99999999") == "99999999"


# ── De memo blijft binnen één parse-aanroep ─────────────────────────────────

class TestMemoIsGeisoleerd:

    def test_elke_aanroep_krijgt_een_eigen_memo(self):
        c1, i1 = _datumomzetters()
        c2, i2 = _datumomzetters()
        assert c1 is not c2 and i1 is not i2
        # Beide leveren dezelfde uitkomst, los van elkaar.
        assert i1("2015-01-01T00:00:00Z") == i2("2015-01-01T00:00:00Z")

    def test_de_memo_lekt_niet_tussen_bestanden(self):
        """Twee bestanden na elkaar: het tweede krijgt zijn eigen waarden."""
        een = json.dumps([{"D": "2015-01-01T00:00:00Z"}]).encode()
        twee = json.dumps([{"D": "2020-06-30T00:00:00Z"}]).encode()
        df1 = _parse_afas_json(io.BytesIO(een))
        df2 = _parse_afas_json(io.BytesIO(twee))
        assert df1["D"].iloc[0] == pd.Timestamp("2015-01-01T00:00:00Z")
        assert df2["D"].iloc[0] == pd.Timestamp("2020-06-30T00:00:00Z")

    def test_dezelfde_waarde_in_twee_kolommen_blijft_correct(self):
        inhoud = json.dumps([{"Start": "2015-01-01T00:00:00Z",
                              "Eind": "2015-01-01T00:00:00Z",
                              "Ander": "2019-09-09T00:00:00Z"}]).encode()
        df = _parse_afas_json(io.BytesIO(inhoud))
        assert df["Start"].iloc[0] == df["Eind"].iloc[0] == pd.Timestamp("2015-01-01T00:00:00Z")
        assert df["Ander"].iloc[0] == pd.Timestamp("2019-09-09T00:00:00Z")


# ── Gouden test: dezelfde DataFrame ─────────────────────────────────────────

MENGELMOES = [
    {"EmployeeId": "000153", "BSN": 132852196, "DateOfBirth": "199-02-23T00:00:00Z",
     "StartDate": "2023-02-05T00:00:00Z", "EndDate": None, "Compact": "20200303",
     "Leeg": "", "Tekst": "Specialist", "Getal": 36, "Bool": True, "Kapot": "99999999"},
    {"EmployeeId": "000154", "BSN": 111222333, "DateOfBirth": "1975-11-02T00:00:00Z",
     "StartDate": "2023-02-05T00:00:00Z", "EndDate": "2024-01-01T00:00:00Z",
     "Compact": "20200303", "Leeg": None, "Tekst": "Vrijwilliger", "Getal": 24.5,
     "Bool": False, "Kapot": "2026-13-45T00:00:00"},
]


class TestGoudenTest:

    @pytest.fixture()
    def dfs(self):
        rauw = json.dumps(MENGELMOES).encode()
        return _parse_afas_json(io.BytesIO(rauw)), _oud_json(io.BytesIO(rauw))

    def test_zelfde_kolommen_in_dezelfde_volgorde(self, dfs):
        nieuw, oud = dfs
        assert list(nieuw.columns) == list(oud.columns)

    def test_zelfde_dtypes(self, dfs):
        nieuw, oud = dfs
        assert nieuw.dtypes.to_dict() == oud.dtypes.to_dict()

    def test_zelfde_waarden(self, dfs):
        nieuw, oud = dfs
        pd.testing.assert_frame_equal(nieuw, oud)

    def test_de_randgevallen_gedragen_zich_zoals_voorheen(self, dfs):
        nieuw, _ = dfs
        # Jaar van drie cijfers matcht de ISO-regex niet: blijft tekst.
        assert nieuw["DateOfBirth"].iloc[0] == "199-02-23T00:00:00Z"
        # Lege string en null worden allebei None.
        assert nieuw["Leeg"].iloc[0] is None and nieuw["Leeg"].iloc[1] is None
        # Onparseerbare datums vallen terug op de tekst.
        assert nieuw["Kapot"].iloc[0] == "99999999"
        assert nieuw["Kapot"].iloc[1] == "2026-13-45T00:00:00"
        # Getallen en booleans behouden hun waarde (pandas maakt er numpy-typen van,
        # net als voorheen — de gouden test hierboven borgt de dtypes).
        assert nieuw["Getal"].iloc[0] == 36
        assert bool(nieuw["Bool"].iloc[1]) is False


# ── XML volgt dezelfde weg ──────────────────────────────────────────────────

XML = b"""<?xml version="1.0" encoding="utf-8"?>
<Profit_Employees>
  <Employee><EmployeeId>000153</EmployeeId><DateOfBirth>20200303</DateOfBirth>
    <StartDate>2023-02-05T00:00:00Z</StartDate><EndDate nil="true"/>
    <Naam>Anna</Naam><Kapot>99999999</Kapot></Employee>
  <Employee><EmployeeId>000154</EmployeeId><DateOfBirth>19751102</DateOfBirth>
    <StartDate>2023-02-05T00:00:00Z</StartDate><EndDate></EndDate>
    <Naam>Jeroen</Naam><Kapot>2026-13-45T00:00:00</Kapot></Employee>
</Profit_Employees>"""


class TestXmlOngewijzigd:

    @pytest.fixture()
    def df(self):
        return _parse_afas_xml(io.BytesIO(XML))

    def test_datums_zijn_omgezet(self, df):
        assert df["DateOfBirth"].iloc[0] == pd.Timestamp("2020-03-03")
        assert df["StartDate"].iloc[0] == pd.Timestamp("2023-02-05T00:00:00Z")

    def test_lege_en_nil_elementen_worden_none(self, df):
        assert df["EndDate"].iloc[0] is None
        assert df["EndDate"].iloc[1] is None

    def test_onparseerbare_waarden_blijven_tekst(self, df):
        assert df["Kapot"].iloc[0] == "99999999"
        assert df["Kapot"].iloc[1] == "2026-13-45T00:00:00"

    def test_gelijk_aan_de_oude_conversie(self, df):
        """Elke datumcel komt overeen met wat pd.to_datetime zou hebben opgeleverd."""
        assert df["DateOfBirth"].iloc[0] == _oud_compact("20200303")
        assert df["DateOfBirth"].iloc[1] == _oud_compact("19751102")
        assert df["StartDate"].iloc[0] == _oud_iso("2023-02-05T00:00:00Z")


# ── CSV blijft buiten schot ─────────────────────────────────────────────────

class TestCsvOngewijzigd:

    def test_csv_gaat_niet_door_de_afas_parser(self):
        from app.reconciliation.calculation_engine import DataLoader
        csv = b"EmployeeId,StartDate\n000153,2023-02-05\n000154,2023-02-06\n"
        df = DataLoader.load(io.BytesIO(csv))
        # pd.read_csv laat de kolom als tekst staan; dat gedrag is ongewijzigd.
        assert list(df.columns) == ["EmployeeId", "StartDate"]
        assert df["StartDate"].iloc[0] == "2023-02-05"
