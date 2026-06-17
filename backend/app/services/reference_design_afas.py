"""
reference_design_afas.py
────────────────────────
Gestructureerde weergave van het *Referentieontwerp KIK-V v6.0 Profit HRM (AFAS)*.

Dit referentieontwerp beschrijft de vertaling van AFAS Profit HRM brongegevens naar de
KIK-V Modelgegevensset. De data hieronder is overgenomen uit:
  - Hoofdstuk 3  "Vertaling naar benodigde gegevens"  (concept -> bronveld)
  - Hoofdstuk 4  "Database export"                    (gegevenselement -> attribuut)
  - Hoofdstuk 2  Uitgangspunten                       (uitwisselprofielen)

Wordt gebruikt door benchmark_against_reference() om een geladen AFAS-export te
vergelijken met wat het referentieontwerp voorschrijft.
"""
from __future__ import annotations

REFERENCE_META = {
    "standard":      "algemeen",
    "title":         "Referentieontwerp KIK-V v6.0 Profit HRM (AFAS)",
    "version":       "6.0",
    "leverancier":   "AFAS",
    "source_system": "Profit HRM",
    "model_version": "KIK-V Modelgegevensset",
}

# ── Statuscodes ────────────────────────────────────────────────────────────────
COVERED       = "covered"        # bronveld voorgeschreven én aanwezig in de data
MISSING       = "missing"        # bronveld voorgeschreven maar NIET aanwezig in de data
OUT_OF_SCOPE  = "out_of_scope"   # in v6.0 (nog) geen bronveld gedefinieerd in het ontwerp

# ── Gegevenselementen / concepten ──────────────────────────────────────────────
# Per gegevenselement (KIK-V hoofdconcept) de bijbehorende concepten/attributen.
# 'afas_attr'  : het voorgeschreven bronveld (zoals in het referentieontwerp, kolom B)
# 'field'      : de genormaliseerde AFAS-veldnaam waarop presence wordt gecheckt
#                (None => geen bronveld gedefinieerd => out_of_scope)
# 'aliases'    : alternatieve veldnamen die als gelijkwaardig gelden
# 'transform'  : voorgeschreven bewerking (kolom D), informatief
# 'note'       : toelichting (kolom E), informatief

