"""
Tests voor Slice 1 van de doelarchitectuur (Stap 1): het canonieke rijmodel en
de ingest-pipeline. Kern: de pipeline moet via `to_legacy_rows` EXACT dezelfde
rijen opleveren als de bestaande parsers - een verliesvrije omzetting, zodat de
validators ongewijzigd blijven werken. Puur functioneel; geen DB of HTTP.
"""
from app.routers.validate import parse_csv_bytes, parse_xml_bytes, parse_json_bytes
from app.services.ingest.canonical import CanonicalCell, CanonicalRow, CanonicalFile
from app.services.ingest.pipeline import to_canonical, ingest

CSV = b"Naam;Geboortedatum;BSN\nJan;1980-02-30;123456782\nPiet;22-04-1990;111222333\n"
XML = (b'<?xml version="1.0"?><Werkgevers><rows>'
       b'<row><EmployerId>01</EmployerId><Name>EnYoi</Name><EndDate nil="true"></EndDate></row>'
       b'<row><EmployerId>02</EmployerId><Name>Zorg</Name></row>'
       b'</rows></Werkgevers>')
JSON = b'{"rows":[{"A":"1","B":"x"},{"A":"2"}]}'


def _canonical_matches_parser(headers, rows, total):
    cf = to_canonical("f", headers, rows, total)
    assert cf.fields == list(headers)
    assert cf.total_rows == total
    assert cf.processed_rows == len(rows)
    # verliesvrij: de legacy-rijen zijn identiek aan de parser-output
    assert cf.to_legacy_rows() == rows
    return cf


def test_csv_roundtrip_identical():
    headers, rows, total = parse_csv_bytes(CSV, "f.csv")
    _canonical_matches_parser(headers, rows, total)


def test_xml_roundtrip_identical_and_partial_keys():
    headers, rows, total = parse_xml_bytes(XML)
    cf = _canonical_matches_parser(headers, rows, total)
    # tweede rij mist 'EndDate' - die sleutel mag NIET worden bijverzonnen
    assert "EndDate" not in cf.rows[1].to_raw()
    assert cf.rows[0].to_raw()["EndDate"] == ""


def test_json_roundtrip_identical():
    headers, rows, total = parse_json_bytes(JSON)
    _canonical_matches_parser(headers, rows, total)


def test_ingest_multiple_files():
    ch, cr, ct = parse_csv_bytes(CSV, "a.csv")
    jh, jr, jt = parse_json_bytes(JSON)
    files = ingest([
        {"filename": "a.csv", "headers": ch, "rows": cr, "total": ct},
        {"filename": "b.json", "headers": jh, "rows": jr, "total": jt},
    ])
    assert len(files) == 2
    assert files[0].filename == "a.csv" and files[0].to_legacy_rows() == cr
    assert files[1].filename == "b.json" and files[1].to_legacy_rows() == jr


def test_truncated_flag():
    rows = [{"A": "1"}, {"A": "2"}]
    cf = to_canonical("f", ["A"], rows, total=10)   # 10 aangeleverd, 2 verwerkt
    assert cf.truncated is True
    assert cf.processed_rows == 2 and cf.total_rows == 10
    cf2 = to_canonical("f", ["A"], rows, total=2)
    assert cf2.truncated is False


def test_cell_defaults_value_to_raw():
    c = CanonicalCell(source_column="BSN", raw="123")
    assert c.value == "123"      # slice 1: value == raw
    assert c.concept is None     # concept-mapping volgt in slice 3


def test_total_defaults_to_rowcount():
    cf = to_canonical("f", ["A"], [{"A": "1"}])
    assert cf.total_rows == 1
