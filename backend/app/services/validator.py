import re
from datetime import datetime
from typing import Any

from app.services.prescan import prescan_columns
from app.services.rules import (
    FIELD_RULES,
    CONTRACTTYPE_VALUES,
    CONTRACTTYPE_TIJDELIJK,
    VERZUIMTYPE_VALUES,
    ONZ_PERS, ONZ_G, ONZ_ORG, ONZ_ZORG, ONZ_FIN,
    get_field_label,
    get_allowed_values,
    get_concept_uri,
    format_allowed_short,
)

# ─── KIK-V REFERENCE SCHEMA ──────────────────────────────────────────────────
KIKV_REFERENCE = {
    "medewerker": {
        "label": "Medewerker", "color": "#6366f1", "icon": "M",
        "description": "Personen & geboortedata",
        "source": "Employees",
        "required_cols": ["personeelsnummer", "geboortedatum"],
        "col_aliases": {
            "personeelsnummer": [
                "personeelsnummer","persoonid","personid","employeeid","medewerkerid",
                "identificationno","identificatieno","employeeobjectid",       # Nedap ONS
            ],
            "geboortedatum": [
                "geboortedatum","datebirth","dateofbirth","geboorte","dob",    # ONS: dateOfBirth
                "dateofbirth",                                                 # AFAS Profit_Employees
            ],
        },
    },
    "werkovereenkomst": {
        "label": "Werkovereenkomst", "color": "#0ea5e9", "icon": "W",
        "description": "Contracten & dienstverbanden",
        "source": "Contracts / Employment",
        "required_cols": ["dienstverbandnummer","personeelsnummer","overeenkomsttype","startdatum"],
        "col_aliases": {
            "dienstverbandnummer": [
                "dienstverbandnummer","contractid","dienstverbandid",
                "objectid",                                                    # Nedap ONS: Contracts.objectId
            ],
            "personeelsnummer": [
                "personeelsnummer","personid","medewerkerid","employeeid",
                "employeeobjectid",                                            # Nedap ONS
            ],
            "overeenkomsttype": [
                "overeenkomsttype","contracttype","employmenttype","typecontract",
                "contracttypename","contracttype_name",                        # Nedap ONS: contractType.name (V/O/S/E)
            ],
            "startdatum": [
                "startdatum","employmentstart","begindatum","indienst",
                "begindate",                                                   # Nedap ONS: Contracts.beginDate
                "startdate",                                                   # AFAS Profit_Timetable
            ],
            "einddatum": [
                "einddatum","employmentend","uitdienst","einde",
                "enddate",                                                     # Nedap ONS: Contracts.endDate / AFAS Timetable
            ],
            "overeenkomstoe": [
                "overeenkomstoe","orgunit","organisatieeenheid","afdeling","locatie","vestiging",
                "teamsname","teamname",                                        # Nedap ONS: Teams.name
                "orgunit","orgunitdesc",                                       # AFAS Profit_Employees
            ],
            "urenperweek": [
                "urenperweek","hoursperweek","contractomvang",
                "fixedhoursperweek",                                           # Nedap ONS: Contracts.fixedHoursPerWeek
                "hoursperweek","hourperweek",                                  # AFAS Profit_Timetable / Profit_Employees
            ],
        },
        "allowed_types": CONTRACTTYPE_VALUES,
    },
    "functie": {
        "label": "Functie", "color": "#8b5cf6", "icon": "F",
        "description": "Functieomschrijvingen",
        "source": "Functions / Expertise_profiles",
        "required_cols": ["functie"],
        "col_aliases": {
            "functie": [
                "functie","functienaam","jobtitle","function",
                "description","expertiseprofiledescription",                   # Nedap ONS: Expertise_profiles.description
            ],
            "zorg":               ["zorg","iszorg","carerole"],
            "kwalificatieniveau": ["kwalificatieniveau","niveau","level","qualification"],
            "startdatum": [
                "startdatum","begindatum",
                "starttime",                                                   # Nedap ONS: expertise_profile_assignments.startTime
            ],
            "einddatum": [
                "einddatum",
                "endtime",                                                     # Nedap ONS: expertise_profile_assignments.endTime
            ],
        },
    },
    "kwalificatieniveau": {
        "label": "KwalificatieNiveau", "color": "#10b981", "icon": "K",
        "description": "Referentie kwalificatiecodes",
        "source": "Reference table",
        "required_cols": ["code"],
        "col_aliases": {
            "kwalificatieniveau": ["kwalificatieniveau","omschrijving","naam","level"],
            "code":               ["code","niveau","id"],
        },
    },
    "kwaliteitsgraden": {
        "label": "KwaliteitsGraden", "color": "#f59e0b", "icon": "G",
        "description": "Kwaliteitscategorieën",
        "source": "Reference table",
        "required_cols": ["kwaliteit"],
        "col_aliases": {
            "kwaliteit": ["kwaliteit","grade","graad","code"],
            "categorie": ["categorie","omschrijving","category"],
        },
    },
    "verzuim": {
        "label": "Verzuim", "color": "#ef4444", "icon": "V",
        "description": "Verzuim- & ziekteperiodes",
        "source": "Illness / Presence_logs",
        "required_cols": ["personeelsnummer","startmoment"],
        "col_aliases": {
            "personeelsnummer": [
                "personeelsnummer","personid","medewerkerid",
                "employeeid",                                                  # Nedap ONS: presence_logs.employeeId
            ],
            "soortverzuim": [
                "soortverzuim","type","soort","verzuimtype",
                "description","activitydescription",                           # Nedap ONS: activities.description
                "absencetypedesc","absencetypeid","reasondesc","reasonid",     # AFAS Profit_Illness
            ],
            "startmoment": [
                "startmoment","startdatum","illnessstart","begindatum",
                "startdate",                                                   # Nedap ONS / AFAS Profit_Illness
            ],
            "eindmoment": [
                "eindmoment","einddatum","illnessend",
                "enddate",                                                     # Nedap ONS / AFAS Profit_Illness
            ],
            "verzuimpercentage": [
                "verzuimpercentage","percentage","presence","arbeidsongeschiktheid",
            ],
        },
        "allowed_types": VERZUIMTYPE_VALUES,
    },

    # ── Vestiging (Nedap ONS: Teams / Locations) ──────────────────────────────
    "vestiging": {
        "label": "Vestiging", "color": "#0ea5e9", "icon": "L",
        "description": "Vestigingen / zorglokaties",
        "source": "Teams / Locations (Nedap ONS, AFAS)",
        "required_cols": ["vestigingid"],
        "col_aliases": {
            "vestigingid": [
                "vestigingid","objectid","locationid","teamid","teamobjectid",
                "locatieid","vestigingsnummer","id",
            ],
            "vestigingsnaam": [
                "vestigingsnaam","name","naam","locatienaam","teamname",
                "description","title",
            ],
            "locatietype": [
                "locatietype","locationtype","type","zorgtype","zorgvorm",
                "teamtype","soort",
            ],
            "zorgsoort": [
                "zorgsoort","caretype","sector","zorgdomein",
                "sectortype",                                                  # VPZ / GHZ / GGZ
            ],
            "regio": [
                "regio","region","gemeente","city","place",
            ],
        },
    },

    # ── Cliënt (Nedap ONS: Clients + WLZ-profiel) ────────────────────────────
    "client": {
        "label": "Cliënt", "color": "#8b5cf6", "icon": "C",
        "description": "Cliëntgegevens met WLZ-indicatie en zorgprofiel",
        "source": "Clients / WLZ-indicaties (Nedap ONS)",
        "required_cols": ["clientid"],
        "col_aliases": {
            "clientid": [
                "clientid","cliëntid","clientnummer","persoonid","objectid",
                "clientobjectid","patientid",
            ],
            "vestigingid": [
                "vestigingid","locationid","locatieid","teamid",
                "primarylocationid",
            ],
            "geboortedatum": [
                "geboortedatum","dateofbirth","birthdate","geboorte","dob",
            ],
            "wlzprofiel": [
                "wlzprofiel","wlzprofile","zorgniveauprofiel","zzp",
                "zorgprofiel","careprofile","indicatieprofiel",
            ],
            "startdatum": [
                "startdatum","startdate","ingangsdatum","begindatum",
                "admissiondate","opnamedatum",
            ],
            "einddatum": [
                "einddatum","enddate","eindebehandeling","ontslagdatum",
                "dischargedate",
            ],
        },
    },

    # ── Kostenplaats (AFAS Profit Finance / WLZ) ─────────────────────────────
    "kostenplaats": {
        "label": "Kostenplaats", "color": "#06b6d4", "icon": "€",
        "description": "Financiële kostenplaatsen en WLZ-budgetten",
        "source": "AFAS Profit Finance / WLZ-kostenplaatsen",
        "required_cols": ["kostenplaatsid"],
        "col_aliases": {
            "kostenplaatsid": [
                "kostenplaatsid","kostenplaatscode","costcenterid","costcenter",
                "id","code","objectid",
            ],
            "omschrijving": [
                "omschrijving","naam","description","name","label",
            ],
            "bedrag": [
                "bedrag","budget","amount","totaal","waarde","value",
            ],
            "periode": [
                "periode","period","jaar","year","maand","month",
            ],
        },
    },

    # ── Grootboek (AFAS Profit Finance) ──────────────────────────────────────
    "grootboek": {
        "label": "Grootboek", "color": "#0284c7", "icon": "G",
        "description": "Grootboekrekeningen en boekingen",
        "source": "AFAS Profit Finance / Grootboek",
        "required_cols": ["rekeningnummer"],
        "col_aliases": {
            "rekeningnummer": [
                "rekeningnummer","accountnumber","glaccountid","grootboekrekening",
                "rekeningcode","accountcode","id","code",
            ],
            "omschrijving": [
                "omschrijving","naam","description","name",
            ],
            "bedrag": [
                "bedrag","amount","debet","credit","saldo","balance",
            ],
        },
    },
}

