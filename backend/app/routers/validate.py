import io
import csv
import json
import xml.etree.ElementTree as ET
import re
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.models import ValidationRun
from app.services.validator import validate_files, detect_schema, auto_map, KIKV_REFERENCE
from app.services.concept_validator import validate_concept_mapping
from app.services.zib_validator import validate_zib
from app.services.zib_rules import detect_zib_schema
from app.services.actuality_validator import validate_actuality, detect_date_fields, get_kikv_norm_for_schema
from app.services.traceability import enrich_file_result, collect_all_issues
from app.services.owl_validator import validate_structural, validate_relational
from app.services.sparql_validator import validate_use_cases

router = APIRouter()

MAX_ROWS = 2000  # cap per bestand om timeouts te voorkomen


def parse_csv_bytes(content: bytes, filename: str, max_rows: int = MAX_ROWS) -> tuple[list, list]:
    text = content.decode("utf-8-sig", errors="replace")
    first_line = text.split("\n")[0]
    delim = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    headers = reader.fieldnames or []
    rows = []
    for row in reader:
        clean = {k.strip('"').strip(): v.strip('"').strip() for k, v in row.items() if k}
        if any(v for v in clean.values()):
            rows.append(clean)
        if len(rows) >= max_rows:
            break
    return list(headers), rows


def _normalize_xml_value(val: str) -> str:
    """Strip tijdzone/tijd van datetime-strings en normaliseer YYYYMMDD naar dd-mm-yyyy."""
    if not val:
        return val
    # ISO datetime: 2026-04-19T00:00:00 → 2026-04-19
    val = re.sub(r'T\d{2}:\d{2}:\d{2}.*$', '', val.strip())
    # YYYYMMDD zonder streepjes → yyyy-mm-dd zodat datumparser het herkent
    if re.fullmatch(r'\d{8}', val):
        val = f"{val[:4]}-{val[4:6]}-{val[6:]}"
    return val


def parse_xml_bytes(content: bytes, max_rows: int = MAX_ROWS) -> tuple[list, list]:
    """Parseer AFAS Profit XML-exports (Profit_Employees, Profit_Timetable, Profit_Illness)."""
    try:
        root = ET.fromstring(content.decode("utf-8", errors="replace"))
    except ET.ParseError as e:
        raise ValueError(f"Ongeldig XML-bestand: {e}")

    headers_ordered: list[str] = []
    headers_seen: set[str] = set()
    rows: list[dict] = []

    for record in root:
        row: dict[str, str] = {}
        for field in record:
            tag = field.tag
            val = _normalize_xml_value(field.text or "")
            row[tag] = val
            if tag not in headers_seen:
                headers_seen.add(tag)
                headers_ordered.append(tag)
        if any(v for v in row.values()):
            rows.append(row)
        if len(rows) >= max_rows:
            break

    return headers_ordered, rows


def parse_upload(content: bytes, filename: str, ext: str) -> tuple[list, list]:
    if ext == "csv":
        return parse_csv_bytes(content, filename)
    if ext == "xml":
        return parse_xml_bytes(content)
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        ws = wb.active
        all_rows = list(ws.iter_rows(values_only=True))
        headers = [str(c or "") for c in all_rows[0]] if all_rows else []
        rows = [
            {headers[i]: str(cell or "") for i, cell in enumerate(row)}
            for row in all_rows[1:]
            if any(cell for cell in row)
        ]
        return headers, rows
    except Exception as e:
        raise HTTPException(400, f"Could not parse Excel file: {e}")


