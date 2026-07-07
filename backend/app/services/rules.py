"""
rules.py — Centrale configuratie voor KIK-V validatieregels

Dit is de ENIGE bron van waarheid voor:
  - Toegestane waarden (allowedValues) per veld
  - Veldlabels en beschrijvingen voor eindgebruikers
  - Verplichte velden en voorwaardelijke eisen
  - Bronverwijzingen naar de KIK-V standaard
  - concept_uri: koppeling naar de KIK-V ONZ-ontologie (stap 2 validatie)

Validator, export en frontend halen hun regels hieruit.
Voeg nieuwe contracttypes of verzuimcategorieën HIER toe — niet in validator.py.
"""

# ─── Ontologie namespaces ─────────────────────────────────────────────────────
ONZ_PERS = "http://purl.org/ozo/onz-pers#"
ONZ_G    = "http://purl.org/ozo/onz-g#"
ONZ_ORG  = "http://purl.org/ozo/onz-org#"
ONZ_ZORG = "http://purl.org/ozo/onz-zorg#"
ONZ_FIN  = "http://purl.org/ozo/onz-fin#"

# ─── Contracttype (OvereenkomstType) ──────────────────────────────────────────
# Bron: KIK-V Modelgegevensset — OvereenkomstType codelijst
# Tijdelijk = einddatum verplicht
# concept_uri verwijst naar de OWL-klasse in onz-pers
CONTRACTTYPE_ALLOWED = [
    {"value": "bepaalde tijd",                       "label": "Bepaalde tijd",                        "tijdelijk": True,  "concept_uri": f"{ONZ_PERS}ArbeidsOvereenkomstBepaaldeTijd"},
    {"value": "halfjaarcontract",                    "label": "Halfjaarcontract",                     "tijdelijk": True,  "concept_uri": f"{ONZ_PERS}ArbeidsOvereenkomstBepaaldeTijd"},
    {"value": "jaarcontract",                        "label": "Jaarcontract",                         "tijdelijk": True,  "concept_uri": f"{ONZ_PERS}ArbeidsOvereenkomstBepaaldeTijd"},
    {"value": "onbepaalde tijd",                     "label": "Onbepaalde tijd",                      "tijdelijk": False, "concept_uri": f"{ONZ_PERS}ArbeidsOvereenkomstOnbepaaldeTijd"},
    {"value": "nulurencontract",                     "label": "Nulurencontract",                      "tijdelijk": False, "concept_uri": f"{ONZ_PERS}NulUrenContract"},
    {"value": "oproepcontract met voorovereenkomst", "label": "Oproepcontract met voorovereenkomst",  "tijdelijk": True,  "concept_uri": f"{ONZ_PERS}OproepcontractMetVoorovereenkomst"},
    {"value": "stagiar",                             "label": "Stagiar",                              "tijdelijk": True,  "concept_uri": f"{ONZ_PERS}StageOvereenkomst"},
    {"value": "uitzendovereenkomst",                 "label": "Uitzendovereenkomst",                  "tijdelijk": True,  "concept_uri": f"{ONZ_PERS}UitzendOvereenkomst"},
    {"value": "bbl",                                 "label": "BBL (Beroepsbegeleidende Leerweg)",    "tijdelijk": True,  "concept_uri": f"{ONZ_PERS}ArbeidsOvereenkomstBBL"},
]

# Afleidingen voor gebruik in de validator
CONTRACTTYPE_VALUES     = [av["value"] for av in CONTRACTTYPE_ALLOWED]
CONTRACTTYPE_TIJDELIJK  = {av["value"] for av in CONTRACTTYPE_ALLOWED if av["tijdelijk"]}

