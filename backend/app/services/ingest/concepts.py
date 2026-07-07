"""
concepts.py - Concept-mapping façade (doelarchitectuur Laag 1, Stap 1 - slice 3).

Eén centrale plek die per bestand bepaalt welk canoniek concept (intern veld)
bij welke bronkolom hoort. Delegeert naar de bestaande mapping-mechanismen zodat
de uitkomst identiek is aan het huidige gedrag (pariteit):
  * KIK-V     -> `auto_map` + `col_aliases` (KIKV_REFERENCE)
  * ZIB       -> `_auto_map` + `ZIB_FIELD_RULES`
  * Algemeen  -> directe match van template-veldnamen op headers

Levert `{bronkolom: concept}`. Het samenvoegen van de alias-registers tot één
concept-register is een latere stap; deze slice legt het énige aanroeppunt vast
en vult `CanonicalFile.field_concepts`.
"""
from __future__ import annotations

from typing import Optional, Sequence

from app.services.validator import auto_map, KIKV_REFERENCE
from app.services.zib_validator import _auto_map as _zib_auto_map
from app.services.zib_rules import get_zib_rules
from app.services.algemeen_validator import ALL_TEMPLATES


def _invert(field_to_col: dict) -> dict:
    """{intern_veld: bronkolom} -> {bronkolom: intern_veld}."""
    return {col: field for field, col in field_to_col.items() if col}


def map_concepts(standard: str, record_type: Optional[str],
                 headers: Optional[Sequence[str]]) -> dict[str, str]:
    """Geef `{bronkolom: concept}` voor een herkend bestand.

    Zonder herkend record_type of zonder headers is er niets te mappen -> {}.
    """
    if not record_type or not headers:
        return {}
    std = (standard or "").lower().strip()
    headers = list(headers)

    if std == "kikv":
        schema = KIKV_REFERENCE.get(record_type)
        if not schema:
            return {}
        return _invert(auto_map(headers, schema["col_aliases"]))

    if std == "zib":
        rules = get_zib_rules(record_type)
        if not rules:
            return {}
        return _invert(_zib_auto_map(headers, rules))

    if std == "algemeen":
        tpl = ALL_TEMPLATES.get(record_type)
        if not tpl:
            return {}
        fields = {**tpl.get("required", {}), **tpl.get("optional", {})}
        # Algemeen matcht template-veldnamen direct op headers (geen alias).
        return {h: h for h in headers if h in fields}

    return {}
