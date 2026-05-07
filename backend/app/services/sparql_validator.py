"""
sparql_validator.py — SPARQL-driven use-case readiness validation
=================================================================
Part 2 of the OWL + SPARQL pipeline.

Produces: use_case_score (0-100) — separate from structural/relational scores.

Architecture
------------
1. csv_to_rdf(files_data)
     Converts CSV rows to an rdflib Graph using concept_uri from rules.py.
     Each row becomes a blank node typed to its OWL class.

2. load_queries(query_dir)
     Loads *.sparql files and parses their metadata comments.

3. execute_query(graph, sparql_text)
     Runs one SPARQL SELECT query, returns {totaal, aanwezig/gekoppeld/etc.}.

4. evaluate_indicator(query_result, threshold)
     Computes pass_rate and determines pass/fail.

5. compute_use_case_score(indicator_results)
     Weighted average of all indicator pass rates.

Dependencies
------------
    pip install rdflib   (already in typical Python envs)

Falls back gracefully if rdflib is not installed — returns score=None with
a clear message so existing functionality is unaffected.
"""
from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Optional

from app.services.rules import FIELD_RULES

# Try importing rdflib — graceful degradation if absent
try:
    from rdflib import Graph, Namespace, URIRef, Literal, BNode
    from rdflib.namespace import RDF, XSD
    _RDFLIB = True
except ImportError:
    _RDFLIB = False

# KIK-V / ONZ namespaces
ONZ_G    = "http://purl.org/ozo/onz-g#"
ONZ_PERS = "http://purl.org/ozo/onz-pers#"
ONZ_ORG  = "http://purl.org/ozo/onz-zorg#"

# Field key → RDF predicate URI mapping (extends rules.py concept_uri)
_FIELD_PREDICATE: dict[str, str] = {
    # medewerker
    "personeelsnummer":    f"{ONZ_G}personeelsnummer",
    "geboortedatum":       f"{ONZ_G}geboortedatum",
    # werkovereenkomst
    "overeenkomsttype":    f"{ONZ_PERS}overeenkomstType",
    "startdatum":          f"{ONZ_G}startDatum",
    "einddatum":           f"{ONZ_G}eindDatum",
    "dienstverbandnummer": f"{ONZ_G}dienstverbandIdentifier",
    "urenperweek":         f"{ONZ_PERS}contractOmvang",
    "overeenkomstoe":      f"{ONZ_G}organisatieEenheid",
    # functie
    "functie":             f"{ONZ_PERS}functieBenaming",
    "kwalificatieniveau":  f"{ONZ_PERS}kwalificatieNiveau",
    # verzuim
    "soortverzuim":        f"{ONZ_PERS}soortVerzuim",
    "startmoment":         f"{ONZ_G}startDatum",
    "eindmoment":          f"{ONZ_G}eindDatum",
    "verzuimpercentage":   f"{ONZ_PERS}aoPercentage",
}

# schema_key → OWL class URI (rdf:type)
_SCHEMA_CLASS: dict[str, str] = {
    "medewerker":      f"{ONZ_PERS}Medewerker",
    "werkovereenkomst": f"{ONZ_PERS}WerkOvereenkomst",
    "functie":         f"{ONZ_PERS}ZorgverlenerFunctie",
    "verzuim":         f"{ONZ_PERS}VerzuimPeriode",
}

# Default thresholds per query (pass if pass_rate >= threshold)
_DEFAULT_THRESHOLDS: dict[str, float] = {
    "IN-M-01": 0.99,
    "IN-M-03": 0.95,
    "IN-WO-01": 0.90,
    "IN-WO-02": 0.95,
    "IN-WO-03": 0.99,
    "IN-V-01":  0.98,
}


# ─── Step 1: CSV → RDF ───────────────────────────────────────────────────────

def csv_to_rdf(files_data: list[dict]) -> "Graph":
    """
    Convert CSV rows to an rdflib in-memory graph.

    Each row becomes a blank node typed to its OWL class.
    Field values are added as datatype literals or plain literals.
    """
    if not _RDFLIB:
        raise RuntimeError("rdflib not installed — pip install rdflib")

    g = Graph()
    g.bind("onz",  Namespace(ONZ_PERS))
    g.bind("onzg", Namespace(ONZ_G))

    for fd in files_data:
        sk      = fd.get("schema_key") or ""
        rows    = fd.get("rows", [])
        mapping = fd.get("mapping", {})
        class_uri = _SCHEMA_CLASS.get(sk)
        if not class_uri:
            continue

        class_ref = URIRef(class_uri)
        field_rules = FIELD_RULES.get(sk, {})

        for row in rows[:500]:
            node = BNode()
            g.add((node, RDF.type, class_ref))

            for field_key, rule in field_rules.items():
                col_name = mapping.get(field_key) or field_key
                val = (row.get(col_name) or "").strip()
                if not val:
                    continue

                pred_uri = _FIELD_PREDICATE.get(field_key) or rule.get("concept_uri")
                if not pred_uri:
                    continue

                pred = URIRef(pred_uri)
                # Detect type
                fmt = rule.get("format", "")
                if "datum" in fmt.lower() or "date" in fmt.lower():
                    lit = Literal(val, datatype=XSD.date)
                elif "getal" in fmt.lower() or "number" in fmt.lower():
                    try:
                        lit = Literal(float(val), datatype=XSD.decimal)
                    except ValueError:
                        lit = Literal(val)
                else:
                    lit = Literal(val)

                g.add((node, pred, lit))

    return g


# ─── Step 2: Load SPARQL queries ─────────────────────────────────────────────

