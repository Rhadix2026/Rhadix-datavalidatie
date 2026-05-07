"""
zib_rules.py — Veldregels voor ZIB-validatie (Zorginformatiebouwstenen, Nictiz 2020)

Ondersteunde ZIB's:
  - nl.zorg.Patient              : patiënt-/cliëntgegevens
  - nl.zorg.Probleem             : diagnoses en aandoeningen
  - nl.zorg.MedicatieAfspraak    : medicatieafspraken
  - nl.zorg.AllergieIntolerantie : allergieën en intoleranties

Veld-structuur per veld:
  required      : bool   — is het veld verplicht?
  type          : str    — string | date | code | bsn | numeric
  aliases       : list   — herkende kolomnamen uit EPD-exports (HiX, Epic, Nedap ONS, etc.)
  allowed_values: list   — gecontroleerde waardelijsten (optioneel)
  concept_uri   : str    — ZIB-URI (nl.zorg namespace)
  concept_label : str    — NL-label van het ZIB-concept
  description   : str    — toelichting voor rapportage
"""

from typing import Any

# ── Namespace ─────────────────────────────────────────────────────────────────
ZIB_BASE = "https://zibs.nl/wiki/"

# ── Toegestane waardelijsten ──────────────────────────────────────────────────

GESLACHT_ALLOWED = [
    {"value": "man",     "label": "Man"},
    {"value": "vrouw",   "label": "Vrouw"},
    {"value": "onbekend","label": "Onbekend"},
    {"value": "undifferentiated", "label": "Niet te bepalen"},
    # EPD-varianten
    {"value": "m",       "label": "Man"},
    {"value": "v",       "label": "Vrouw"},
    {"value": "o",       "label": "Onbekend"},
    {"value": "male",    "label": "Man"},
    {"value": "female",  "label": "Vrouw"},
    {"value": "unknown", "label": "Onbekend"},
]
GESLACHT_VALUES = [av["value"] for av in GESLACHT_ALLOWED]

PROBLEEM_STATUS_ALLOWED = [
    {"value": "actief",              "label": "Actief"},
    {"value": "niet meer aanwezig",  "label": "Niet meer aanwezig"},
    {"value": "inactief",            "label": "Inactief"},
    {"value": "onbekend",            "label": "Onbekend"},
    # Engels (Epic / FHIR)
    {"value": "active",              "label": "Actief"},
    {"value": "resolved",            "label": "Niet meer aanwezig"},
    {"value": "inactive",            "label": "Inactief"},
    {"value": "unknown",             "label": "Onbekend"},
]
PROBLEEM_STATUS_VALUES = [av["value"] for av in PROBLEEM_STATUS_ALLOWED]

ALLERGIE_CATEGORIE_ALLOWED = [
    {"value": "geneesmiddel",   "label": "Geneesmiddel"},
    {"value": "voedsel",        "label": "Voedsel"},
    {"value": "omgeving",       "label": "Omgeving"},
    {"value": "overig",         "label": "Overig"},
    {"value": "onbekend",       "label": "Onbekend"},
    # Engels
    {"value": "medication",     "label": "Geneesmiddel"},
    {"value": "food",           "label": "Voedsel"},
    {"value": "environment",    "label": "Omgeving"},
    {"value": "other",          "label": "Overig"},
    {"value": "unknown",        "label": "Onbekend"},
]
ALLERGIE_CATEGORIE_VALUES = [av["value"] for av in ALLERGIE_CATEGORIE_ALLOWED]

CRITICALITY_ALLOWED = [
    {"value": "laag",           "label": "Laag"},
    {"value": "hoog",           "label": "Hoog"},
    {"value": "onbekend",       "label": "Onbekend"},
    {"value": "low",            "label": "Laag"},
    {"value": "high",           "label": "Hoog"},
    {"value": "unable-to-assess","label": "Onbekend"},
]
CRITICALITY_VALUES = [av["value"] for av in CRITICALITY_ALLOWED]

