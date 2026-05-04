"""
reports.py — REST-endpoints voor de drie Rhadix rapporttypen.

Architectuur (scheiding van verantwoordelijkheden):
  ┌──────────────────────────────────────────────────────────────────┐
  │  report_models.py         → datatypen (Pydantic)                 │
  │  report_builder.py        → data bouwen vanuit ValidationRun     │
  │  report_pdf_template.py   → PDF-opmaak: kleuren, stijlen,        │
  │                             bouwstenen (RhadixRenderer)           │
  │  reports.py (dit bestand) → thin router + assembler-functies     │
  └──────────────────────────────────────────────────────────────────┘

Endpoints:
  GET  /api/reports/{run_id}/beschikbaarheid       → BeschikbaarheidsReport (JSON)
  GET  /api/reports/{run_id}/beschikbaarheid/pdf   → Beschikbaarheidsrapport (PDF)
  GET  /api/reports/{run_id}/kikv_readiness        → KikvReadinessReport    (JSON)
  GET  /api/reports/{run_id}/kikv_readiness/pdf    → KIK-V Readiness rapport (PDF)
  GET  /api/reports/{run_id}/management            → ManagementReport       (JSON)
  GET  /api/reports/{run_id}/management/pdf        → Gecombineerd Managementrapport (PDF)
  GET  /api/reports/{run_id}/types                 → beschikbare rapporttypen

Query-parameters (alle endpoints):
  organization_name  — naam van de zorginstelling (standaard: "Zorginstelling")
  systems            — komma-gescheiden lijst bronsystemen (bijv. "AFAS HRM,NMBRS")
"""

from __future__ import annotations

import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import ValidationRun
from app.models.report_models import (
    AvailabilityStatus,
    BeschikbaarheidsReport,
    KikvReadinessReport,
    ManagementReport,
)
from app.services.report_builder import build_report, _field_label as _fl
from app.services.report_pdf_template import (
    RhadixRenderer as R,
    COLORS,
    STYLES,
    score_color_name,
    availability_label,
    readiness_label,
    quality_label,
    READINESS_STATUS_LABEL,
    READINESS_STATUS_COLOR,
    AVAILABILITY_STATUS_LABEL,
    AVAILABILITY_STATUS_COLOR,
    SEVERITY_COLOR,
)