def load_queries(query_dir: str) -> list[dict]:
    """
    Load all *.sparql files from query_dir.

    Returns list of:
      {indicator_id, description, sparql, threshold, filename}
    """
    queries = []
    qpath   = Path(query_dir)
    if not qpath.exists():
        return queries

    for f in sorted(qpath.glob("*.sparql")):
        text = f.read_text(encoding="utf-8")
        # Parse indicator ID from filename (IN-M-01_*.sparql)
        m = re.match(r"(IN-[A-Z]+-\d+)", f.stem)
        indicator_id = m.group(1) if m else f.stem

        # Parse description from first comment line
        desc_match = re.search(r"^#\s*(.+)", text, re.MULTILINE)
        description = desc_match.group(1).strip() if desc_match else indicator_id

        threshold = _DEFAULT_THRESHOLDS.get(indicator_id, 0.95)

        queries.append({
            "indicator_id": indicator_id,
            "description":  description,
            "sparql":       text,
            "threshold":    threshold,
            "filename":     f.name,
        })

    return queries


# ─── Step 3: Execute one SPARQL query ────────────────────────────────────────

def execute_query(graph: "Graph", sparql_text: str) -> dict:
    """
    Execute a SPARQL SELECT on graph.
    Returns the first result row as {var_name: value, …}, or {} on error.
    """
    if not _RDFLIB:
        return {}
    try:
        results = list(graph.query(sparql_text))
        if not results:
            return {}
        first_row = results[0]
        # Convert to plain dict
        vars_ = [str(v) for v in results.vars]
        return {
            var: (int(str(val)) if val is not None and str(val).isdigit() else
                  (str(val) if val is not None else 0))
            for var, val in zip(vars_, first_row)
        }
    except Exception as e:
        return {"_error": str(e)}


# ─── Step 4: Evaluate one indicator ──────────────────────────────────────────

def evaluate_indicator(query_result: dict, threshold: float, indicator_id: str) -> dict:
    """
    Compute pass_rate from the query result dict and apply threshold.

    Heuristic: looks for 'totaal' + one of 'aanwezig'/'gekoppeld'/'met_type'/'contracten'.
    """
    if "_error" in query_result:
        return {
            "pass":      False,
            "pass_rate": 0.0,
            "totaal":    0,
            "numerator": 0,
            "threshold": threshold,
            "error":     query_result["_error"],
        }

    totaal = int(query_result.get("totaal", 0) or query_result.get("medewerkers", 0))
    numer_key = next(
        (k for k in ("aanwezig", "gekoppeld", "met_type", "contracten") if k in query_result),
        None
    )
    numerator = int(query_result.get(numer_key, 0)) if numer_key else 0

    if totaal == 0:
        pass_rate = 1.0  # No data — cannot fail
        passed    = True
    else:
        pass_rate = round(numerator / totaal, 4)
        passed    = pass_rate >= threshold

    return {
        "pass":      passed,
        "pass_rate": round(pass_rate * 100, 1),
        "totaal":    totaal,
        "numerator": numerator,
        "threshold": round(threshold * 100, 1),
    }


# ─── Step 5: Compute use_case_score ──────────────────────────────────────────

def compute_use_case_score(indicator_results: list[dict]) -> float:
    """
    Weighted average of all indicator pass_rates.
    Each indicator has equal weight (1.0) unless overridden.
    """
    if not indicator_results:
        return 100.0
    total_weight = 0.0
    weighted_sum = 0.0
    for r in indicator_results:
        w = r.get("weight", 1.0)
        total_weight += w
        weighted_sum += r.get("pass_rate", 0.0) * w
    return round(weighted_sum / total_weight, 1) if total_weight else 0.0


# ─── Main entry point ────────────────────────────────────────────────────────

def validate_use_cases(
    files_data: list[dict],
    query_dir: Optional[str] = None,
) -> dict:
    """
    Full SPARQL-driven use-case validation pipeline.

    Parameters
    ----------
    files_data  : list of {filename, schema_key, rows[], mapping{}}
    query_dir   : path to directory containing *.sparql files.
                  Defaults to backend/kikv_queries/ relative to this file.

    Returns
    -------
    {
        use_case_score    : float 0-100 (or None if rdflib absent)
        indicator_results : list[{indicator_id, description, pass, pass_rate,
                                   totaal, numerator, threshold, error?}]
        graph_triples     : int   (size of the in-memory RDF graph)
        rdflib_available  : bool
    }
    """
    if not _RDFLIB:
        return {
            "use_case_score":    None,
            "indicator_results": [],
            "graph_triples":     0,
            "rdflib_available":  False,
            "message":           "rdflib niet geïnstalleerd — voer 'pip install rdflib' uit.",
        }

    # Resolve query_dir
    if query_dir is None:
        here = Path(__file__).parent.parent.parent  # backend/
        query_dir = str(here / "kikv_queries")

    # Build RDF graph
    try:
        graph = csv_to_rdf(files_data)
    except Exception as e:
        return {
            "use_case_score":    None,
            "indicator_results": [],
            "graph_triples":     0,
            "rdflib_available":  True,
            "message":           f"RDF conversie mislukt: {e}",
        }

    graph_triples = len(graph)

    # Load and execute queries
    queries = load_queries(query_dir)
    indicator_results: list[dict] = []

    for q in queries:
        raw = execute_query(graph, q["sparql"])
        eval_ = evaluate_indicator(raw, q["threshold"], q["indicator_id"])
        indicator_results.append({
            "indicator_id": q["indicator_id"],
            "description":  q["description"],
            "filename":     q["filename"],
            **eval_,
        })

    use_case_score = compute_use_case_score(indicator_results)

    return {
        "use_case_score":    use_case_score,
        "indicator_results": indicator_results,
        "graph_triples":     graph_triples,
        "rdflib_available":  True,
    }
