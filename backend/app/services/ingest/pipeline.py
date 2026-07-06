"""
pipeline.py - Ingest-pipeline (doelarchitectuur Laag 1, Stap 1).

Zet reeds ingelezen bestanden (headers + ruwe rijen, zoals `parse_upload` die
oplevert) om naar het canonieke model. Bewust ontkoppeld van FastAPI/`parse_upload`
om circulaire imports met `routers.validate` te vermijden: de caller parseert en
geeft het resultaat hierheen door.

SLICE 1: puur een verliesvrije omzetting. Bronherkenning, concept-mapping en
normalisatie volgen in latere slices; het gedrag voor de validators verandert
niet (zie `CanonicalFile.to_legacy_rows`).
"""
from __future__ import annotations

from typing import Iterable, Mapping

from app.services.ingest.canonical import CanonicalFile, CanonicalRow


def to_canonical(filename: str, headers: list[str], raw_rows: list[dict],
                 total: int | None = None) -> CanonicalFile:
    """Bouw een CanonicalFile uit een reeds geparset bestand.

    `total` is het aantal aangeleverde rijen (voor de cap); valt terug op het
    aantal doorgegeven rijen als het niet bekend is.
    """
    rows = [CanonicalRow.from_raw(r) for r in raw_rows]
    return CanonicalFile(
        filename=filename,
        fields=list(headers),
        rows=rows,
        total_rows=total if total is not None else len(rows),
    )


def ingest(parsed: Iterable[Mapping]) -> list[CanonicalFile]:
    """Zet een reeks geparste bestanden om naar canonieke bestanden.

    Elk item is een mapping met sleutels `filename`, `headers`, `rows` en
    optioneel `total` - hetzelfde formaat dat `upload_and_validate` al opbouwt.
    """
    out: list[CanonicalFile] = []
    for p in parsed:
        out.append(to_canonical(
            filename=p["filename"],
            headers=p.get("headers", []),
            raw_rows=p.get("rows", []),
            total=p.get("total"),
        ))
    return out