KIKV_FIELDS_REFERENCE = [
    # ── Medewerker ────────────────────────────────────────────────────────────
    {
        "concept": "Werknemer", "concept_uri": f"{ONZ_G}Employee",
        "field": "PersonId", "schema": "medewerker",
        "source": "Employees.PersonIdEmployeeId", "type": "string", "required": True,
        "description": "Uniek persoonsnummer van de medewerker",
        "field_concept_uri": f"{ONZ_G}EmployeeIdentifier",
        "field_concept_label": "Werknemersidentifier",
    },
    {
        "concept": "Werknemer", "concept_uri": f"{ONZ_G}Employee",
        "field": "Geboortedatum", "schema": "medewerker",
        "source": "Employees.DateBirth", "type": "date", "required": True,
        "description": "Geboortedatum van de medewerker (dd/mm/yyyy)",
        "field_concept_uri": f"{ONZ_G}hasDateOfBirth",
        "field_concept_label": "heeft geboortedatum",
    },
    # ── Werkovereenkomst ──────────────────────────────────────────────────────
    {
        "concept": "Werkovereenkomst", "concept_uri": f"{ONZ_PERS}WerkOvereenkomst",
        "field": "EmploymentType", "schema": "werkovereenkomst",
        "source": "Employees.EmploymentType", "type": "string", "required": True,
        "description": "Type arbeidsovereenkomst", "allowed_values": CONTRACTTYPE_VALUES,
        "field_concept_uri": f"{ONZ_PERS}ArbeidsOvereenkomst",
        "field_concept_label": "Arbeidsovereenkomst",
    },
    {
        "concept": "Werkovereenkomst", "concept_uri": f"{ONZ_PERS}WerkOvereenkomst",
        "field": "EmploymentStart", "schema": "werkovereenkomst",
        "source": "Employees.EmploymentStart", "type": "date", "required": True,
        "description": "Startdatum van de werkovereenkomst",
        "field_concept_uri": f"{ONZ_G}startDatum",
        "field_concept_label": "startdatum",
    },
    {
        "concept": "Werkovereenkomst", "concept_uri": f"{ONZ_PERS}WerkOvereenkomst",
        "field": "EmploymentEnd", "schema": "werkovereenkomst",
        "source": "Employees.EmploymentEnd", "type": "date", "required": False,
        "description": "Einddatum werkovereenkomst (leeg = actief)",
        "field_concept_uri": f"{ONZ_G}eindDatum",
        "field_concept_label": "einddatum",
    },
    {
        "concept": "Werkovereenkomst", "concept_uri": f"{ONZ_PERS}WerkOvereenkomst",
        "field": "OrgUnit", "schema": "werkovereenkomst",
        "source": "Employees.OrgUnit", "type": "string", "required": True,
        "description": "Organisatie-eenheid / locatie van de medewerker",
        "field_concept_uri": f"{ONZ_ORG}OrganisatorischeEenheid",
        "field_concept_label": "Organisatorische eenheid",
    },
    {
        "concept": "Contractomvang", "concept_uri": f"{ONZ_PERS}ContractOmvang",
        "field": "HourPerWeek", "schema": "werkovereenkomst",
        "source": "Employees.HourPerWeek", "type": "number", "required": True,
        "description": "Contractueel aantal uren per week",
        "field_concept_uri": f"{ONZ_PERS}ContractOmvangWaarde",
        "field_concept_label": "Contractomvangwaarde",
    },
    # ── Functie ───────────────────────────────────────────────────────────────
    {
        "concept": "Zorgverlener functie", "concept_uri": f"{ONZ_PERS}ZorgverlenerFunctie",
        "field": "FunctionName", "schema": "functie",
        "source": "Functions.description", "type": "string", "required": True,
        "description": "Naam van de functie",
        "field_concept_uri": f"{ONZ_PERS}ZorgverlenerFunctie",
        "field_concept_label": "Zorgverlener (functie)",
    },
    {
        "concept": "Kwalificatieniveau", "concept_uri": f"{ONZ_PERS}IGJKwalificatieWaarde",
        "field": "QualificationLevel", "schema": "functie",
        "source": "Functions.level", "type": "string", "required": False,
        "description": "IGJ kwalificatieniveau van de functie",
        "field_concept_uri": f"{ONZ_PERS}IGJKwalificatieWaarde",
        "field_concept_label": "IGJ Kwalificatiewaarde",
    },
    # ── Verzuim ───────────────────────────────────────────────────────────────
    {
        "concept": "Verzuimperiode", "concept_uri": f"{ONZ_PERS}VerzuimPeriode",
        "field": "IllnessStart", "schema": "verzuim",
        "source": "Illness.startdate", "type": "date", "required": False,
        "description": "Startdatum van de verzuimperiode",
        "field_concept_uri": f"{ONZ_G}startDatum",
        "field_concept_label": "startdatum",
    },
    {
        "concept": "Verzuimperiode", "concept_uri": f"{ONZ_PERS}VerzuimPeriode",
        "field": "IllnessEnd", "schema": "verzuim",
        "source": "Illness.enddate", "type": "date", "required": False,
        "description": "Einddatum van de verzuimperiode",
        "field_concept_uri": f"{ONZ_G}eindDatum",
        "field_concept_label": "einddatum",
    },
    {
        "concept": "Arbeidsongeschiktheidspercentage", "concept_uri": f"{ONZ_PERS}AOPercentage",
        "field": "Presence", "schema": "verzuim",
        "source": "100% - Illness.Presence", "type": "number", "required": False,
        "description": "Ziekteverzuimpercentage (0-100)",
        "field_concept_uri": f"{ONZ_PERS}AOPercentage",
        "field_concept_label": "Arbeidsongeschiktheidspercentage",
    },
    {
        "concept": "Verzuimperiode", "concept_uri": f"{ONZ_PERS}VerzuimPeriode",
        "field": "SoortVerzuim", "schema": "verzuim",
        "source": "Illness.type", "type": "string", "required": False,
        "description": "Soort verzuim (ZiektePeriode, ZwangerschapsVerlof, etc.)",
        "allowed_values": VERZUIMTYPE_VALUES,
        "field_concept_uri": f"{ONZ_PERS}VerzuimPeriode",
        "field_concept_label": "Verzuimperiode",
    },
]

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def normalize(s: str) -> str:
    return re.sub(r'[\s_\-\.]', '', str(s or '').lower())

