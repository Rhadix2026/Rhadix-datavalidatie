"""
source_systems.py — Bibliotheek van bronsystemen en hun KIK-V veldmappings.

Elke entry beschrijft:
  - id:           Unieke sleutel (gebruikt in de validator)
  - label:        Weergavenaam in de UI
  - vendor:       Leverancier
  - version:      Versie van het referentieontwerp
  - color:        Kleur in de UI
  - schemas:      Per KIK-V schema: de verwachte exportkolomnamen
  - notes:        Aandachtspunten en beperkingen

Voeg een nieuw bronsysteem toe door een nieuw blok te kopiëren en aan te passen.
De validator laadt de col_aliases uit dit bestand — niet aanpassen in validator.py.
"""

# ─────────────────────────────────────────────────────────────────────────────
# CONTRACT TYPE CODE VERTALINGEN per bronsysteem
# Waarde in het bronsysteem → KIK-V OvereenkomstType waarde
# ─────────────────────────────────────────────────────────────────────────────

CONTRACT_TYPE_TRANSLATIONS: dict[str, dict[str, str]] = {
    "nedap_ons": {
        # Contracts.contractType.name codes → KIK-V waarden
        "v":  "onbepaalde tijd",       # Vaste arbeidsovereenkomst
        "o":  "oproepcontract met voorovereenkomst",
        "s":  "stagiar",               # Stage-overeenkomst
        "e":  "uitzendovereenkomst",   # Extern/Uitzend
        # Niet beschikbaar in standaard ONS export:
        # bepaalde tijd, nulurencontract, bbl, vrijwilligersovereenkomst
    },
    "afas_hrm": {
        # AFAS exporteert al de KIK-V tekst, geen vertaling nodig
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# BRONSYSTEEM BIBLIOTHEEK
# ─────────────────────────────────────────────────────────────────────────────

SOURCE_SYSTEMS: dict[str, dict] = {

    # ── AFAS Profit HRM ───────────────────────────────────────────────────────
    "afas_hrm": {
        "id":      "afas_hrm",
        "label":   "AFAS Profit HRM",
        "vendor":  "AFAS Software",
        "version": "KIK-V referentieontwerp standaard",
        "color":   "#2d6be4",
        "icon":    "A",
        "description": (
            "HR- en salarissysteem. AFAS exporteert data als CSV via GetConnector. "
            "Kolomnamen zijn grotendeels Nederlandstalig en sluiten al nauw aan "
            "op de KIK-V Modelgegevensset."
        ),
        "schemas": {
            "medewerker": {
                "label":       "Medewerkers export",
                "source_name": "Employees (AFAS Profit HRM)",
                "fields": {
                    "personeelsnummer": {
                        "ons_kolom":     "PersoneelsNummer",
                        "type":          "string",
                        "required":      True,
                        "toelichting":   "Uniek medewerker-ID binnen AFAS.",
                    },
                    "geboortedatum": {
                        "ons_kolom":     "GeboorteDatum",
                        "type":          "date (dd/mm/yyyy)",
                        "required":      True,
                        "toelichting":   "Geboortedatum van de medewerker.",
                    },
                },
            },
            "werkovereenkomst": {
                "label":       "Werkovereenkomsten export",
                "source_name": "Employees.Employment (AFAS Profit HRM)",
                "fields": {
                    "dienstverbandnummer": {
                        "ons_kolom":     "DienstverbandNummer",
                        "type":          "string",
                        "required":      True,
                        "toelichting":   "Uniek ID per dienstverband.",
                    },
                    "personeelsnummer": {
                        "ons_kolom":     "PersoneelsNummer",
                        "type":          "string",
                        "required":      True,
                        "toelichting":   "Koppeling naar medewerker.",
                    },
                    "overeenkomsttype": {
                        "ons_kolom":     "OvereenkomstType",
                        "type":          "string (KIK-V codelijst)",
                        "required":      True,
                        "toelichting":   "Exporteert al de KIK-V tekst, geen vertaling nodig.",
                    },
                    "startdatum": {
                        "ons_kolom":     "StartDatum",
                        "type":          "date (dd/mm/yyyy)",
                        "required":      True,
                        "toelichting":   "Ingangsdatum van het dienstverband.",
                    },
                    "einddatum": {
                        "ons_kolom":     "EindDatum",
                        "type":          "date (dd/mm/yyyy)",
                        "required":      False,
                        "toelichting":   "Verplicht bij tijdelijke contracttypes.",
                    },
                },
            },
            "verzuim": {
                "label":       "Verzuim export",
                "source_name": "Illness (AFAS Profit HRM)",
                "fields": {
                    "personeelsnummer": {
                        "ons_kolom": "PersoneelsNummer",
                        "type":      "string",
                        "required":  True,
                    },
                    "startmoment": {
                        "ons_kolom": "Startmoment",
                        "type":      "date (dd/mm/yyyy)",
                        "required":  True,
                    },
                    "eindmoment": {
                        "ons_kolom": "Eindmoment",
                        "type":      "date (dd/mm/yyyy)",
                        "required":  False,
                    },
                    "verzuimpercentage": {
                        "ons_kolom": "VerzuimPercentage",
                        "type":      "number (0-100)",
                        "required":  False,
                    },
                },
            },
        },
        "notes": [
            "AFAS exporteert kolomnamen in PascalCase (bijv. PersoneelsNummer).",
            "OvereenkomstType wordt al in de KIK-V tekst geëxporteerd — geen vertaling nodig.",
            "Verzuimpercentage beschikbaar als 'Presence' (100 - aanwezigheidspercentage).",
        ],
        "export_method": "GetConnector (REST API of CSV-export via AFAS UI)",
    },

    # ── Nedap ONS ─────────────────────────────────────────────────────────────
    "nedap_ons": {
        "id":      "nedap_ons",
        "label":   "Nedap ONS",
        "vendor":  "Nedap",
        "version": "KIK-V Referentieontwerp ONS v6.0 (11-05-2025)",
        "color":   "#0ea5e9",
        "icon":    "N",
        "description": (
            "Zorginformatiesysteem voor VVT, GHZ en GGZ. ONS registreert cliënt- en "
            "medewerkergegevens. Kolomnamen zijn Engelstalig (camelCase). "
            "Contracttypes worden als code geëxporteerd (V/O/S/E) en vereisen vertaling "
            "naar KIK-V waarden. Verzuimpercentage is niet beschikbaar in standaard export."
        ),
        "schemas": {
            "medewerker": {
                "label":       "Employees export",
                "source_name": "Employees (Nedap ONS)",
                "fields": {
                    "personeelsnummer": {
                        "ons_kolom":   "identificationNo",
                        "alternatief": "employeeId / employeeObjectId",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Medewerkernummer in ONS.",
                    },
                    "geboortedatum": {
                        "ons_kolom":   "dateOfBirth",
                        "type":        "date",
                        "required":    True,
                        "toelichting": "Geboortedatum van de medewerker.",
                    },
                },
            },
            "werkovereenkomst": {
                "label":       "Contracts export",
                "source_name": "Contracts (Nedap ONS)",
                "fields": {
                    "dienstverbandnummer": {
                        "ons_kolom":   "objectId",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Contracts.objectId — uniek contract-ID.",
                    },
                    "personeelsnummer": {
                        "ons_kolom":   "employeeId",
                        "alternatief": "employeeObjectId",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Koppeling naar Employees.identificationNo.",
                    },
                    "overeenkomsttype": {
                        "ons_kolom":   "contractType / contractType.name",
                        "type":        "code (V/O/S/E)",
                        "required":    True,
                        "toelichting": (
                            "ONS exporteert een code. Vertaling naar KIK-V: "
                            "V=onbepaalde tijd, O=oproepcontract met voorovereenkomst, "
                            "S=stagiar, E=uitzendovereenkomst. "
                            "Bepaalde tijd, nulurencontract en BBL zijn niet beschikbaar."
                        ),
                    },
                    "startdatum": {
                        "ons_kolom":   "beginDate",
                        "type":        "date",
                        "required":    True,
                        "toelichting": "Contracts.beginDate — startdatum van het contract.",
                    },
                    "einddatum": {
                        "ons_kolom":   "endDate",
                        "type":        "date",
                        "required":    False,
                        "toelichting": "Contracts.endDate — einddatum (leeg = actief contract).",
                    },
                    "urenperweek": {
                        "ons_kolom":   "fixedHoursPerWeek",
                        "type":        "number",
                        "required":    False,
                        "toelichting": "Contracts.fixedHoursPerWeek — contractomvang.",
                    },
                },
            },
            "functie": {
                "label":       "Expertise_profiles export",
                "source_name": "Expertise_profiles + expertise_profile_assignments (Nedap ONS)",
                "fields": {
                    "functie": {
                        "ons_kolom":   "description",
                        "type":        "string",
                        "required":    True,
                        "toelichting": (
                            "Expertise_profiles.description — functieomschrijving. "
                            "Koppeling via employeeObjectId → expertise_profile_assignments "
                            "→ expertise_profiles."
                        ),
                    },
                    "startdatum": {
                        "ons_kolom":   "startTime",
                        "type":        "date",
                        "required":    False,
                        "toelichting": "expertise_profile_assignments.startTime.",
                    },
                    "einddatum": {
                        "ons_kolom":   "endTime",
                        "type":        "date",
                        "required":    False,
                        "toelichting": "expertise_profile_assignments.endTime.",
                    },
                },
            },
            "verzuim": {
                "label":       "Presence_logs export (verzuim)",
                "source_name": "Presence_logs + Activities (Nedap ONS)",
                "fields": {
                    "personeelsnummer": {
                        "ons_kolom":   "employeeId",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "presence_logs.employeeId → Employees.identificationNo.",
                    },
                    "soortverzuim": {
                        "ons_kolom":   "description (activities)",
                        "type":        "string",
                        "required":    False,
                        "toelichting": (
                            "activities.description geeft het soort verzuim: "
                            "'Ziekte' = ziekteperiode, 'Zwangerschapsverlof' = zwangerschapsverlof. "
                            "Koppeling: presence_logs.activityObjectId → activities.objectId."
                        ),
                    },
                    "startmoment": {
                        "ons_kolom":   "startDate",
                        "type":        "date",
                        "required":    True,
                        "toelichting": "Presence_logs.startDate — minimum startdatum per verzuimperiode.",
                    },
                    "eindmoment": {
                        "ons_kolom":   "endDate",
                        "type":        "date",
                        "required":    False,
                        "toelichting": "Presence_logs.endDate — maximum datum per verzuimperiode.",
                    },
                    "verzuimpercentage": {
                        "ons_kolom":   "— (niet beschikbaar)",
                        "type":        "n.v.t.",
                        "required":    False,
                        "toelichting": (
                            "VerzuimTijdKwaliteit (ziekteverzuimpercentage) is niet standaard "
                            "beschikbaar in ONS. Eventueel te berekenen via uren activities "
                            "ten opzichte van contracturen."
                        ),
                        "niet_beschikbaar": True,
                    },
                },
            },
        },
        "notes": [
            "ONS exporteert kolomnamen in camelCase (bijv. identificationNo, beginDate).",
            "ContractType wordt als code geëxporteerd (V/O/S/E) — vertaling naar KIK-V vereist.",
            "Bepaalde tijd, nulurencontract en BBL zijn niet beschikbaar in standaard ONS export.",
            "Verzuimpercentage is niet beschikbaar; berekening vereist maatwerk.",
            "Vestiging/Locatie via Teams.name (contracts.employeeId → team_assignments → teams).",
            "Verzuim is gebaseerd op presence_logs gefilterd op activiteitstype (Ziekte/Zwangerschapsverlof).",
        ],
        "export_method": (
            "ONS REST API of CSV-export. Tabellen: Employees, Contracts, "
            "Expertise_profiles, expertise_profile_assignments, Presence_logs, Activities, Teams."
        ),
    },
}


def get_system(system_id: str) -> dict | None:
    """Geeft de definitie van een bronsysteem terug, of None als niet gevonden."""
    return SOURCE_SYSTEMS.get(system_id)


def get_all_systems() -> list[dict]:
    """Geeft alle bronsystemen als lijst terug (zonder de uitgebreide schemas)."""
    return [
        {
            "id":          s["id"],
            "label":       s["label"],
            "vendor":      s["vendor"],
            "version":     s["version"],
            "color":       s["color"],
            "icon":        s["icon"],
            "description": s["description"],
            "notes":       s.get("notes", []),
            "export_method": s.get("export_method", ""),
        }
        for s in SOURCE_SYSTEMS.values()
    ]


def get_contract_translation(system_id: str, raw_value: str) -> str:
    """
    Vertaalt een bronsysteem-specifieke contracttype-code naar de KIK-V waarde.
    Geeft de originele waarde terug als er geen vertaling is.
    """
    translations = CONTRACT_TYPE_TRANSLATIONS.get(system_id, {})
    return translations.get(str(raw_value).lower().strip(), raw_value)
