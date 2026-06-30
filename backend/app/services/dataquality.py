"""
dataquality.py — Gedeelde validatie-primitieven (Stap 0 doelarchitectuur).

Eén bron van waarheid voor datum-herkenning/parsing, gebruikt door de
validatiesporen zodat datumlogica niet meer per spoor divergeert. Lost de
Noorderboog-bevindingen (TB-007) structureel op:
  * de poortwachter `is_date` accepteert dezelfde formaten als de parser
    (jaar-eerst/ISO, kort AFAS yyyymmdd, NL dag-eerst) -> KIK-V keurt
    AFAS-datums niet meer onterecht af;
  * geldigheid betekent een ECHT bestaande kalenderdatum -> Algemeen mist
    een niet-bestaande datum (bv. 2026-02-30) niet meer.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional


def parse_date(val: Any) -> Optional[datetime]:
    """Parse een datum uit meerdere formaten, zonder dag/maand te gokken.

    Ondersteund (ondubbelzinnig via positie van het 4-cijferige jaar):
      - ISO / jaar-eerst:  2026-04-22, 2026/04/22, 2026-04-22T00:00:00Z
      - kort AFAS:         20260422 (yyyymmdd)
      - NL / dag-eerst:    22-04-2026, 22/04/2026, 22.04.2026
    Het echt dubbelzinnige geval dd-mm vs mm-dd (jaar achteraan, beide <=12)
    wordt NIET gegokt: we houden de NL-conventie (dag-eerst) aan. Een niet
    bestaande kalenderdatum levert None op.
    """
    if not val:
        return None
    s = str(val).strip()
    if not s:
        return None
    # jaar-eerst (ISO, evt. met tijd): 2026-04-22 of 2026/04/22
    m = re.match(r'(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})', s)
    if m:
        try: return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError: return None
    # kort yyyymmdd (8 cijfers, AFAS Profit korte datums)
    m = re.match(r'^(\d{4})(\d{2})(\d{2})$', s)
    if m:
        try: return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError: return None
    # NL dag-eerst (jaar achteraan): 22-04-2026 / 22/04/2026 / 22.04.2026
    m = re.match(r'(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})', s)
    if m:
        try: return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError: return None
    return None


def is_date(val: Any) -> bool:
    """True als de waarde een herkenbare EN kalendergeldige datum is.

    Poortwachter gelijk aan `parse_date`: dezelfde formaten, en ongeldige
    kalenderdatums (bv. 2026-02-30) tellen als geen datum.
    """
    return parse_date(val) is not None