# ─── Soort verzuim ────────────────────────────────────────────────────────────
# Bron: KIK-V Modelgegevensset — SoortVerzuim codelijst
# concept_uri verwijst naar de OWL-subklasse van VerzuimPeriode in onz-pers
VERZUIMTYPE_ALLOWED = [
    {"value": "ziek",                "label": "Ziek",                "concept_uri": f"{ONZ_PERS}ZiektePeriode"},
    {"value": "zwangerschapsverlof", "label": "Zwangerschapsverlof", "concept_uri": f"{ONZ_PERS}ZwangerschapsVerlof"},
    {"value": "arbeidsongeschikt",   "label": "Arbeidsongeschikt",   "concept_uri": f"{ONZ_PERS}ArbeidsOngeschiktheid"},
    {"value": "bijzonder verlof",    "label": "Bijzonder verlof",    "concept_uri": f"{ONZ_PERS}VerzuimPeriode"},
]

VERZUIMTYPE_VALUES = [av["value"] for av in VERZUIMTYPE_ALLOWED]

# ─── AFAS-verzuim mapping → KIK-V SoortVerzuim ────────────────────────────────
# AFAS levert de verzuimsoort als code (AbsenceTypeId) en/of omschrijving
# (AbsenceTypeDesc). Beide mappen we naar de KIK-V SoortVerzuim-waarden.
# NB: bevestigd met domein/KIK-V (2026-06). Twijfelgevallen gemarkeerd.
AFAS_VERZUIM_CODE_MAP = {
    "a":   "bijzonder verlof",      # Adoptie
    "b":   "ziek",                  # Bedrijfsongeval
    "d":   "arbeidsongeschikt",     # Arbeidsongeschikt door derde
    "o":   "ziek",                  # Overig ongeval
    "p":   "bijzonder verlof",      # Pleegzorg
    "z":   "ziek",                  # Ziek
    "zb":  "ziek",                  # Ziek a.g.v. bevalling
    "zod": "ziek",                  # Ziek a.g.v. orgaandonatie
    "zzw": "zwangerschapsverlof",   # Ziek a.g.v. zwangerschap
    "zw":  "zwangerschapsverlof",   # Zwangerschap / bevalling
}
AFAS_VERZUIM_DESC_MAP = {
    "adoptie":                          "bijzonder verlof",
    "bedrijfsongeval":                  "ziek",
    "arbeidsongeschikt door derde":     "arbeidsongeschikt",
    "overig ongeval":                   "ziek",
    "pleegzorg":                        "bijzonder verlof",
    "ziek":                             "ziek",
    "ziek als gevolg van bevalling":    "ziek",
    "ziek als gevolg van orgaandonatie":"ziek",
    "ziek als gevolg van zwangerschap": "zwangerschapsverlof",
    "zwangerschap / bevalling":         "zwangerschapsverlof",
    "zwangerschap/bevalling":           "zwangerschapsverlof",
}

def normalize_verzuimtype(val) -> str:
    """Map een AFAS-code of -omschrijving naar de KIK-V SoortVerzuim-waarde.
    Geeft een al-geldige KIK-V-waarde ongewijzigd terug; onbekende waarden
    blijven staan (worden dan terecht afgekeurd)."""
    if val is None:
        return ""
    v = str(val).strip().lower()
    if not v:
        return ""
    if v in VERZUIMTYPE_VALUES:        return v
    if v in AFAS_VERZUIM_DESC_MAP:     return AFAS_VERZUIM_DESC_MAP[v]
    if v in AFAS_VERZUIM_CODE_MAP:     return AFAS_VERZUIM_CODE_MAP[v]
    return v


