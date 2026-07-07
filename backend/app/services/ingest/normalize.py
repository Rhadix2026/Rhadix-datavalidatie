"""
normalize.py - Waarde-normalisatie aan de bron (doelarchitectuur Laag 1, Stap 1 - slice 4).

Normaliseert waarden één keer bij ingest, zodat elke controle daarna hetzelfde
'ziet'. Hergebruikt de al gedeelde primitieven:
  * Datums  -> `dataquality.parse_date` (ISO 'YYYY-MM-DD'); ongeldige/lege waarden
              blijven ongewijzigd staan zodat niets verloren gaat.
  * Codelijst (verzuimsoort) -> `rules.normalize_verzuimtype` op Algemeen-velden
              met type 'verzuimtype'.

Datumkolommen worden naam-gebaseerd herkend met `detect_date_fields` - dezelfde
detector die de actualiteitscheck al gebruikt, dus standaard-onafhankelijk.

Belangrijk: dit vult alleen `CanonicalCell.value`. De ruwe waarde (`raw`) en
`to_legacy_rows()` blijven ongewijzigd, zodat de bestaande validators identiek
blijven draaien. De omslag naar `value` is een latere stap.
"""
from __future__ import annotations

from typing import Sequence

from app.services.dataquality import parse_date
from app.services.rules import normalize_verzuimtype
from app.services.actuality_validator import detect_date_fields
from app.services.algemeen_validator import ALL_TEMPLATES


def normalize_date(raw):
    """Ruwe datumwaarde -> ISO 'YYYY-MM-DD'. Leeg/ongeldig blijft ongewijzigd."""
    if raw is None:
        return raw
    s = str(raw).strip()
    if not s:
        return raw
    d = parse_date(s)
    return d.date().isoformat() if d else raw


def normalize_verzuim(raw):
    """Ruwe verzuimsoort -> genormaliseerde KIK-V-waarde (leeg blijft leeg)."""
    if raw is None or str(raw).strip() == "":
        return raw
    return normalize_verzuimtype(raw)


def date_columns(headers: Sequence[str]) -> set[str]:
    """Naam-gebaseerde set datumkolommen (via de bestaande actualiteitsdetector)."""
    return set(detect_date_fields(list(headers)).get("all_date_cols", []))


def _verzuim_columns(standard, record_type, headers) -> set[str]:
    """Algemeen-kolommen met type 'verzuimtype' (concept == kolomnaam)."""
    if (standard or "").lower() != "algemeen" or not record_type:
        return set()
    tpl = ALL_TEMPLATES.get(record_type)
    if not tpl:
        return set()
    fields = {**tpl.get("required", {}), **tpl.get("optional", {})}
    verzuim = {f for f, t in fields.items() if t == "verzuimtype"}
    return {h for h in headers if h in verzuim}


def normalize_file(cf) -> None:
    """Vul `cell.value` met genormaliseerde waarden voor datum- en codelijst-
    kolommen. In-place; laat `raw` en overige kolommen (value == raw) ongemoeid."""
    if not cf.rows:
        return
    dcols = date_columns(cf.fields)
    vcols = _verzuim_columns(cf.source_type, cf.record_type, cf.fields)
    if not dcols and not vcols:
        return
    for row in cf.rows:
        for col in dcols:
            cell = row.cells.get(col)
            if cell is not None:
                cell.value = normalize_date(cell.raw)
        for col in vcols:
            cell = row.cells.get(col)
            if cell is not None:
                cell.value = normalize_verzuim(cell.raw)
