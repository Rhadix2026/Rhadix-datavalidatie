"""
gitlab_importer.py
------------------
Fetches KIK-V indicator files from GitLab and builds a local Rhadix profile JSON.

Design goals:
  - Runs on the user's machine (GitLab is accessible from there, not from the sandbox)
  - Uses only stdlib + requests (already in requirements)
  - Groups files by indicator number extracted from filename
  - Calls indicator_parser.parse_file() for each file
  - Returns a dict that can be saved to data/profiles/<name>.json

Entry point:
  import_profile(repo, ref, folder, *, token=None, timeout=20) -> dict
"""
from __future__ import annotations

import re
import json
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Optional

try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from app.services.indicator_parser import parse_file

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GITLAB_API = "https://gitlab.com/api/v4"
DEFAULT_REPO   = "kik-v/uitwisselprofielen/uitwisselprofiel-zorgkantoren"
DEFAULT_REF    = "1.3.4"
DEFAULT_FOLDER = "Gevalideerde_vragen_technisch"
SUPPORTED_EXTS = {".rq", ".sparql", ".md", ".ttl"}

# Indicator ID patterns found in KIK-V filenames:
#   IN-M-01, IN-WO-01, IN-V-01, etc.
#   Also numeric-only groups: 1.1, 2.3
_IND_PATTERN_RE = re.compile(
    r'(IN-[A-Z]+-\d+(?:\.\d+)?|(?<!\w)\d+\.\d+(?:\.\d+)?)(?:[_\-.]|$)',
    re.I
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _encoded_path(repo: str) -> str:
    return urllib.parse.quote(repo, safe='')


def _headers(token: Optional[str]) -> dict[str, str]:
    h: dict[str, str] = {"Accept": "application/json"}
    if token:
        h["PRIVATE-TOKEN"] = token
    return h


def _indicator_id(filename: str) -> str:
    """Extract the canonical indicator ID from a filename."""
    m = _IND_PATTERN_RE.search(filename)
    if m:
        return m.group(1).upper()
    # Fall back: stem without extension
    base = filename.rsplit('.', 1)[0]
    return base.replace('_', '-').upper()


def _fetch_tree(repo: str, ref: str, folder: str, token: Optional[str], timeout: int) -> list[dict]:
    """Return flat list of file entries from GitLab tree API (recursive)."""
    if not HAS_REQUESTS:
        raise RuntimeError("requests library is not installed. Run: pip install requests")

    url = (
        f"{GITLAB_API}/projects/{_encoded_path(repo)}/repository/tree"
        f"?path={urllib.parse.quote(folder)}&ref={urllib.parse.quote(ref)}"
        f"&recursive=true&per_page=100"
    )
    all_items: list[dict] = []
    while url:
        resp = _requests.get(url, headers=_headers(token), timeout=timeout)
        resp.raise_for_status()
        items = resp.json()
        all_items.extend(i for i in items if i.get("type") == "blob")
        # Pagination
        next_url = resp.headers.get("X-Next-Page")
        url = (
            f"{GITLAB_API}/projects/{_encoded_path(repo)}/repository/tree"
            f"?path={urllib.parse.quote(folder)}&ref={urllib.parse.quote(ref)}"
            f"&recursive=true&per_page=100&page={next_url}"
            if next_url else None
        )
    return all_items


def _fetch_file_content(repo: str, ref: str, file_path: str, token: Optional[str], timeout: int) -> str:
    """Fetch raw content of a single file from GitLab."""
    encoded_fp = urllib.parse.quote(file_path, safe='')
    url = (
        f"{GITLAB_API}/projects/{_encoded_path(repo)}/repository/files"
        f"/{encoded_fp}/raw?ref={urllib.parse.quote(ref)}"
    )
    resp = _requests.get(url, headers=_headers(token), timeout=timeout)
    resp.raise_for_status()
    return resp.text


# ---------------------------------------------------------------------------
# Core importer
# ---------------------------------------------------------------------------

def import_profile(
    repo: str = DEFAULT_REPO,
    ref: str = DEFAULT_REF,
    folder: str = DEFAULT_FOLDER,
    *,
    token: Optional[str] = None,
    timeout: int = 20,
    profile_name: Optional[str] = None,
) -> dict[str, Any]:
    """
    Fetch all indicator files from GitLab and return a Rhadix profile dict.

    Returns
    -------
    {
      "name": str,
      "version": str,
      "source": str,
      "ref": str,
      "folder": str,
      "imported_at": ISO-8601,
      "indicator_count": int,
      "file_count": int,
      "parse_errors": [...],
      "indicators": {
        "IN-M-01": {
          "id": "IN-M-01",
          "files": { "sparql": {...}, "markdown": {...}, "turtle": {...} },
          "metadata": { title, description, select_vars, predicates, ... }
        },
        ...
      }
    }
    """
    # 1. Fetch directory tree
    tree_items = _fetch_tree(repo, ref, folder, token, timeout)

    # 2. Filter to supported extensions
    supported = [
        item for item in tree_items
        if any(item["name"].lower().endswith(ext) for ext in SUPPORTED_EXTS)
    ]

    # 3. Group by indicator ID
    groups: dict[str, list[dict]] = {}
    for item in supported:
        ind_id = _indicator_id(item["name"])
        groups.setdefault(ind_id, []).append(item)

    # 4. Fetch and parse each file
    parse_errors: list[dict] = []
    indicators: dict[str, Any] = {}

    for ind_id, items in sorted(groups.items()):
        ind_entry: dict[str, Any] = {
            "id": ind_id,
            "files": {},
            "metadata": {},
        }

        for item in items:
            fname = item["name"]
            fpath = item["path"]
            ext   = fname.lower().rsplit('.', 1)[-1]
            try:
                content = _fetch_file_content(repo, ref, fpath, token, timeout)
                parsed  = parse_file(fname, content)
                ftype   = parsed["type"]
                ind_entry["files"][ftype] = {
                    "filename": fname,
                    "path": fpath,
                    "content": content,
                    "parsed": parsed["parsed"],
                }
            except Exception as exc:
                parse_errors.append({
                    "indicator_id": ind_id,
                    "filename": fname,
                    "path": fpath,
                    "error": str(exc),
                })

        # Merge parsed metadata into a flat summary
        ind_entry["metadata"] = _merge_metadata(ind_entry["files"])
        indicators[ind_id] = ind_entry

    name = profile_name or f"kik-v-{ref}"
    return {
        "name": name,
        "version": ref,
        "source": f"https://gitlab.com/{repo}",
        "ref": ref,
        "folder": folder,
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "indicator_count": len(indicators),
        "file_count": sum(len(v["files"]) for v in indicators.values()),
        "parse_errors": parse_errors,
        "indicators": indicators,
    }


def _merge_metadata(files: dict) -> dict[str, Any]:
    """Combine parsed results from different file types into a compact summary."""
    meta: dict[str, Any] = {}

    if "markdown" in files:
        md = files["markdown"]["parsed"]
        meta["title"]       = md.get("title")
        meta["description"] = md.get("description")
        meta["sections"]    = md.get("sections", [])
        meta["kv_pairs"]    = md.get("key_value_pairs", {})
        meta["concepts"]    = md.get("concepts", [])   # [{"label":..., "uri":...}]

    if "sparql" in files:
        sp = files["sparql"]["parsed"]
        meta["select_vars"]          = sp.get("select_vars", [])
        meta["parameters"]           = sp.get("parameters", [])
        meta["predicates"]           = sp.get("predicates", [])
        meta["filters"]              = sp.get("filters", [])
        meta["group_by_vars"]        = sp.get("group_by_vars", [])
        meta["date_logic"]           = sp.get("date_logic", [])
        meta["aggregate_functions"]  = sp.get("aggregate_functions", [])
        meta["limit"]                = sp.get("limit")
        meta["sparql_prefixes"]      = sp.get("prefixes", {})

    if "turtle" in files:
        tt = files["turtle"]["parsed"]
        meta["rdf_classes"]        = tt.get("named_resources", [])
        meta["subclass_relations"] = tt.get("subclass_relations", [])
        meta["property_triples"]   = tt.get("property_triples", [])

    return meta


# ---------------------------------------------------------------------------
# Profile storage helpers (used by the router)
# ---------------------------------------------------------------------------

import os
import pathlib

_PROFILES_DIR = pathlib.Path(__file__).parent.parent.parent / "data" / "profiles"


def save_profile(profile: dict, name: Optional[str] = None) -> pathlib.Path:
    """Save profile dict as JSON to data/profiles/<name>.json."""
    _PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = (name or profile.get("name", "profile")).replace(" ", "_")
    out_path = _PROFILES_DIR / f"{safe_name}.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, indent=2, ensure_ascii=False)
    return out_path


def list_profiles() -> list[dict]:
    """Return summary list of all saved profiles (no full indicator data)."""
    if not _PROFILES_DIR.exists():
        return []
    profiles = []
    for p in sorted(_PROFILES_DIR.glob("*.json")):
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
            profiles.append({
                "name":            data.get("name"),
                "version":         data.get("version"),
                "source":          data.get("source"),
                "ref":             data.get("ref"),
                "folder":          data.get("folder"),
                "imported_at":     data.get("imported_at"),
                "indicator_count": data.get("indicator_count", 0),
                "file_count":      data.get("file_count", 0),
                "parse_error_count": len(data.get("parse_errors", [])),
                "filename":        p.name,
            })
        except Exception:
            pass
    return profiles


def load_profile(filename: str) -> dict:
    """Load a saved profile by filename."""
    path = _PROFILES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {filename}")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def reparse_profile(filename: str) -> dict:
    """Re-run indicator_parser on all raw file content already stored in a profile.

    This updates metadata (titles, descriptions, concepts) without re-fetching
    from GitLab — useful after parser improvements.
    """
    profile = load_profile(filename)
    indicators = profile.get("indicators", {})

    for ind_id, ind in indicators.items():
        files = ind.get("files", {})
        new_files: dict = {}
        for ftype, fdata in files.items():
            raw = fdata.get("raw") or fdata.get("content", "")
            if not raw:
                # Try to get raw from nested parsed.raw (markdown stores it there)
                raw = (fdata.get("parsed") or {}).get("raw", "")
            if raw:
                # Reconstruct a fake filename to dispatch to the right parser
                ext_map = {"sparql": ".rq", "markdown": ".md", "turtle": ".ttl"}
                fake_fname = f"indicator{ext_map.get(ftype, '.txt')}"
                parsed = parse_file(fake_fname, raw)
                new_files[ftype] = {
                    "raw":    raw,
                    "parsed": parsed["parsed"],
                }
            else:
                new_files[ftype] = fdata
        ind["files"] = new_files
        ind["metadata"] = _merge_metadata(new_files)

    profile["indicators"] = indicators
    path = _PROFILES_DIR / filename
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, indent=2, ensure_ascii=False)
    return profile
