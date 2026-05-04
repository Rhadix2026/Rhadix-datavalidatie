/**
 * reports.d.ts — TypeScript-interfaces voor de drie Rhadix rapporttypen.
 *
 * Spiegelt exact de Pydantic-modellen in backend/app/models/report_models.py.
 * Importeer in frontend-componenten als:
 *
 *   import type { BeschikbaarheidsReport, KikvReadinessReport, ManagementReport } from '../types/reports'
 *
 * Rapportdata is bewust gescheiden van UI-weergave: deze interfaces beschrijven
 * uitsluitend de datastructuur. Presentatielogica hoort in React-componenten.
 */

// ─── Enumeraties ──────────────────────────────────────────────────────────────

export type ReportType =
  | 'beschikbaarheid'
  | 'kikv_readiness'
  | 'management'

export type Severity = 'error' | 'warning' | 'info'

export type AvailabilityStatus =
  | 'aanwezig'        // veld aanwezig en gevuld
  | 'ontbreekt'       // veld geheel afwezig of leeg
  | 'niet_eenduidig'  // veld aanwezig maar waarden buiten codelijst

export type ReadinessStatus =
  | 'gereed'          // ≥ 90% conform
  | 'gedeeltelijk'    // 50–89% conform
  | 'niet_gereed'     // < 50% conform

export type Priority = 'hoog' | 'gemiddeld' | 'laag'

export type ImpactLevel = 'hoog' | 'gemiddeld' | 'laag'

export type IssueCategory =
  | 'beschikbaarheid'
  | 'kwaliteit'
  | 'mapping'
  | 'cross'


// ─── Veldniveau ───────────────────────────────────────────────────────────────

/** Beschikbaarheidsstatus van één KIK-V veld binnen een schema. */
export interface FieldAvailability {
  field_key:      string
  field_label:    string
  concept:        string               // 'Mens', 'WerkOvereenkomst', 'Verzuimperiode'
  is_required:    boolean
  status:         AvailabilityStatus
  mapped_column:  string | null        // kolomnaam in het aangeleverde bestand
  coverage_pct:   number               // % rijen met niet-lege waarde (0–100)
  empty_count:    number
  invalid_count:  number
  total_rows:     number
  source:         string | null        // bijv. 'KIK-V OvereenkomstType codelijst'
}

/** Kwaliteitsindicatoren voor één veld — stap-2-rapporten. */
export interface FieldQuality {
  field_key:     string
  field_label:   string
  concept:       string
  schema_key:    string
  error_count:   number
  warning_count: number
  affected_rows: number
  total_rows:    number
  quality_score: number    // 0–100; 100 = geen fouten
  issue_labels:  string[]
}


// ─── Schemaniveau ─────────────────────────────────────────────────────────────

/** Beschikbaarheidsstatus van één geüpload schema. */
export interface SchemaAvailability {
  schema_key:           string
  schema_label:         string
  file_uploaded:        boolean
  filename:             string | null
  row_count:            number
  recognized_columns:   number
  total_columns:        number
  availability_score:   number    // 0–100
  fields:               FieldAvailability[]
}


// ─── Samenvattingsniveau ──────────────────────────────────────────────────────

/** Samenvattende beschikbaarheidsscores over alle schema's. */
export interface AvailabilitySummary {
  total_schemas:      number
  schemas_uploaded:   number
  total_fields:       number
  fields_present:     number
  fields_missing:     number
  fields_ambiguous:   number
  required_missing:   number
  availability_score: number    // gewogen gemiddelde, 0–100
  schemas:            SchemaAvailability[]
}

/** Samenvattende kwaliteitsscores op veldniveau. */
export interface QualitySummary {
  total_errors:    number
  total_warnings:  number
  quality_score:   number    // 0–100
  field_qualities: FieldQuality[]
}


// ─── KIK-V Indicator ──────────────────────────────────────────────────────────

/** Eén KIK-V uitwisselprofiel/indicator met readiness-oordeel. */
export interface KikvIndicator {
  indicator_id:       string
  indicator_name:     string
  exchange_profile:   string
  description:        string
  required_fields:    string[]   // ['schema_key.field_key', ...]
  available_fields:   string[]
  missing_fields:     string[]
  data_quality_score: number
  readiness_status:   ReadinessStatus
  blocking_issues:    string[]
}

