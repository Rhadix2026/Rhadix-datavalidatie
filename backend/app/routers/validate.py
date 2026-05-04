import io
import csv
import json
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import ValidationRun
from app.services.validator import validate_files, detect_schema, auto_map, KIKV_REFERENCE

router = APIRouter()

def parse_csv_bytes(content: bytes, filename: str) -> tuple[list, list]:
    text = content.decode("utf-8-sig", errors="replace")
    first_line = text.split("\n")[0]
    delim = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    headers = reader.fieldnames or []
    rows = [{k.strip('"').strip(): v.strip('"').strip() for k, v in row.items()} for row in reader]
    rows = [r for r in rows if any(v for v in r.values())]
    return list(headers), rows

@router.post("/upload")
async def upload_and_validate(
    files: List[UploadFile] = File(...),
    label: str = None,
    db: Session = Depends(get_db)
):
    files_input = []
    for upload in files:
        content = await upload.read()
        ext = upload.filename.split(".")[-1].lower()
        if ext not in ("csv", "xlsx", "xls"):
            raise HTTPException(400, f"Unsupported file type: {ext}")
        if ext == "csv":
            headers, rows = parse_csv_bytes(content, upload.filename)
        else:
            try:
                import openpyxl
                wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
                ws = wb.active
                all_rows = list(ws.iter_rows(values_only=True))
                headers = [str(c or "") for c in all_rows[0]] if all_rows else []
                rows = [{headers[i]: str(cell or "") for i, cell in enumerate(row)} for row in all_rows[1:] if any(cell for cell in row)]
            except Exception as e:
                raise HTTPException(400, f"Could not parse Excel file: {e}")

        sk = detect_schema(upload.filename, headers)
        files_input.append({"filename": upload.filename, "schema_key": sk, "headers": headers, "rows": rows})

    result = validate_files(files_input)

    run = ValidationRun(
        label=label or f"Validatie {len(files)} bestand{'en' if len(files)>1 else ''}",
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

    return {**result, "run_id": run.id, "created_at": run.created_at.isoformat()}
