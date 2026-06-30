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


def test_parser_telt_totaal_en_capt(monkeypatch):
    """Stap 0: parser geeft échte totaalcount terug en capt opslag (rij-cap zichtbaar)."""
    import json as _json
    from app.routers import validate as V
    big = _json.dumps({"rows": [{"A": str(i)} for i in range(50)]}).encode()
    headers, rows, total = V.parse_json_bytes(big, max_rows=10)
    assert total == 50          # echte aantal
    assert len(rows) == 10      # opslag gecapt
