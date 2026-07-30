"""
Tests voor de AFAS GetConnector JSON-parser (parse_json_bytes) en de pariteit
met de XML-parser (parse_xml_bytes). Puur functioneel — geen DB of HTTP.
"""
from app.routers.validate import parse_json_bytes, parse_xml_bytes

JSON_ENVELOPE = b'''{
  "skip": 0, "take": 500,
  "rows": [
    {"EmployerId": "01", "Name": "EnYoi Zorg", "UnitId": 1,
     "Blocked": false, "EndDate": null, "ModifiedDate": "20200225",
     "StartDate": "2010-11-10T00:00:00Z", "FTE": 36.0}
  ]
}'''

XML_GETCONNECTOR = b'''<?xml version="1.0" encoding="UTF-8"?>
<Werkgevers><rows><row>
  <EmployerId>01</EmployerId><Name>EnYoi Zorg</Name><UnitId>1</UnitId>
  <Blocked>False</Blocked><EndDate nil="true"></EndDate><ModifiedDate>20200225</ModifiedDate>
  <StartDate>2010-11-10T00:00:00Z</StartDate><FTE>36.0</FTE>
</row></rows></Werkgevers>'''


def test_json_envelope_basic():
    headers, rows, _ = parse_json_bytes(JSON_ENVELOPE)
    assert headers[0] == "EmployerId"
    assert len(rows) == 1
    r = rows[0]
    assert r["Name"] == "EnYoi Zorg"
    assert r["UnitId"] == "1"            # number -> string
    assert r["Blocked"] == "False"       # bool -> "False" (AFAS-XML casing)
    assert r["EndDate"] == ""            # null -> ""
    assert r["ModifiedDate"] == "2020-02-25"          # YYYYMMDD genormaliseerd
    assert r["StartDate"] == "2010-11-10"             # ISO datetime -> datum
    assert r["FTE"] == "36.0"


def test_json_xml_parity():
    jh, jr, _ = parse_json_bytes(JSON_ENVELOPE)
    xh, xr, _ = parse_xml_bytes(XML_GETCONNECTOR)
    assert jr == xr                      # zelfde rijwaarden uit JSON en XML
    assert set(jh) == set(xh)


def test_json_plain_list():
    headers, rows, _ = parse_json_bytes(b'[{"A":"1"},{"A":"2","B":"x"}]')
    assert len(rows) == 2
    assert "B" in headers


def test_json_single_record():
    headers, rows, _ = parse_json_bytes(b'{"A":"1","B":"2"}')
    assert len(rows) == 1 and rows[0] == {"A": "1", "B": "2"}


def test_json_invalid():
    import pytest
    with pytest.raises(ValueError):
        parse_json_bytes(b'{not json')


def test_json_afas_leading_zero_number_tolerated():
    """AFAS Profit exporteert getallen soms met voorloopnul (bijv.
    "HouseNumber": 00) — strikt genomen ongeldige JSON. De parser repareert die
    ongequote getal-tokens en leest het bestand toch in, i.p.v. te klappen."""
    payload = b'[{"EmployeeId":"000153","HouseNumber": 00,"AddNumber": 007,"FTE": 0.67,"Mail":"a@b.nl"}]'
    headers, rows, _ = parse_json_bytes(payload)
    assert len(rows) == 1
    assert rows[0]["EmployeeId"] == "000153"   # gequote string blijft heel
    assert rows[0]["HouseNumber"] == "0"        # 00 -> 0
    assert rows[0]["AddNumber"] == "7"          # 007 -> 7
    assert rows[0]["FTE"] == "0.67"             # decimaal ongemoeid
    # echt kapotte JSON blijft een nette fout geven
    import pytest
    with pytest.raises(ValueError):
        parse_json_bytes(b'[{"a": }]')


def test_json_numeric_not_date_mangled():
    """AFAS levert personeelsnummer/BSN soms als getal. Een 8-cijferig getal mag
    NIET als YYYYMMDD-datum worden geïnterpreteerd (regressie: 010203040 -> 1020-30-40)."""
    import json as _json
    payload = _json.dumps([
        {"EmployeeId": 10203040, "BSN": 123456789, "FTE": 24.0, "HourPerWeek": 36},
    ]).encode()
    _, rows, _ = parse_json_bytes(payload)
    r = rows[0]
    assert r["EmployeeId"] == "10203040"      # geen 1020-30-40
    assert r["BSN"] == "123456789"            # 9-cijferig getal blijft heel
    assert r["FTE"] == "24.0"
    assert r["HourPerWeek"] == "36"
    # echte datum als string blijft wél genormaliseerd
    _, rows2, _ = parse_json_bytes(b'[{"StartDate":"20200225"}]')
    assert rows2[0]["StartDate"] == "2020-02-25"


def test_parser_telt_totaal_en_capt(monkeypatch):
    """Stap 0: parser geeft échte totaalcount terug en capt opslag (rij-cap zichtbaar)."""
    import json as _json
    from app.routers import validate as V
    big = _json.dumps({"rows": [{"A": str(i)} for i in range(50)]}).encode()
    headers, rows, total = V.parse_json_bytes(big, max_rows=10)
    assert total == 50          # echte aantal
    assert len(rows) == 10      # opslag gecapt