REFERENCE_ELEMENTEN = [
    {
        "key": "mens",
        "label": "Mens",
        "concepts": [
            {"concept": "Mens (identificatie)", "afas_attr": "Employees.EmployeeId",
             "field": "EmployeeId", "aliases": ["PersonId"],
             "transform": "", "note": "Relatie Employees_basic met Employees controleren."},
            {"concept": "Geboortedatum", "afas_attr": "Employees.DateBirth",
             "field": "DateBirth", "aliases": ["DateOfBirth"],
             "transform": "", "note": ""},
        ],
    },
    {
        "key": "werkovereenkomst",
        "label": "WerkOvereenkomst",
        "concepts": [
            {"concept": "Mens (relatie)", "afas_attr": "Employees.EmployeeId",
             "field": "EmployeeId", "aliases": ["PersonId"], "transform": "", "note": ""},
            {"concept": "Arbeidsovereenkomst bepaalde tijd", "afas_attr": "Employees.EmploymentType",
             "field": "EmploymentType", "aliases": [],
             "transform": 'EmploymentType = "bepaalde tijd"/"halfjaarcontract"/"jaarcontract"/"x maanden"', "note": ""},
            {"concept": "Arbeidsovereenkomst onbepaalde tijd", "afas_attr": "Employees.EmploymentType",
             "field": "EmploymentType", "aliases": [],
             "transform": 'EmploymentType = "onbepaalde tijd"', "note": ""},
            {"concept": "Nulurencontract", "afas_attr": "Employees.EmploymentType",
             "field": "EmploymentType", "aliases": [], "transform": "EmploymentType = nulurencontract", "note": ""},
            {"concept": "Oproepcontract met voorovereenkomst", "afas_attr": "Employees.EmploymentType",
             "field": "EmploymentType", "aliases": [], "transform": "EmploymentType = oproepcontract met voorovereenkomst", "note": ""},
            {"concept": "Stage-overeenkomst", "afas_attr": "Employees.EmploymentType",
             "field": "EmploymentType", "aliases": [], "transform": "EmploymentType = stagair", "note": ""},
            {"concept": "Uitzendovereenkomst", "afas_attr": "Employees.EmploymentType",
             "field": "EmploymentType", "aliases": [], "transform": "EmploymentType = uitzendovereenkomst", "note": ""},
            {"concept": "Arbeidsovereenkomst BBL", "afas_attr": "Employees.EmploymentType",
             "field": "EmploymentType", "aliases": [], "transform": "EmploymentType = BBL", "note": ""},
            {"concept": "Vrijwilligersovereenkomst", "afas_attr": "",
             "field": None, "aliases": [], "transform": "", "note": "Geen bronveld in Profit HRM gedefinieerd."},
            {"concept": "WerkOvereenkomst startDatum", "afas_attr": "Employees.EmploymentStart",
             "field": "EmploymentStart", "aliases": [], "transform": "", "note": ""},
            {"concept": "WerkOvereenkomst eindDatum", "afas_attr": "Employees.EmploymentEnd",
             "field": "EmploymentEnd", "aliases": [], "transform": "", "note": ""},
            {"concept": "Functie", "afas_attr": "Employees.FunctionId",
             "field": "FunctionId", "aliases": [], "transform": "", "note": ""},
            {"concept": "Functie startDatum", "afas_attr": "Employees.EmploymentStart",
             "field": "EmploymentStart", "aliases": [], "transform": "", "note": ""},
            {"concept": "Functie eindDatum", "afas_attr": "Employees.EmploymentEnd",
             "field": "EmploymentEnd", "aliases": [], "transform": "", "note": ""},
            {"concept": "Vestiging", "afas_attr": "Employees.OrgUnit",
             "field": "OrgUnit", "aliases": [], "transform": "", "note": "Medewerker.org.eenheid"},
            {"concept": "Locatie", "afas_attr": "Employees.OrgUnit",
             "field": "OrgUnit", "aliases": [], "transform": "", "note": "Medewerker.org.eenheid"},
            {"concept": "Werkgever", "afas_attr": "",
             "field": None, "aliases": [], "transform": "", "note": "Geen bronveld gedefinieerd."},
            {"concept": "Contractomvang", "afas_attr": "Employees.HourPerWeek",
             "field": "HourPerWeek", "aliases": ["HoursPerWeek"], "transform": "", "note": "Gerelateerd: parttime%, min/max uren per week."},
            {"concept": "Contractomvang startDatum", "afas_attr": "Employees.EmploymentStart",
             "field": "EmploymentStart", "aliases": [], "transform": "", "note": ""},
            {"concept": "Contractomvang eindDatum", "afas_attr": "Employees.EmploymentEnd",
             "field": "EmploymentEnd", "aliases": [], "transform": "", "note": ""},
            {"concept": "Contractomvangwaarde", "afas_attr": "Employees.HourPerWeek",
             "field": "HourPerWeek", "aliases": ["HoursPerWeek"], "transform": "", "note": ""},
            {"concept": "Parttime factor", "afas_attr": "Employees.HourPerWeek",
             "field": "HourPerWeek", "aliases": ["HoursPerWeek", "PartTime"], "transform": "", "note": "Gerelateerd: parttime%."},
        ],
    },
    {
        "key": "verzuimperiode",
        "label": "Verzuimperiode",
        "concepts": [
            {"concept": "Mens (relatie)", "afas_attr": "Employees.EmployeeId",
             "field": "EmployeeId", "aliases": ["PersonId"], "transform": "", "note": ""},
            {"concept": "Ziekteperiode (verzuimmelding)", "afas_attr": "Illness.AbsenceTypeId",
             "field": "AbsenceTypeId", "aliases": [], "transform": "verzuimcode-type hanteren", "note": "verzuimmelding.Type"},
            {"concept": "Zwangerschapsverlof", "afas_attr": "",
             "field": None, "aliases": [], "transform": "", "note": "Geen bronveld gedefinieerd."},
            {"concept": "VerzuimTijdKwaliteit (ziekteverzuim%)", "afas_attr": "100% - Illness.Presence",
             "field": "Presence", "aliases": [], "transform": "100% - Illness.Presence", "note": "Nog toetsen in de praktijk."},
            {"concept": "DurationValue startDatum", "afas_attr": "Illness.startdate",
             "field": "StartDate", "aliases": ["startdate"], "transform": "", "note": "verzuimmelding.Begindatum/-tijd"},
            {"concept": "DurationValue eindDatum", "afas_attr": "Illness.enddate",
             "field": "EndDate", "aliases": ["enddate"], "transform": "", "note": "verzuimmelding.Einddatum/-tijd"},
        ],
    },
    {
        "key": "gewerkte_periode",
        "label": "Gewerkte periode",
        "concepts": [
            {"concept": "Mens", "afas_attr": "", "field": None, "aliases": [], "transform": "", "note": "Geen bronveld in Profit HRM gedefinieerd."},
            {"concept": "Werkovereenkomst", "afas_attr": "", "field": None, "aliases": [], "transform": "", "note": "Geen bronveld gedefinieerd."},
            {"concept": "Gewerkte tijd", "afas_attr": "", "field": None, "aliases": [], "transform": "", "note": "Geen bronveld gedefinieerd."},
            {"concept": "Startmoment", "afas_attr": "", "field": None, "aliases": [], "transform": "", "note": "Geen bronveld gedefinieerd."},
            {"concept": "Eindmoment", "afas_attr": "", "field": None, "aliases": [], "transform": "", "note": "Geen bronveld gedefinieerd."},
            {"concept": "Organisatieonderdeel", "afas_attr": "", "field": None, "aliases": [], "transform": "", "note": "Geen bronveld gedefinieerd."},
            {"concept": "Type inzet", "afas_attr": "", "field": None, "aliases": [], "transform": "", "note": "Geen bronveld gedefinieerd."},
        ],
    },
    {
        "key": "verloonde_periode",
        "label": "Verloonde periode",
        "concepts": [
            {"concept": "Mens", "afas_attr": "", "field": None, "aliases": [], "transform": "", "note": "Geen bronveld gedefinieerd."},
            {"concept": "Werkovereenkomst", "afas_attr": "", "field": None, "aliases": [], "transform": "", "note": "Geen bronveld gedefinieerd."},
            {"concept": "Verloonde tijd", "afas_attr": "", "field": None, "aliases": [], "transform": "", "note": "Geen bronveld gedefinieerd."},
            {"concept": "DurationValue", "afas_attr": "", "field": None, "aliases": [], "transform": "", "note": "Geen bronveld gedefinieerd."},
            {"concept": "TemporalQuality", "afas_attr": "", "field": None, "aliases": [], "transform": "", "note": "Geen bronveld gedefinieerd."},
            {"concept": "Vestiging", "afas_attr": "", "field": None, "aliases": [], "transform": "", "note": "Geen bronveld gedefinieerd."},
        ],
    },
]