TOEDIENINGSWEG_ALLOWED = [
    {"value": "oraal",          "label": "Oraal"},
    {"value": "intraveneus",    "label": "Intraveneus"},
    {"value": "subcutaan",      "label": "Subcutaan"},
    {"value": "inhalatie",      "label": "Inhalatie"},
    {"value": "transdermaal",   "label": "Transdermaal"},
    {"value": "rectaal",        "label": "Rectaal"},
    {"value": "sublinguaal",    "label": "Sublinguaal"},
    {"value": "topicaal",       "label": "Topicaal"},
    {"value": "nasaal",         "label": "Nasaal"},
    {"value": "overig",         "label": "Overig"},
    # Engels
    {"value": "oral",           "label": "Oraal"},
    {"value": "intravenous",    "label": "Intraveneus"},
    {"value": "subcutaneous",   "label": "Subcutaan"},
    {"value": "inhalation",     "label": "Inhalatie"},
    {"value": "transdermal",    "label": "Transdermaal"},
    {"value": "rectal",         "label": "Rectaal"},
]
TOEDIENINGSWEG_VALUES = [av["value"] for av in TOEDIENINGSWEG_ALLOWED]

# ── ZIB veldregels ────────────────────────────────────────────────────────────

ZIB_FIELD_RULES: dict[str, dict[str, Any]] = {

    # ── nl.zorg.Patient ───────────────────────────────────────────────────────
    "patient": {
        "bsn": {
            "required": True,
            "type": "bsn",
            "concept_uri": f"{ZIB_BASE}Patient-v3.2(2020EN)#NL-CM:0.1.7",
            "concept_label": "Burgerservicenummer",
            "description": "Burgerservicenummer (11-cijferig, elfproef)",
            "aliases": [
                "bsn", "burgerservicenummer", "patiënt bsn", "patient_bsn",
                "ssn", "nationalpatientidentifier", "nationaalpatientnummer",
                "patientssn", "bsnummer",
            ],
        },
        "voornaam": {
            "required": True,
            "type": "string",
            "concept_uri": f"{ZIB_BASE}Patient-v3.2(2020EN)#NL-CM:0.1.26",
            "concept_label": "Voornaam",
            "description": "Voornaam of initialen van de patiënt",
            "aliases": [
                "voornaam", "voornamen", "firstname", "first_name", "givenname",
                "given_name", "naam_voornaam", "forename", "initialen", "initials",
            ],
        },
        "achternaam": {
            "required": True,
            "type": "string",
            "concept_uri": f"{ZIB_BASE}Patient-v3.2(2020EN)#NL-CM:0.1.24",
            "concept_label": "Achternaam",
            "description": "Achternaam (familienaam) van de patiënt",
            "aliases": [
                "achternaam", "familienaam", "lastname", "last_name", "surname",
                "family_name", "naam_achternaam", "familyname",
            ],
        },
        "geboortedatum": {
            "required": True,
            "type": "date",
            "concept_uri": f"{ZIB_BASE}Patient-v3.2(2020EN)#NL-CM:0.1.10",
            "concept_label": "Geboortedatum",
            "description": "Geboortedatum van de patiënt (dd/mm/yyyy)",
            "aliases": [
                "geboortedatum", "geboortedatum_patiënt", "dateofbirth", "date_of_birth",
                "dob", "birthdate", "birth_date", "gebdatum", "geb_datum",
            ],
        },
        "geslacht": {
            "required": True,
            "type": "code",
            "allowed_values": GESLACHT_ALLOWED,
            "concept_uri": f"{ZIB_BASE}Patient-v3.2(2020EN)#NL-CM:0.1.9",
            "concept_label": "Geslacht",
            "description": f"Administratief geslacht. Toegestaan: {', '.join(GESLACHT_VALUES)}",
            "aliases": [
                "geslacht", "sex", "gender", "administratief_geslacht",
                "geslachtsaanduiding", "biologisch_geslacht",
            ],
        },
        "postcode": {
            "required": False,
            "type": "string",
            "concept_uri": f"{ZIB_BASE}Patient-v3.2(2020EN)#NL-CM:0.1.43",
            "concept_label": "Postcode",
            "description": "Postcode van het woonadres",
            "aliases": [
                "postcode", "zipcode", "zip_code", "postal_code", "postalcode",
                "zip", "pc",
            ],
        },
        "woonplaats": {
            "required": False,
            "type": "string",
            "concept_uri": f"{ZIB_BASE}Patient-v3.2(2020EN)#NL-CM:0.1.41",
            "concept_label": "Woonplaats",
            "description": "Woonplaats van het woonadres",
            "aliases": [
                "woonplaats", "stad", "city", "place", "gemeente",
                "place_of_residence", "city_of_residence",
            ],
        },
        "telefoonnummer": {
            "required": False,
            "type": "string",
            "concept_uri": f"{ZIB_BASE}Patient-v3.2(2020EN)#NL-CM:0.1.31",
            "concept_label": "Telefoonnummer",
            "description": "Telefoonnummer van de patiënt",
            "aliases": [
                "telefoonnummer", "telefoon", "phone", "phone_number", "phonenumber",
                "tel", "mobile", "mobiel", "gsm",
            ],
        },
    },

    # ── nl.zorg.Probleem ──────────────────────────────────────────────────────
    "probleem": {
        "patient_id": {
            "required": True,
            "type": "string",
            "concept_uri": f"{ZIB_BASE}Probleem-v4.4(2020EN)#subject",
            "concept_label": "PatiëntReferentie",
            "description": "Verwijzing naar de patiënt (BSN of intern ID)",
            "aliases": [
                "bsn", "patient_id", "patientid", "patiëntnummer", "patient_nummer",
                "patientnummer", "subject", "patient_bsn",
            ],
        },
        "probleem_naam": {
            "required": True,
            "type": "string",
            "concept_uri": f"{ZIB_BASE}Probleem-v4.4(2020EN)#NL-CM:5.1.3",
            "concept_label": "ProbleemNaam",
            "description": "Naam of omschrijving van het probleem / de diagnose",
            "aliases": [
                "probleemnaam", "probleem_naam", "diagnose", "diagnosis",
                "aandoening", "condition", "problemname", "problem_name",
                "naam", "omschrijving", "description",
            ],
        },
        "probleem_code": {
            "required": False,
            "type": "string",
            "concept_uri": f"{ZIB_BASE}Probleem-v4.4(2020EN)#NL-CM:5.1.3",
            "concept_label": "ProbleemCode (SNOMED CT)",
            "description": "SNOMED CT-code of ICD-10 code van het probleem",
            "aliases": [
                "probleem_code", "probleemcode", "snomedcode", "snomed_code",
                "icdcode", "icd_code", "icd10", "diagnosecode", "diagnosis_code",
                "code",
            ],
        },
        "probleem_status": {
            "required": True,
            "type": "code",
            "allowed_values": PROBLEEM_STATUS_ALLOWED,
            "concept_uri": f"{ZIB_BASE}Probleem-v4.4(2020EN)#NL-CM:5.1.10",
            "concept_label": "ProbleemStatus",
            "description": f"Status van het probleem. Toegestaan: {', '.join(PROBLEEM_STATUS_VALUES)}",
            "aliases": [
                "probleem_status", "probleemstatus", "status", "verificationstatus",
                "clinical_status", "clinicalstatus", "problem_status",
            ],
        },
        "begin_datum": {
            "required": False,
            "type": "date",
            "concept_uri": f"{ZIB_BASE}Probleem-v4.4(2020EN)#NL-CM:5.1.6",
            "concept_label": "ProbleemBeginDatum",
            "description": "Datum waarop het probleem begonnen is",
            "aliases": [
                "begin_datum", "begindatum", "startdatum", "start_datum",
                "onset_date", "onsetdate", "onset", "diagnosedatum",
            ],
        },
        "eind_datum": {
            "required": False,
            "type": "date",
            "concept_uri": f"{ZIB_BASE}Probleem-v4.4(2020EN)#NL-CM:5.1.7",
            "concept_label": "ProbleemEindDatum",
            "description": "Datum waarop het probleem is opgelost (alleen bij status 'niet meer aanwezig')",
            "aliases": [
                "eind_datum", "einddatum", "abatement_date", "abatementdate",
                "resolved_date", "end_date", "enddate",
            ],
        },
    },

    # ── nl.zorg.MedicatieAfspraak ─────────────────────────────────────────────
    "medicatieafspraak": {
        "patient_id": {
            "required": True,
            "type": "string",
            "concept_uri": f"{ZIB_BASE}MedicatieAfspraak-v1.2(2020EN)#subject",
            "concept_label": "PatiëntReferentie",
            "description": "Verwijzing naar de patiënt (BSN of intern ID)",
            "aliases": [
                "bsn", "patient_id", "patientid", "patiëntnummer",
                "patient_nummer", "patientnummer", "subject",
            ],
        },
        "geneesmiddel": {
            "required": True,
            "type": "string",
            "concept_uri": f"{ZIB_BASE}MedicatieAfspraak-v1.2(2020EN)#NL-CM:9.6.19926",
            "concept_label": "Geneesmiddel",
            "description": "Naam van het geneesmiddel",
            "aliases": [
                "geneesmiddel", "medication", "medicatie", "drug", "medicine",
                "medicatienaam", "medication_name", "drug_name", "middel",
                "product", "productnaam",
            ],
        },
        "geneesmiddel_code": {
            "required": False,
            "type": "string",
            "concept_uri": f"{ZIB_BASE}MedicatieAfspraak-v1.2(2020EN)#NL-CM:9.6.19926",
            "concept_label": "GeneesmiddelCode (ATC/G-standaard)",
            "description": "ATC-code of G-standaard PRK/HPK-code van het middel",
            "aliases": [
                "geneesmiddel_code", "atccode", "atc_code", "atc", "hpk",
                "prk", "gstandaard", "g_standaard", "medicatiecode",
                "drug_code", "medication_code",
            ],
        },
        "gebruiksperiode_start": {
            "required": True,
            "type": "date",
            "concept_uri": f"{ZIB_BASE}MedicatieAfspraak-v1.2(2020EN)#NL-CM:9.6.19936",
            "concept_label": "GebruiksperiodeStart",
            "description": "Startdatum van de medicatieafspraak",
            "aliases": [
                "gebruiksperiode_start", "startdatum", "start_datum", "start_date",
                "startdate", "ingangsdatum", "medication_start", "prescribed_date",
                "afspraakdatum",
            ],
        },
        "gebruiksperiode_eind": {
            "required": False,
            "type": "date",
            "concept_uri": f"{ZIB_BASE}MedicatieAfspraak-v1.2(2020EN)#NL-CM:9.6.19937",
            "concept_label": "GebruiksperiodeEind",
            "description": "Einddatum van de medicatieafspraak (leeg = onbepaald)",
            "aliases": [
                "gebruiksperiode_eind", "einddatum", "eind_datum", "end_date",
                "enddate", "stoopdatum", "stop_date", "medication_end",
            ],
        },
        "dosering": {
            "required": False,
            "type": "string",
            "concept_uri": f"{ZIB_BASE}MedicatieAfspraak-v1.2(2020EN)#NL-CM:9.6.19938",
            "concept_label": "Dosering",
            "description": "Dosering (bijv. '1 tablet 2x daags')",
            "aliases": [
                "dosering", "dose", "dosis", "dosage", "hoeveelheid",
                "gebruiksaanwijzing", "instructions", "sig",
            ],
        },
        "toedieningsweg": {
            "required": False,
            "type": "code",
            "allowed_values": TOEDIENINGSWEG_ALLOWED,
            "concept_uri": f"{ZIB_BASE}MedicatieAfspraak-v1.2(2020EN)#NL-CM:9.6.19940",
            "concept_label": "Toedieningsweg",
            "description": f"Manier van toediening. Toegestaan: {', '.join(TOEDIENINGSWEG_VALUES)}",
            "aliases": [
                "toedieningsweg", "route", "administration_route", "route_of_administration",
                "toediening", "routeofadministration",
            ],
        },
        "voorschrijver": {
            "required": False,
            "type": "string",
            "concept_uri": f"{ZIB_BASE}MedicatieAfspraak-v1.2(2020EN)#NL-CM:9.6.1030",
            "concept_label": "Voorschrijver",
            "description": "Naam of ID van de voorschrijvende arts",
            "aliases": [
                "voorschrijver", "prescriber", "arts", "doctor", "physician",
                "prescribing_physician", "agbcode", "agb_code",
            ],
        },
    },

    # ── nl.zorg.AllergieIntolerantie ─────────────────────────────────────────
    "allergie": {
        "patient_id": {
            "required": True,
            "type": "string",
            "concept_uri": f"{ZIB_BASE}AllergieIntolerantie-v3.3(2020EN)#subject",
            "concept_label": "PatiëntReferentie",
            "description": "Verwijzing naar de patiënt (BSN of intern ID)",
            "aliases": [
                "bsn", "patient_id", "patientid", "patiëntnummer",
                "patient_nummer", "patientnummer", "subject",
            ],
        },
        "veroorzakend_middel": {
            "required": True,
            "type": "string",
            "concept_uri": f"{ZIB_BASE}AllergieIntolerantie-v3.3(2020EN)#NL-CM:8.2.2",
            "concept_label": "VeroorzakendMiddel",
            "description": "Naam van de stof die de allergie/intolerantie veroorzaakt",
            "aliases": [
                "veroorzakend_middel", "veroorzakendmiddel", "substance", "stof",
                "allergen", "allergeen", "causative_agent", "causativeagent",
                "middel", "agent",
            ],
        },
        "allergie_categorie": {
            "required": False,
            "type": "code",
            "allowed_values": ALLERGIE_CATEGORIE_ALLOWED,
            "concept_uri": f"{ZIB_BASE}AllergieIntolerantie-v3.3(2020EN)#NL-CM:8.2.4",
            "concept_label": "AllergieCategorie",
            "description": f"Categorie van de allergie. Toegestaan: {', '.join(ALLERGIE_CATEGORIE_VALUES)}",
            "aliases": [
                "allergie_categorie", "allergiecategorie", "category",
                "allergy_category", "type", "allergietype",
            ],
        },
        "kritikaliteit": {
            "required": False,
            "type": "code",
            "allowed_values": CRITICALITY_ALLOWED,
            "concept_uri": f"{ZIB_BASE}AllergieIntolerantie-v3.3(2020EN)#NL-CM:8.2.20",
            "concept_label": "Kritikaliteit",
            "description": f"Ernst van de reactie. Toegestaan: {', '.join(CRITICALITY_VALUES)}",
            "aliases": [
                "kritikaliteit", "criticality", "ernst", "severity",
                "allergy_severity", "mate_van_ernst",
            ],
        },
        "begin_datum": {
            "required": False,
            "type": "date",
            "concept_uri": f"{ZIB_BASE}AllergieIntolerantie-v3.3(2020EN)#NL-CM:8.2.6",
            "concept_label": "BeginDatum",
            "description": "Datum waarop de allergie/intolerantie werd vastgesteld",
            "aliases": [
                "begin_datum", "begindatum", "startdatum", "onset_date",
                "onset", "vastgesteld_op", "registered_date",
            ],
        },
        "reactie": {
            "required": False,
            "type": "string",
            "concept_uri": f"{ZIB_BASE}AllergieIntolerantie-v3.3(2020EN)#NL-CM:8.2.10",
            "concept_label": "Reactie",
            "description": "Omschrijving van de allergische reactie",
            "aliases": [
                "reactie", "reaction", "manifestation", "manifestatie",
                "symptoom", "symptom", "allergische_reactie",
            ],
        },
    },
}

