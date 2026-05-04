"""
rules.py — Centrale configuratie voor KIK-V validatieregels

Dit is de ENIGE bron van waarheid voor:
  - Toegestane waarden (allowedValues) per veld
  - Veldlabels en beschrijvingen voor eindgebruikers
  - Verplichte velden en voorwaardelijke eisen
  - Bronverwijzingen naar de KIK-V standaard

Validator, export en frontend halen hun regels hieruit.
Voeg nieuwe contracttypes of verzuimcategorieën HIER toe — niet in validator.py.
"""

# ─── Contracttype (OvereenkomstType) ──────────────────────────────────────────
# Bron: KIK-V Modelgegevensset — OvereenkomstType codelijst
# Tijdelijk = einddatum verplicht
CONTRACTTYPE_ALLOWED = [
    {"value": "bepaalde tijd",                       "label": "Bepaalde tijd",                        "tijdelijk": True},
    {"value": "halfjaarcontract",                    "label": "Halfjaarcontract",                     "tijdelijk": True},
    {"value": "jaarcontract",                        "label": "Jaarcontract",                         "tijdelijk": True},
    {"value": "onbepaalde tijd",                     "label": "Onbepaalde tijd",                      "tijdelijk": False},
    {"value": "nulurencontract",                     "label": "Nulurencontract",                      "tijdelijk": False},
    {"value": "oproepcontract met voorovereenkomst", "label": "Oproepcontract met voorovereenkomst",  "tijdelijk": True},
    {"value": "stagiar",                             "label": "Stagiar",                              "tijdelijk": True},
    {"value": "uitzendovereenkomst",                 "label": "Uitzendovereenkomst",                  "tijdelijk": True},
    {"value": "bbl",                                 "label": "BBL (Beroepsbegeleidende Leerweg)",    "tijdelijk": True},
]

# Afleidingen voor gebruik in de validator
CONTRACTTYPE_VALUES     = [av["value"] for av in CONTRACTTYPE_ALLOWED]
CONTRACTTYPE_TIJDELIJK  = {av["value"] for av in CONTRACTTYPE_ALLOWED if av["tijdelijk"]}

# ─── Soort verzuim ────────────────────────────────────────────────────────────
# Bron: KIK-V Modelgegevensset — SoortVerzuim codelijst
VERZUIMTYPE_ALLOWED = [
    {"value": "ziek",                "label": "Ziek"},
    {"value": "zwangerschapsverlof", "label": "Zwangerschapsverlof"},
    {"value": "arbeidsongeschikt",   "label": "Arbeidsongeschikt"},
    {"value": "bijzonder verlof",    "label": "Bijzonder verlof"},
]

VERZUIMTYPE_VALUES = [av["value"] for av in VERZUIMTYPE_ALLOWED]

# ─── FIELD_RULES — compleet regeloverzicht per schema/veld ────────────────────
FIELD_RULES: dict = {
    "werkovereenkomst": {
        "overeenkomsttype": {
            "label":        "Contracttype",
            "description":  "Type arbeidsovereenkomst conform de KIK-V OvereenkomstType codelijst.",
            "required":     True,
            "source":       "KIK-V OvereenkomstType codelijst",
            "allowedValues": CONTRACTTYPE_ALLOWED,
        },
        "startdatum": {
            "label":        "Startdatum",
            "description":  "Ingangsdatum van het dienstverband.",
            "required":     True,
            "format":       "dd/mm/yyyy",
        },
        "einddatum": {
            "label":        "Einddatum",
            "description":  "Einddatum van het contract. Verplicht bij tijdelijke contracttypes.",
            "required":     False,
            "requiredWhen": "Contracttype is tijdelijk (bepaalde tijd, halfjaarcontract, jaarcontract, "
                            "oproepcontract met voorovereenkomst, stagiar, uitzendovereenkomst, bbl).",
            "format":       "dd/mm/yyyy",
        },
        "personeelsnummer": {
            "label":        "Personeelsnummer",
            "description":  "Uniek identificatienummer van de medewerker.",
            "required":     True,
        },
        "dienstverbandnummer": {
            "label":        "Dienstverbandnummer",
            "description":  "Uniek identificatienummer van het dienstverband.",
            "required":     True,
        },
    },
    "medewerker": {
        "personeelsnummer": {
            "label":        "Personeelsnummer",
            "description":  "Uniek identificatienummer van de medewerker.",
            "required":     True,
        },
        "geboortedatum": {
            "label":        "Geboortedatum",
            "description":  "Geboortedatum van de medewerker.",
            "required":     True,
            "format":       "dd/mm/yyyy",
        },
    },
    "functie": {
        "functie": {
            "label":        "Functienaam",
            "description":  "Naam van de functie.",
            "required":     True,
        },
        "kwalificatieniveau": {
            "label":        "Kwalificatieniveau",
            "description":  "KIK-V kwalificatieniveaucode gekoppeld aan de functie.",
            "required":     False,
            "source":       "KIK-V KwalificatieNiveau referentietabel",
        },
    },
    "verzuim": {
        "personeelsnummer": {
            "label":        "Personeelsnummer",
            "description":  "Personeelsnummer van de medewerker.",
            "required":     True,
        },
        "soortverzuim": {
            "label":        "Soort verzuim",
            "description":  "Categorie van het verzuim conform de KIK-V SoortVerzuim codelijst.",
            "required":     False,
            "source":       "KIK-V SoortVerzuim codelijst",
            "allowedValues": VERZUIMTYPE_ALLOWED,
        },
        "startmoment": {
            "label":        "Startmoment",
            "description":  "Startdatum van de verzuimperiode.",
            "required":     True,
            "format":       "dd/mm/yyyy",
        },
        "eindmoment": {
            "label":        "Eindmoment",
            "description":  "Einddatum van de verzuimperiode.",
            "required":     False,
            "format":       "dd/mm/yyyy",
        },
        "verzuimpercentage": {
            "label":        "Verzuimpercentage",
            "description":  "Mate van arbeidsongeschiktheid als percentage.",
            "required":     False,
            "format":       "Getal tussen 0 en 100",
        },
    },
}


def get_field_label(schema_key: str, field_key: str) -> str:
    """Geeft het gebruikersvriendelijke label voor een veld terug."""
    return FIELD_RULES.get(schema_key, {}).get(field_key, {}).get("label", field_key)


def get_allowed_values(schema_key: str, field_key: str) -> list:
    """Geeft de lijst van toegestane waarden (als dicts) terug, of []."""
    return FIELD_RULES.get(schema_key, {}).get(field_key, {}).get("allowedValues", [])


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
