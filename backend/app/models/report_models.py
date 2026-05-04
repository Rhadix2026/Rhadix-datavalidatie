"""
report_models.py — Pydantic-typestructuur voor de drie Rhadix rapporttypen.

Drie rapporttypen:
  - BeschikbaarheidsReport  : na stap 1 — databeschikbaarheid per veld/schema
  - KikvReadinessReport     : na stap 2 — beschikbaarheid + kwaliteit t.o.v. KIK-V
  - ManagementReport        : overkoepelend — Rhadix Index, risico's, actieplan

Ontwerpprincipes:
  - Rapportdata is volledig gescheiden van UI-weergave.
  - Alle modellen zijn JSON-serialiseerbaar (FastAPI + Pydantic v2).
  - Builder-laag (report_builder.py) transformeert ruwe scanresultaten
    naar deze typen; routers en frontend hoeven de logica niet te kennen.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ─── Enumeraties ──────────────────────────────────────────────────────────────

class ReportType(str, Enum):
    beschikbaarheid = "beschikbaarheid"
    kikv_readiness  = "kikv_readiness"
    management      = "management"

class Severity(str, Enum):
    error   = "error"
    warning = "warning"
    info    = "info"

class AvailabilityStatus(str, Enum):
    aanwezig        = "aanwezig"        # veld aanwezig en gevuld
    ontbreekt       = "ontbreekt"       # veld geheel afwezig of leeg
    niet_eenduidig  = "niet_eenduidig"  # veld aanwezig maar waarden buiten codelijst

class ReadinessStatus(str, Enum):
    gereed          = "gereed"          # ≥ 90% conform
    gedeeltelijk    = "gedeeltelijk"    # 50–89% conform
    niet_gereed     = "niet_gereed"     # < 50% conform

class Priority(str, Enum):
    hoog     = "hoog"
    gemiddeld = "gemiddeld"
    laag     = "laag"

class ImpactLevel(str, Enum):
    hoog     = "hoog"
    gemiddeld = "gemiddeld"
    laag     = "laag"

class IssueCategory(str, Enum):
    beschikbaarheid = "beschikbaarheid"
    kwaliteit       = "kwaliteit"
    mapping         = "mapping"
    cross           = "cross"


# ─── Veldniveau ───────────────────────────────────────────────────────────────

class FieldAvailability(BaseModel):
    """Beschikbaarheidsstatus van één KIK-V veld binnen een schema."""
    field_key:      str                  # intern sleutelwoord, bijv. 'overeenkomsttype'
    field_label:    str                  # gebruikersvriendelijke naam, bijv. 'Contracttype'
    concept:        str                  # KIK-V concept: 'Mens', 'WerkOvereenkomst', 'Verzuim'
    is_required:    bool                 # verplicht volens KIK-V?
    status:         AvailabilityStatus
    mapped_column:  Optional[str] = None  # kolomnaam in het aangeleverde bestand
    coverage_pct:   float = 0.0           # % rijen met een niet-lege waarde (0–100)
    empty_count:    int   = 0             # aantal lege rijen
    invalid_count:  int   = 0             # aantal rijen met ongeldige waarde
    total_rows:     int   = 0
    source:         Optional[str] = None  # bijv. 'KIK-V OvereenkomstType codelijst'


class FieldQuality(BaseModel):
    """Kwaliteitsindicatoren voor één veld — gebruikt in stap-2-rapporten."""
    field_key:      str
    field_label:    str
    concept:        str
    schema_key:     str
    error_count:    int   = 0
    warning_count:  int   = 0
    affected_rows:  int   = 0
    total_rows:     int   = 0
    quality_score:  float = 100.0   # 0–100; 100 = geen fouten
    issue_labels:   list[str] = Field(default_factory=list)  # leesbare labels


# ─── Schemaniveau ─────────────────────────────────────────────────────────────

class SchemaAvailability(BaseModel):
    """Beschikbaarheidsstatus van één geüpload schema (bijv. 'werkovereenkomst')."""
    schema_key:            str
    schema_label:          str           # bijv. 'Werkovereenkomst'
    file_uploaded:         bool
    filename:              Optional[str] = None
    row_count:             int  = 0
    recognized_columns:    int  = 0      # kolommen die aan een KIK-V veld gemapped zijn
    total_columns:         int  = 0      # totaal kolommen in het bestand
    availability_score:    float = 0.0   # 0–100
    fields:                list[FieldAvailability] = Field(default_factory=list)

    @property
    def missing_required_count(self) -> int:
        return sum(
            1 for f in self.fields
            if f.is_required and f.status == AvailabilityStatus.ontbreekt
        )


# ─── Samenvattingsniveau ──────────────────────────────────────────────────────

class AvailabilitySummary(BaseModel):
    """
    Samenvattende beschikbaarheidsscores over alle schema's.
    Primaire uitvoer voor het Beschikbaarheidsrapport.
    """
    total_schemas:       int   = 0
    schemas_uploaded:    int   = 0
    total_fields:        int   = 0
    fields_present:      int   = 0   # status == aanwezig
    fields_missing:      int   = 0   # status == ontbreekt
    fields_ambiguous:    int   = 0   # status == niet_eenduidig
    required_missing:    int   = 0   # verplichte velden die ontbreken
    availability_score:  float = 0.0  # gewogen gemiddelde, 0–100
    schemas:             list[SchemaAvailability] = Field(default_factory=list)


class QualitySummary(BaseModel):
    """
    Samenvattende kwaliteitsscores op veldniveau.
    Primaire uitvoer voor stap-2-rapporten.
    """
    total_errors:    int   = 0
    total_warnings:  int   = 0
    quality_score:   float = 100.0   # 0–100
    field_qualities: list[FieldQuality] = Field(default_factory=list)


# ─── KIK-V Indicator ──────────────────────────────────────────────────────────

class KikvIndicator(BaseModel):
    """
    Eén KIK-V uitwisselprofiel/indicator met readiness-oordeel.

    Indicators zijn gedefinieerd in report_builder.py (KIKV_INDICATORS).
    Ze bundelen de velden die nodig zijn voor één specifieke KIK-V uitwisseling
    en geven een gecombineerd oordeel op basis van beschikbaarheid én kwaliteit.
    """
    indicator_id:       str               # bijv. 'medewerker_id'
    indicator_name:     str               # bijv. 'Medewerker identificatie'
    exchange_profile:   str               # bijv. 'Mens — Basisgegevens'
    description:        str = ""
    required_fields:    list[str]         # [schema_key.field_key, ...]
    available_fields:   list[str]         # subset van required_fields die aanwezig + conform zijn
    missing_fields:     list[str]         # subset die ontbreekt of niet-conform is
    data_quality_score: float = 0.0       # 0–100
    readiness_status:   ReadinessStatus
    blocking_issues:    list[str] = Field(default_factory=list)  # issue-labels die blokkeren


class KikvReadinessSummary(BaseModel):
    """
    Samenvatting van alle KIK-V indicators.
    Primaire uitvoer voor het KIK-V Readiness rapport.
    """
    indicators_total:    int   = 0
    indicators_ready:    int   = 0
    indicators_partial:  int   = 0
    indicators_not_ready: int  = 0
    readiness_score:     float = 0.0   # 0–100
    indicators:          list[KikvIndicator] = Field(default_factory=list)


# ─── Issue, Actie, Aanbeveling ────────────────────────────────────────────────

class RowDetail(BaseModel):
    """Eén rij met een fout of waarschuwing — directe kopie van backend issue-rij."""
    rowNumber:     Optional[int]  = None
    personId:      Optional[str]  = None
    field:         Optional[str]  = None
    currentValue:  Optional[str]  = None
    expectedValue: Optional[str]  = None
    message:       Optional[str]  = None


class ReportIssue(BaseModel):
    """
    Eén bevinding, met optionele per-rij details.
    Geschikt voor alle drie de rapporten; rapporten filteren op severity/category.
    """
    issue_id:      str
    severity:      Severity
    category:      IssueCategory
    schema_key:    str
    schema_label:  str
    field:         Optional[str] = None
    field_label:   Optional[str] = None
    label:         str                    # korte leesbare omschrijving
    count:         int = 0               # aantal betrokken rijen
    detail:        Optional[str] = None  # samenvatting (bijv. 'Personen: P1, P2')
    rows:          list[RowDetail] = Field(default_factory=list)
    allowed_values: list[dict]    = Field(default_factory=list)
    source:        Optional[str]  = None


class ReportAction(BaseModel):
    """
    Eén aanbevolen actie, afgeleid van issues.
    Wordt opgenomen in KIK-V Readiness en Management rapporten.
    """
    action_id:        str
    title:            str
    priority:         Priority
    category:         str               # bijv. 'Datakwaliteit', 'Systeem', 'Proces'
    estimated_hours:  float = 0.0
    description:      str = ""
    steps:            list[str] = Field(default_factory=list)
    related_issues:   list[str] = Field(default_factory=list)  # issue_id's


class ReportRecommendation(BaseModel):
    """
    Strategische aanbeveling op basis van de analyse.
    Wordt opgenomen in alle drie de rapporten, met de nadruk op het Management rapport.
    """
    recommendation_id: str
    category:          str
    title:             str
    rationale:         str
    impact:            ImpactLevel
    related_schemas:   list[str] = Field(default_factory=list)


# ─── De drie rapporttypen ─────────────────────────────────────────────────────

class ReportMeta(BaseModel):
    """Metadata die in alle drie de rapporten aanwezig is."""
    report_type:       ReportType
    scan_id:           int
    organization_name: str = "Zorginstelling"
    application_name:  str = "Rhadix Validator"
    generated_at:      datetime = Field(default_factory=datetime.utcnow)
    scan_label:        str = ""
    scan_date:         Optional[datetime] = None
    systems:           list[str] = Field(default_factory=list)  # geselecteerde bronsystemen


class BeschikbaarheidsReport(BaseModel):
    """
    Rapport type 1 — gegenereerd na stap 1 (upload + schema-detectie).

    Focus: welke velden/data-elementen zijn aanwezig, ontbreken of niet eenduidig?
    Doelgroep: data-analist, implementatie-verantwoordelijke.
    """
    meta:                  ReportMeta
    availability_summary:  AvailabilitySummary
    issues:                list[ReportIssue] = Field(default_factory=list)
    recommendations:       list[ReportRecommendation] = Field(default_factory=list)


class KikvReadinessReport(BaseModel):
    """
    Rapport type 2 — gegenereerd na stap 2 (volledige validatie).

    Focus: per KIK-V uitwisselprofiel, is de data beschikbaar én kwalitatief bruikbaar?
    Doelgroep: informatiearchitect, KIK-V implementatie-team.
    """
    meta:                   ReportMeta
    rhadix_index:           int = 0
    availability_summary:   AvailabilitySummary
    quality_summary:        QualitySummary
    kikv_readiness_summary: KikvReadinessSummary
    issues:                 list[ReportIssue] = Field(default_factory=list)
    actions:                list[ReportAction] = Field(default_factory=list)
    recommendations:        list[ReportRecommendation] = Field(default_factory=list)


class ManagementReport(BaseModel):
    """
    Rapport type 3 — overkoepelend managementrapport.

    Focus: Rhadix Index, toplijn-beschikbaarheid, toplijn-kwaliteit, risico's, actieplan.
    Doelgroep: bestuurder, zorgmanager, CISO/privacy-officer.
    Bevat alleen high-priority issues en strategische aanbevelingen.
    """
    meta:                   ReportMeta
    rhadix_index:           int   = 0
    rhadix_index_prev:      Optional[int] = None  # voor trendlijn (toekomstig)
    executive_summary:      str   = ""
    availability_summary:   AvailabilitySummary
    quality_summary:        QualitySummary
    kikv_readiness_summary: KikvReadinessSummary
    issues:                 list[ReportIssue] = Field(default_factory=list)   # alleen hoge prioriteit
    actions:                list[ReportAction] = Field(default_factory=list)
    recommendations:        list[ReportRecommendation] = Field(default_factory=list)
