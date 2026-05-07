"""
actuality_validator.py — Data Actualiteit Score
================================================
Berekent hoe actueel de data is op basis van datum-velden.

Teruggegeven dict per bestand:
  actuality_score        : float 0-100
  total_records          : int
  actual_count           : int
  outdated_count         : int
  inconsistent_count     : int
  outdated               : list[{rowNumber, field, currentValue, days_old, message}]
  inconsistent           : list[{rowNumber, field, currentValue, message}]
  age_histogram          : list[{bucket, count, label}]
  pie                    : {actual, outdated, inconsistent}
  detected_fields        : {mutation, start, end, reference, all_date_cols}
  reference_date         : str (ISO)
  max_age_days           : int
  filename               : str  (toegevoegd door caller)
"""

from __future__ import annotations
import re
from datetime import date, datetime, timedelta
from typing import Optional

# ─── datum-patronen voor auto-detectie ───────────────────────────────────────
_MUTATION_PAT  = re.compile(r"(mutatie|mutation|gewijzigd|gewijzigddatum|updated|lastmodified|last_modified|wijzigingsdatum)", re.I)
_START_PAT     = re.compile(r"(startdatum|start_datum|ingangsdatum|begindatum|begin_datum|aanvangsdatum|datum_start|datum_begin)", re.I)
_END_PAT       = re.compile(r"(einddatum|eind_datum|einddatumtijd|expiratiedatum|vervaldatum|datum_eind|datum_einde)", re.I)
_REFERENCE_PAT = re.compile(r"(referentiedatum|peildatum|peil_datum|meetdatum|meet_datum)", re.I)
_DATE_GENERAL  = re.compile(r"(datum|date|dtime|datetime|_dt$|dt_)", re.I)

# histogram-buckets (bovengrenzen in dagen)
_BUCKETS = [0, 7, 14, 30, 60, 90, 180, 365, 9_999]
_BUCKET_LABELS = ["0-7d", "7-14d", "14-30d", "30-60d", "60-90d", "90-180d", "180-365d", "365d+"]


# ─── KIK-V Uitwisselkalender — actualiteitseisen per uitwisselprofiel ─────────
#
# Bron: KIK-V Uitwisselkalender (kik-v-publicatieplatform.nl/afsprakenset/3.1.0)
# Zorgkantoren: kwartaaldata (Q1-Q4) → max 90 dagen
# VWS Jaarverantwoording: gaat over het VORIGE boekjaar, deadline juni volgend jaar
#   → oudste data (jan 1 vorig jaar) is bij levering ~18 maanden oud = 548 dagen
# NZa Kostenonderzoek: gaat ook over het vorige boekjaar, zelfde deadline als VWS
#   → max_age_days = 548 (18 maanden)
# IGJ: afhankelijk van bezoek (on-demand) → 180 dagen als praktische richtlijn
#
KIKV_ACTUALITY_NORMS: dict[str, dict] = {
    "zorgkantoren": {
        "label":        "Zorgkantoren",
        "cadence":      "Kwartaal (Q1–Q4)",
        "max_age_days": 90,
        "color":        "#16a34a",
        "schemas":      ["medewerker", "werkovereenkomst", "functie", "verzuim", "vestiging", "client"],
        "description":  "Kwartaaluitwisseling voor zorgkantoren — data mag maximaal 90 dagen oud zijn.",
    },
    "vws": {
        "label":        "VWS Jaarverantwoording",
        "cadence":      "Jaarlijks (deadline juni)",
        "max_age_days": 548,
        "color":        "#7c3aed",
        "schemas":      ["medewerker", "werkovereenkomst", "functie", "verzuim", "client"],
        "description":  (
            "VWS Jaarverantwoording gaat over het vorige boekjaar (jan–dec), "
            "deadline aanlevering: 30 juni van het lopende jaar. "
            "Data voor jaar Y wordt in juni Y+1 aangeleverd — oudste records "
            "(jan Y) zijn dan ~18 maanden (548 dagen) oud."
        ),
    },
    "nza": {
        "label":        "NZa Kostenonderzoek",
        "cadence":      "Jaarlijks (deadline juni)",
        "max_age_days": 548,
        "color":        "#d97706",
        "schemas":      ["kostenplaats", "grootboek"],
        "description":  (
            "NZa Kostenonderzoek gaat over het vorige boekjaar (jan–dec), "
            "deadline aanlevering: 30 juni van het lopende jaar. "
            "Data voor jaar Y wordt in juni Y+1 aangeleverd — oudste records "
            "(jan Y) zijn dan ~18 maanden (548 dagen) oud."
        ),
    },
    "igj": {
        "label":        "IGJ Inspectiebezoek",
        "cadence":      "Afhankelijk van bezoek",
        "max_age_days": 180,
        "color":        "#ea580c",
        "schemas":      ["medewerker", "werkovereenkomst", "client", "vestiging"],
        "description":  "IGJ raadpleegt data bij (onaangekondigd) bezoek — richtlijn: max 180 dagen oud.",
    },
}

