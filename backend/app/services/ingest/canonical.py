"""
canonical.py - Canoniek rijmodel (doelarchitectuur Laag 1, Stap 1).

Doel: elk aangeleverd bestand, ongeacht bron (AFAS XML/JSON, ONS CSV, ZIB, ...),
representeren in EEN uniform model met behoud van provenance (bronkolom +
onbewerkte waarde). De validatiepaden consumeren straks dit model in plaats van
elk hun eigen parsing/mapping/normalisatie te doen.

SLICE 1 (dit bestand): alleen de datastructuren + een verliesvrije round-trip
naar het bestaande dict-rijformaat. Bronherkenning (`source_type`/`record_type`),
concept-mapping (`concept`) en waarde-normalisatie (`value`) worden in latere
slices ingevuld; tot die tijd geldt `value == raw` en `concept is None`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CanonicalCell:
    """Een cel met provenance: bronkolom, onbewerkte waarde en (later) een
    genormaliseerde waarde + gemapt concept."""
    source_column: str
    raw: str
    value: Any = None
    concept: Optional[str] = None

    def __post_init__(self) -> None:
        # Slice 1: genormaliseerde waarde valt samen met de ruwe waarde.
        if self.value is None:
            self.value = self.raw


@dataclass
class CanonicalRow:
    """Een rij als geordende verzameling cellen, gesleuteld op bronkolom.
    Bewaart de invoegvolgorde zodat de round-trip identiek blijft."""
    cells: dict[str, CanonicalCell] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw_row: dict[str, str]) -> "CanonicalRow":
        cells = {k: CanonicalCell(source_column=k, raw=v) for k, v in raw_row.items()}
        return cls(cells=cells)

    def to_raw(self) -> dict[str, str]:
        """Reconstrueert exact het oorspronkelijke dict[str, str]-rijformaat."""
        return {c.source_column: c.raw for c in self.cells.values()}


@dataclass
class CanonicalFile:
    """Een ingelezen bestand in canonieke vorm."""
    filename: str
    fields: list[str] = field(default_factory=list)      # bronkolommen (headers)
    rows: list[CanonicalRow] = field(default_factory=list)
    total_rows: int = 0                                   # aangeleverd (voor de cap)
    source_type: Optional[str] = None                    # slice 2: bronherkenning
    record_type: Optional[str] = None                    # slice 2: record/schema
    field_concepts: dict[str, str] = field(default_factory=dict)  # slice 3: bronkolom -> concept

    @property
    def processed_rows(self) -> int:
        return len(self.rows)

    @property
    def truncated(self) -> bool:
        return self.total_rows > self.processed_rows

    def concept_for(self, source_column: str) -> Optional[str]:
        """Het canonieke concept voor een bronkolom, of None."""
        return self.field_concepts.get(source_column)

    def to_legacy_rows(self) -> list[dict]:
        """Levert de rijen in het bestaande dict[str, str]-formaat, zodat
        validators ongewijzigd kunnen blijven draaien (compatibiliteitslaag)."""
        return [r.to_raw() for r in self.rows]
