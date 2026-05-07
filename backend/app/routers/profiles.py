"""
routers/profiles.py
-------------------
API endpoints for KIK-V profile import and management.

Routes:
  POST /api/profiles/import-gitlab   — trigger GitLab import, save, return summary
  GET  /api/profiles/                — list all saved profiles
  GET  /api/profiles/{filename}      — load full profile (with indicators)
  DELETE /api/profiles/{filename}    — delete a saved profile
"""
from __future__ import annotations

import os
import pathlib
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.gitlab_importer import (
    import_profile,
    save_profile,
    list_profiles,
    load_profile,
    reparse_profile,
    DEFAULT_REPO,
    DEFAULT_REF,
    DEFAULT_FOLDER,
)

router = APIRouter(prefix="/api/profiles", tags=["profiles"])

_PROFILES_DIR = pathlib.Path(__file__).parent.parent.parent / "data" / "profiles"


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class ImportRequest(BaseModel):
    repo:   str = DEFAULT_REPO
    ref:    str = DEFAULT_REF
    folder: str = DEFAULT_FOLDER
    token:  Optional[str] = None
    name:   Optional[str] = None


class ProfileSummary(BaseModel):
    name:              Optional[str]
    version:           Optional[str]
    source:            Optional[str]
    ref:               Optional[str]
    folder:            Optional[str]
    imported_at:       Optional[str]
    indicator_count:   int
    file_count:        int
    parse_error_count: int
    filename:          str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/import-gitlab", summary="Import KIK-V profile from GitLab")
async def import_from_gitlab(body: ImportRequest):
    """
    Fetches files from GitLab, parses them, and stores the profile locally.

    - `repo`   — GitLab project path (default: kik-v/...)
    - `ref`    — branch or tag (default: 1.3.4)
    - `folder` — subfolder in repo (default: Gevalideerde_vragen_technisch)
    - `token`  — optional GitLab personal access token (public repo → not needed)
    - `name`   — optional profile name override
    """
    try:
        profile = import_profile(
            repo=body.repo,
            ref=body.ref,
            folder=body.folder,
            token=body.token or None,
            profile_name=body.name,
        )
        out_path = save_profile(profile, name=body.name or profile.get("name"))
        return {
            "status": "ok",
            "filename": out_path.name,
            "name":            profile["name"],
            "version":         profile["version"],
            "indicator_count": profile["indicator_count"],
            "file_count":      profile["file_count"],
            "parse_errors":    profile["parse_errors"],
            "imported_at":     profile["imported_at"],
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/", summary="List all saved profiles")
async def get_profiles():
    """Return a list of all locally stored KIK-V profiles (summary only)."""
    return list_profiles()


@router.get("/{filename}", summary="Load a full profile")
async def get_profile(filename: str):
    """
    Return the full profile JSON including all indicators and parsed content.

    Use `indicators_only=true` to skip raw file content.
    """
    try:
        data = load_profile(filename)
        return data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{filename}' not found")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{filename}/reparse", summary="Re-parse a saved profile with updated parser")
async def reparse_saved_profile(filename: str):
    """Re-run indicator_parser on all raw content already stored in a profile.

    Updates metadata (titles, descriptions, concepts) without re-fetching from GitLab.
    Call this after a parser update to refresh titles and descriptions.
    """
    try:
        profile = reparse_profile(filename)
        return {
            "status":          "ok",
            "filename":        filename,
            "indicator_count": profile.get("indicator_count", 0),
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{filename}' not found")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{filename}", summary="Delete a saved profile")
async def delete_profile(filename: str):
    """Remove a profile from local storage."""
    path = _PROFILES_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{filename}' not found")
    if not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json profile files can be deleted")
    try:
        path.unlink()
        return {"status": "deleted", "filename": filename}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Readiness matrix endpoint ────────────────────────────────────────────────

from app.services.readiness_analyzer import analyze_readiness


@router.post("/{filename}/readiness", summary="Compute readiness matrix for a profile")
async def compute_readiness(filename: str, scan_result: dict):
    """
    Compare an imported KIK-V profile against the current scan result.

    Body: the full JSON returned by POST /api/validate (KIK-V path).

    Returns the readiness matrix:
    - per-indicator classification (fully / partially / blocked)
    - profile_readiness_score
    - top-10 blocking fields and relationships
    - heatmap (indicators × source domains)
    """
    try:
        profile = load_profile(filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{filename}' not found")

    try:
        matrix = analyze_readiness(profile, scan_result)
        return matrix
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/readiness-preview", summary="Readiness matrix without a saved profile")
async def readiness_preview(body: dict):
    """
    Quick readiness analysis using an inline profile + scan result.

    Body: { "profile": {...}, "scan_result": {...} }
    """
    profile     = body.get("profile", {})
    scan_result = body.get("scan_result", {})
    if not profile or not scan_result:
        raise HTTPException(status_code=422, detail="Both 'profile' and 'scan_result' are required")
    try:
        return analyze_readiness(profile, scan_result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