# Volgorde van prioriteit: welk profiel is leidend per schema?
_SCHEMA_PRIMARY_PROFILE = {
    "medewerker":       "zorgkantoren",
    "werkovereenkomst": "zorgkantoren",
    "functie":          "zorgkantoren",
    "verzuim":          "zorgkantoren",
    "vestiging":        "zorgkantoren",
    "client":           "zorgkantoren",
    "kostenplaats":     "nza",
    "grootboek":        "nza",
}


def get_kikv_norm_for_schema(schema_key: str) -> dict | None:
    """
    Geeft de primaire KIK-V actualiteitsnorm voor een gegeven schema-sleutel.
    Geeft None terug als geen norm bekend is.
    """
    profile_key = _SCHEMA_PRIMARY_PROFILE.get(schema_key)
    if not profile_key:
        return None
    norm = KIKV_ACTUALITY_NORMS[profile_key]
    return {**norm, "profile_key": profile_key}


# ─── hulpfuncties ─────────────────────────────────────────────────────────────

def _parse_date(val: str) -> Optional[date]:
    """Probeert meerdere formaten. Geeft None terug bij mislukking."""
    val = val.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d",
                "%d-%m-%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def detect_date_fields(headers: list[str]) -> dict:
    """
    Auto-detecteert datum-kolommen op basis van kolomnamen.
    Geeft een dict terug met de meest relevante kolommen per rol.
    """
    norm = {h: re.sub(r"[\s_\-]", "", h.lower()) for h in headers}

    def _first_match(pattern) -> Optional[str]:
        for h, n in norm.items():
            if pattern.search(n):
                return h
        return None

    mutation  = _first_match(_MUTATION_PAT)
    start     = _first_match(_START_PAT)
    end       = _first_match(_END_PAT)
    reference = _first_match(_REFERENCE_PAT)

    all_date_cols = [h for h, n in norm.items() if _DATE_GENERAL.search(h)]

    return {
        "mutation":      mutation,
        "start":         start,
        "end":           end,
        "reference":     reference,
        "all_date_cols": all_date_cols,
    }


def _age_bucket_index(days: int) -> int:
    for i, upper in enumerate(_BUCKETS[1:]):
        if days <= upper:
            return i
    return len(_BUCKET_LABELS) - 1


# ─── hoofd-validator ──────────────────────────────────────────────────────────