router = APIRouter()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_run(run_id: int, db: Session) -> ValidationRun:
    run = db.query(ValidationRun).filter(ValidationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Scan {run_id} niet gevonden.")
    if run.status != "completed":
        raise HTTPException(status_code=422, detail="Scan is nog niet voltooid.")
    return run


def _parse_systems(systems_str: str | None) -> list[str]:
    if not systems_str:
        return []
    return [s.strip() for s in systems_str.split(",") if s.strip()]


def _require_stap2_data(run: ValidationRun) -> None:
    """
    Bewaker: KIK-V Readiness- en Managementrapporten vereisen geüploade bestanden.
    """
    results      = run.results or {}
    file_results = results.get("file_results", [])
    if not file_results:
        raise HTTPException(
            status_code=422,
            detail=(
                "Voer eerst stap 2 uit om kwaliteit en KIK-V readiness te rapporteren. "
                "Zorg dat er bestanden zijn aangeleverd bij de scan."
            ),
        )


def _streaming_pdf(pdf_bytes: bytes, filename: str) -> StreamingResponse:
    buf = io.BytesIO(pdf_bytes)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── Types endpoint ───────────────────────────────────────────────────────────

@router.get("/{run_id}/types")
def get_available_report_types(run_id: int, db: Session = Depends(get_db)) -> dict:
    run     = _get_run(run_id, db)
    results = run.results or {}
    has_data = any(fr.get("issues") for fr in results.get("file_results", []))
    return {
        "scan_id":    run_id,
        "scan_label": run.label,
        "types": [
            {
                "type":        "beschikbaarheid",
                "label":       "Beschikbaarheidsrapport",
                "description": "Databeschikbaarheid per veld/schema — na stap 1",
                "available":   True,
            },
            {
                "type":        "kikv_readiness",
                "label":       "KIK-V Readiness rapport",
                "description": "Beschikbaarheid + kwaliteit t.o.v. KIK-V uitwisselprofielen — na stap 2",
                "available":   has_data or run.error_count > 0 or run.warn_count > 0,
            },
            {
                "type":        "management",
                "label":       "Gecombineerd managementrapport",
                "description": "Rhadix Index, risico's en actieplan voor bestuur/management — na stap 2",
                "available":   has_data or run.error_count > 0 or run.warn_count > 0,
            },
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ASSEMBLER-FUNCTIES
# Elke assembler zet een Pydantic-rapportobject om naar een PDF-story.
# Alle opmaakbeslissingen staan in report_pdf_template.py.
# ═══════════════════════════════════════════════════════════════════════════════

def _assemble_beschikbaarheid(
    report: BeschikbaarheidsReport,
    run: ValidationRun,
    systems_str: str,
    now_str: str,
) -> list:
    """
    Assembler voor het Beschikbaarheidsrapport (Stap 1).
    Secties: titelbalk → infobalk → stap-badge → scoretabel →
             per-schema veldtabellen → conclusie → vervolgstappen → footer
    """
    avail     = report.availability_summary
    recs      = report.recommendations
    scan_date = run.created_at.strftime("%d %B %Y") if run.created_at else now_str
    score     = avail.availability_score

    # ── Importeer ReportLab-typen via template ──
    try:
        from reportlab.platypus import Paragraph, Spacer, KeepTogether
        from reportlab.lib.styles import ParagraphStyle
    except ImportError:
        raise HTTPException(500, "reportlab not installed")

    COLORS._init()
    STYLES._build()
    C = COLORS

    # ── Helperfunctie voor field-stijl (unieke naam per veld) ──
    def ps(uid: str, **kw) -> ParagraphStyle:
        return STYLES.ps(uid, **kw)

    # Status-label + kleur
    STATUS_LABEL = AVAILABILITY_STATUS_LABEL
    STATUS_COLOR = AVAILABILITY_STATUS_COLOR

    info_parts = [report.meta.organization_name, f"Scan: {run.label or '—'}",
                  f"Datum: {scan_date}"]
    if systems_str and systems_str != "—":
        info_parts.append(f"Bronsysteem: {systems_str}")

    story: list = []

    # 1. Header
    story += R.header_bar("Rhadix Beschikbaarheidsrapport", now_str)
    story += R.info_bar(info_parts)
    story += R.step_badge(
        "STAP 1 — Beschikbaarheid van data",
        "Dit rapport richt zich uitsluitend op de beschikbaarheid van data-elementen. "
        "Datakwaliteit en KIK-V readiness worden behandeld in stap 2.",
        color="blue",
    )

    # 2. Scoretabel
    story += R.section("Samenvatting beschikbaarheid")
    story += R.score_table(
        headers=["Beschikbaarheidsscore", "Totaal velden", "Aanwezig",
                 "Ontbreekt", "Deels beschikbaar"],
        values=[f"{score:.0f}%", str(avail.total_fields),
                str(avail.fields_present), str(avail.fields_missing),
                str(avail.fields_ambiguous)],
        value_colors=[score_color_name(score), "green",
                      "green" if avail.fields_present > 0 else "gray",
                      "red" if avail.fields_missing > 0 else "green",
                      "amber" if avail.fields_ambiguous > 0 else "green"],
    )
    story += R.space(4)
    story += R.text(availability_label(score), "small")
    if avail.required_missing > 0:
        story += R.warning_line(f"⚠  {avail.required_missing} verplichte veld(en) ontbreken.", "red")
    story += R.separator()

    # 3. Per-schema veldtabellen
    story += R.section("Overzicht per data-element")

    for schema in avail.schemas:
        uploaded_label = (
            f"{schema.row_count} rijen  ·  "
            f"{schema.recognized_columns}/{schema.total_columns} kolommen herkend"
            if schema.file_uploaded else "Bestand niet aangeleverd"
        )
        hdr_color = score_color_name(schema.availability_score) if schema.file_uploaded else "gray"
        schema_hdr_block = R.schema_header(
            label=schema.schema_label,
            sublabel=uploaded_label,
            score_str=f"{schema.availability_score:.0f}%",
            color="blue" if schema.file_uploaded else "gray",
        )

        if not schema.file_uploaded:
            story += R.keep(schema_hdr_block + [
                Spacer(1, 3),
                Paragraph(
                    "Geen bestand aangeleverd voor dit schema. "
                    "Alle velden voor dit domein zijn als 'Ontbreekt' geclassificeerd.",
                    STYLES.small,
                ),
                Spacer(1, 10),
            ])
            continue

        # Veldtabel-rijen
        field_hdrs = ["Veld", "Verplicht", "Status", "Bronkolom", "Dekking", "Toelichting"]
        field_rows = []
        row_tints  = {}

        for row_i, f in enumerate(schema.fields, start=1):
            st_label = STATUS_LABEL.get(f.status, f.status)
            verplicht = "Ja" if f.is_required else "Nee"
            bronkolom = f.mapped_column or "—"
            dekking   = f"{f.coverage_pct:.0f}%" if f.total_rows > 0 else "—"
            if f.status == AvailabilityStatus.aanwezig:
                toelichting = "Veld aanwezig en gevuld."
            elif f.status == AvailabilityStatus.ontbreekt:
                toelichting = (
                    "Kolom niet herkend in het bestand." if not f.mapped_column
                    else f"{f.empty_count} rijen leeg." if f.empty_count > 0
                    else "Waarden afwezig."
                )
            else:
                toelichting = f"{f.invalid_count} rijen met afwijkende waarden."

            row_tints[row_i] = STATUS_COLOR.get(f.status, "gray")
            field_rows.append([
                Paragraph(f.field_label, ps(f"fl{f.field_key}", fontName="Helvetica-Bold", fontSize=8)),
                verplicht,
                Paragraph(st_label, ps(f"fst{f.field_key}", fontName="Helvetica-Bold",
                                        fontSize=8)),
                Paragraph(bronkolom, ps(f"fbc{f.field_key}", fontSize=8,
                                         fontName="Helvetica" if bronkolom == "—" else "Helvetica-Oblique")),
                dekking,
                Paragraph(toelichting, ps(f"ftoe{f.field_key}", fontSize=8)),
            ])

        ftbl = R.data_table(
            headers=field_hdrs,
            rows=field_rows,
            col_widths_mm=[32, 18, 30, 30, 15, 47],
            header_bg="dark",
            stripe=True,
            row_tints=row_tints,
            tint_col=2,
        )

        story += R.keep(schema_hdr_block + [Spacer(1, 2)])
        story += ftbl
        story += R.space(14)

    story += R.separator()

    # 4. Conclusie
    story += R.section("Conclusie")
    schemas_up = avail.schemas_uploaded
    total_sc   = avail.total_schemas

    if score >= 80 and avail.required_missing == 0:
        conclusie = (
            f"De beschikbaarheidsscore van <b>{score:.0f}%</b> geeft aan dat de aangeleverde data "
            f"grotendeels volledig is. Alle verplichte velden zijn aanwezig in "
            f"{schemas_up} van de {total_sc} verwachte schema's. "
            "De dataset is geschikt voor verdere validatie in stap 2."
        )
    elif score >= 60:
        conclusie = (
            f"De beschikbaarheidsscore van <b>{score:.0f}%</b> wijst op een gedeeltelijk complete dataset. "
            f"{avail.fields_missing} velden ontbreken en {avail.fields_ambiguous} velden zijn deels beschikbaar. "
            "Herstel de ontbrekende velden vóór u doorgaat naar stap 2."
        )
        if avail.required_missing > 0:
            conclusie += f" Let op: {avail.required_missing} van de ontbrekende velden zijn verplicht."
    else:
        conclusie = (
            f"De beschikbaarheidsscore van <b>{score:.0f}%</b> geeft aan dat een groot deel van de "
            "verwachte data-elementen ontbreekt of niet herkend wordt. "
            f"{avail.fields_missing} velden ontbreken, waarvan {avail.required_missing} verplicht. "
            "Verbetering van de databeschikbaarheid is een vereiste vóór verdere analyse."
        )

    missing_labels = [s.schema_label for s in avail.schemas if not s.file_uploaded]
    if missing_labels:
        conclusie += (
            f" De volgende schema's zijn niet aangeleverd: {', '.join(missing_labels)}."
            " Voeg deze toe voor een volledig beeld."
        )
    story += R.text(conclusie, "body")
    story += R.space(10)

    # 5. Vervolgstappen
    story += R.section("Aanbevolen vervolgstappen")
    steps: list[str] = []
    if missing_labels:
        steps.append(
            f"<b>Upload ontbrekende bestanden</b> — de schema's {', '.join(missing_labels)} "
            "zijn niet aangeleverd."
        )
    if avail.required_missing > 0:
        steps.append(
            f"<b>Vul verplichte velden aan</b> — {avail.required_missing} verplichte veld(en) "
            "ontbreken. Controleer de exportconfiguratie van uw bronsysteem."
        )
    unmapped = [s for s in avail.schemas if s.file_uploaded
                and s.total_columns > 0 and s.recognized_columns < s.total_columns]
    if unmapped:
        steps.append(
            "<b>Stem kolomnamen af</b> — Rhadix herkent niet alle kolommen automatisch. "
            "Hernoem kolommen naar de bekende KIK-V aliassen."
        )
    if avail.fields_ambiguous > 0:
        steps.append(
            f"<b>Controleer deels beschikbare velden</b> — {avail.fields_ambiguous} veld(en) "
            "zijn aanwezig maar bevatten afwijkende of lege waarden."
        )
    for rec in recs[:3]:
        steps.append(f"<b>{rec.title}</b> — {rec.rationale}")
    steps.append(
        "<b>Ga verder naar stap 2</b> — na het oplossen van de beschikbaarheidsproblemen "
        "kunt u de datakwaliteit en KIK-V-conformiteit beoordelen via het Rhadix Dashboard."
    )
    story += R.bullets(steps)

    # 6. Footer
    story += R.footer_bar(
        f"Rhadix Beschikbaarheidsrapport — Stap 1  ·  "
        f"{report.meta.organization_name}  ·  Gegenereerd op {now_str}"
    )
    return story


def _assemble_kikv(
    report: KikvReadinessReport,
    run: ValidationRun,
    systems_str: str,
    now_str: str,
) -> list:
    """
    Assembler voor het KIK-V Readiness rapport (Stap 2).
    Secties: titelbalk → infobalk → stap-badge → scoretabel →
             scoreverantwoording → per-indicator → issues → aanbevelingen → footer
    """
    avail   = report.availability_summary
    qual    = report.quality_summary
    kikv    = report.kikv_readiness_summary
    issues  = report.issues
    recs    = report.recommendations
    actions = report.actions

    scan_date   = run.created_at.strftime("%d %B %Y") if run.created_at else now_str
    ready_score = kikv.readiness_score

    try:
        from reportlab.platypus import Paragraph, Spacer, KeepTogether
        from reportlab.lib.styles import ParagraphStyle
    except ImportError:
        raise HTTPException(500, "reportlab not installed")

    COLORS._init()
    STYLES._build()
    C = COLORS

    def ps(uid: str, **kw) -> ParagraphStyle:
        return STYLES.ps(uid, **kw)

    # Kwaliteitsmap voor indicator-velden
    qual_map = {
        f"{fq.schema_key}.{fq.field_key}": fq.quality_score
        for fq in qual.field_qualities
    }

    info_parts = [report.meta.organization_name, f"Scan: {run.label or '—'}",
                  f"Datum: {scan_date}", "Ruleset: KIK-V Modelgegevensset v1.0"]
    if systems_str and systems_str != "—":
        info_parts.insert(1, f"Bronsysteem: {systems_str}")

    story: list = []

    # 1. Header
    story += R.header_bar("Rhadix KIK-V Readiness rapport", now_str)
    story += R.info_bar(info_parts)
    story += R.step_badge(
        "STAP 2 — Databeschikbaarheid + Datakwaliteit t.o.v. KIK-V",
        "",
        color="teal",
    )

    # 2. Scoretabel
    story += R.section("Samenvatting")
    overall_color = score_color_name(ready_score)
    story += R.score_table(
        headers=["Beschikbaarheidsscore", "Kwaliteitsscore",
                 "KIK-V Readiness", "Indicators gereed"],
        values=[f"{avail.availability_score:.0f}%", f"{qual.quality_score:.0f}%",
                f"{ready_score:.0f}%", f"{kikv.indicators_ready}/{kikv.indicators_total}"],
        value_colors=[
            score_color_name(avail.availability_score),
            score_color_name(qual.quality_score),
            overall_color,
            "green" if kikv.indicators_ready == kikv.indicators_total else "amber",
        ],
    )
    story += R.space(4)
    story += R.status_row(f"Totaalstatus: {readiness_label(ready_score)}", overall_color)

    # 3. Scoreverantwoording
    story += R.section("Scoreverantwoording")
    story += R.text(
        "Elke score in dit rapport is herleidbaar naar concrete issues en datavelden — geen black-box. "
        "De <b>beschikbaarheidsscore</b> is het gewogen gemiddelde van de veldstatus per schema "
        "(aanwezig = 100%, deels beschikbaar = 50%, ontbreekt = 0%). "
        "De <b>kwaliteitsscore</b> per veld wordt berekend als: "
        "100 − ((fouten × 2 + waarschuwingen) / totaal rijen × 100). "
        "De <b>KIK-V readiness score</b> per indicator combineert 60% beschikbaarheid + 40% kwaliteit. "
        "Een indicator is 'gereed' bij ≥90%, 'gedeeltelijk' bij 50–89%, en 'niet gereed' bij &lt;50%.",
        "body",
    )
    story += R.separator()

    # 4. Per-indicator secties
    story += R.section("KIK-V Uitwisselindicatoren")

    for ind in kikv.indicators:
        rs         = ind.readiness_status if isinstance(ind.readiness_status, str) else ind.readiness_status.value
        rc         = READINESS_STATUS_COLOR.get(rs, "amber")
        rl         = READINESS_STATUS_LABEL.get(rs, "—")

        # Indicator-headertabel
        ind_hdr = R.keep(R.schema_header(
            label=ind.indicator_name,
            sublabel=ind.exchange_profile,
            score_str=rl,
            color=rc,
        ))

        # Veldenoverzicht
        field_hdrs = ["Vereist veld", "Status", "Kwaliteitsscore"]
        field_rows = []
        for ref in ind.required_fields:
            parts = ref.split(".", 1)
            sk, fk = (parts[0], parts[1]) if len(parts) == 2 else (ref, ref)
            is_avail   = ref in ind.available_fields
            qs         = qual_map.get(ref)
            qs_str     = f"{qs:.0f}%" if qs is not None else ("100%" if is_avail else "—")
            qs_col     = score_color_name(qs if qs is not None else 100) if is_avail else "red"
            field_lbl  = _fl(sk, fk)
            status_lbl = "✓ Aanwezig" if is_avail else "✕ Ontbreekt"
            status_col = "green" if is_avail else "red"
            field_rows.append([
                Paragraph(field_lbl, ps(f"ff{ref}", fontName="Helvetica-Bold", fontSize=8)),
                Paragraph(status_lbl, ps(f"fs{ref}", fontName="Helvetica-Bold",
                                          fontSize=8, textColor=COLORS.GREEN if is_avail else COLORS.RED)),
                Paragraph(qs_str, ps(f"fq{ref}", fontName="Helvetica-Bold",
                                      fontSize=8, textColor=COLORS.GREEN if qs_col == "green"
                                      else COLORS.AMBER if qs_col == "amber" else COLORS.RED)),
            ])

        ftbl_block = R.data_table(
            headers=field_hdrs,
            rows=field_rows,
            col_widths_mm=[70, 52, 50],
            header_bg="dark",
        )

        # Blokkerende factoren
        blocking_block: list = []
        if ind.blocking_issues:
            blocking_block = (
                [Paragraph("Blokkerende factoren:", ps(f"bh{ind.indicator_id}",
                    fontSize=8, fontName="Helvetica-Bold", textColor=COLORS.RED))]
                + R.bullets(ind.blocking_issues)
            )

        # Score-toelichting
        score_note = Paragraph(
            f"Kwaliteitsscore: <b>{ind.data_quality_score:.0f}%</b>  ·  "
            f"Beschikbaarheid: <b>{len(ind.available_fields)}/{len(ind.required_fields)} velden</b>  ·  "
            "Formule: 60% beschikbaarheid + 40% kwaliteit",
            ps(f"sn{ind.indicator_id}", fontSize=8, textColor=COLORS.GRAY,
               fontName="Helvetica-Oblique"),
        )

        # Conclusierij
        conclusie_lbl = (
            "Bruikbaar voor KIK-V-uitwisseling"      if rs == "gereed" else
            "Deels bruikbaar — herstel vereist"       if rs == "gedeeltelijk" else
            "Niet bruikbaar — ontbrekende/afwijkende data"
        )
        conc_block = R.status_row(f"Conclusie: {conclusie_lbl}", rc)

        # Samenvoegen als KeepTogether-blok
        desc_block = (
            [Paragraph(ind.description, STYLES.small), Spacer(1, 4)]
            if ind.description else []
        )
        block = (
            R.schema_header(label=ind.indicator_name, sublabel=ind.exchange_profile,
                             score_str=rl, color=rc)
            + [Spacer(1, 3)]
            + desc_block
            + ftbl_block
            + ([Spacer(1, 4)] + blocking_block if blocking_block else [])
            + [Spacer(1, 4), score_note, Spacer(1, 4)]
            + conc_block
            + [Spacer(1, 14)]
        )

        story += R.keep(block[:5])   # header + desc-begin samengehouden
        story += block[5:]

    story += R.separator()

    # 5. Issues
    error_issues   = [i for i in issues if i.severity == "error"]
    warning_issues = [i for i in issues if i.severity == "warning"]

    for group_label, group_issues, group_color_name in [
        ("Fouten",         error_issues,   "red"),
        ("Waarschuwingen", warning_issues, "amber"),
    ]:
        if not group_issues:
            continue

        story += R.section(f"Issues — {group_label} ({len(group_issues)})")

        issue_hdrs = ["Veld", "Omschrijving", "Rijen", "Voorbeeld persoon", "Aanbevolen actie"]
        issue_rows = []
        for iss in group_issues:
            actie = "Controleer en herstel de betrokken records."
            iss_id_lower = iss.issue_id.lower()
            if "einddatum" in iss_id_lower:
                actie = "Voeg einddatum toe vanuit contractdocumentatie."
            elif "contracttype" in iss_id_lower or "overeenkomsttype" in iss_id_lower:
                actie = "Map waarde naar KIK-V OvereenkomstType codelijst."
            elif "datum" in iss_id_lower or "date" in iss_id_lower:
                actie = "Corrigeer naar dd/mm/yyyy formaat."
            elif "personeelsnummer" in iss_id_lower:
                actie = "Vul verplicht veld in voor alle records."
            elif "unmapped" in iss_id_lower:
                actie = "Hernoem kolom naar herkende KIK-V alias."
            elif "duplicate" in iss_id_lower:
                actie = "Verwijder of samenvoeg dubbele records."

            example = ""
            if iss.rows:
                example = iss.rows[0].personId or f"rij {iss.rows[0].rowNumber or '?'}"
            elif iss.detail:
                example = iss.detail[:30]

            issue_rows.append([
                Paragraph(iss.field_label or iss.field or iss.schema_label,
                          ps(f"if{id(iss)}", fontSize=8, fontName="Helvetica-Bold")),
                Paragraph(iss.label, ps(f"il{id(iss)}", fontSize=8)),
                str(iss.count),
                Paragraph(example, ps(f"ip{id(iss)}", fontSize=8,
                          fontName="Helvetica-Oblique", textColor=COLORS.GRAY)),
                Paragraph(actie, ps(f"ia{id(iss)}", fontSize=8)),
            ])

        story += R.data_table(
            headers=issue_hdrs,
            rows=issue_rows,
            col_widths_mm=[30, 45, 14, 30, 53],
            header_bg="dark",
        )
        story += R.space(14)

        # Per-rij details voor fouten (max 3 issues, 5 rijen elk)
        if group_color_name == "red":
            for iss in group_issues[:3]:
                if not iss.rows:
                    continue
                story += R.warning_line(
                    f"Detailrijen — {iss.label} ({iss.schema_label})", "red"
                )
                row_hdrs = ["Rij", "Persoon/ID", "Veld",
                            "Huidige waarde", "Verwachte waarde", "Toelichting"]
                row_rows = []
                for rv in iss.rows[:5]:
                    row_rows.append([
                        str(rv.rowNumber or ""),
                        str(rv.personId or ""),
                        str(rv.field or ""),
                        Paragraph(str(rv.currentValue or "leeg"),
                                  ps(f"rv{id(rv)}", fontSize=7,
                                     textColor=COLORS.RED if not rv.currentValue else COLORS.TEXT)),
                        Paragraph(str(rv.expectedValue or ""),
                                  ps(f"re{id(rv)}", fontSize=7, textColor=COLORS.GRAY)),
                        Paragraph(str(rv.message or ""), ps(f"rm{id(rv)}", fontSize=7)),
                    ])
                story += R.data_table(
                    headers=row_hdrs,
                    rows=row_rows,
                    col_widths_mm=[12, 22, 22, 28, 34, 54],
                    header_bg="dark",
                )
                if len(iss.rows) > 5:
                    story += R.text(
                        f"… en {len(iss.rows) - 5} meer rijen. Bekijk het volledige overzicht in Rhadix.",
                        "small",
                    )
                story += R.space(8)

    story += R.separator()

    # 6. Aanbevelingen + acties
    if recs or actions:
        story += R.section("Aanbevelingen")
        story += R.bullets([
            f"<b>{rec.title}</b> [{rec.impact.upper()}] — {rec.rationale}"
            for rec in recs[:4]
        ])
        if actions:
            story += R.section("Prioritaire acties", heading_level=3)
            story += R.bullets([
                f"<b>[{act.priority.capitalize()}] {act.title}</b> — {act.description[:120]}"
                for act in actions[:4]
            ])
        story += R.space(14)

    # 7. Footer
    story += R.footer_bar(
        f"Rhadix KIK-V Readiness rapport — Stap 2  ·  {report.meta.organization_name}"
        f"  ·  Ruleset: KIK-V Modelgegevensset v1.0  ·  Gegenereerd op {now_str}"
    )
    return story


def _assemble_management(
    report: ManagementReport,
    run: ValidationRun,
    systems_str: str,
    now_str: str,
) -> list:
    """
    Assembler voor het Gecombineerd Managementrapport (Stap 1 + 2).
    Secties: titelbalk → sub-badge → metatabel → Rhadix Index KPI →
             executive summary → databeschikbaarheid → datakwaliteit →
             KIK-V readiness → risico's → actieplan → advies → footer
    """
    avail   = report.availability_summary
    qual    = report.quality_summary
    kikv    = report.kikv_readiness_summary
    meta    = report.meta
    rhadix  = report.rhadix_index
    issues  = report.issues
    actions = report.actions
    recs    = report.recommendations

    avail_score = round(avail.availability_score, 0)
    qual_score  = round(qual.quality_score, 0)
    ready_score = round(kikv.readiness_score, 0)
    scan_date   = (
        meta.scan_date.strftime("%-d %B %Y") if meta.scan_date else now_str
    )

    try:
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle
    except ImportError:
        raise HTTPException(500, "reportlab not installed")

    COLORS._init()
    STYLES._build()

    def ps(uid: str, **kw) -> ParagraphStyle:
        return STYLES.ps(uid, **kw)

    story: list = []

    # 1. Header
    story += R.header_bar("Rhadix Managementrapport", now_str)
    story += R.subtitle_badge("GECOMBINEERD MANAGEMENTRAPPORT  ·  STAP 1 + 2")
    story += R.meta_table(
        organization=report.meta.organization_name,
        systems_str=systems_str or "—",
        scan_date=scan_date,
        generated_date=now_str,
    )

    # 2. Rhadix Index + KPI-hero
    story += R.section("1. Management Samenvatting")
    story += R.kpi_hero(
        main_value=str(rhadix),
        main_label="Rhadix Index",
        main_sublabel=quality_label(rhadix),
        main_color=score_color_name(rhadix),
        kpis=[
            {"value": f"{avail_score:.0f}", "label": "Beschikbaarheid",
             "sub": "Stap 1", "color": score_color_name(avail_score)},
            {"value": f"{qual_score:.0f}", "label": "Kwaliteit",
             "sub": "Stap 2", "color": score_color_name(qual_score)},
            {"value": f"{ready_score:.0f}", "label": "KIK-V Readiness",
             "sub": f"{kikv.indicators_ready}/{kikv.indicators_total} gereed",
             "color": score_color_name(ready_score)},
        ],
    )

    # Executive summary
    if report.executive_summary:
        story += R.text(report.executive_summary, "body")
    story += R.separator()

    # 3. Databeschikbaarheid
    story += R.section("2. Analyse Databeschikbaarheid")
    schema_hdrs  = ["Schema", "Aangeleverd", "Rijen", "Score", "Ontbrekend verplicht"]
    schema_rows  = []
    schema_tints = {}
    for i, s in enumerate(avail.schemas, 1):
        cn = score_color_name(s.availability_score) if s.file_uploaded else "gray"
        schema_tints[i] = cn
        schema_rows.append([
            Paragraph(s.schema_label, STYLES.tbl_cell),
            Paragraph("✓ Ja" if s.file_uploaded else "✕ Nee",
                      ps(f"sup{s.schema_key}", fontSize=8, fontName="Helvetica-Bold",
                         textColor=COLORS.GREEN if s.file_uploaded else COLORS.RED)),
            str(s.row_count) if s.file_uploaded else "—",
            Paragraph(f"{s.availability_score:.0f}%",
                      ps(f"ssc{s.schema_key}", fontSize=8, fontName="Helvetica-Bold")),
            str(s.missing_required_count),
        ])
    story += R.data_table(
        headers=schema_hdrs, rows=schema_rows,
        col_widths_mm=[40, 28, 22, 22, 60],
        header_bg="blue", row_tints=schema_tints, tint_col=3,
    )

    # Ontbrekende verplichte velden
    missing_fields = [
        f"{s.schema_label} → {f.field_label}"
        for s in avail.schemas
        for f in s.fields
        if f.is_required and f.status == "ontbreekt"
    ]
    if missing_fields:
        story += R.space(6)
        story += R.section("Ontbrekende verplichte velden", heading_level=3)
        story += R.bullets([f"<b>{mf}</b>" for mf in missing_fields[:8]])
    story += R.separator()

    # 4. Datakwaliteit
    story += R.section("3. Datakwaliteit")
    story += R.score_table(
        headers=["Kwaliteitsscore", "Totaal fouten", "Totaal waarschuwingen",
                 "Velden met issues"],
        values=[f"{qual_score:.0f}%", str(qual.total_errors),
                str(qual.total_warnings), str(len(qual.field_qualities))],
        value_colors=[score_color_name(qual_score),
                      "red" if qual.total_errors > 0 else "green",
                      "amber" if qual.total_warnings > 0 else "green",
                      "amber" if qual.field_qualities else "green"],
    )
    if issues:
        story += R.space(8)
        story += R.section("Kritische issues", heading_level=3)
        issue_hdrs = ["Veld", "Omschrijving", "Aantal rijen", "Schema"]
        issue_rows = [
            [
                Paragraph(iss.field_label or iss.field or "—",
                          ps(f"if2{id(iss)}", fontSize=8, fontName="Helvetica-Bold",
                             textColor=COLORS.RED)),
                Paragraph(iss.label, ps(f"il2{id(iss)}", fontSize=8)),
                str(iss.count),
                iss.schema_label,
            ]
            for iss in issues[:8]
        ]
        story += R.data_table(
            headers=issue_hdrs, rows=issue_rows,
            col_widths_mm=[40, 70, 20, 42], header_bg="blue",
        )
    story += R.separator()

    # 5. KIK-V Readiness
    story += R.section("4. KIK-V Readiness")
    ind_hdrs = ["Indicator", "Uitwisselprofiel", "Status",
                "Beschikbaar", "Kwaliteit"]
    ind_rows  = []
    ind_tints = {}
    for i, ind in enumerate(kikv.indicators, 1):
        rs = ind.readiness_status if isinstance(ind.readiness_status, str) \
             else ind.readiness_status.value
        rc = READINESS_STATUS_COLOR.get(rs, "amber")
        rl = READINESS_STATUS_LABEL.get(rs, "—")
        n_req   = len(ind.required_fields)
        n_avail = len(ind.available_fields)
        ind_tints[i] = rc
        ind_rows.append([
            Paragraph(ind.indicator_name,
                      ps(f"in{i}", fontSize=8, fontName="Helvetica-Bold")),
            Paragraph(ind.exchange_profile, ps(f"ep{i}", fontSize=8)),
            Paragraph(rl, ps(f"rs{i}", fontSize=8, fontName="Helvetica-Bold")),
            f"{n_avail}/{n_req}",
            f"{ind.data_quality_score:.0f}%",
        ])
    story += R.data_table(
        headers=ind_hdrs, rows=ind_rows,
        col_widths_mm=[44, 60, 32, 18, 18],
        header_bg="blue", row_tints=ind_tints, tint_col=2,
    )
    story += R.separator()

    # 6. Risico's
    story += R.section("5. Risico-analyse")
    risks: list[str] = []
    not_ready_names = [
        ind.indicator_name for ind in kikv.indicators
        if (ind.readiness_status if isinstance(ind.readiness_status, str)
            else ind.readiness_status.value) == "niet_gereed"
    ]
    not_uploaded = [s.schema_label for s in avail.schemas if not s.file_uploaded]
    if not_uploaded:
        risks.append(
            f"<b>[HOOG] Ontbrekende schema's</b> — {', '.join(not_uploaded)} zijn niet aangeleverd. "
            "KIK-V-uitwisseling is onmogelijk zonder volledige dataset."
        )
    if avail.required_missing > 0:
        risks.append(
            f"<b>[HOOG] Verplichte velden ontbreken</b> — {avail.required_missing} verplichte "
            "KIK-V-velden zijn niet beschikbaar. Dit blokkeert uitwisseling."
        )
    if not_ready_names:
        risks.append(
            f"<b>[HOOG] Indicatoren niet gereed</b> — "
            f"{', '.join(not_ready_names)} voldoen niet aan KIK-V-standaard."
        )
    if qual_score < 70:
        risks.append(
            f"<b>[GEMIDDELD] Datakwaliteit laag</b> — kwaliteitsscore {qual_score:.0f}% "
            "ligt onder de aanbevolen drempel van 70%. Correcties nodig."
        )
    total_hours = sum(a.estimated_hours for a in actions)
    if total_hours > 10:
        risks.append(
            f"<b>[GEMIDDELD] Implementatieplanning</b> — herstelacties vergen "
            f"geschat {total_hours:.0f} uur. Plan dit in de projectplanning."
        )
    if not risks:
        risks.append(
            "<b>[LAAG] Geen kritische risico's</b> — de data is grotendeels conform "
            "KIK-V-standaard. Kleine verbeteringen zijn aanbevolen."
        )
    story += R.bullets(risks)
    story += R.separator()

    # 7. Actieplan
    story += R.section("6. Actieplan")
    if actions:
        story += R.action_table(actions)
    else:
        story += R.text("Geen acties vereist — data is conform KIK-V-standaard.", "body")
    story += R.separator()

    # 8. Advies
    story += R.section("7. Strategisch Advies")
    priority_recs  = [rec for rec in recs if rec.impact == "hoog"]
    later_recs     = [rec for rec in recs if rec.impact != "hoog"]

    if priority_recs:
        story += R.section("Direct aanpakken", heading_level=3)
        story += R.bullets([
            f"<b>{rec.title}</b> — {rec.rationale}" for rec in priority_recs[:4]
        ])
    if later_recs:
        story += R.section("Kan later worden opgepakt", heading_level=3)
        story += R.bullets([
            f"<b>{rec.title}</b> — {rec.rationale}" for rec in later_recs[:3]
        ])

    # Vervolgstap
    story += R.space(6)
    story += R.section("Vervolgstap", heading_level=3)
    story += R.text(
        "Herstel de geïdentificeerde knelpunten en voer opnieuw een scan uit. "
        "De Rhadix Index zal stijgen naarmate databeschikbaarheid en -kwaliteit verbeteren. "
        "Doel voor KIK-V-uitwisseling: Rhadix Index ≥ 80, alle uitwisselindicatoren 'Gereed'.",
        "body",
    )

    # 9. Footer
    story += R.footer_bar(
        f"Rhadix Gecombineerd Managementrapport  ·  {report.meta.organization_name}"
        f"  ·  Gegenereerd op {now_str}"
    )
    return story


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — JSON
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{run_id}/beschikbaarheid", response_model=BeschikbaarheidsReport)
def get_beschikbaarheidsrapport(
    run_id:            int,
    organization_name: str = Query(default="Zorginstelling"),
    systems:           str | None = Query(default=None),
    db:                Session = Depends(get_db),
) -> BeschikbaarheidsReport:
    run = _get_run(run_id, db)
    return build_report(run, "beschikbaarheid", organization_name, _parse_systems(systems))


@router.get("/{run_id}/kikv_readiness", response_model=KikvReadinessReport)
def get_kikv_readiness_rapport(
    run_id:            int,
    organization_name: str = Query(default="Zorginstelling"),
    systems:           str | None = Query(default=None),
    db:                Session = Depends(get_db),
) -> KikvReadinessReport:
    run = _get_run(run_id, db)
    _require_stap2_data(run)
    return build_report(run, "kikv_readiness", organization_name, _parse_systems(systems))


@router.get("/{run_id}/management", response_model=ManagementReport)
def get_management_rapport(
    run_id:            int,
    organization_name: str = Query(default="Zorginstelling"),
    systems:           str | None = Query(default=None),
    db:                Session = Depends(get_db),
) -> ManagementReport:
    run = _get_run(run_id, db)
    _require_stap2_data(run)
    return build_report(run, "management", organization_name, _parse_systems(systems))


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — PDF
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{run_id}/beschikbaarheid/pdf")
def export_beschikbaarheidsrapport_pdf(
    run_id:            int,
    organization_name: str = Query(default="Zorginstelling"),
    systems:           str | None = Query(default=None),
    db:                Session = Depends(get_db),
):
    """
    Rhadix Beschikbaarheidsrapport als PDF (Stap 1).
    Bevat: scoretabel, per-veld tabel per schema, conclusie en vervolgstappen.
    """
    run = _get_run(run_id, db)
    if not _RL_AVAILABLE():
        raise HTTPException(500, "reportlab niet geïnstalleerd")

    report: BeschikbaarheidsReport = build_report(
        run, "beschikbaarheid", organization_name, _parse_systems(systems)
    )
    now_str     = datetime.now().strftime("%d-%m-%Y")
    systems_str = ", ".join(_parse_systems(systems)) or "—"
    story       = _assemble_beschikbaarheid(report, run, systems_str, now_str)
    pdf_bytes   = R.build_pdf(story, title=f"Rhadix Beschikbaarheidsrapport — {organization_name}")
    filename    = f"Rhadix_Beschikbaarheidsrapport_{run.id}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return _streaming_pdf(pdf_bytes, filename)


@router.get("/{run_id}/kikv_readiness/pdf")
def export_kikv_readiness_pdf(
    run_id:            int,
    organization_name: str = Query(default="Zorginstelling"),
    systems:           str | None = Query(default=None),
    db:                Session = Depends(get_db),
):
    """
    Rhadix KIK-V Readiness rapport als PDF (Stap 2).
    Bevat transparante scoreverantwoording: elke score is herleidbaar.
    """
    run = _get_run(run_id, db)
    _require_stap2_data(run)
    if not _RL_AVAILABLE():
        raise HTTPException(500, "reportlab niet geïnstalleerd")

    report: KikvReadinessReport = build_report(
        run, "kikv_readiness", organization_name, _parse_systems(systems)
    )
    now_str     = datetime.now().strftime("%d-%m-%Y")
    systems_str = ", ".join(_parse_systems(systems)) or "—"
    story       = _assemble_kikv(report, run, systems_str, now_str)
    pdf_bytes   = R.build_pdf(story, title=f"Rhadix KIK-V Readiness rapport — {organization_name}")
    filename    = f"Rhadix_KIKVReadiness_{run.id}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return _streaming_pdf(pdf_bytes, filename)


@router.get("/{run_id}/management/pdf")
def export_management_pdf(
    run_id:            int,
    organization_name: str = Query(default="Zorginstelling"),
    systems:           str | None = Query(default=None),
    db:                Session = Depends(get_db),
):
    """
    Rhadix Gecombineerd Managementrapport als PDF (Stap 1 + 2).
    Geschikt voor bestuur, management en projectleiding.
    """
    run = _get_run(run_id, db)
    _require_stap2_data(run)
    if not _RL_AVAILABLE():
        raise HTTPException(500, "reportlab niet geïnstalleerd")

    report: ManagementReport = build_report(
        run, "management", organization_name, _parse_systems(systems)
    )
    now_str     = datetime.now().strftime("%d %B %Y").lstrip("0")
    systems_str = ", ".join(_parse_systems(systems)) or "—"
    story       = _assemble_management(report, run, systems_str, now_str)
    pdf_bytes   = R.build_pdf(story, title=f"Rhadix Managementrapport — {organization_name}")
    filename    = f"Rhadix_Managementrapport_{run.id}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return _streaming_pdf(pdf_bytes, filename)


# ── Hulpfunctie voor ReportLab check ──────────────────────────────────────────

def _RL_AVAILABLE() -> bool:
    try:
        import reportlab  # noqa: F401
        return True
    except ImportError:
        return False