# ─── FIELD_RULES — compleet regeloverzicht per schema/veld ────────────────────
# concept_uri: URI van het bijbehorende KIK-V ontologieconcept (stap 2 validatie)
FIELD_RULES: dict = {
    "werkovereenkomst": {
        "overeenkomsttype": {
            "label":        "Contracttype",
            "description":  "Type arbeidsovereenkomst conform de KIK-V OvereenkomstType codelijst.",
            "required":     True,
            "source":       "KIK-V OvereenkomstType codelijst",
            "concept_uri":  f"{ONZ_PERS}WerkOvereenkomst",
            "concept_label": "Werkovereenkomst",
            "allowedValues": CONTRACTTYPE_ALLOWED,
        },
        "startdatum": {
            "label":        "Startdatum",
            "description":  "Ingangsdatum van het dienstverband.",
            "required":     True,
            "format":       "dd/mm/yyyy",
            "concept_uri":  f"{ONZ_G}startDatum",
            "concept_label": "startdatum",
        },
        "einddatum": {
            "label":        "Einddatum",
            "description":  "Einddatum van het contract. Verplicht bij tijdelijke contracttypes.",
            "required":     False,
            "requiredWhen": "Contracttype is tijdelijk (bepaalde tijd, halfjaarcontract, jaarcontract, "
                            "oproepcontract met voorovereenkomst, stagiar, uitzendovereenkomst, bbl).",
            "format":       "dd/mm/yyyy",
            "concept_uri":  f"{ONZ_G}eindDatum",
            "concept_label": "einddatum",
        },
        "personeelsnummer": {
            "label":        "Personeelsnummer",
            "description":  "Uniek identificatienummer van de medewerker.",
            "required":     True,
            "concept_uri":  f"{ONZ_G}EmployeeIdentifier",
            "concept_label": "Werknemersidentifier",
        },
        "dienstverbandnummer": {
            "label":        "Dienstverbandnummer",
            "description":  "Uniek identificatienummer van het dienstverband.",
            "required":     True,
            "concept_uri":  f"{ONZ_G}FormalIdentifier",
            "concept_label": "Formele identifier",
        },
        "urenperweek": {
            "label":        "Uren per week",
            "description":  "Contractueel aantal uren per week.",
            "required":     False,
            "format":       "Getal (bijv. 36)",
            "concept_uri":  f"{ONZ_PERS}ContractOmvang",
            "concept_label": "Contractomvang",
        },
    },
    "medewerker": {
        "personeelsnummer": {
            "label":        "Personeelsnummer",
            "description":  "Uniek identificatienummer van de medewerker.",
            "required":     True,
            "concept_uri":  f"{ONZ_G}EmployeeIdentifier",
            "concept_label": "Werknemersidentifier",
        },
        "geboortedatum": {
            "label":        "Geboortedatum",
            "description":  "Geboortedatum van de medewerker.",
            "required":     True,
            "format":       "dd/mm/yyyy",
            "concept_uri":  f"{ONZ_G}hasDateOfBirth",
            "concept_label": "heeft geboortedatum",
        },
    },
    "functie": {
        "functie": {
            "label":        "Functienaam",
            "description":  "Naam van de functie.",
            "required":     True,
            "concept_uri":  f"{ONZ_PERS}ZorgverlenerFunctie",
            "concept_label": "Zorgverlener (functie)",
        },
        "kwalificatieniveau": {
            "label":        "Kwalificatieniveau",
            "description":  "KIK-V kwalificatieniveaucode gekoppeld aan de functie.",
            "required":     False,
            "source":       "KIK-V KwalificatieNiveau referentietabel",
            "concept_uri":  f"{ONZ_PERS}IGJKwalificatieWaarde",
            "concept_label": "IGJ Kwalificatiewaarde",
        },
    },
    "verzuim": {
        "personeelsnummer": {
            "label":        "Personeelsnummer",
            "description":  "Personeelsnummer van de medewerker.",
            "required":     True,
            "concept_uri":  f"{ONZ_G}EmployeeIdentifier",
            "concept_label": "Werknemersidentifier",
        },
        "soortverzuim": {
            "label":        "Soort verzuim",
            "description":  "Categorie van het verzuim conform de KIK-V SoortVerzuim codelijst.",
            "required":     False,
            "source":       "KIK-V SoortVerzuim codelijst",
            "concept_uri":  f"{ONZ_PERS}VerzuimPeriode",
            "concept_label": "Verzuimperiode",
            "allowedValues": VERZUIMTYPE_ALLOWED,
        },
        "startmoment": {
            "label":        "Startmoment",
            "description":  "Startdatum van de verzuimperiode.",
            "required":     True,
            "format":       "dd/mm/yyyy",
            "concept_uri":  f"{ONZ_G}startDatum",
            "concept_label": "startdatum",
        },
        "eindmoment": {
            "label":        "Eindmoment",
            "description":  "Einddatum van de verzuimperiode.",
            "required":     False,
            "format":       "dd/mm/yyyy",
            "concept_uri":  f"{ONZ_G}eindDatum",
            "concept_label": "einddatum",
        },
        "verzuimpercentage": {
            "label":        "Verzuimpercentage",
            "description":  "Mate van arbeidsongeschiktheid als percentage.",
            "required":     False,
            "format":       "Getal tussen 0 en 100",
            "concept_uri":  f"{ONZ_PERS}AOPercentage",
            "concept_label": "Arbeidsongeschiktheidspercentage",
        },
    },

    # ── Vestiging ─────────────────────────────────────────────────────────────
    # Bron: KIK-V Zorgkantoren uitwisselprofiel — locatiegegevens
    "vestiging": {
        "vestigingsnummer": {
            "label":        "Vestigingsnummer",
            "description":  "Uniek identificatienummer van de vestiging (AGB-code of intern nummer).",
            "required":     True,
            "source":       "KIK-V onz-org#Vestigingsnummer",
            "concept_uri":  f"{ONZ_ORG}Vestigingsnummer",
            "concept_label": "Vestigingsnummer",
        },
        "naam": {
            "label":        "Naam vestiging",
            "description":  "Officiële naam van de zorglocatie of vestiging.",
            "required":     True,
            "concept_uri":  f"{ONZ_ORG}Vestiging",
            "concept_label": "Vestiging",
        },
        "zorgkantoorregiocode": {
            "label":        "Zorgkantoor regiocode",
            "description":  "Code van het zorgkantoor-regio waartoe de vestiging behoort (vereist voor Zorgkantoren uitwisseling).",
            "required":     True,
            "source":       "KIK-V Zorgkantoor regio codelijst",
            "concept_uri":  f"{ONZ_ORG}ZorgkantoorRegio",
            "concept_label": "Zorgkantoor regio",
        },
    },

    # ── Cliënt ────────────────────────────────────────────────────────────────
    # Bron: KIK-V Zorgkantoren + VWS + IGJ uitwisselprofielen — cliëntgegevens
    "client": {
        "clientid": {
            "label":        "Cliënt-ID",
            "description":  "Unieke interne identificatie van de cliënt.",
            "required":     True,
            "concept_uri":  f"{ONZ_G}FormalIdentifier",
            "concept_label": "Formele identifier",
        },
        "geboortedatum": {
            "label":        "Geboortedatum",
            "description":  "Geboortedatum van de cliënt (voor leeftijdscategorisering KIK-V).",
            "required":     True,
            "format":       "dd/mm/yyyy",
            "concept_uri":  f"{ONZ_G}hasDateOfBirth",
            "concept_label": "heeft geboortedatum",
        },
        "wlzindicatie": {
            "label":        "WLZ-indicatie",
            "description":  "Wet Langdurige Zorg indicatiebesluit van de cliënt.",
            "required":     False,
            "source":       "KIK-V WlzIndicatie — onz-zorg",
            "concept_uri":  f"{ONZ_ZORG}WlzIndicatie",
            "concept_label": "Wlz-indicatie",
        },
        "wmoindicatie": {
            "label":        "WMO-indicatie",
            "description":  "Wet Maatschappelijke Ondersteuning indicatie van de cliënt.",
            "required":     False,
            "source":       "KIK-V WmoIndicatie — onz-zorg",
            "concept_uri":  f"{ONZ_ZORG}WmoIndicatie",
            "concept_label": "Wmo-indicatie",
        },
        "zorgprofiel": {
            "label":        "Zorgprofiel / ZZP",
            "description":  "Zorgzwaartepakket of leveringsvorm van de cliënt.",
            "required":     False,
            "source":       "KIK-V ZorgProfiel — onz-zorg",
            "concept_uri":  f"{ONZ_ZORG}ZorgProfiel",
            "concept_label": "Zorgprofiel",
        },
    },

    # ── Kostenplaats ──────────────────────────────────────────────────────────
    # Bron: KIK-V NZa kostenonderzoek + VWS Jaarverantwoording — financiën
    "kostenplaats": {
        "kostenplaatsid": {
            "label":        "Kostenplaats-ID",
            "description":  "Unieke code van de kostenplaats.",
            "required":     True,
            "concept_uri":  f"{ONZ_FIN}Kostenplaats",
            "concept_label": "Kostenplaats",
        },
        "omschrijving": {
            "label":        "Omschrijving",
            "description":  "Naam of omschrijving van de kostenplaats.",
            "required":     False,
            "concept_uri":  f"{ONZ_FIN}Kostenplaats",
            "concept_label": "Kostenplaats",
        },
        "bedrag": {
            "label":        "Bedrag / budget",
            "description":  "Gerealiseerd bedrag of budget op de kostenplaats.",
            "required":     True,
            "format":       "Getal (euro, bijv. 12345.67)",
            "concept_uri":  f"{ONZ_FIN}EindSaldo",
            "concept_label": "Eind saldo",
        },
        "periode": {
            "label":        "Periode",
            "description":  "Boekingsperiode (jaar of jaar+maand).",
            "required":     False,
            "format":       "Getal (bijv. 2024 of 202401)",
            "concept_uri":  f"{ONZ_FIN}VerloondePeriode",
            "concept_label": "Verloonde periode",
        },
    },

    # ── Grootboek ─────────────────────────────────────────────────────────────
    # Bron: KIK-V NZa kostenonderzoek + VWS Jaarverantwoording — grootboek
    "grootboek": {
        "rekeningnummer": {
            "label":        "Rekeningnummer",
            "description":  "Grootboekrekening-nummer conform de jaarrekening.",
            "required":     True,
            "concept_uri":  f"{ONZ_FIN}Grootboekrubriek",
            "concept_label": "Grootboekrubriek",
        },
        "omschrijving": {
            "label":        "Omschrijving",
            "description":  "Naam of omschrijving van de grootboekrekening.",
            "required":     False,
            "concept_uri":  f"{ONZ_FIN}Grootboekrubriek",
            "concept_label": "Grootboekrubriek",
        },
        "bedrag": {
            "label":        "Bedrag / saldo",
            "description":  "Gerealiseerd bedrag of saldo op de grootboekrekening.",
            "required":     True,
            "format":       "Getal (euro, bijv. 12345.67)",
            "concept_uri":  f"{ONZ_FIN}Grootboekpost",
            "concept_label": "Grootboekpost",
        },
    },
}