@router.post("/upload")
async def upload_and_validate(
    files: List[UploadFile] = File(...),
    label: Optional[str] = Form(None),
    standard: Optional[str] = Form("kikv"),   # "kikv" | "zib"
    max_age_days: Optional[int] = Form(30),   # drempel voor actualiteitscheck
    db: Session = Depends(get_db),
):
    """
    Upload bestanden en valideer tegen KIK-V (standard='kikv') of ZIB's (standard='zib').
    Voegt altijd 'actuality' toe aan de response.
    """
    standard = (standard or "kikv").lower().strip()

    parsed = []
    for upload in files:
        content = await upload.read()
        ext = upload.filename.split(".")[-1].lower()
        if ext not in ("csv", "xlsx", "xls", "xml"):
            raise HTTPException(400, f"Unsupported file type: {ext}")
        headers, rows = parse_upload(content, upload.filename, ext)
        rows = rows[:MAX_ROWS]   # cap
        parsed.append({"filename": upload.filename, "headers": headers, "rows": rows})

    # ── Actualiteit (altijd, voor alle bestanden) ─────────────────────────────
    actuality_results = []
    for p in parsed:
        fields = detect_date_fields(p["headers"])
        sk = detect_schema(p["filename"], p["headers"])
        ar = validate_actuality(p["rows"], field_map=fields, max_age_days=max_age_days or 30)
        ar["filename"]   = p["filename"]
        ar["schema_key"] = sk
        # KIK-V actualiteitsnorm op basis van gedetecteerd schema
        ar["kikv_norm"]  = get_kikv_norm_for_schema(sk) if sk else None
        # Voeg source_file toe aan elk individueel issue-item
        for issue_list in ("outdated", "inconsistent"):
            for item in ar.get(issue_list, []):
                item["source_file"] = p["filename"]
        actuality_results.append(ar)

    # ── ZIB-pad ───────────────────────────────────────────────────────────────
    if standard == "zib":
        zib_input = [{"filename": p["filename"], "rows": p["rows"]} for p in parsed]
        result = validate_zib(zib_input)

        files_summary = [
            {
                "filename":   p["filename"],
                "schema_key": detect_zib_schema(p["filename"]) or "onbekend",
                "rows":       len(p["rows"]),
            }
            for p in parsed
        ]
        run_id = None
        created_at = None
        try:
            run = ValidationRun(
                label=label or f"ZIB-scan {len(parsed)} bestand{'en' if len(parsed) > 1 else ''}",
                files=files_summary,
                results=result,
                total_rows=sum(len(p["rows"]) for p in parsed),
                error_count=sum(
                    len([i for i in fr.get("issues", []) if i.get("severity") == "error"])
                    for fr in result["file_results"]
                ),
                warn_count=sum(
                    len([i for i in fr.get("issues", []) if i.get("severity") == "warning"])
                    for fr in result["file_results"]
                ),
                score=result["score"],
                status="completed",
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            run_id = run.id
            created_at = run.created_at.isoformat()
        except Exception as db_err:
            print(f"[WARN] DB save failed (result still returned): {db_err}")
            try:
                db.rollback()
            except Exception:
                pass

        # Verrijk ZIB issues met traceervelden
        for fr in result.get("file_results", []):
            fname  = fr.get("filename", "")
            sk     = fr.get("schema_key") or "onbekend"
            layer  = "zib_availability"
            prescan_layer = "prescan"
            for issue in fr.get("issues", []):
                if issue.get("prescan"):
                    enrich_file_result({"issues": [issue]}, layer=prescan_layer, source_file=fname, schema_key=sk)
                else:
                    enrich_file_result({"issues": [issue]}, layer="zib_quality", source_file=fname, schema_key=sk)

        all_issues = collect_all_issues(zib_result=result, actuality_results=actuality_results)

        return {
            **result,
            "run_id":      run_id,
            "created_at":  created_at,
            "concept_mapping": [],
            "actuality":   actuality_results,
            "all_issues":  all_issues,
        }

    # ── KIK-V-pad ─────────────────────────────────────────────────────────────
    files_input = []
    for p in parsed:
        sk = detect_schema(p["filename"], p["headers"])
        files_input.append({
            "filename":   p["filename"],
            "schema_key": sk,
            "headers":    p["headers"],
            "rows":       p["rows"],
        })

    result = validate_files(files_input)

    run_id = None
    created_at = None
    try:
        run = ValidationRun(
            label=label or f"Validatie {len(files)} bestand{'en' if len(files) > 1 else ''}",
            files=result["files_summary"],
            results=result,
            total_rows=result["total_rows"],
            error_count=result["total_errors"],
            warn_count=result["total_warns"],
            score=result["score"],
            status="completed",
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id
        created_at = run.created_at.isoformat()
    except Exception as db_err:
        print(f"[WARN] DB save failed (result still returned): {db_err}")
        try:
            db.rollback()
        except Exception:
            pass

    # Stap 2: concept-mapping
    concept_results = []
    for f in files_input:
        sk = f["schema_key"]
        if not sk:
            continue
        aliases = KIKV_REFERENCE.get(sk, {}).get("col_aliases", {})
        fmap    = auto_map(f["headers"], aliases)
        cr      = validate_concept_mapping(sk, f["rows"], fmap)
        # Transformeer naar het formaat dat de frontend verwacht
        summary = cr.get("summary", {})
        schema_label = KIKV_REFERENCE.get(sk, {}).get("label", sk.capitalize())
        total    = summary.get("total_fields", 0)
        matched  = summary.get("mapped_fields", 0)
        # Groepeer velden per ontologie-domein (module)
        domains_map: dict = {}
        for field, fdata in cr.get("fields", {}).items():
            uri = fdata.get("concept_uri", "")
            # Extraheer module uit URI (bijv. onz-pers, onz-g)
            module = uri.split("#")[0].split("/")[-1] if "#" in uri else "onbekend"
            if module not in domains_map:
                domains_map[module] = {"name": module, "fields": [], "all_mapped": True}
            domains_map[module]["fields"].append(field)
            if fdata.get("unmapped_rows", 0) > 0:
                domains_map[module]["all_mapped"] = False
        domains = [
            {"name": d["name"], "status": "volledig" if d["all_mapped"] else "gedeeltelijk"}
            for d in domains_map.values()
        ]
        # Skip schemas without ontologie-mapping (bijv. vestiging/client zonder FIELD_RULES)
        if total == 0:
            continue
        concept_results.append({
            # "schema" en "summary" zijn de veldnamen die ConceptMappingRapport.jsx verwacht
            "schema":       sk,
            "schema_key":   sk,          # bewaard voor achterwaartse compatibiliteit
            "schema_label": schema_label,
            "fields":       cr.get("fields", {}),
            "domains":      domains,
            "summary": {
                "mapping_score": summary.get("mapping_score", 100.0),
                "total_fields":  total,    # was: total_concepts
                "mapped_fields": matched,  # was: matched_concepts
            },
            # Vlak niveau bewaard voor Dashboard.jsx (gebruikt optional chaining)
            "mapping_score":    summary.get("mapping_score", 100.0),
            "total_concepts":   total,
            "matched_concepts": matched,
        })

    # ── OWL structural + relational + SPARQL use-case scores ────────────────
    owl_files_data = [
        {
            "filename":   f["filename"],
            "schema_key": f.get("schema_key") or f.get("schema", ""),
            "rows":       f.get("rows", []),
            "mapping":    auto_map(f["headers"], KIKV_REFERENCE.get(f.get("schema_key") or f.get("schema", ""), {}).get("col_aliases", {})),
        }
        for f in files_input
    ]
    structural_result  = validate_structural(owl_files_data)
    relational_result  = validate_relational(owl_files_data)
    use_case_result    = validate_use_cases(owl_files_data)

    # Verrijk KIK-V issues met traceervelden
    for fsum in result.get("files_summary", []):
        fname = fsum.get("filename", "")
        sk    = fsum.get("schema_key") or ""
        for issue in fsum.get("issues", []):
            layer = "prescan" if issue.get("prescan") else "quality"
            enrich_file_result({"issues": [issue]}, layer=layer, source_file=fname, schema_key=sk)

    all_issues = collect_all_issues(kikv_result=result, actuality_results=actuality_results)

    return {
        **result,
        "run_id":          run_id,
        "created_at":      created_at,
        "concept_mapping": concept_results,
        "actuality":       actuality_results,
        "all_issues":      all_issues,
        # ── Nieuwe scores (Part 1 + 2 + 3 — los van Rhadix Index) ──────────
        "structural_score":    structural_result.get("structural_score"),
        "structural_issues":   structural_result.get("structural_issues", []),
        "structural_checks":   {
            "total":  structural_result.get("checks_total"),
            "passed": structural_result.get("checks_passed"),
            "coverage": structural_result.get("rule_coverage", []),
        },
        "relational_score":    relational_result.get("relational_score"),
        "relational_issues":   relational_result.get("relational_issues", []),
        "relational_fk":       relational_result.get("fk_results", []),
        "use_case_score":      use_case_result.get("use_case_score"),
        "indicator_results":   use_case_result.get("indicator_results", []),
        "rdf_graph_triples":   use_case_result.get("graph_triples", 0),
    }