# ── Uitwisselprofielen (Hoofdstuk 2) ───────────────────────────────────────────
# LET OP: in referentieontwerp v6.0 is de concept->uitwisselprofiel-matrix (welk
# concept voor welk profiel nodig is) NIET ingevuld. Profieldekking is daarom niet
# hard af te leiden uit dit document; onderstaande lijst is informatief.
UITWISSELPROFIELEN = [
    {"code": "ZK-IB",    "omschrijving": "Inkoopondersteuning en Beleidsontwikkeling"},
    {"code": "IGJ-CI",   "omschrijving": "Contextinformatie tbv Inspectiebezoek"},
    {"code": "NZa-BK",   "omschrijving": "Basisinformatie Kostenonderzoek"},
    {"code": "VWS-BM",   "omschrijving": "Beleidsontwikkeling en -monitoring"},
    {"code": "IGJ-CIO",  "omschrijving": "Contextinformatie onaangekondigd Inspectiebezoek"},
    {"code": "IGJ-CIA",  "omschrijving": "Contextinformatie aangekondigd Inspectiebezoek"},
    {"code": "NZA-BKN",  "omschrijving": "Basisinformatie Kostenonderzoek Nieuw"},
    {"code": "NZA-WMG",  "omschrijving": "Structurele Informatieverstrekking Bedrijfsvoering WMG"},
    {"code": "VWS-JV",   "omschrijving": "Jaarverantwoording"},
    {"code": "VWS-MEVA", "omschrijving": "Macro Economische Vraagstukken en Arbeidsmarkt"},
    {"code": "Actiz-BB", "omschrijving": "BelangenBehartiging"},
    {"code": "PFN-CK",   "omschrijving": "Ondersteuning CliëntKeuze Verpleging en Verzorging"},
    {"code": "ZK-CK",    "omschrijving": "Ondersteuning CliëntKeuze Verpleging en Verzorging"},
    {"code": "RIVM-SIV", "omschrijving": "Surveillance Infectieziekten Verpleeghuizen"},
    {"code": "RS",       "omschrijving": "Regionale Samenwerking"},
    {"code": "KB",       "omschrijving": "Kwaliteitsbeeld"},
]

PROFIEL_NOTE = (
    "In referentieontwerp v6.0 is de concept→uitwisselprofiel-matrix niet ingevuld. "
    "Profieldekking per profiel is daarom niet af te leiden uit dit document; de lijst is informatief. "
    "Zodra de matrix beschikbaar is, kan profieldekking automatisch worden berekend."
)