def get_field_label(schema_key: str, field_key: str) -> str:
    """Geeft het gebruikersvriendelijke label voor een veld terug."""
    return FIELD_RULES.get(schema_key, {}).get(field_key, {}).get("label", field_key)


def get_allowed_values(schema_key: str, field_key: str) -> list:
    """Geeft de lijst van toegestane waarden (als dicts) terug, of []."""
    return FIELD_RULES.get(schema_key, {}).get(field_key, {}).get("allowedValues", [])


def get_concept_uri(schema_key: str, field_key: str) -> str | None:
    """Geeft de ontologie-concept-URI terug voor een schema/veld combinatie."""
    return FIELD_RULES.get(schema_key, {}).get(field_key, {}).get("concept_uri")


def format_allowed_short(allowed_values: list, max_shown: int = 3) -> str:
    """
    Formatteert toegestane waarden beknopt voor eindgebruikers.
    Voorbeeld: 'bepaalde tijd, halfjaarcontract, jaarcontract of 6 andere'
    """
    labels = [av["label"] if isinstance(av, dict) else av for av in allowed_values]
    if len(labels) <= max_shown:
        return ", ".join(labels)
    shown = labels[:max_shown]
    rest  = len(labels) - max_shown
    return f"{', '.join(shown)} of {rest} andere"