def is_date(val: Any) -> bool:
    return bool(re.match(r'\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}', str(val or '')))

def parse_date(val: Any):
    if not val: return None
    m = re.match(r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})', str(val))
    if m:
        try: return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except: return None
    return None

def auto_map(headers: list, aliases: dict) -> dict:
    """
    Map bestandskolommen naar interne veldnamen via alias-lijsten.

    Twee passes zodat exacte matches altijd winnen van substring-matches.
    Voorbeeld: bestand met kolommen ['Datum', 'EindDatum'] → 'EindDatum' wint
    voor 'einddatum', ook al bevat 'datum' de substring 'datum'.
    """
    mapping: dict = {}
    norm_headers = {h: normalize(h) for h in headers}

    # Pass 1 — exacte match (normalized header == alias)
    for field, alias_list in aliases.items():
        if field in mapping:
            continue
        for h, hn in norm_headers.items():
            if hn in alias_list:
                mapping[field] = h
                break

    # Pass 2 — substring-match voor nog niet gemapte velden
    for field, alias_list in aliases.items():
        if field in mapping:
            continue
        for h, hn in norm_headers.items():
            if any(hn in a or a in hn for a in alias_list):
                mapping[field] = h
                break

    return mapping

def detect_schema(filename: str, headers: list) -> str | None:
    fn = normalize(filename)
    if "medewerker" in fn or "employees" in fn or "employee" in fn: return "medewerker"
    if "werkovereenkomst" in fn or "contract" in fn or "timetable" in fn: return "werkovereenkomst"
    if "functie" in fn and "niveau" not in fn: return "functie"
    if "kwalificatieniveau" in fn or "kwn" in fn: return "kwalificatieniveau"
    if "kwaliteitsgr" in fn or "graden" in fn: return "kwaliteitsgraden"
    if "verzuim" in fn or "illness" in fn: return "verzuim"
    if "vestiging" in fn or "locatie" in fn or "teams" in fn: return "vestiging"
    if "client" in fn or "cliënt" in fn or "patient" in fn: return "client"
    # Financiële bestanden: herken als kostenplaats of grootboek (voor Financiën domein)
    if "kostenplaats" in fn or "wlzkostenplaats" in fn: return "kostenplaats"
    if "grootboek" in fn or "journaal" in fn: return "grootboek"
    # Overige financiële bestanden worden niet als HRM-schema herkend
    if any(x in fn for x in ("boeking", "rubriek", "balans", "resultaat",
                              "declaratie", "factuur", "budget", "fin")):
        return None
    best, best_score = None, 0
    norm_headers = [normalize(h) for h in headers]
    for key, schema in KIKV_REFERENCE.items():
        # Eis minimaal 2 matches én dat het primaire id-veld aanwezig is
        aliases_flat = [a for al in schema["col_aliases"].values() for a in al]
        score = sum(1 for nh in norm_headers if nh in aliases_flat)
        if score < 2:
            continue
        # Controleer of een discriminerend veld aanwezig is (personeelsnummer o.i.d.)
        primary_fields = list(schema["col_aliases"].keys())[:2]   # eerste 2 velden zijn primair
        primary_aliases = [a for f in primary_fields for a in schema["col_aliases"].get(f, [])]
        if not any(nh in primary_aliases for nh in norm_headers):
            continue
        if score > best_score:
            best_score, best = score, key
    return best

