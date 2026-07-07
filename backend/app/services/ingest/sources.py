"""
sources.py - Bronherkenning-façade (doelarchitectuur Laag 1, Stap 1 - slice 2).

Eén centrale ingang die per aangeleverd bestand bepaalt om welk record-/schema-type
het gaat. Delegeert (nog) naar de drie bestaande detectoren - `detect_schema`
(KIK-V), `detect_zib_schema` (ZIB) en `_detect_template` (Algemeen) - zodat de
uitkomst per constructie identiek is aan het huidige gedrag (pariteit).

Het samenvoegen van de detectie-metadata tot één register is de volgende
micro-stap; deze slice legt het énige aanroeppunt vast en vult daarmee
`source_type`/`record_type` op het canonieke model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from app.services.validator import detect_schema as _detect_kikv
from app.services.zib_rules import detect_zib_schema as _detect_zib
from app.services.algemeen_validator import _detect_template as _detect_algemeen

# De drie standaarden/paden die de tool kent.
STANDARDS = ("kikv", "zib", "algemeen")


@dataclass
class SourceMatch:
    """Uitkomst van bronherkenning voor één bestand."""
    standard: str                    # 'kikv' | 'zib' | 'algemeen'
    record_type: Optional[str]       # het herkende schema-/template-type, of None

    @property
    def recognized(self) -> bool:
        return self.record_type is not None


def _detect_for(standard: str, filename: str, headers: Sequence[str]) -> Optional[str]:
    if standard == "kikv":
        return _detect_kikv(filename, list(headers))
    if standard == "zib":
        return _detect_zib(filename)          # ZIB detecteert op bestandsnaam
    if standard == "algemeen":
        return _detect_algemeen(filename, list(headers))
    return None


def detect_source(filename: str, headers: Optional[Sequence[str]] = None,
                  standard: str = "kikv") -> SourceMatch:
    """Bepaal het record-/schema-type voor een bestand binnen een standaard.

    Dit is dé centrale ingang voor bronherkenning; delegeert naar de bestaande
    detectoren zodat het gedrag identiek blijft aan de huidige paden.
    """
    std = (standard or "kikv").lower().strip()
    record_type = _detect_for(std, filename or "", headers or [])
    return SourceMatch(standard=std, record_type=record_type)
