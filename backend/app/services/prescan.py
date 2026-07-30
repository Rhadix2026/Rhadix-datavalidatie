"""
prescan.py — Format-validatie op basis van open standaarden

Valideert kolomwaarden op formaat, onafhankelijk van het gegevensschema:
  BSN        — elfproef (NL wetgeving)
  IBAN       — mod-97 checksum (ISO 13616)
  Telefoon   — NL formaat E.164 / 06-XXXXXXXX
  Datum      — ISO 8601 / NL dd-mm-yyyy
  Postcode   — NL 4+2 formaat (PTT)
  E-mail     — RFC 5322 basis
  AGB-code   — 8 cijfers (VEKTIS register)
  BIG-nummer — 11 cijfers (CIBG register)

Uitvoer volgt hetzelfde issue-formaat als de hoofdvalidators zodat de
frontend geen aanpassingen nodig heeft.
"""

import re
import datetime

# ── Validators ────────────────────────────────────────────────────────────────

def validate_bsn(val: str) -> tuple[bool, str]:
    """BSN elfproef: 9-cijferig, voldoet aan 11-proef."""
    digits = re.sub(r"\D", "", val)
    if len(digits) == 8:
        digits = "0" + digits
    if len(digits) != 9:
        n = len(re.sub(r"\D", "", val))
        return False, f"BSN heeft {n} cijfers (verwacht 8 of 9)"
    total = sum(int(d) * (9 - i) for i, d in enumerate(digits[:8]))
    total -= int(digits[8])
    if total % 11 != 0:
        return False, "BSN ongeldig (elfproef mislukt)"
    return True, ""


def validate_iban(val: str) -> tuple[bool, str]:
    """ISO 13616 IBAN-validatie via mod-97."""
    iban = re.sub(r"\s", "", val).upper()
    if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]+$", iban):
        return False, f"IBAN «{val[:30]}» heeft ongeldig formaat"
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    if int(numeric) % 97 != 1:
        return False, f"IBAN «{val[:30]}» heeft ongeldige checksum"
    return True, ""


def validate_phone_nl(val: str) -> tuple[bool, str]:
    """NL telefoonnummer: 10 cijfers, beginnet met 0 (of +31)."""
    digits = re.sub(r"[\s\-\(\)\+\.]", "", val)
    # +31XXXXXXXXX → 0XXXXXXXXX
    if digits.startswith("31") and len(digits) == 11:
        digits = "0" + digits[2:]
    if not re.match(r"^0[0-9]{9}$", digits):
        return False, f"Telefoonnummer «{val[:20]}» is geen geldig NL-nummer (verwacht 10 cijfers)"
    return True, ""


def validate_date(val: str) -> tuple[bool, str]:
    """Datum in gangbare NL/ISO-formaten."""
    val_str = str(val).strip()
    formats = [
        "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",
        "%Y-%m-%d", "%Y/%m/%d",
        "%d-%m-%y", "%d/%m/%y",
    ]
    for fmt in formats:
        try:
            datetime.datetime.strptime(val_str, fmt)
            return True, ""
        except ValueError:
            continue
    return False, f"Datum «{val_str}» heeft ongeldig formaat (verwacht dd-mm-yyyy of yyyy-mm-dd)"


def validate_postcode_nl(val: str) -> tuple[bool, str]:
    """NL postcode: 4 cijfers + optionele spatie + 2 letters."""
    if re.match(r"^\d{4}\s?[A-Za-z]{2}$", str(val).strip()):
        return True, ""
    return False, f"Postcode «{str(val)[:10]}» is geen geldig NL-formaat (verwacht 1234 AB)"


def validate_email(val: str) -> tuple[bool, str]:
    """E-mailadres — RFC 5322 basispatroon."""
    if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$", str(val).strip()):
        return True, ""
    return False, f"E-mailadres «{str(val)[:40]}» heeft ongeldig formaat"


def validate_agb(val: str) -> tuple[bool, str]:
    """AGB-code: exact 8 cijfers (VEKTIS)."""
    digits = re.sub(r"\D", "", str(val))
    if len(digits) == 8:
        return True, ""
    return False, f"AGB-code «{str(val)[:15]}» heeft {len(digits)} cijfers (verwacht 8)"


def validate_big(val: str) -> tuple[bool, str]:
    """BIG-nummer: exact 11 cijfers (CIBG-register)."""
    digits = re.sub(r"\D", "", str(val))
    if len(digits) == 11:
        return True, ""
    return False, f"BIG-nummer «{str(val)[:15]}» heeft {len(digits)} cijfers (verwacht 11)"


# ── Format-detectie op kolomnaam ──────────────────────────────────────────────

FORMAT_PATTERNS: list[tuple[str, list[str]]] = [
    ("bsn",      ["bsn", "burgerservicenummer", "burgerservicenr"]),
    ("iban",     ["iban", "bankrekening", "bankrekeningnr"]),
    ("phone",    ["telefoon", "telefoonnummer", "mobiel", "tel", "phone", "mobile", "gsm"]),
    ("date",     ["datum", "date", "geboortedatum", "einddatum", "startdatum",
                  "ingangsdatum", "vervaldatum", "peildatum", "registratiedatum"]),
    ("postcode", ["postcode", "pc", "zip", "zipcode"]),
    ("email",    ["email", "e_mail", "emailadres", "mail"]),
    ("agb",      ["agb", "agbcode", "agb_code"]),
    ("big",      ["big", "bignummer", "big_nummer", "bigregistratie", "bignr"]),
]