/** Samenvatting van alle KIK-V indicators. */
export interface KikvReadinessSummary {
  indicators_total:     number
  indicators_ready:     number
  indicators_partial:   number
  indicators_not_ready: number
  readiness_score:      number    // 0–100
  indicators:           KikvIndicator[]
}


// ─── Issue, Actie, Aanbeveling ────────────────────────────────────────────────

/** Eén rij met een fout of waarschuwing. */
export interface RowDetail {
  rowNumber:     number  | null
  personId:      string  | null
  field:         string  | null
  currentValue:  string  | null
  expectedValue: string  | null
  message:       string  | null
}

/** Eén bevinding, met optionele per-rij details. */
export interface ReportIssue {
  issue_id:      string
  severity:      Severity
  category:      IssueCategory
  schema_key:    string
  schema_label:  string
  field:         string | null
  field_label:   string | null
  label:         string
  count:         number
  detail:        string | null
  rows:          RowDetail[]
  allowed_values: Array<{ value: string; label: string; tijdelijk?: boolean }>
  source:        string | null
}

/** Eén aanbevolen actie, afgeleid van issues. */
export interface ReportAction {
  action_id:       string
  title:           string
  priority:        Priority
  category:        string
  estimated_hours: number
  description:     string
  steps:           string[]
  related_issues:  string[]
}

/** Strategische aanbeveling op basis van de analyse. */
export interface ReportRecommendation {
  recommendation_id: string
  category:          string
  title:             string
  rationale:         string
  impact:            ImpactLevel
  related_schemas:   string[]
}


// ─── Rapportmetadata ──────────────────────────────────────────────────────────

/** Metadata aanwezig in alle drie de rapporten. */
export interface ReportMeta {
  report_type:       ReportType
  scan_id:           number
  organization_name: string
  application_name:  string
  generated_at:      string   // ISO 8601 datetime
  scan_label:        string
  scan_date:         string | null
  systems:           string[]
}


// ─── De drie rapporttypen ─────────────────────────────────────────────────────

/**
 * Rapport type 1 — gegenereerd na stap 1 (upload + schema-detectie).
 * Focus: welke velden/data-elementen zijn aanwezig, ontbreken of niet eenduidig?
 * Doelgroep: data-analist, implementatie-verantwoordelijke.
 */
export interface BeschikbaarheidsReport {
  meta:                 ReportMeta
  availability_summary: AvailabilitySummary
  issues:               ReportIssue[]
  recommendations:      ReportRecommendation[]
}

/**
 * Rapport type 2 — gegenereerd na stap 2 (volledige validatie).
 * Focus: per KIK-V uitwisselprofiel, is de data beschikbaar én kwalitatief bruikbaar?
 * Doelgroep: informatiearchitect, KIK-V implementatie-team.
 */
export interface KikvReadinessReport {
  meta:                   ReportMeta
  rhadix_index:           number
  availability_summary:   AvailabilitySummary
  quality_summary:        QualitySummary
  kikv_readiness_summary: KikvReadinessSummary
  issues:                 ReportIssue[]
  actions:                ReportAction[]
  recommendations:        ReportRecommendation[]
}

/**
 * Rapport type 3 — overkoepelend managementrapport.
 * Focus: Rhadix Index, toplijn beschikbaarheid/kwaliteit, risico's, actieplan.
 * Doelgroep: bestuurder, zorgmanager, CISO/privacy-officer.
 * Bevat alleen hoge-prioriteit issues en strategische aanbevelingen.
 */
export interface ManagementReport {
  meta:                   ReportMeta
  rhadix_index:           number
  rhadix_index_prev:      number | null   // toekomstig: trendlijn
  executive_summary:      string
  availability_summary:   AvailabilitySummary
  quality_summary:        QualitySummary
  kikv_readiness_summary: KikvReadinessSummary
  issues:                 ReportIssue[]   // alleen hoge prioriteit
  actions:                ReportAction[]
  recommendations:        ReportRecommendation[]
}

/** Union-type voor alle drie rapporttypen samen. */
export type AnyReport =
  | BeschikbaarheidsReport
  | KikvReadinessReport
  | ManagementReport

/** Beschrijving van één beschikbaar rapporttype (van /api/reports/{id}/types). */
export interface ReportTypeInfo {
  type:        ReportType
  label:       string
  description: string
  available:   boolean
}

/** Response van GET /api/reports/{run_id}/types */
export interface ReportTypesResponse {
  scan_id:    number
  scan_label: string
  types:      ReportTypeInfo[]
}