# ─── PER-FILE CHECKS ──────────────────────────────────────────────────────────

MAX_ROWS_PER_ISSUE = 50   # cap per issue om grote payloads te vermijden

def run_file_checks(schema_key: str, rows: list, mapping: dict) -> list:
    schema  = KIKV_REFERENCE.get(schema_key, {})
    issues: list = []

    # ── interne helpers ───────────────────────────────────────────────────────
    def col(field: str):
        return mapping.get(field)

    def _pid(row: dict) -> str:
        """Beste beschikbare persoon-identifier uit een rij."""
        for f in ("personeelsnummer", "dienstverbandnummer", "medewerkerid"):
            c = col(f)
            if c and row.get(c):
                return str(row[c])
        return ""

    def make_detail(row_idx: int, row: dict, field: str,
                    current: str, expected: str, message: str) -> dict:
        """Bouw één rij-detail object (conform gewenste output-structuur)."""
        return {
            "rowNumber":     row_idx + 2,   # +1 nul-index, +1 headerrij
            "personId":      _pid(row),
            "field":         field,
            "currentValue":  str(current)  if current  is not None else "",
            "expectedValue": str(expected) if expected is not None else "",
            "message":       message,
        }

    def add_rows(id_: str, label: str, severity: str,
                 row_details: list, detail_override: str = None,
                 allowed_values: list = None,
                 field_label: str = None,
                 source: str = None) -> None:
        """
        Voeg een issue toe met per-rij details. Kap op MAX_ROWS_PER_ISSUE.

        allowed_values  — lijst van toegestane waarden (dicts of strings),
                          van rules.py; wordt meegegeven aan de frontend zodat
                          die een leesbare codelijst kan tonen.
        field_label     — gebruikersvriendelijk veldnaam (bijv. 'Contracttype').
        source          — bronverwijzing (bijv. 'KIK-V OvereenkomstType codelijst').
        """
        if not row_details:
            return
        total  = len(row_details)
        capped = row_details[:MAX_ROWS_PER_ISSUE]
        pids   = list(dict.fromkeys(rd["personId"] for rd in capped if rd["personId"]))
        if detail_override:
            detail = detail_override
        elif pids:
            shown  = pids[:10]
            detail = "Personen: " + ", ".join(shown) + ("…" if len(pids) > 10 else "")
        else:
            detail = f"{total} rijen"
        entry: dict = {
            "id":        id_,
            "label":     label,
            "severity":  severity,
            "count":     total,
            "detail":    detail,
            "rows":      capped,
            "truncated": total > MAX_ROWS_PER_ISSUE,
        }
        if allowed_values is not None:
            entry["allowedValues"] = allowed_values
        if field_label:
            entry["fieldLabel"] = field_label
        if source:
            entry["source"] = source
        issues.append(entry)

    def add(id_: str, label: str, severity: str,
            count: int, detail: str = None) -> None:
        """Voeg een issue toe zonder per-rij detail (teller-only)."""
        if count > 0:
            issues.append({
                "id": id_, "label": label, "severity": severity,
                "count": count, "detail": detail,
                "rows": [], "truncated": False,
            })

    # ── medewerker ────────────────────────────────────────────────────────────
    if schema_key == "medewerker":
        id_col  = col("personeelsnummer")
        dob_col = col("geboortedatum")

        if id_col:
            id_counts: dict[str, int] = {}
            for r in rows:
                v = r.get(id_col, "")
                if v:
                    id_counts[v] = id_counts.get(v, 0) + 1
            dupe_vals = {v for v, c in id_counts.items() if c > 1}

            add_rows("dup_id", "Dubbele personeelsnummers", "error", [
                make_detail(i, r, "personeelsnummer", r.get(id_col, ""),
                            "Uniek nummer",
                            f"Nummer '{r.get(id_col,'')}' komt {id_counts.get(r.get(id_col,''), 0)}× voor")
                for i, r in enumerate(rows)
                if r.get(id_col, "") in dupe_vals
            ])
            add_rows("empty_id", "Lege personeelsnummers", "error", [
                make_detail(i, r, "personeelsnummer", "", "Verplicht uniek nummer",
                            "Personeelsnummer ontbreekt")
                for i, r in enumerate(rows) if not r.get(id_col, "")
            ])
            add_rows("placeholder", "Placeholder ID (99999)", "error", [
                make_detail(i, r, "personeelsnummer", "99999",
                            "Geldig uniek nummer", "Systeemplacholder — verwijderen")
                for i, r in enumerate(rows) if r.get(id_col, "") == "99999"
            ])

        if dob_col:
            add_rows("empty_dob", "Lege geboortedatum", "error", [
                make_detail(i, r, "geboortedatum", "", "dd/mm/yyyy",
                            "Geboortedatum ontbreekt")
                for i, r in enumerate(rows) if not r.get(dob_col, "")
            ])
            add_rows("bad_dob", "Ongeldige datumnotatie geboortedatum", "warning", [
                make_detail(i, r, "geboortedatum", r.get(dob_col, ""),
                            "dd/mm/yyyy",
                            f"Notatie niet herkend: '{r.get(dob_col, '')}'")
                for i, r in enumerate(rows)
                if r.get(dob_col, "") and not is_date(r.get(dob_col, ""))
            ])

    # ── werkovereenkomst ──────────────────────────────────────────────────────
    elif schema_key == "werkovereenkomst":
        allowed      = schema.get("allowed_types", [])  # uit rules.py via KIKV_REFERENCE
        ot_col       = col("overeenkomsttype")
        st_col       = col("startdatum")
        ed_col       = col("einddatum")
        pid_col      = col("personeelsnummer")

        # Haal meta uit rules.py voor gebruikersvriendelijke output
        _ot_rules    = FIELD_RULES.get("werkovereenkomst", {}).get("overeenkomsttype", {})
        _ot_av       = _ot_rules.get("allowedValues", [])
        _ot_label    = _ot_rules.get("label", "Contracttype")
        _ot_source   = _ot_rules.get("source", "")
        _ot_expected = format_allowed_short(_ot_av)   # bijv. "Bepaalde tijd, Halfjaarcontract, Jaarcontract of 6 andere"

        if ot_col:
            add_rows(
                "invalid_type",
                "Ongeldig contracttype",
                "error",
                [
                    make_detail(
                        i, r,
                        field    = _ot_label,
                        current  = r.get(ot_col, ""),
                        expected = _ot_expected,
                        message  = (
                            f"'{r.get(ot_col, '')}' is geen geldig contracttype. "
                            f"Kies een waarde uit de KIK-V OvereenkomstType codelijst."
                        ),
                    )
                    for i, r in enumerate(rows)
                    if r.get(ot_col, "") and r.get(ot_col, "").lower().strip() not in allowed
                ],
                allowed_values = _ot_av,
                field_label    = _ot_label,
                source         = _ot_source,
            )
            add_rows(
                "missing_type",
                "Contracttype ontbreekt",
                "error",
                [
                    make_detail(
                        i, r,
                        field    = _ot_label,
                        current  = "",
                        expected = _ot_expected,
                        message  = "Contracttype is verplicht. Vul een geldige waarde in.",
                    )
                    for i, r in enumerate(rows) if not r.get(ot_col, "")
                ],
                allowed_values = _ot_av,
                field_label    = _ot_label,
                source         = _ot_source,
            )

        if st_col:
            add_rows("missing_start", "Lege StartDatum", "error", [
                make_detail(i, r, "startdatum", "", "dd/mm/yyyy", "StartDatum ontbreekt")
                for i, r in enumerate(rows) if not r.get(st_col, "")
            ])

        if pid_col:
            add_rows("placeholder", "Placeholder persoon (99999)", "error", [
                make_detail(i, r, "personeelsnummer",
                            r.get(pid_col, ""), "Geldig uniek nummer",
                            "Systeemplacholder of leeg personeelsnummer")
                for i, r in enumerate(rows)
                if r.get(pid_col, "") == "99999" or not r.get(pid_col, "")
            ])

        # Einddatum: alleen verplicht voor tijdelijke contracten (bron: CONTRACTTYPE_TIJDELIJK in rules.py)
        if ot_col and ed_col:
            temp_missing, perm_open = [], 0
            for i, r in enumerate(rows):
                ct = str(r.get(ot_col, "") or "").lower().strip()
                ed = str(r.get(ed_col, "") or "").strip()
                if ct in CONTRACTTYPE_TIJDELIJK and not ed:
                    temp_missing.append(
                        make_detail(i, r, "Einddatum", "", "dd/mm/yyyy",
                                    f"Tijdelijk contract ('{ct}') vereist een einddatum.")
                    )
                elif ct not in CONTRACTTYPE_TIJDELIJK and not ed:
                    perm_open += 1
            add_rows("missing_einddatum_temp",
                     "Einddatum ontbreekt bij tijdelijk contract", "error",
                     temp_missing)
            add("open_contracts", "Open contracten (geen einddatum)", "info",
                perm_open, "Normaal voor vaste medewerkers")
        elif ed_col and not ot_col:
            open_count = sum(1 for r in rows if not str(r.get(ed_col, "") or "").strip())
            add("open_contracts", "Open contracten (geen einddatum)", "info",
                open_count, "Normaal voor actieve medewerkers")
        else:
            add("unmapped_einddatum", "Einddatum kolom niet herkend in bestand",
                "warning", 1,
                "Verwachte kolomnamen: Einddatum, EmploymentEnd, Uitdienst, Einde")

    # ── functie ───────────────────────────────────────────────────────────────
    elif schema_key == "functie":
        fn_col = col("functie")
        nv_col = col("kwalificatieniveau")

        if nv_col:
            add_rows("missing_niveau", "Lege KwalificatieNiveau", "warning", [
                make_detail(i, r, "kwalificatieniveau", "", "Kwalificatiecode",
                            "KwalificatieNiveau ontbreekt")
                for i, r in enumerate(rows) if not r.get(nv_col, "")
            ])

        if fn_col:
            name_counts: dict[str, int] = {}
            for r in rows:
                v = r.get(fn_col, "")
                if v:
                    name_counts[v] = name_counts.get(v, 0) + 1
            dupe_names = {v for v, c in name_counts.items() if c > 1}
            add_rows("dup_functie", "Dubbele functienamen", "warning", [
                make_detail(i, r, "functie", r.get(fn_col, ""),
                            "Unieke functienaam",
                            f"Naam '{r.get(fn_col,'')}' komt {name_counts.get(r.get(fn_col,''), 0)}× voor")
                for i, r in enumerate(rows)
                if r.get(fn_col, "") in dupe_names
            ])

    # ── verzuim ───────────────────────────────────────────────────────────────
    elif schema_key == "verzuim":
        allowed      = schema.get("allowed_types", [])   # uit rules.py via KIKV_REFERENCE
        sv_col       = col("soortverzuim")
        sm_col       = col("startmoment")
        em_col       = col("eindmoment")
        pct_col      = col("verzuimpercentage")
        pid_col      = col("personeelsnummer")

        _sv_rules    = FIELD_RULES.get("verzuim", {}).get("soortverzuim", {})
        _sv_av       = _sv_rules.get("allowedValues", [])
        _sv_label    = _sv_rules.get("label", "Soort verzuim")
        _sv_source   = _sv_rules.get("source", "")
        _sv_expected = format_allowed_short(_sv_av)

        if sv_col:
            add_rows(
                "invalid_soort",
                "Ongeldig soort verzuim",
                "error",
                [
                    make_detail(
                        i, r,
                        field    = _sv_label,
                        current  = r.get(sv_col, ""),
                        expected = _sv_expected,
                        message  = (
                            f"'{r.get(sv_col, '')}' is geen geldige verzuimcategorie. "
                            f"Kies een waarde uit de KIK-V SoortVerzuim codelijst."
                        ),
                    )
                    for i, r in enumerate(rows)
                    if r.get(sv_col, "") and r.get(sv_col, "").lower().strip() not in allowed
                ],
                allowed_values = _sv_av,
                field_label    = _sv_label,
                source         = _sv_source,
            )

        if sm_col:
            add_rows("missing_start", "Lege startmoment", "error", [
                make_detail(i, r, "startmoment", "", "dd/mm/yyyy", "Startmoment ontbreekt")
                for i, r in enumerate(rows) if not r.get(sm_col, "")
            ])
            if em_col:
                add_rows("end_before_start", "Einddatum vóór startdatum", "error", [
                    make_detail(i, r, "eindmoment",
                                r.get(em_col, ""),
                                f"Na {r.get(sm_col, '')}",
                                f"Eindmoment ({r.get(em_col, '')}) ligt vóór startmoment ({r.get(sm_col, '')})")
                    for i, r in enumerate(rows)
                    if (parse_date(r.get(sm_col, "")) and parse_date(r.get(em_col, ""))
                        and parse_date(r.get(em_col, "")) < parse_date(r.get(sm_col, "")))
                ])

        if pct_col:
            def _bad_pct(v: str) -> bool:
                if not v:
                    return False
                return not str(v).replace(".", "", 1).isdigit() or float(v) < 0 or float(v) > 100

            add_rows("invalid_pct", "Ongeldig verzuimpercentage", "error", [
                make_detail(i, r, "verzuimpercentage",
                            r.get(pct_col, ""), "0 – 100",
                            f"Waarde '{r.get(pct_col,'')}' buiten bereik of ongeldig getal")
                for i, r in enumerate(rows) if _bad_pct(r.get(pct_col, ""))
            ])
            add_rows("missing_pct", "Lege verzuimpercentage", "warning", [
                make_detail(i, r, "verzuimpercentage", "", "0 – 100",
                            "Verzuimpercentage ontbreekt")
                for i, r in enumerate(rows) if not r.get(pct_col, "")
            ])

        # Overlap — teller-only (vereist paarsgewijze vergelijking)
        if pid_col and sm_col:
            by_person: dict = {}
            for r in rows:
                pid = r.get(pid_col)
                if pid:
                    by_person.setdefault(pid, []).append(r)
            overlap = 0
            for periods in by_person.values():
                parsed = sorted(
                    [(parse_date(r.get(sm_col, "")),
                      parse_date(r.get(em_col, "")) if em_col else None or datetime(9999, 12, 31))
                     for r in periods if parse_date(r.get(sm_col, ""))],
                    key=lambda x: x[0],
                )
                for j in range(len(parsed) - 1):
                    if parsed[j][1] and parsed[j][1] >= parsed[j + 1][0]:
                        overlap += 1
            add("overlap", "Overlappende periodes", "warning", overlap)

        if pid_col:
            add_rows("placeholder", "Placeholder persoon (99999)", "error", [
                make_detail(i, r, "personeelsnummer",
                            r.get(pid_col, ""), "Geldig personeelsnummer",
                            "Systeemplacholder of leeg personeelsnummer")
                for i, r in enumerate(rows)
                if r.get(pid_col, "") == "99999" or not r.get(pid_col, "")
            ])

    return issues

