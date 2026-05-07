"""
readiness_analyzer.py
---------------------
For every KIK-V indicator in an imported profile, determines whether the
currently uploaded source data can support that indicator's SPARQL query.

Inputs
------
- profile       : dict from gitlab_importer (with `indicators` sub-dict)
- scan_result   : dict returned by the /api/validate endpoint (KIK-V path)

Output (returned dict)
----------------------
{
  "profile_readiness_score": float,          # 0-100
  "fully_computable":    int,
  "partially_computable": int,
  "blocked":             int,
  "total_indicators":    int,
  "top_blocking_fields":        [...],       # top-10
  "top_blocking_relationships": [...],       # top-10
  "indicator_results":   {id: {...}, ...},
}
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

# ─── Canonical source domains Rhadix understands ──────────────────────────────

KNOWN_DOMAINS = {"medewerker", "werkovereenkomst", "functie", "verzuim",
                 "vestiging", "client"}

# Vertaaltabel schema_key → domein voor readiness-analyse
# Meerdere schema's kunnen naar hetzelfde domein verwijzen
SCHEMA_TO_DOMAIN: dict[str, str] = {
    "medewerker":       "medewerker",
    "werkovereenkomst": "werkovereenkomst",
    "functie":          "functie",
    "verzuim":          "verzuim",
    "vestiging":        "zorgkantoor",   # locatiedata activeert zorgkantoor-domein
    "client":           "zorgkantoor",   # cliëntdata activeert zorgkantoor-domein
}

# ─── Predicate local-name → list[(domain, field)] ────────────────────────────
# Covers all KIK-V onz-pers / onz-g predicates that appear in the SPARQL files

PRED_LOCAL_TO_FIELDS: dict[str, list[tuple[str, str]]] = {
    # Generic identifier predicates
    "personeelsnummer":   [
        ("medewerker",        "personeelsnummer"),
        ("werkovereenkomst",  "personeelsnummer"),
        ("functie",           "personeelsnummer"),
        ("verzuim",           "personeelsnummer"),
    ],
    "employeeidentifier": [("medewerker", "personeelsnummer")],
    "identifier":         [("medewerker", "personeelsnummer")],

    # Medewerker
    "geboortedatum":      [("medewerker", "geboortedatum")],
    "dateofbirth":        [("medewerker", "geboortedatum")],
    "hasDateOfBirth":     [("medewerker", "geboortedatum")],

    # WerkOvereenkomst
    "startdatum":         [("werkovereenkomst", "startdatum")],
    "einddatum":          [("werkovereenkomst", "einddatum")],
    "startDate":          [("werkovereenkomst", "startdatum")],
    "endDate":            [("werkovereenkomst", "einddatum")],
    "overeenkomsttype":   [("werkovereenkomst", "overeenkomsttype")],
    "contracttype":       [("werkovereenkomst", "overeenkomsttype")],
    "urenperweek":        [("werkovereenkomst", "urenperweek")],
    "contractomvang":     [("werkovereenkomst", "urenperweek")],
    "omvang":             [("werkovereenkomst", "urenperweek")],
    "dienstverbandnummer":[("werkovereenkomst", "dienstverbandnummer")],

    # Functie
    "functie":            [("functie", "functie")],
    "kwalificatieniveau": [("functie", "kwalificatieniveau")],
    "igj":                [("functie", "kwalificatieniveau")],

    # Verzuim
    "soortverzuim":       [("verzuim", "soortverzuim")],
    "verzuimtype":        [("verzuim", "soortverzuim")],
    "startmoment":        [("verzuim", "startmoment")],
    "eindmoment":         [("verzuim", "eindmoment")],
    "verzuimpercentage":  [("verzuim", "verzuimpercentage")],
    "aoPercentage":       [("verzuim", "verzuimpercentage")],
}

# ─── RDF class local-name → domain ───────────────────────────────────────────

CLASS_LOCAL_TO_DOMAIN: dict[str, str] = {
    # Full names
    "medewerker":             "medewerker",
    "werkovereenkomst":       "werkovereenkomst",
    "verzuimperiode":         "verzuim",
    "verzuim":                "verzuim",
    "zorgverlenerfunctie":    "functie",
    "functie":                "functie",
    # Partial / abbreviated forms found in KIK-V filenames
    "employee":               "medewerker",
    "contract":               "werkovereenkomst",
    "absence":                "verzuim",
    "role":                   "functie",
    # ZK-IB cliënt/zorgkantoor klassen (ex: prefix — niet KIK-V HR)
    "zorgkantoor":            "zorgkantoor",
    "peildatumpicklist":      "zorgkantoor",
    "client":                 "zorgkantoor",
    "cliënt":                 "zorgkantoor",
    "zorgproces":             "zorgkantoor",
    "vestiging":              "zorgkantoor",
}

# Fields that serve as FK relationships (domain, from_field, target_domain)
FK_RELATIONSHIPS: list[tuple[str, str, str]] = [
    ("werkovereenkomst",  "personeelsnummer", "medewerker"),
    ("functie",           "personeelsnummer", "medewerker"),
    ("verzuim",           "personeelsnummer", "medewerker"),
]

# All fields available per domain (union of what Rhadix checks)
ALL_DOMAIN_FIELDS: dict[str, list[str]] = {
    "medewerker":       ["personeelsnummer", "geboortedatum"],
    "werkovereenkomst": ["personeelsnummer", "startdatum", "einddatum",
                         "overeenkomsttype", "urenperweek", "dienstverbandnummer"],
    "functie":          ["personeelsnummer", "functie", "kwalificatieniveau"],
    "verzuim":          ["personeelsnummer", "soortverzuim", "startmoment",
                         "eindmoment", "verzuimpercentage"],
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

_PREFIX_LOCAL_RE = re.compile(r'(?:[\w-]+:)?(\w+)$')


def _local(name: str) -> str:
    """Extract the local part of a prefixed name or URI."""
    if '#' in name:
        return name.rsplit('#', 1)[-1]
    m = _PREFIX_LOCAL_RE.search(name)
    return m.group(1) if m else name


def _required_domains_from_classes(rdf_classes: list[str]) -> set[str]:
    domains: set[str] = set()
    for cls in rdf_classes:
        loc = _local(cls).lower()
        for pattern, domain in CLASS_LOCAL_TO_DOMAIN.items():
            if pattern in loc:
                domains.add(domain)
    return domains


def _required_fields_from_predicates(
    predicates: list[str],
    parameters: list[str],
) -> dict[str, list[str]]:
    """
    Returns {domain: [field, ...]} for all required (domain, field) pairs.
    """
    domain_fields: dict[str, set[str]] = defaultdict(set)

    # From SPARQL predicates
    for pred in predicates:
        loc = _local(pred).lower()
        for pattern, pairs in PRED_LOCAL_TO_FIELDS.items():
            if pattern.lower() == loc or pattern.lower() in loc:
                for domain, field in pairs:
                    domain_fields[domain].add(field)

    # From SELECT vars / parameters — heuristic match
    for var in parameters:
        loc = var.lower().replace('_', '').replace('-', '')
        for pattern, pairs in PRED_LOCAL_TO_FIELDS.items():
            if pattern.lower().replace('_', '') in loc or loc in pattern.lower():
                for domain, field in pairs:
                    domain_fields[domain].add(field)

    return {d: sorted(f) for d, f in domain_fields.items()}


def _required_relationships(required_domains: set[str]) -> list[dict]:
    """FK relationships that must hold given the required domains."""
    rels = []
    for from_domain, from_field, target_domain in FK_RELATIONSHIPS:
        if from_domain in required_domains and target_domain in required_domains:
            rels.append({
                "from_domain":  from_domain,
                "from_field":   from_field,
                "target_domain": target_domain,
            })
    return rels


# ─── Extract uploaded context from scan_result ───────────────────────────────

def _parse_scan_context(scan_result: dict) -> dict:
    """
    Derive what's available from the scan result:
      - uploaded_domains: set of schema_keys that were uploaded
      - mapped_fields:    {domain: set[field]} actually mapped
      - field_errors:     {(domain, field): error_count}
      - structural_score, relational_score, use_case_score, availability_score
      - relational_issues: list of FK failures
      - indicator_sparql_results: {indicator_id: pass_rate}
    """
    uploaded_domains: set[str] = set()
    mapped_fields:    dict[str, set[str]] = defaultdict(set)
    field_errors:     dict[tuple[str, str], int] = defaultdict(int)

    for fsum in scan_result.get("files_summary", []):
        sk = fsum.get("schema_key") or ""
        if sk not in KNOWN_DOMAINS:
            continue
        # Vertaal schema_key naar het readiness-domein (bijv. vestiging → zorgkantoor)
        domain = SCHEMA_TO_DOMAIN.get(sk, sk)
        uploaded_domains.add(domain)
        sk = domain  # gebruik domein voor verdere verwerking (mapped_fields, errors)

        # What fields are actually mapped (present in the file)
        mapping = fsum.get("field_map") or fsum.get("mapping") or {}
        for rhadix_field, source_col in mapping.items():
            if source_col:  # not None/empty → field was found
                mapped_fields[sk].add(rhadix_field)

        # Also infer from issues: if an issue references a field, domain is present
        for issue in fsum.get("issues", []):
            field = issue.get("field") or issue.get("source_column") or ""
            field_lc = field.lower().replace(" ", "_")
            if field_lc:
                # Count as error
                field_errors[(sk, field_lc)] += 1

    # Scores
    structural_score  = scan_result.get("structural_score")
    relational_score  = scan_result.get("relational_score")
    use_case_score    = scan_result.get("use_case_score")
    availability_score = scan_result.get("score")  # main Rhadix availability score

    # Relational FK failures
    fk_issues = []
    for fk in scan_result.get("relational_fk", []):
        if (fk.get("passed", 0) or 0) < (fk.get("total", 1) or 1):
            fk_issues.append(fk)

    # SPARQL use-case indicator results → keyed by indicator_id
    indicator_sparql: dict[str, dict] = {}
    for ir in scan_result.get("indicator_results", []):
        iid = ir.get("indicator_id") or ir.get("id") or ""
        if iid:
            indicator_sparql[iid.upper()] = ir

    return {
        "uploaded_domains":   uploaded_domains,
        "mapped_fields":      dict(mapped_fields),
        "field_errors":       dict(field_errors),
        "structural_score":   structural_score,
        "relational_score":   relational_score,
        "use_case_score":     use_case_score,
        "availability_score": availability_score,
        "fk_issues":          fk_issues,
        "indicator_sparql":   indicator_sparql,
    }


# ─── Per-indicator readiness ──────────────────────────────────────────────────

def _score_indicator(
    ind:     dict,
    ctx:     dict,
) -> dict[str, Any]:
    """
    Evaluate one indicator against the scan context.

    Returns
    -------
    {
      id, title,
      readiness: "fully" | "partially" | "blocked",
      readiness_score: 0-100,
      required_domains: [],
      required_fields:  {domain: [field]},
      required_relationships: [],
      missing_domains:  [],
      missing_fields:   {domain: [field]},
      missing_mappings: [],
      blocking_issues:  [],
      warnings:         [],
      sparql_pass_rate: float | None,
    }
    """
    meta = ind.get("metadata") or {}
    ind_id = ind["id"]
    title  = meta.get("title") or ind_id

    rdf_classes = meta.get("rdf_classes", [])
    predicates  = meta.get("predicates",  [])
    parameters  = meta.get("parameters",  [])
    select_vars = meta.get("select_vars", [])

    # ── Required domains ──
    req_domains = _required_domains_from_classes(rdf_classes)

    # Fallback: if no classes extracted but we have predicates, derive from them
    req_fields_map = _required_fields_from_predicates(predicates, parameters + select_vars)
    if not req_domains:
        req_domains = set(req_fields_map.keys())

    # If still nothing: check if this is a BIND-only template (no triple patterns needed)
    if not req_domains and not req_fields_map:
        # BIND-only indicators (17.x handmatige invulformulieren) hebben geen ontologie-afhankelijkheid
        sparql_parsed = (ind.get("files") or {}).get("sparql", {}).get("parsed", {})
        has_binds    = bool(sparql_parsed.get("binds"))
        has_preds    = bool(sparql_parsed.get("predicates") or predicates)
        is_bind_only = has_binds and not has_preds
        if is_bind_only:
            return {
                "id":                      ind_id,
                "title":                   title,
                "readiness":               "fully",
                "readiness_score":         100,
                "required_domains":        [],
                "required_fields":         {},
                "required_relationships":  [],
                "missing_domains":         [],
                "missing_fields":          {},
                "missing_mappings":        [],
                "blocking_issues":         [],
                "warnings":                ["Handmatig invulformulier — geen brondata vereist"],
                "sparql_pass_rate":        None,
            }
        return {
            "id":                      ind_id,
            "title":                   title,
            "readiness":               "partially",
            "readiness_score":         50,
            "required_domains":        [],
            "required_fields":         {},
            "required_relationships":  [],
            "missing_domains":         [],
            "missing_fields":          {},
            "missing_mappings":        [],
            "blocking_issues":         ["Onvoldoende metadata — predicaten en klassen niet extraheerbaar"],
            "warnings":                [],
            "sparql_pass_rate":        None,
        }

    uploaded    = ctx["uploaded_domains"]
    mapped_flds = ctx["mapped_fields"]
    fld_errors  = ctx["field_errors"]
    fk_issues   = ctx["fk_issues"]

    # ── Missing domains ──
    missing_domains = sorted(req_domains - uploaded)

    # ── Missing fields ──
    missing_fields: dict[str, list[str]] = {}
    missing_mappings: list[str] = []
    for domain, fields in req_fields_map.items():
        if domain not in uploaded:
            # Entire domain missing — fields are implicitly missing too
            missing_fields[domain] = fields
            continue
        available = mapped_flds.get(domain, set())
        # If mapped_fields is empty (mapping not in scan_result), check ALL_DOMAIN_FIELDS
        if not available:
            available = set(ALL_DOMAIN_FIELDS.get(domain, []))
        missing = [f for f in fields if f not in available]
        if missing:
            missing_fields[domain] = missing
            missing_mappings.extend(f"{domain}.{f}" for f in missing)

    # ── Required FK relationships ──
    req_rels = _required_relationships(req_domains)

    # ── Blocking issues ──
    blocking: list[str] = []
    warnings: list[str] = []

    for d in missing_domains:
        blocking.append(f"Bronbestand '{d}' niet geüpload")

    for domain, fields in missing_fields.items():
        if domain in missing_domains:
            continue  # already a domain-level blocker
        for f in fields:
            err_count = fld_errors.get((domain, f), 0)
            if err_count > 0:
                blocking.append(f"Veld '{domain}.{f}' aanwezig maar bevat {err_count} fouten")
            else:
                blocking.append(f"Veld '{domain}.{f}' niet gevonden in brondata")

    # FK warnings
    for rel in req_rels:
        rel_domain = rel["from_domain"]
        rel_field  = rel["from_field"]
        if rel_domain in missing_domains:
            continue
        for fk in fk_issues:
            if fk.get("from_schema") == rel_domain:
                warnings.append(
                    f"FK-integriteit: {rel_domain}.{rel_field} → {rel['target_domain']} "
                    f"({fk.get('failed', '?')} ontbrekende verwijzingen)"
                )

    # Structural quality warning
    struct_score = ctx.get("structural_score")
    if struct_score is not None and struct_score < 80:
        warnings.append(f"Structurele score laag ({struct_score:.0f}%) — OWL-conformiteit onvoldoende")

    # SPARQL use-case result for this indicator
    sparql_res  = ctx["indicator_sparql"].get(ind_id.upper())
    sparql_pass = sparql_res.get("pass_rate") if sparql_res else None

    if sparql_pass is not None and sparql_pass < 0.9:
        pct = f"{sparql_pass * 100:.0f}%"
        if sparql_pass < 0.5:
            blocking.append(f"SPARQL-validatie slechts {pct} geslaagd")
        else:
            warnings.append(f"SPARQL-validatie {pct} geslaagd (drempel: 90%)")

    # ── Readiness score (0-100) ──
    n_req_domains = max(len(req_domains), 1)
    n_uploaded    = len(req_domains - set(missing_domains))
    domain_cov    = n_uploaded / n_req_domains

    all_req_fields = [f for fields in req_fields_map.values() for f in fields]
    n_req_fields   = max(len(all_req_fields), 1)
    n_miss_fields  = sum(len(f) for f in missing_fields.values())
    field_cov      = max(0.0, (n_req_fields - n_miss_fields) / n_req_fields)

    # Weighted: domains 60%, fields 40%
    raw_score = domain_cov * 60 + field_cov * 40

    # Penalty: -5 per warning (capped), SPARQL bonus/penalty
    raw_score -= min(len(warnings) * 5, 20)
    if sparql_pass is not None:
        raw_score = raw_score * 0.7 + sparql_pass * 100 * 0.3

    readiness_score = max(0, min(100, round(raw_score)))

    # ── Classification ──
    if blocking:
        if domain_cov == 0:
            readiness = "blocked"
        elif readiness_score >= 40:
            readiness = "partially"
        else:
            readiness = "blocked"
    elif warnings:
        readiness = "partially"
    else:
        readiness = "fully"

    return {
        "id":                     ind_id,
        "title":                  title,
        "readiness":              readiness,
        "readiness_score":        readiness_score,
        "required_domains":       sorted(req_domains),
        "required_fields":        req_fields_map,
        "required_relationships": req_rels,
        "missing_domains":        missing_domains,
        "missing_fields":         missing_fields,
        "missing_mappings":       missing_mappings,
        "blocking_issues":        blocking,
        "warnings":               warnings,
        "sparql_pass_rate":       sparql_pass,
    }


# ─── Top-N aggregations ───────────────────────────────────────────────────────

def _top_blocking_fields(results: list[dict], n: int = 10) -> list[dict]:
    counter: Counter = Counter()
    for r in results:
        for domain, fields in r.get("missing_fields", {}).items():
            for f in fields:
                counter[f"{domain}.{f}"] += 1
    return [{"field": k, "blocked_indicators": v}
            for k, v in counter.most_common(n)]


def _top_blocking_relationships(results: list[dict], n: int = 10) -> list[dict]:
    counter: Counter = Counter()
    for r in results:
        if r["readiness"] in ("blocked", "partially"):
            for rel in r.get("required_relationships", []):
                key = f"{rel['from_domain']}.{rel['from_field']} → {rel['target_domain']}"
                # Only count if the from_domain is missing
                if rel["from_domain"] in r.get("missing_domains", []):
                    counter[key] += 1
    return [{"relationship": k, "blocked_indicators": v}
            for k, v in counter.most_common(n)]


# ─── Heatmap: indicators × domains ───────────────────────────────────────────

def _build_heatmap(results: list[dict]) -> list[dict]:
    """
    Each row: {indicator_id, title, medewerker, werkovereenkomst, functie, verzuim}
    Each cell value: "required_present" | "required_missing" | "not_required"
    """
    rows = []
    for r in results:
        req    = set(r.get("required_domains", []))
        miss   = set(r.get("missing_domains",  []))
        cell: dict[str, str] = {}
        for domain in sorted(KNOWN_DOMAINS):
            if domain not in req:
                cell[domain] = "not_required"
            elif domain in miss:
                cell[domain] = "required_missing"
            else:
                cell[domain] = "required_present"
        rows.append({
            "indicator_id": r["id"],
            "title":        r["title"],
            "readiness":    r["readiness"],
            **cell,
        })
    return rows


# ─── Public entry point ───────────────────────────────────────────────────────

def analyze_readiness(profile: dict, scan_result: dict) -> dict[str, Any]:
    """
    Compute the full readiness matrix for a profile against a scan result.

    Parameters
    ----------
    profile     : saved profile dict (from load_profile / import_profile)
    scan_result : current scan result from /api/validate

    Returns
    -------
    Full readiness matrix dict (described at top of file).
    """
    ctx = _parse_scan_context(scan_result)
    indicators = profile.get("indicators", {})

    ind_results: dict[str, dict] = {}
    for ind_id, ind_data in indicators.items():
        # Sla index-bestanden over — beginnen met '-' of hebben geen metadata
        if ind_id.startswith("-"):
            continue
        ind_results[ind_id] = _score_indicator(ind_data, ctx)

    results_list = list(ind_results.values())

    fully      = sum(1 for r in results_list if r["readiness"] == "fully")
    partially  = sum(1 for r in results_list if r["readiness"] == "partially")
    blocked    = sum(1 for r in results_list if r["readiness"] == "blocked")
    total      = len(results_list)

    profile_score = round(
        (fully + 0.5 * partially) / max(total, 1) * 100, 1
    )

    return {
        "profile_name":            profile.get("name"),
        "profile_version":         profile.get("version"),
        "profile_readiness_score": profile_score,
        "fully_computable":        fully,
        "partially_computable":    partially,
        "blocked":                 blocked,
        "total_indicators":        total,
        # Scan scores (passed through for display)
        "availability_score":      ctx["availability_score"],
        "structural_score":        ctx["structural_score"],
        "relational_score":        ctx["relational_score"],
        "use_case_score":          ctx["use_case_score"],
        "uploaded_domains":        sorted(ctx["uploaded_domains"]),
        # Aggregations
        "top_blocking_fields":        _top_blocking_fields(results_list),
        "top_blocking_relationships": _top_blocking_relationships(results_list),
        "heatmap":                    _build_heatmap(results_list),
        # Per-indicator detail
        "indicator_results":          ind_results,
    }