def validate_actuality(
    rows: list[dict],
    field_map: Optional[dict] = None,
    reference_date: Optional[date] = None,
    max_age_days: int = 30,
) -> dict:
    """
    Parameters
    ----------
    rows            : lijst van rij-dicts (kolomnaam → waarde).
    field_map       : output van detect_date_fields(); None = auto-detect.
    reference_date  : peilpunt (default: vandaag).
    max_age_days    : maximale leeftijd (dagen) voor 'actueel'.

    Returns
    -------
    Zie module-docstring.
    """
    if not rows:
        return _empty_result(field_map, reference_date, max_age_days)

    if field_map is None:
        field_map = detect_date_fields(list(rows[0].keys()))

    if reference_date is None:
        reference_date = date.today()

    mut_col  = field_map.get("mutation")
    start_col = field_map.get("start")
    end_col   = field_map.get("end")

    # Primaire kolom voor actualiteitscheck: mutation > start > eerste datum-col
    primary_col = mut_col or start_col
    if primary_col is None and field_map.get("all_date_cols"):
        primary_col = field_map["all_date_cols"][0]

    total      = len(rows)
    outdated   = []
    inconsistent = []
    histogram_counts = [0] * len(_BUCKET_LABELS)
    actual_count = 0
    unparseable_count = 0

    for idx, row in enumerate(rows):
        row_num = idx + 1

        # ── inconsistentie-check: start > end ──────────────────────────────
        if start_col and end_col:
            sv = row.get(start_col, "").strip()
            ev = row.get(end_col, "").strip()
            if sv and ev:
                sd = _parse_date(sv)
                ed = _parse_date(ev)
                if sd and ed and ed < sd:
                    inconsistent.append({
                        "rowNumber":    row_num,
                        "field":        f"{start_col} / {end_col}",
                        "currentValue": f"{sv} → {ev}",
                        "severity":     "error",
                        "message":      f"Einddatum ({ev}) ligt vóór startdatum ({sv})",
                        "suggested_fix": f"Controleer rij {row_num}: einddatum mag niet vóór startdatum liggen",
                    })

        # ── actualiteitscheck op primaire kolom ────────────────────────────
        if primary_col:
            pval = row.get(primary_col, "").strip()
            if pval:
                pd_ = _parse_date(pval)
                if pd_:
                    days_old = (reference_date - pd_).days
                    if days_old < 0:
                        days_old = 0  # toekomstdatum → beschouw als actueel
                    bucket_i = _age_bucket_index(days_old)
                    histogram_counts[bucket_i] += 1
                    if days_old <= max_age_days:
                        actual_count += 1
                    else:
                        outdated.append({
                            "rowNumber":    row_num,
                            "field":        primary_col,
                            "currentValue": pval,
                            "days_old":     days_old,
                            "severity":     "warning",
                            "message":      f"Record is {days_old} dagen oud (max {max_age_days}d)",
                            "suggested_fix": f"Actualiseer {primary_col} in rij {row_num} (huidige waarde: {pval})",
                        })
                else:
                    # Onparseerbare datum → telt niet mee als actueel
                    unparseable_count += 1

    # Bereken score
    parseable = actual_count + len(outdated)   # rijen met een geldige datum
    if parseable > 0:
        score = round(actual_count / parseable * 100, 1)
    elif total > 0:
        score = 0.0
    else:
        score = 100.0

    outdated_count     = len(outdated)
    inconsistent_count = len(inconsistent)

    age_histogram = [
        {"bucket": i, "label": _BUCKET_LABELS[i], "count": histogram_counts[i]}
        for i in range(len(_BUCKET_LABELS))
    ]

    return {
        "actuality_score":     score,
        "total_records":       total,
        "actual_count":        actual_count,
        "outdated_count":      outdated_count,
        "inconsistent_count":  inconsistent_count,
        "outdated":            outdated[:200],       # max 200 items
        "inconsistent":        inconsistent[:200],
        "age_histogram":       age_histogram,
        "pie": {
            "actual":      actual_count,
            "outdated":    outdated_count,
            "inconsistent": inconsistent_count,
        },
        "detected_fields":    field_map,
        "reference_date":     reference_date.isoformat(),
        "max_age_days":       max_age_days,
        "primary_col":        primary_col,
        "unparseable_count":  unparseable_count,
    }


def _empty_result(field_map, reference_date, max_age_days) -> dict:
    rd = reference_date.isoformat() if reference_date else date.today().isoformat()
    return {
        "actuality_score":    None,
        "total_records":      0,
        "actual_count":       0,
        "outdated_count":     0,
        "inconsistent_count": 0,
        "outdated":           [],
        "inconsistent":       [],
        "age_histogram":      [{"bucket": i, "label": _BUCKET_LABELS[i], "count": 0} for i in range(len(_BUCKET_LABELS))],
        "pie":                {"actual": 0, "outdated": 0, "inconsistent": 0},
        "detected_fields":    field_map or {},
        "reference_date":     rd,
        "max_age_days":       max_age_days,
        "primary_col":        None,
        "unparseable_count":  0,
    }