# ─── CROSS-FILE CHECKS ────────────────────────────────────────────────────────
def run_cross_checks(files_data: dict) -> list:
    cross = []

    def get_set(schema_key, field):
        fd = files_data.get(schema_key)
        if not fd: return set()
        col = fd["mapping"].get(field)
        if not col: return set()
        return set(r.get(col,"") for r in fd["rows"] if r.get(col,"") and r.get(col,"") != "99999")

    def add(id_, label, severity, count, detail=None):
        if count > 0:
            cross.append({"id": id_, "label": label, "severity": severity, "count": count, "detail": detail})

    if "medewerker" in files_data and "werkovereenkomst" in files_data:
        med_ids = get_set("medewerker", "personeelsnummer")
        werk_ids = get_set("werkovereenkomst", "personeelsnummer")
        unknown = werk_ids - med_ids
        add("werk_unknown", "Werkovereenkomst: personen niet in Medewerker", "error", len(unknown),
            f"Nummers: {', '.join(list(unknown)[:5])}{'…' if len(unknown)>5 else ''}" if unknown else None)
        missing = med_ids - werk_ids
        add("med_no_contract", "Medewerkers zonder werkovereenkomst", "warning", len(missing),
            f"Nummers: {', '.join(list(missing)[:5])}{'…' if len(missing)>5 else ''}" if missing else None)

    if "medewerker" in files_data and "verzuim" in files_data:
        med_ids = get_set("medewerker", "personeelsnummer")
        verz_ids = get_set("verzuim", "personeelsnummer")
        unknown = verz_ids - med_ids
        add("verz_unknown", "Verzuim: personen niet in Medewerker", "error", len(unknown),
            f"Nummers: {', '.join(list(unknown)[:5])}" if unknown else None)

    if "kwalificatieniveau" in files_data and "kwaliteitsgraden" in files_data:
        grades = get_set("kwaliteitsgraden", "kwaliteit")
        codes = get_set("kwalificatieniveau", "code")
        missing = codes - grades
        add("kwn_grade_mismatch", "KwalificatieNiveau codes niet in KwaliteitsGraden", "warning", len(missing),
            f"Codes: {', '.join(missing)}" if missing else None)

    if "functie" in files_data and "kwalificatieniveau" in files_data:
        valid_codes = get_set("kwalificatieniveau", "code")
        fd = files_data["functie"]
        nc = fd["mapping"].get("kwalificatieniveau")
        fn_col = fd["mapping"].get("functie")
        if nc and fn_col:
            bad = [r.get(fn_col,"") for r in fd["rows"] if r.get(nc,"") and r.get(nc,"") not in valid_codes]
            add("func_niveau_invalid", "Functie KwalificatieNiveau niet in referentietabel", "warning", len(bad),
                ', '.join(bad) if bad else None)

    return cross

