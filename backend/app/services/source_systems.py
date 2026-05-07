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

    # ── Exact Financial ───────────────────────────────────────────────────────
    "exact_fin": {
        "id":      "exact_fin",
        "label":   "Exact Financial",
        "vendor":  "Exact Software",
        "version": "KIK-V Referentieontwerp Exact v6.0 (11-05-2025)",
        "color":   "#10b981",
        "icon":    "E",
        "description": (
            "Financieel ERP-systeem. Exact levert grootboekgegevens en financiële boekingen "
            "via een SQL-databasekoppeling of exportfunctie. Primair relevant voor het "
            "uitwisselprofiel Zorgkantoren (ZK-IB): grootboekrubrieken, financiële boekingen "
            "en WLZ-kostenplaatsen."
        ),
        "schemas": {
            "grootboekrubriek": {
                "label":       "Grootboekrubriek export",
                "source_name": "Grootboekrubriek (Exact Financial)",
                "fields": {
                    "grootboekRekeningNummer": {
                        "ons_kolom":   "grootboekRekeningNummer",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Rekeningnummer van de grootboekrubriek.",
                    },
                    "grootboekRekeningOmschrijving": {
                        "ons_kolom":   "grootboekRekeningOmschrijving",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Omschrijving van de grootboekrubriek.",
                    },
                    "startDatum": {
                        "ons_kolom":   "startDatum",
                        "type":        "date (dd/mm/yyyy)",
                        "required":    True,
                        "toelichting": "Datum vanaf wanneer het rekeningnummer tot de rubriek behoort.",
                    },
                    "eindDatum": {
                        "ons_kolom":   "eindDatum",
                        "type":        "date (dd/mm/yyyy)",
                        "required":    False,
                        "toelichting": "Datum tot wanneer het rekeningnummer tot de rubriek behoort.",
                    },
                },
            },
            "financiele_boeking": {
                "label":       "Financiële boekingen export",
                "source_name": "FinancieleBoeking (Exact Financial)",
                "fields": {
                    "boekingsBedrag": {
                        "ons_kolom":   "boekingsBedrag",
                        "alternatief": "Value",
                        "type":        "number (decimal)",
                        "required":    True,
                        "toelichting": "Boekingsbedrag op grootboekrekening voor kostenplaats.",
                    },
                    "financieleBoekingsDatum": {
                        "ons_kolom":   "financieleBoekingsDatum",
                        "type":        "date (dd/mm/yyyy)",
                        "required":    True,
                        "toelichting": "Boekingsdatum op grootboekrekening voor kostenplaats.",
                    },
                    "grootBoekRekening": {
                        "ons_kolom":   "grootBoekRekening",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Grootboekrekening van de boeking.",
                    },
                    "kostenPlaats": {
                        "ons_kolom":   "kostenPlaats",
                        "alternatief": "costcentre",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Organisatieonderdeel (kostenplaats) waarvoor de boeking van toepassing is.",
                    },
                },
            },
            "wlz_kostenplaats": {
                "label":       "WLZ-kostenplaatsen export",
                "source_name": "WLZ Toerekening kostenPlaats (Exact Financial)",
                "fields": {
                    "kostenPlaats": {
                        "ons_kolom":   "kostenPlaats",
                        "alternatief": "costcentre",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Kostenplaatsen die WLZ-gerelateerd zijn.",
                    },
                },
            },
        },
        "notes": [
            "Exact exporteert via SQL-databasekoppeling of rapportage-exportfunctie.",
            "Kolomnamen volgen de KIK-V modelgegevensset (camelCase).",
            "WLZ-kostenplaatsen zijn een filterset van alle kostenplaatsen.",
            "Primair relevant voor ZK-IB (Zorgkantoor Inkoop en Beleidsontwikkeling).",
        ],
        "export_method": "SQL-databasekoppeling of exportfunctie via Exact UI.",
    },

    # ── AFAS PROFIT Financieel ─────────────────────────────────────────────────
    "afas_profit_fin": {
        "id":      "afas_profit_fin",
        "label":   "AFAS PROFIT Financieel",
        "vendor":  "AFAS Software",
        "version": "KIK-V Referentieontwerp PROFIT FIN v6.0 (11-05-2025)",
        "color":   "#f59e0b",
        "icon":    "P",
        "description": (
            "Financiële module van AFAS PROFIT. Levert grootboekgegevens en financiële "
            "boekingen via SQL-databasekoppeling of exportfunctie. Primair relevant voor "
            "het uitwisselprofiel Zorgkantoren (ZK-IB). Let op: dit is de financiële module — "
            "de HR-module is apart beschikbaar als 'AFAS Profit HRM'."
        ),
        "schemas": {
            "grootboekrubriek": {
                "label":       "Grootboekrubriek export",
                "source_name": "Grootboekrubriek (AFAS PROFIT FIN)",
                "fields": {
                    "grootboekRekeningNummer": {
                        "ons_kolom":   "grootboekRekeningNummer",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Rekeningnummer van de grootboekrubriek in PROFIT.",
                    },
                    "grootboekRekeningOmschrijving": {
                        "ons_kolom":   "grootboekRekeningOmschrijving",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Omschrijving van de grootboekrubriek in PROFIT.",
                    },
                    "startDatum": {
                        "ons_kolom":   "startDatum",
                        "type":        "date (dd/mm/yyyy)",
                        "required":    True,
                        "toelichting": "Datum vanaf wanneer het rekeningnummer tot de rubriek behoort.",
                    },
                    "eindDatum": {
                        "ons_kolom":   "eindDatum",
                        "type":        "date (dd/mm/yyyy)",
                        "required":    False,
                        "toelichting": "Datum tot wanneer het rekeningnummer tot de rubriek behoort.",
                    },
                },
            },
            "financiele_boeking": {
                "label":       "Financiële boekingen export",
                "source_name": "FinancieleBoeking (AFAS PROFIT FIN)",
                "fields": {
                    "boekingsBedrag": {
                        "ons_kolom":   "boekingsBedrag",
                        "alternatief": "Value",
                        "type":        "number (decimal)",
                        "required":    True,
                        "toelichting": "Boekingsbedrag op grootboekrekening voor kostenplaats.",
                    },
                    "financieleBoekingsDatum": {
                        "ons_kolom":   "financieleBoekingsDatum",
                        "type":        "date (dd/mm/yyyy)",
                        "required":    True,
                        "toelichting": "Boekingsdatum op grootboekrekening voor kostenplaats.",
                    },
                    "grootBoekRekening": {
                        "ons_kolom":   "grootBoekRekening",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Grootboekrekening van de boeking.",
                    },
                    "kostenPlaats": {
                        "ons_kolom":   "kostenPlaats",
                        "alternatief": "costcentre",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Kostenplaats waarvoor de boeking van toepassing is.",
                    },
                },
            },
            "wlz_kostenplaats": {
                "label":       "WLZ-kostenplaatsen export",
                "source_name": "WLZ Toerekening kostenPlaats (AFAS PROFIT FIN)",
                "fields": {
                    "kostenPlaats": {
                        "ons_kolom":   "kostenPlaats",
                        "alternatief": "costcentre",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Kostenplaatsen die WLZ-gerelateerd zijn.",
                    },
                },
            },
        },
        "notes": [
            "AFAS PROFIT FIN exporteert via SQL-databasekoppeling of exportfunctie.",
            "Niet verwarren met AFAS Profit HRM — dat is de personeels-/salarismodule.",
            "WLZ-kostenplaatsen zijn een filterset van alle kostenplaatsen.",
            "Primair relevant voor ZK-IB (Zorgkantoor Inkoop en Beleidsontwikkeling).",
        ],
        "export_method": "SQL-databasekoppeling of exportfunctie via AFAS UI.",
    },

    # ── Visma PUUR ────────────────────────────────────────────────────────────
    "visma_puur": {
        "id":      "visma_puur",
        "label":   "Visma PUUR",
        "vendor":  "Visma",
        "version": "KIK-V Referentieontwerp PUUR v6.0 (11-05-2025)",
        "color":   "#8b5cf6",
        "icon":    "V",
        "description": (
            "Zorgadministratiesysteem van Visma voor VVT. PUUR registreert "
            "WLZ-arrangementen, cliëntgegevens en zorgproducten. Ontsluiting via "
            "API (gedeeltelijk) en SQL-databasekoppeling. Primair relevant voor "
            "het uitwisselprofiel Zorgkantoren (ZK-IB)."
        ),
        "schemas": {
            "arrangement": {
                "label":       "Arrangement export",
                "source_name": "Arrangement (Visma PUUR)",
                "fields": {
                    "Arrangement_ID": {
                        "ons_kolom":   "Arrangement_ID",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Uniek ID van het arrangement.",
                    },
                    "Client_ID": {
                        "ons_kolom":   "Client_ID",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Koppeling naar de cliënt.",
                    },
                    "Begindatum": {
                        "ons_kolom":   "Begindatum",
                        "type":        "date (dd/mm/yyyy)",
                        "required":    True,
                        "toelichting": "Startdatum van het arrangement.",
                    },
                    "Einddatum": {
                        "ons_kolom":   "Einddatum",
                        "type":        "date (dd/mm/yyyy)",
                        "required":    False,
                        "toelichting": "Einddatum van het arrangement (leeg = actief).",
                    },
                },
            },
            "arrangement_product": {
                "label":       "ArrangementProduct export",
                "source_name": "ArrangementProduct (Visma PUUR)",
                "fields": {
                    "Arrangement_ID": {
                        "ons_kolom":   "Arrangement_ID",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Koppeling naar het arrangement.",
                    },
                    "ArrangementProduct_ID": {
                        "ons_kolom":   "ArrangementProduct_ID",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Uniek ID van het arrangementproduct.",
                    },
                    "Product_ID": {
                        "ons_kolom":   "Product_ID",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Koppeling naar het zorgproduct.",
                    },
                    "Startdatum": {
                        "ons_kolom":   "Startdatum",
                        "type":        "date (dd/mm/yyyy)",
                        "required":    True,
                        "toelichting": "Startdatum van het arrangementproduct.",
                    },
                    "Einddatum": {
                        "ons_kolom":   "Einddatum",
                        "type":        "date (dd/mm/yyyy)",
                        "required":    False,
                        "toelichting": "Einddatum van het arrangementproduct.",
                    },
                },
            },
            "arrangement_product_wlz": {
                "label":       "ArrangementProductWLZ export",
                "source_name": "ArrangementProductWLZ (Visma PUUR)",
                "fields": {
                    "ArrangementProduct_ID": {
                        "ons_kolom":   "ArrangementProduct_ID",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Koppeling naar het arrangementproduct.",
                    },
                    "IndicatieAanvraagnummer": {
                        "ons_kolom":   "IndicatieAanvraagnummer",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "WLZ-indicatieaanvraagnummer.",
                    },
                    "Besluitnummer": {
                        "ons_kolom":   "Besluitnummer",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "WLZ-besluitnummer.",
                    },
                    "BeginDatumDeclaratie": {
                        "ons_kolom":   "BeginDatumDeclaratie",
                        "type":        "date (dd/mm/yyyy)",
                        "required":    True,
                        "toelichting": "Begindatum van de declaratieperiode.",
                    },
                    "EindDatumDeclaratie": {
                        "ons_kolom":   "EindDatumDeclaratie",
                        "type":        "date (dd/mm/yyyy)",
                        "required":    True,
                        "toelichting": "Einddatum van de declaratieperiode.",
                    },
                    "Zorgzwaartepakketcode": {
                        "ons_kolom":   "Zorgzwaartepakketcode",
                        "type":        "string (ZZP-codelijst)",
                        "required":    True,
                        "toelichting": "ZZP-code van het WLZ-arrangementproduct.",
                    },
                },
            },
            "team": {
                "label":       "Team (locatie) export",
                "source_name": "Team (Visma PUUR)",
                "fields": {
                    "Client_ID": {
                        "ons_kolom":   "Client_ID",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Koppeling naar de cliënt.",
                    },
                    "organisatieonderdeel": {
                        "ons_kolom":   "organisatieonderdeel",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Organisatieonderdeel / locatie van het team.",
                    },
                },
            },
            "wlz_product": {
                "label":       "WLZProduct export",
                "source_name": "WLZProduct (Visma PUUR)",
                "fields": {
                    "prestatiecode": {
                        "ons_kolom":   "prestatiecode",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "WLZ-prestatiecode van het zorgproduct.",
                    },
                    "Product_ID": {
                        "ons_kolom":   "Product_ID",
                        "type":        "string",
                        "required":    True,
                        "toelichting": "Interne product-ID, koppeling naar ArrangementProduct.",
                    },
                },
            },
        },
        "notes": [
            "PUUR exporteert via API (gedeeltelijk) én SQL-databasekoppeling.",
            "Niet alle gegevens zijn beschikbaar via de API — database is leading.",
            "eCare stelt specifieke API-endpoints beschikbaar voor KIKV-ontsluiting "
            "(o.a. wondzorgdossier en ACP).",
            "Primair relevant voor ZK-IB (Zorgkantoor Inkoop en Beleidsontwikkeling).",
        ],
        "export_method": (
            "API koppeling (gedeeltelijk) + SQL-databasekoppeling. "
            "Tabellen: Arrangement, ArrangementProduct, ArrangementProductWLZ, Team, WLZProduct. "
            "API-endpoints: GET /patients/{ecareId}/<<WONDZORGDOSSIER>>, GET /patients/{ecareId}/<<ACP>>."
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
