"""
report_builder.py — Transformeert ruwe ValidationRun-data naar de drie Rhadix rapporttypen.

Gebruik:
    from app.services.report_builder import build_report

    rapport = build_report(run, report_type="beschikbaarheid")
    rapport = build_report(run, report_type="kikv_readiness")
    rapport = build_report(run, report_type="management")

De builder leest uitsluitend uit:
  - ValidationRun.results  (JSON payload van de validator)
  - ValidationRun.*        (score, label, created_at, files, ...)
  - rules.py               (FIELD_RULES, CONTRACTTYPE_ALLOWED, ...)

De builder schrijft NOOIT naar de database. Hij is puur functioneel.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from app.models.report_models import (
    AvailabilitySummary,
    AvailabilityStatus,
    BeschikbaarheidsReport,
    FieldAvailability,
    FieldQuality,
    ImpactLevel,
    IssueCategory,
    KikvIndicator,
    KikvReadinessReport,
    KikvReadinessSummary,
    ManagementReport,
    Priority,
    QualitySummary,
    ReadinessStatus,
    ReportAction,
    ReportIssue,
    ReportMeta,
    ReportRecommendation,
    ReportType,
    RowDetail,
    SchemaAvailability,
    Severity,
)
from app.services.rules import FIELD_RULES

# ─── Schema-metadata ──────────────────────────────────────────────────────────
# Koppelt interne schema-sleutels aan leesbare labels en KIK-V concepten.

SCHEMA_META: dict[str, dict] = {
    "medewerker":      {"label": "Medewerker",      "concept": "Mens"},
    "werkovereenkomst":{"label": "Werkovereenkomst", "concept": "WerkOvereenkomst"},
    "functie":         {"label": "Functie",          "concept": "WerkOvereenkomst"},
    "verzuim":         {"label": "Verzuim",          "concept": "Verzuimperiode"},
}

SCHEMA_ORDER = ["medewerker", "werkovereenkomst", "functie", "verzuim"]

# ─── KIK-V Uitwisselindicatoren ───────────────────────────────────────────────
# Elk uitwisselprofiel beschrijft welke velden nodig zijn voor één KIK-V uitwisseling.
# Formaat field_refs: "schema_key.field_key"

KIKV_INDICATORS: list[dict] = [
    {
        "indicator_id":    "mens_identificatie",
        "indicator_name":  "Medewerker identificatie",
        "exchange_profile":"Mens — Basisgegevens",
        "description":     "Unieke identificatie van iedere zorgmedewerker via personeelsnummer en geboortedatum.",
        "required_fields": ["medewerker.personeelsnummer", "medewerker.geboortedatum"],
    },
    {
        "indicator_id":    "dienstverband_type",
        "indicator_name":  "Dienstverbandtype",
        "exchange_profile":"WerkOvereenkomst — Contracttype",
        "description":     "Contracttype conform KIK-V OvereenkomstType codelijst, inclusief einddatum voor tijdelijke contracten.",
        "required_fields": ["werkovereenkomst.overeenkomsttype", "werkovereenkomst.startdatum", "werkovereenkomst.personeelsnummer"],
    },
    {
        "indicator_id":    "dienstverband_periode",
        "indicator_name":  "Dienstverbandperiode",
        "exchange_profile":"WerkOvereenkomst — Looptijd",
        "description":     "Start- en einddatum van het dienstverband voor tijdelijke contracten.",
        "required_fields": ["werkovereenkomst.startdatum", "werkovereenkomst.einddatum"],
    },
    {
        "indicator_id":    "functie_kwalificatie",
        "indicator_name":  "Functie & kwalificatieniveau",
        "exchange_profile":"WerkOvereenkomst — Functie",
        "description":     "Functienaam en KIK-V kwalificatieniveaucode voor rapportage over scholing.",
        "required_fields": ["functie.functie", "functie.kwalificatieniveau"],
    },
    {
        "indicator_id":    "verzuim_registratie",
        "indicator_name":  "Verzuimregistratie",
        "exchange_profile":"Verzuimperiode — Basisgegevens",
        "description":     "Start en soort verzuim conform KIK-V SoortVerzuim codelijst.",
        "required_fields": ["verzuim.personeelsnummer", "verzuim.startmoment", "verzuim.soortverzuim"],
    },
    {
        "indicator_id":    "verzuim_percentage",
        "indicator_name":  "Verzuimpercentage",
        "exchange_profile":"Verzuimperiode — Omvang",
        "description":     "Mate van arbeidsongeschiktheid als percentage (0–100) voor KIK-V-rapportage.",
        "required_fields": ["verzuim.startmoment", "verzuim.verzuimpercentage"],
    },
]


# ─── Hulpfuncties ─────────────────────────────────────────────────────────────

def _schema_label(schema_key: str) -> str:
    return SCHEMA_META.get(schema_key, {}).get("label", schema_key.capitalize())

def _concept(schema_key: str) -> str:
    return SCHEMA_META.get(schema_key, {}).get("concept", "Overig")

def _field_label(schema_key: str, field_key: str) -> str:
    return FIELD_RULES.get(schema_key, {}).get(field_key, {}).get("label", field_key)

def _field_is_required(schema_key: str, field_key: str) -> bool:
    return FIELD_RULES.get(schema_key, {}).get(field_key, {}).get("required", False)

def _field_source(schema_key: str, field_key: str) -> str | None:
    return FIELD_RULES.get(schema_key, {}).get(field_key, {}).get("source")

def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))

def _quality_score(errors: int, warnings: int, total_rows: int) -> float:
    """
    Kwaliteitsscore 0–100.
    Fouten wegen zwaarder (factor 2) dan waarschuwingen.
    """
    if total_rows <= 0:
        return 100.0
    penalty = (errors * 2 + warnings) / total_rows * 100
    return _clamp(100.0 - penalty)


# ─── AvailabilitySummary bouwen ───────────────────────────────────────────────

def _build_availability(results: dict, file_index: dict[str, dict]) -> AvailabilitySummary:
    """
    Bouwt AvailabilitySummary op uit de validator-resultaten.

    file_index: {schema_key → file_result dict} — beschikbaar via _index_files().
    """
    schemas: list[SchemaAvailability] = []

    for schema_key in SCHEMA_ORDER:
        field_rules = FIELD_RULES.get(schema_key, {})
        fr = file_index.get(schema_key)  # file_result of None

        fields: list[FieldAvailability] = []

        for field_key, rule in field_rules.items():
            concept     = _concept(schema_key)
            is_required = bool(rule.get("required", False))
            source      = rule.get("source")
            label       = rule.get("label", field_key)

            if fr is None:
                # Schema niet geüpload
                status        = AvailabilityStatus.ontbreekt
                mapped_column = None
                coverage_pct  = 0.0
                empty_count   = 0
                invalid_count = 0
                total_rows    = 0
            else:
                # Kijk of er issues zijn die dit veld raken
                field_issues = [
                    iss for iss in fr.get("issues", [])
                    if _issue_concerns_field(iss, field_key)
                ]
                errors   = sum(1 for i in field_issues if i.get("severity") == "error")
                warnings = sum(1 for i in field_issues if i.get("severity") == "warning")
                total_rows    = fr.get("row_count", 0)
                affected_rows = sum(i.get("count", 0) for i in field_issues)

                # Bepaal coverage
                empty_count   = sum(
                    i.get("count", 0) for i in field_issues
                    if "ontbreekt" in i.get("label", "").lower()
                    or "leeg" in i.get("label", "").lower()
                    or "missing" in i.get("id", "").lower()
                )
                invalid_count = sum(
                    i.get("count", 0) for i in field_issues
                    if "ongeldig" in i.get("label", "").lower()
                    or "afwijkend" in i.get("label", "").lower()
                    or "niet" in i.get("label", "").lower()
                    or "invalid" in i.get("id", "").lower()
                )
                filled_rows  = max(0, total_rows - empty_count)
                coverage_pct = (filled_rows / total_rows * 100) if total_rows > 0 else 0.0

                # Mappingstatus: check of kolom herkend is
                mapped_column = fr.get("columns_mapped", {}).get(field_key)

                # Bepaal status
                if errors > 0 and empty_count >= total_rows * 0.5:
                    status = AvailabilityStatus.ontbreekt
                elif errors > 0 or invalid_count > 0:
                    status = AvailabilityStatus.niet_eenduidig
                elif mapped_column is None and is_required:
                    status = AvailabilityStatus.ontbreekt
                else:
                    status = AvailabilityStatus.aanwezig

            fields.append(FieldAvailability(
                field_key=field_key,
                field_label=label,
                concept=concept,
                is_required=is_required,
                status=status,
                mapped_column=mapped_column,
                coverage_pct=round(coverage_pct, 1),
                empty_count=empty_count,
                invalid_count=invalid_count,
                total_rows=total_rows,
                source=source,
            ))

        # Schema-score: gewogen gemiddelde veldstatus
        if fields:
            present     = sum(1 for f in fields if f.status == AvailabilityStatus.aanwezig)
            ambiguous   = sum(1 for f in fields if f.status == AvailabilityStatus.niet_eenduidig)
            avail_score = _clamp((present * 1.0 + ambiguous * 0.5) / len(fields) * 100)
        else:
            avail_score = 0.0

        schemas.append(SchemaAvailability(
            schema_key=schema_key,
            schema_label=_schema_label(schema_key),
            file_uploaded=fr is not None,
            filename=fr.get("filename") if fr else None,
            row_count=fr.get("row_count", 0) if fr else 0,
            recognized_columns=len(fr.get("columns_mapped", {})) if fr else 0,
            total_columns=fr.get("total_columns", 0) if fr else 0,
            availability_score=round(avail_score, 1),
            fields=fields,
        ))

    # Totaaltellingen
    all_fields    = [f for s in schemas for f in s.fields]
    total_schemas = len(schemas)
    uploaded      = sum(1 for s in schemas if s.file_uploaded)
    total_f       = len(all_fields)
    present_f     = sum(1 for f in all_fields if f.status == AvailabilityStatus.aanwezig)
    missing_f     = sum(1 for f in all_fields if f.status == AvailabilityStatus.ontbreekt)
    ambiguous_f   = sum(1 for f in all_fields if f.status == AvailabilityStatus.niet_eenduidig)
    req_missing   = sum(1 for f in all_fields if f.is_required and f.status == AvailabilityStatus.ontbreekt)

    uploaded_scores = [s.availability_score for s in schemas if s.file_uploaded]
    overall_score   = sum(uploaded_scores) / len(uploaded_scores) if uploaded_scores else 0.0

    return AvailabilitySummary(
        total_schemas=total_schemas,
        schemas_uploaded=uploaded,
        total_fields=total_f,
        fields_present=present_f,
        fields_missing=missing_f,
        fields_ambiguous=ambiguous_f,
        required_missing=req_missing,
        availability_score=round(overall_score, 1),
        schemas=schemas,
    )


def _issue_concerns_field(issue: dict, field_key: str) -> bool:
    """Heuristiek: raakt dit issue het opgegeven veld?"""
    issue_id = issue.get("id", "").lower()
    label    = issue.get("label", "").lower()
    return field_key.lower() in issue_id or field_key.lower() in label


# ─── QualitySummary bouwen ────────────────────────────────────────────────────

def _build_quality(results: dict, file_index: dict[str, dict]) -> QualitySummary:
    field_qualities: list[FieldQuality] = []

    for schema_key, fr in file_index.items():
        field_rules = FIELD_RULES.get(schema_key, {})
        total_rows  = fr.get("row_count", 0)

        # Groepeer issues per veld
        for field_key, rule in field_rules.items():
            field_issues = [
                iss for iss in fr.get("issues", [])
                if _issue_concerns_field(iss, field_key)
            ]
            if not field_issues:
                continue

            errors        = sum(i.get("count", 0) for i in field_issues if i.get("severity") == "error")
            warnings      = sum(i.get("count", 0) for i in field_issues if i.get("severity") == "warning")
            affected_rows = min(total_rows, sum(i.get("count", 0) for i in field_issues))

            field_qualities.append(FieldQuality(
                field_key=field_key,
                field_label=rule.get("label", field_key),
                concept=_concept(schema_key),
                schema_key=schema_key,
                error_count=errors,
                warning_count=warnings,
                affected_rows=affected_rows,
                total_rows=total_rows,
                quality_score=round(_quality_score(errors, warnings, total_rows), 1),
                issue_labels=[i.get("label", "") for i in field_issues],
            ))

    total_errors   = sum(fq.error_count   for fq in field_qualities)
    total_warnings = sum(fq.warning_count for fq in field_qualities)

    # Globale kwaliteitsscore = gemiddelde van veldscores (gewogen naar affected_rows)
    total_weighted = sum(fq.quality_score * max(fq.total_rows, 1) for fq in field_qualities)
    total_rows_sum = sum(max(fq.total_rows, 1) for fq in field_qualities)
    quality_score  = (total_weighted / total_rows_sum) if total_rows_sum > 0 else 100.0

    # Sorteer op slechtste score eerst
    field_qualities.sort(key=lambda fq: fq.quality_score)

    return QualitySummary(
        total_errors=total_errors,
        total_warnings=total_warnings,
        quality_score=round(quality_score, 1),
        field_qualities=field_qualities,
    )


# ─── KikvReadinessSummary bouwen ─────────────────────────────────────────────

def _build_kikv_readiness(
    availability: AvailabilitySummary,
    quality: QualitySummary,
    file_index: dict[str, dict],
) -> KikvReadinessSummary:
    """
    Beoordeelt elke KIK-V indicator op basis van:
      1. Of alle vereiste velden beschikbaar zijn.
      2. Of de kwaliteit van die velden voldoende is (quality_score van FieldQuality).
    """
    # Bouw snel-opzoekbare dicts
    field_avail: dict[str, AvailabilityStatus] = {}
    for schema in availability.schemas:
        for f in schema.fields:
            key = f"{schema.schema_key}.{f.field_key}"
            field_avail[key] = f.status

    field_quality_map: dict[str, float] = {}
    for fq in quality.field_qualities:
        key = f"{fq.schema_key}.{fq.field_key}"
        field_quality_map[key] = fq.quality_score

    indicators: list[KikvIndicator] = []

    for ind_def in KIKV_INDICATORS:
        required  = ind_def["required_fields"]
        available = []
        missing   = []
        blocking  = []
        quality_scores = []

        for ref in required:
            status = field_avail.get(ref, AvailabilityStatus.ontbreekt)
            if status == AvailabilityStatus.aanwezig:
                available.append(ref)
                qs = field_quality_map.get(ref, 100.0)
                quality_scores.append(qs)
                if qs < 60.0:
                    # Kwaliteit te laag — telt als blokkerende issue
                    schema_k, field_k = ref.split(".", 1)
                    blocking.append(
                        f"{_field_label(schema_k, field_k)}: kwaliteitsscore {qs:.0f}%"
                    )
            elif status == AvailabilityStatus.niet_eenduidig:
                available.append(ref)  # aanwezig maar niet volledig conform
                quality_scores.append(50.0)
                schema_k, field_k = ref.split(".", 1)
                blocking.append(f"{_field_label(schema_k, field_k)}: waarden niet eenduidig")
            else:
                missing.append(ref)
                schema_k, field_k = ref.split(".", 1)
                blocking.append(f"{_field_label(schema_k, field_k)}: ontbreekt")

        # Gemiddelde kwaliteitsscore voor de aanwezige velden
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        pct_available = len(available) / len(required) if required else 0.0

        # Gecombineerde score: 60% beschikbaarheid, 40% kwaliteit
        combined = pct_available * 60 + (avg_quality / 100) * 40

        if combined >= 90:
            status = ReadinessStatus.gereed
        elif combined >= 50:
            status = ReadinessStatus.gedeeltelijk
        else:
            status = ReadinessStatus.niet_gereed

        indicators.append(KikvIndicator(
            indicator_id=ind_def["indicator_id"],
            indicator_name=ind_def["indicator_name"],
            exchange_profile=ind_def["exchange_profile"],
            description=ind_def.get("description", ""),
            required_fields=required,
            available_fields=available,
            missing_fields=missing,
            data_quality_score=round(avg_quality, 1),
            readiness_status=status,
            blocking_issues=blocking,
        ))

    ready    = sum(1 for i in indicators if i.readiness_status == ReadinessStatus.gereed)
    partial  = sum(1 for i in indicators if i.readiness_status == ReadinessStatus.gedeeltelijk)
    not_rdy  = sum(1 for i in indicators if i.readiness_status == ReadinessStatus.niet_gereed)
    total    = len(indicators)
    score    = (ready * 100 + partial * 50) / total if total else 0.0

    return KikvReadinessSummary(
        indicators_total=total,
        indicators_ready=ready,
        indicators_partial=partial,
        indicators_not_ready=not_rdy,
        readiness_score=round(score, 1),
        indicators=indicators,
    )


# ─── Issues bouwen ────────────────────────────────────────────────────────────

def _build_issues(results: dict, file_index: dict[str, dict], max_rows: int = 25) -> list[ReportIssue]:
    issues: list[ReportIssue] = []

    SEV_MAP = {"error": Severity.error, "warning": Severity.warning, "info": Severity.info}

    for schema_key, fr in file_index.items():
        for raw in fr.get("issues", []):
            rows = [
                RowDetail(
                    rowNumber=r.get("rowNumber"),
                    personId=r.get("personId"),
                    field=r.get("field"),
                    currentValue=r.get("currentValue"),
                    expectedValue=r.get("expectedValue"),
                    message=r.get("message"),
                )
                for r in (raw.get("rows") or [])[:max_rows]
            ]

            # Bepaal categorie op basis van issue-id
            issue_id_lower = raw.get("id", "").lower()
            if "unmapped" in issue_id_lower or "herkend" in issue_id_lower:
                category = IssueCategory.mapping
            elif "missing" in issue_id_lower or "ontbreekt" in issue_id_lower:
                category = IssueCategory.beschikbaarheid
            else:
                category = IssueCategory.kwaliteit

            issues.append(ReportIssue(
                issue_id=f"{schema_key}.{raw.get('id', 'unknown')}",
                severity=SEV_MAP.get(raw.get("severity", "info"), Severity.info),
                category=category,
                schema_key=schema_key,
                schema_label=_schema_label(schema_key),
                field=raw.get("field"),
                field_label=raw.get("fieldLabel"),
                label=raw.get("label", ""),
                count=raw.get("count", 0),
                detail=raw.get("detail"),
                rows=rows,
                allowed_values=raw.get("allowedValues") or [],
                source=raw.get("source"),
            ))

    # Cross-bestand issues
    for raw in results.get("cross_results", []):
        issues.append(ReportIssue(
            issue_id=f"cross.{raw.get('id', 'unknown')}",
            severity=SEV_MAP.get(raw.get("severity", "info"), Severity.info),
            category=IssueCategory.cross,
            schema_key="cross",
            schema_label="Cross-bestand",
            label=raw.get("label", ""),
            count=raw.get("count", 0),
            detail=raw.get("detail"),
        ))

    # Sorteer: errors → warnings → info, dan op count aflopend
    SEV_ORDER = {Severity.error: 0, Severity.warning: 1, Severity.info: 2}
    issues.sort(key=lambda i: (SEV_ORDER[i.severity], -i.count))
    return issues


# ─── Acties bouwen ────────────────────────────────────────────────────────────

# Statische actiesjablonen, gecorreleerd aan bekende issue-patronen.
# De builder matcht issues op sleutelwoorden en genereert acties.

_ACTION_TEMPLATES: list[dict] = [
    {
        "match_ids":    ["missing_einddatum_temp"],
        "action_id":    "act_einddatum",
        "title":        "Einddatum toevoegen bij tijdelijke contracten",
        "priority":     Priority.hoog,
        "category":     "Datakwaliteit",
        "hours":        3.0,
        "description":  "Bij tijdelijke contracten is een einddatum verplicht conform KIK-V. "
                        "Voeg de ontbrekende einddatums toe vanuit de contractdocumentatie.",
        "steps": [
            "Exporteer de lijst met betrokken personeelsnummers uit Rhadix",
            "Zoek de contractdocumenten op in het bronsysteem",
            "Vul de einddatums in en sla op",
            "Hervalideer het bestand in Rhadix",
        ],
    },
    {
        "match_ids":    ["invalid_contracttype", "unknown_contracttype"],
        "action_id":    "act_contracttype",
        "title":        "Contracttype mappen naar KIK-V codelijst",
        "priority":     Priority.hoog,
        "category":     "Datamapping",
        "hours":        2.0,
        "description":  "Het contracttype-veld bevat waarden die niet in de KIK-V OvereenkomstType codelijst staan. "
                        "Maak een mapping van interne waarden naar de standaardcodelijst.",
        "steps": [
            "Bekijk de lijst met afwijkende contracttypewaarden in Rhadix",
            "Maak een mapping-tabel: intern → KIK-V waarde",
            "Pas de exportroutine in het bronsysteem aan",
            "Hervalideer",
        ],
    },
    {
        "match_ids":    ["invalid_date", "invalid_geboortedatum", "invalid_startdatum"],
        "action_id":    "act_datumformaat",
        "title":        "Datumnotatie standaardiseren naar dd/mm/yyyy",
        "priority":     Priority.gemiddeld,
        "category":     "Datakwaliteit",
        "hours":        1.5,
        "description":  "Datumvelden bevatten niet-herkende notaties. KIK-V vereist dd/mm/yyyy.",
        "steps": [
            "Identificeer de huidige datumnotatie in het bronsysteem",
            "Pas de export-instellingen aan naar dd/mm/yyyy",
            "Test met een steekproef van 10 rijen",
        ],
    },
    {
        "match_ids":    ["missing_required", "missing_personeelsnummer", "missing_startmoment"],
        "action_id":    "act_verplichte_velden",
        "title":        "Verplichte velden aanvullen",
        "priority":     Priority.hoog,
        "category":     "Datavolledigheid",
        "hours":        2.5,
        "description":  "Verplichte KIK-V velden ontbreken in de aangeleverde bestanden. "
                        "Vul deze aan of controleer de exportconfiguratie.",
        "steps": [
            "Bekijk het Beschikbaarheidsrapport voor de volledige lijst",
            "Controleer of de kolom aanwezig is in het bronsysteem",
            "Pas de exportdefinitie aan om het veld mee te nemen",
            "Hervalideer",
        ],
    },
    {
        "match_ids":    ["unmapped", "not_recognized"],
        "action_id":    "act_kolomnamen",
        "title":        "Kolomnamen afstemmen op KIK-V aliassen",
        "priority":     Priority.gemiddeld,
        "category":     "Datamapping",
        "hours":        1.0,
        "description":  "Sommige kolommen worden niet automatisch herkend. "
                        "Hernoem ze of voeg ze toe aan de alias-configuratie in Rhadix.",
        "steps": [
            "Zie de mappingproblemen in het Beschikbaarheidsrapport",
            "Hernoem de kolom in het exportbestand naar een herkende alias",
            "Of voeg de kolomnaam toe aan col_aliases in validator.py",
        ],
    },
    {
        "match_ids":    ["duplicate_personeelsnummer", "duplicate"],
        "action_id":    "act_duplicaten",
        "title":        "Dubbele personeelsnummers verwijderen",
        "priority":     Priority.hoog,
        "category":     "Dataïntegriteit",
        "hours":        2.0,
        "description":  "Dubbele personeelsnummers veroorzaken inconsistentie in KIK-V-rapportage.",
        "steps": [
            "Exporteer de lijst met dubbele nummers uit Rhadix",
            "Bepaal welke registratie de 'master' is",
            "Verwijder of samenvoeg duplicaten in het bronsysteem",
            "Voeg een unieke-index-beperking toe",
        ],
    },
]


def _build_actions(issues: list[ReportIssue]) -> list[ReportAction]:
    actions: list[ReportAction] = []
    used_action_ids: set[str] = set()
    issue_id_set = {i.issue_id.split(".", 1)[-1] for i in issues if i.severity in (Severity.error, Severity.warning)}

    for tmpl in _ACTION_TEMPLATES:
        matched_issue_ids = [
            iid for iid in tmpl["match_ids"]
            if any(iid in raw_id for raw_id in issue_id_set)
        ]
        if not matched_issue_ids and tmpl["action_id"] not in ("act_verplichte_velden",):
            continue
        # Voorkom dubbele acties
        if tmpl["action_id"] in used_action_ids:
            continue
        used_action_ids.add(tmpl["action_id"])

        related = [
            i.issue_id for i in issues
            if any(m in i.issue_id for m in tmpl["match_ids"])
        ]

        actions.append(ReportAction(
            action_id=tmpl["action_id"],
            title=tmpl["title"],
            priority=tmpl["priority"],
            category=tmpl["category"],
            estimated_hours=tmpl["hours"],
            description=tmpl["description"],
            steps=tmpl["steps"],
            related_issues=related,
        ))

    # Altijd actie voor verplichte velden toevoegen als er errors zijn
    if any(i.severity == Severity.error for i in issues) and "act_verplichte_velden" not in used_action_ids:
        actions.append(ReportAction(
            action_id="act_verplichte_velden",
            title="Verplichte velden aanvullen",
            priority=Priority.hoog,
            category="Datavolledigheid",
            estimated_hours=2.5,
            description="Er zijn verplichte KIK-V velden die ontbreken.",
            steps=_ACTION_TEMPLATES[3]["steps"],
        ))

    # Sorteer op prioriteit
    PRIO_ORDER = {Priority.hoog: 0, Priority.gemiddeld: 1, Priority.laag: 2}
    actions.sort(key=lambda a: PRIO_ORDER[a.priority])
    return actions


# ─── Aanbevelingen bouwen ─────────────────────────────────────────────────────

def _build_recommendations(
    availability: AvailabilitySummary,
    quality: QualitySummary,
    kikv: KikvReadinessSummary,
    issues: list[ReportIssue],
) -> list[ReportRecommendation]:
    recs: list[ReportRecommendation] = []

    if availability.schemas_uploaded < availability.total_schemas:
        missing_schemas = [
            s.schema_label for s in availability.schemas if not s.file_uploaded
        ]
        recs.append(ReportRecommendation(
            recommendation_id="rec_upload_all",
            category="Volledigheid",
            title=f"Upload ontbrekende schema's: {', '.join(missing_schemas)}",
            rationale="Niet alle KIK-V-schema's zijn aangeleverd. Zonder volledige dataset "
                      "kan de Rhadix Index niet representatief worden berekend.",
            impact=ImpactLevel.hoog,
            related_schemas=[s.schema_key for s in availability.schemas if not s.file_uploaded],
        ))

    if availability.required_missing > 0:
        recs.append(ReportRecommendation(
            recommendation_id="rec_required_fields",
            category="Datavolledigheid",
            title=f"{availability.required_missing} verplichte KIK-V-veld(en) ontbreken",
            rationale="Verplichte velden zijn noodzakelijk voor elke KIK-V-uitwisseling. "
                      "Zonder deze velden kunnen uitwisselprofielen niet worden ingevuld.",
            impact=ImpactLevel.hoog,
            related_schemas=[
                s.schema_key for s in availability.schemas
                if any(f.is_required and f.status == AvailabilityStatus.ontbreekt for f in s.fields)
            ],
        ))

    if quality.quality_score < 80:
        recs.append(ReportRecommendation(
            recommendation_id="rec_quality_low",
            category="Datakwaliteit",
            title="Datakwaliteit onder de 80% — prioriteer correctie vóór uitwisseling",
            rationale=f"De gemiddelde kwaliteitsscore is {quality.quality_score:.0f}%. "
                      "KIK-V-afnemers verwachten minimaal 90% voor betrouwbare rapportage.",
            impact=ImpactLevel.hoog,
            related_schemas=[fq.schema_key for fq in quality.field_qualities if fq.quality_score < 80],
        ))

    if kikv.indicators_not_ready > 0:
        recs.append(ReportRecommendation(
            recommendation_id="rec_kikv_blockers",
            category="KIK-V Gereedheid",
            title=f"{kikv.indicators_not_ready} KIK-V uitwisselindicator(en) nog niet gereed",
            rationale="Niet-gereed indicators betekenen dat deze uitwisselingen niet kunnen "
                      "plaatsvinden totdat de onderliggende dataproblemen zijn opgelost.",
            impact=ImpactLevel.hoog,
            related_schemas=list({
                ref.split(".")[0]
                for ind in kikv.indicators if ind.readiness_status == ReadinessStatus.niet_gereed
                for ref in ind.missing_fields
            }),
        ))

    if availability.availability_score >= 90 and quality.quality_score >= 85:
        recs.append(ReportRecommendation(
            recommendation_id="rec_ready_for_exchange",
            category="KIK-V Gereedheid",
            title="Data grotendeels gereed voor KIK-V-uitwisseling",
            rationale=f"Beschikbaarheidsscore {availability.availability_score:.0f}% en "
                      f"kwaliteitsscore {quality.quality_score:.0f}% liggen boven de drempel. "
                      "Focus op de resterende issues voor volledige conformiteit.",
            impact=ImpactLevel.gemiddeld,
            related_schemas=[],
        ))

    return recs


# ─── Executive summary (management rapport) ───────────────────────────────────

def _build_executive_summary(
    run: Any,
    availability: AvailabilitySummary,
    quality: QualitySummary,
    kikv: KikvReadinessSummary,
) -> str:
    score = int(getattr(run, "score", 0) or 0)
    rhadix_index = min(100, round((score + max(0, score - 20)) / 2))

    ready_pct   = round(kikv.indicators_ready / kikv.indicators_total * 100) if kikv.indicators_total else 0
    partial_pct = round(kikv.indicators_partial / kikv.indicators_total * 100) if kikv.indicators_total else 0

    return (
        f"De Rhadix-analyse over {getattr(run, 'label', 'deze scan')} toont een Rhadix Index van "
        f"{rhadix_index}/100. "
        f"De databeschikbaarheid bedraagt {availability.availability_score:.0f}% "
        f"({availability.fields_present} van {availability.total_fields} velden aanwezig). "
        f"De datakwaliteitsscore is {quality.quality_score:.0f}%"
        f"{' — onder de aanbevolen drempel van 80%' if quality.quality_score < 80 else ''}. "
        f"Van de {kikv.indicators_total} KIK-V uitwisselindicatoren is "
        f"{ready_pct}% gereed, {partial_pct}% gedeeltelijk gereed. "
        f"Er zijn {quality.total_errors} fouten en {quality.total_warnings} waarschuwingen "
        f"geïdentificeerd die aandacht vereisen vóór KIK-V-uitwisseling."
    )


# ─── Hulp: file_index ─────────────────────────────────────────────────────────

def _index_files(results: dict) -> dict[str, dict]:
    """
    Maakt een {schema_key → file_result} mapping.
    Als meerdere bestanden hetzelfde schema hebben, wordt het eerste genomen.
    """
    index: dict[str, dict] = {}
    for fr in results.get("file_results", []):
        sk = fr.get("schema_key", "")
        if sk and sk not in index:
            index[sk] = fr
    return index


# ─── Publieke entry-point ─────────────────────────────────────────────────────

def build_report(
    run: Any,
    report_type: str,
    organization_name: str = "Zorginstelling",
    systems: list[str] | None = None,
) -> BeschikbaarheidsReport | KikvReadinessReport | ManagementReport:
    """
    Transformeert een ValidationRun naar één van de drie rapporttypen.

    Args:
        run            — SQLAlchemy ValidationRun object (of dict met dezelfde keys).
        report_type    — 'beschikbaarheid', 'kikv_readiness' of 'management'.
        organization_name — naam van de zorginstelling (optioneel).
        systems        — lijst van geselecteerde bronsystemen (optioneel).

    Returns:
        Een volledig gevuld rapport-Pydantic-object, klaar voor JSON-serialisatie.
    """
    results     = (run.results if hasattr(run, "results") else run.get("results")) or {}
    file_index  = _index_files(results)
    rtype       = ReportType(report_type)

    score       = int(getattr(run, "score", None) or results.get("score", 0) or 0)
    rhadix_index = min(100, round((score + max(0, score - 20)) / 2))

    meta = ReportMeta(
        report_type=rtype,
        scan_id=getattr(run, "id", 0),
        organization_name=organization_name,
        application_name="Rhadix Validator",
        generated_at=datetime.utcnow(),
        scan_label=getattr(run, "label", "") or "",
        scan_date=getattr(run, "created_at", None),
        systems=systems or [],
    )

    # ── Gedeelde bouwstenen ──
    availability = _build_availability(results, file_index)
    issues       = _build_issues(results, file_index)

    if rtype == ReportType.beschikbaarheid:
        recs = _build_recommendations(availability, QualitySummary(), KikvReadinessSummary(), issues)
        return BeschikbaarheidsReport(
            meta=meta,
            availability_summary=availability,
            issues=[i for i in issues if i.category == IssueCategory.beschikbaarheid
                    or i.category == IssueCategory.mapping],
            recommendations=recs,
        )

    # Stap-2-rapporten hebben ook kwaliteit en KIK-V readiness nodig
    quality = _build_quality(results, file_index)
    kikv    = _build_kikv_readiness(availability, quality, file_index)
    actions = _build_actions(issues)
    recs    = _build_recommendations(availability, quality, kikv, issues)

    if rtype == ReportType.kikv_readiness:
        return KikvReadinessReport(
            meta=meta,
            rhadix_index=rhadix_index,
            availability_summary=availability,
            quality_summary=quality,
            kikv_readiness_summary=kikv,
            issues=issues,
            actions=actions,
            recommendations=recs,
        )

    # Management rapport: alleen hoge-prioriteit issues
    high_issues = [i for i in issues if i.severity == Severity.error][:10]
    summary     = _build_executive_summary(run, availability, quality, kikv)

    return ManagementReport(
        meta=meta,
        rhadix_index=rhadix_index,
        executive_summary=summary,
        availability_summary=availability,
        quality_summary=quality,
        kikv_readiness_summary=kikv,
        issues=high_issues,
        actions=actions,
        recommendations=recs,
    )