# ─── MAIN VALIDATE ENTRY POINT ───────────────────────────────────────────────
def validate_files(files_input: list) -> dict:
    """
    files_input: list of {filename, schema_key, headers, rows}
    Returns full validation result dict
    """
    files_data = {}
    file_results = []

    for fi in files_input:
        sk = fi.get("schema_key") or detect_schema(fi["filename"], fi["headers"])
        if not sk or sk not in KIKV_REFERENCE:
            continue
        schema = KIKV_REFERENCE[sk]
        mapping = auto_map(fi["headers"], schema["col_aliases"])
        issues = run_file_checks(sk, fi["rows"], mapping)

        # Pre-scan: formaat-validatie op extra kolommen (niet in schema-mapping)
        known_col_names = set(mapping.values())
        prescan_issues  = prescan_columns(fi["rows"], known_cols=known_col_names)
        issues.extend(prescan_issues)

        # Normaliseer rijen naar interne veldnamen zodat cross-check werkt
        # over meerdere bronsystemen met verschillende kolomnamen (bijv. ONS + AFAS HRM)
        rev_map = {col: field for field, col in mapping.items()}
        norm_rows = [{rev_map.get(k, k): v for k, v in row.items()} for row in fi["rows"]]
        # Samenvoegen (niet overschrijven) zodat ONS + AFAS HRM samen cross-gecheckt worden
        if sk not in files_data:
            files_data[sk] = {"rows": norm_rows, "mapping": {f: f for f in mapping.keys()}}
        else:
            files_data[sk]["rows"].extend(norm_rows)
            # Mapping uitbreiden met velden uit dit bestand (volgorde-onafhankelijk)
            for f in mapping.keys():
                files_data[sk]["mapping"].setdefault(f, f)
        file_results.append({
            "schema_key":  sk,
            "filename":    fi["filename"],
            "row_count":   len(fi["rows"]),
            "headers":     fi["headers"],
            "mapping":     mapping,
            "issues":      issues,
            "error_count": sum(1 for i in issues if i["severity"] == "error"),
            "warn_count":  sum(1 for i in issues if i["severity"] == "warning"),
        })

    cross_results = run_cross_checks(files_data)
    total_rows   = sum(fr["row_count"] for fr in file_results)
    total_errors = sum(fr["error_count"] for fr in file_results) + sum(1 for c in cross_results if c["severity"] == "error")
    total_warns  = sum(fr["warn_count"]  for fr in file_results) + sum(1 for c in cross_results if c["severity"] == "warning")
    max_issues   = total_rows * max(len(file_results), 1)
    score        = max(0.0, round(100.0 - (total_errors * 5 + total_warns * 2), 1))

    return {
        "file_results":   file_results,
        "cross_results":  cross_results,
        "total_rows":     total_rows,
        "total_errors":   total_errors,
        "total_warns":    total_warns,
        "score":          score,
        "files_summary":  [{"filename": fr["filename"], "schema_key": fr["schema_key"], "row_count": fr["row_count"]} for fr in file_results],
    }