VALIDATORS: dict[str, callable] = {
    "bsn":      validate_bsn,
    "iban":     validate_iban,
    "phone":    validate_phone_nl,
    "date":     validate_date,
    "postcode": validate_postcode_nl,
    "email":    validate_email,
    "agb":      validate_agb,
    "big":      validate_big,
}

FORMAT_LABELS: dict[str, str] = {
    "bsn":      "BSN (elfproef)",
    "iban":     "IBAN (ISO 13616)",
    "phone":    "Telefoonnummer (NL E.164)",
    "date":     "Datum (dd-mm-yyyy / yyyy-mm-dd)",
    "postcode": "Postcode (NL 4+2)",
    "email":    "E-mailadres (RFC 5322)",
    "agb":      "AGB-code (8 cijfers)",
    "big":      "BIG-nummer (11 cijfers)",
}

FORMAT_SOURCES: dict[str, str] = {
    "bsn":      "Open standaard: BSN elfproef (NL wetgeving)",
    "iban":     "Open standaard: ISO 13616 IBAN",
    "phone":    "Open standaard: E.164 / NL Telecomwet",
    "date":     "Open standaard: ISO 8601",
    "postcode": "Open standaard: NL Postcode (PTT formaat)",
    "email":    "Open standaard: RFC 5322",
    "agb":      "Open standaard: VEKTIS AGB-register",
    "big":      "Open standaard: BIG-register (CIBG)",
}


def detect_format(col_name: str) -> str | None:
    """Detecteert het formaat-type van een kolom op basis van de kolomnaam."""
    norm = col_name.strip().lower().replace(" ", "_").replace("-", "_")
    for fmt, aliases in FORMAT_PATTERNS:
        for alias in aliases:
            if alias == norm or alias in norm or norm in alias:
                return fmt
    return None


def validate_format(fmt: str, val: str) -> tuple[bool, str]:
    """Valideert een waarde voor het gegeven formaat-type."""
    validator = VALIDATORS.get(fmt)
    if not validator:
        return True, ""
    return validator(val)


# ── Hoofd-functies ────────────────────────────────────────────────────────────

def prescan_columns(rows: list[dict], known_cols: set[str] | None = None) -> list[dict]:
    """
    Scant kolommen in `rows` op formaat-validatie op basis van kolomnaam.

    Parameters
    ----------
    rows        : lijst van rij-dicts (CSV-data)
    known_cols  : kolommen die al door de hoofdvalidator worden gecontroleerd
                  (worden overgeslagen om dubbele rapportage te voorkomen)

    Returns
    -------
    Lijst van issues in hetzelfde formaat als de hoofdvalidators.
    Elk issue bevat 'prescan: True' als markering.
    """
    if not rows:
        return []

    known_cols = known_cols or set()
    issues: list[dict] = []

    for col in rows[0].keys():
        if col in known_cols:
            continue
        fmt = detect_format(col)
        if not fmt:
            continue

        validator  = VALIDATORS[fmt]
        label      = FORMAT_LABELS[fmt]
        source     = FORMAT_SOURCES[fmt]
        error_rows: list[dict] = []
        error_count = 0

        for i, row in enumerate(rows):
            val     = row.get(col, "")
            val_str = str(val).strip() if val is not None else ""
            if not val_str:
                continue  # lege waarden vallen buiten de format-check

            ok, message = validator(val_str)
            if not ok:
                error_count += 1
                if len(error_rows) < 50:
                    error_rows.append({
                        "rowNumber":     i + 1,
                        "personId":      "",
                        "field":         col,
                        "currentValue":  val_str[:60],
                        "expectedValue": label,
                        "message":       message,
                    })

        if error_count > 0:
            issues.append({
                "label":          f"{col} — {label}",
                "severity":       "warning",
                "detail":         f"{error_count} rijen met ongeldige waarde (pre-scan formaat)",
                "count":          error_count,
                "rows":           error_rows,
                "allowed_values": [],
                "source":         f"Pre-scan: {source}",
                "prescan":        True,
            })

    return issues


def prescan_quality_stats(rows: list[dict], known_cols: set[str] | None = None) -> tuple[int, int]:
    """
    Berekent (total_checked, total_errors) voor format-detecteerbare extra kolommen.
    Wordt gebruikt om de kwaliteit_score te corrigeren in de hoofdvalidators.
    """
    if not rows:
        return 0, 0

    known_cols    = known_cols or set()
    total_checked = 0
    total_errors  = 0

    for col in rows[0].keys():
        if col in known_cols:
            continue
        fmt = detect_format(col)
        if not fmt:
            continue

        validator = VALIDATORS[fmt]
        for row in rows:
            val     = row.get(col, "")
            val_str = str(val).strip() if val is not None else ""
            if not val_str:
                continue
            total_checked += 1
            ok, _ = validator(val_str)
            if not ok:
                total_errors += 1

    return total_checked, total_errors