# ── Schema-detectie aliassen (bestandsnamen → schema_key) ─────────────────────
ZIB_SCHEMA_ALIASES: dict[str, list[str]] = {
    "patient":           ["patient", "patiënt", "client", "cliënt", "bewoner",
                          "patients", "clients", "patienten", "clienten", "bewoners"],
    "probleem":          ["probleem", "diagnose", "problemen", "diagnoses",
                          "aandoening", "aandoeningen", "condition", "conditions",
                          "problem", "problems"],
    "medicatieafspraak": ["medicatie", "medicatieafspraak", "medicatieafspraken",
                          "medication", "medications", "medicament", "medicamenten",
                          "voorschrift", "voorschriften", "prescription", "prescriptions"],
    "allergie":          ["allergie", "allergieën", "intolerantie", "intoleranties",
                          "allergy", "allergies", "allergieinolerantie",
                          "allergyintolerance"],
}

# ── Helper: schema_key ophalen op bestandsnaam ────────────────────────────────

def detect_zib_schema(filename: str) -> str | None:
    """Retourneert de ZIB schema_key op basis van de bestandsnaam, of None."""
    name = filename.lower().replace(" ", "_").replace("-", "_")
    # Verwijder extensie
    for ext in (".csv", ".xlsx", ".xls", ".tsv"):
        if name.endswith(ext):
            name = name[: -len(ext)]
    for schema_key, aliases in ZIB_SCHEMA_ALIASES.items():
        for alias in aliases:
            if alias.replace(" ", "_") in name:
                return schema_key
    return None

def get_zib_rules(schema_key: str) -> dict:
    """Retourneert het veldregels-dict voor een ZIB schema_key."""
    return ZIB_FIELD_RULES.get(schema_key, {})
