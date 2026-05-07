"""
indicator_parser.py
-------------------
Parses KIK-V indicator files (.rq / .sparql, .md, .ttl) and extracts structured metadata.
No external SPARQL execution – purely lexical / regex extraction.
"""
from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# SPARQL / .rq parser
# ---------------------------------------------------------------------------

_SELECT_RE   = re.compile(r'\bSELECT\b\s+(DISTINCT\s+)?(.+?)(?=\bWHERE\b)', re.I | re.S)
_VAR_RE      = re.compile(r'\?(\w+)')
_PREFIX_RE   = re.compile(r'PREFIX\s+(\w*:)\s*<([^>]+)>', re.I)
_FILTER_RE   = re.compile(r'FILTER\s*\((.+?)\)', re.I | re.S)
_GROUP_RE    = re.compile(r'GROUP\s+BY\s+(.+?)(?=\bHAVING\b|\bORDER\b|\bLIMIT\b|\bOFFSET\b|$)', re.I | re.S)
_HAVING_RE   = re.compile(r'HAVING\s*\((.+?)\)', re.I | re.S)
_ORDER_RE    = re.compile(r'ORDER\s+BY\s+(.+?)(?=\bLIMIT\b|\bOFFSET\b|$)', re.I | re.S)
_LIMIT_RE    = re.compile(r'LIMIT\s+(\d+)', re.I)
_PRED_RE     = re.compile(r'[;,\s]\s*([\w]+:[\w]+)\s+\?', re.I)
_DATE_FN_RE  = re.compile(r'\b(NOW|YEAR|MONTH|DAY|xsd:date|xsd:dateTime|STRDT|STRLANG|COALESCE)\s*\(', re.I)
_BIND_RE     = re.compile(r'\bBIND\s*\((.+?)\s+AS\s+\?(\w+)\s*\)', re.I | re.S)


def parse_sparql(text: str) -> dict[str, Any]:
    """Extract metadata from a SPARQL SELECT query string."""
    prefixes: dict[str, str] = {}
    for m in _PREFIX_RE.finditer(text):
        prefixes[m.group(1)] = m.group(2)

    # SELECT output variables
    select_vars: list[str] = []
    sm = _SELECT_RE.search(text)
    if sm:
        raw_select = sm.group(2)
        if raw_select.strip() == '*':
            select_vars = ['*']
        else:
            select_vars = _VAR_RE.findall(raw_select)

    # All ?variables referenced in query
    all_vars = list(dict.fromkeys(_VAR_RE.findall(text)))

    # Parameters: vars in WHERE but not in SELECT (heuristic)
    parameters = [v for v in all_vars if v not in select_vars and v != '*']

    # Predicates used  (prefix:localname)
    predicates = list(dict.fromkeys(_PRED_RE.findall(text)))

    # FILTER clauses
    filters = [m.group(1).strip() for m in _FILTER_RE.finditer(text)]

    # GROUP BY variables
    group_by_vars: list[str] = []
    gm = _GROUP_RE.search(text)
    if gm:
        group_by_vars = _VAR_RE.findall(gm.group(1))

    # HAVING
    having = [m.group(1).strip() for m in _HAVING_RE.finditer(text)]

    # ORDER BY (raw text)
    order_by: list[str] = []
    om = _ORDER_RE.search(text)
    if om:
        order_by = om.group(1).strip().split()

    # LIMIT
    limit: int | None = None
    lm = _LIMIT_RE.search(text)
    if lm:
        limit = int(lm.group(1))

    # Date-related functions
    date_logic = list(dict.fromkeys(_DATE_FN_RE.findall(text)))

    # BIND expressions
    binds = [{"expression": m.group(1).strip(), "as": m.group(2)} for m in _BIND_RE.finditer(text)]

    # Detect aggregates
    agg_fns = list(dict.fromkeys(re.findall(r'\b(COUNT|SUM|AVG|MIN|MAX|GROUP_CONCAT|SAMPLE)\s*\(', text, re.I)))

    return {
        "prefixes": prefixes,
        "select_vars": select_vars,
        "parameters": parameters,
        "predicates": predicates,
        "filters": filters,
        "group_by_vars": group_by_vars,
        "having": having,
        "order_by": order_by,
        "limit": limit,
        "date_logic": date_logic,
        "binds": binds,
        "aggregate_functions": agg_fns,
    }


# ---------------------------------------------------------------------------
# Markdown parser
# ---------------------------------------------------------------------------

_MD_FRONTMATTER_RE = re.compile(r'^---\s*\n(.+?)\n---\s*\n', re.S)
_MD_FM_KV_RE       = re.compile(r'^(\w[\w\s]*):\s*(.+)', re.M)
_MD_TITLE_RE    = re.compile(r'^#\s+(.+)', re.M)
_MD_H2_RE       = re.compile(r'^##\s+(.+)', re.M)
_MD_BOLD_RE     = re.compile(r'\*\*(.+?)\*\*')
_MD_TABLE_RE    = re.compile(r'(\|.+\|[\r\n]+\|[-| :]+\|[\r\n]+(?:\|.+\|[\r\n]*)+)', re.M)
_MD_KV_RE       = re.compile(r'^[-*]\s+\*\*(.+?)\*\*\s*[:\-–]\s*(.+)', re.M)
_MD_CONCEPT_RE  = re.compile(r'^[-*]\s+\[([^\]]+)\]\(([^)]+)\)', re.M)


def parse_markdown(text: str) -> dict[str, Any]:
    """Extract title, description, sections, and key-value pairs from Markdown.

    Handles YAML frontmatter (---...---) which KIK-V indicators use
    to store the human-readable title.
    """
    # 1. YAML frontmatter
    frontmatter: dict[str, str] = {}
    body = text
    fm_match = _MD_FRONTMATTER_RE.match(text)
    if fm_match:
        for m in _MD_FM_KV_RE.finditer(fm_match.group(1)):
            frontmatter[m.group(1).strip()] = m.group(2).strip()
        body = text[fm_match.end():]

    # 2. Title: frontmatter > H1 heading
    title: str | None = frontmatter.get("title") or None
    if not title:
        tm = _MD_TITLE_RE.search(body)
        if tm:
            title = tm.group(1).strip()

    # 3. H2 sections
    sections = [m.group(1).strip() for m in _MD_H2_RE.finditer(body)]

    # 4. Description: prose after first heading, before next heading
    description = ""
    tm2 = _MD_TITLE_RE.search(body)
    search_start = body[tm2.end():] if tm2 else body
    desc_lines = []
    for line in search_start.splitlines():
        if line.startswith('#'):
            break
        stripped = line.strip()
        if stripped and not stripped.startswith('-') and not stripped.startswith('*'):
            desc_lines.append(stripped)
    description = ' '.join(desc_lines[:5])

    # 5. Key-value pairs: **Key**: value
    kv_pairs = {m.group(1).strip(): m.group(2).strip() for m in _MD_KV_RE.finditer(body)}

    # 6. Concept links: - [Label](uri)
    concepts = [{"label": m.group(1), "uri": m.group(2)}
                for m in _MD_CONCEPT_RE.finditer(body)]

    # 7. Tables
    tables = [t.strip() for t in _MD_TABLE_RE.findall(body)]

    return {
        "title":           title,
        "description":     description,
        "frontmatter":     frontmatter,
        "sections":        sections,
        "key_value_pairs": kv_pairs,
        "concepts":        concepts,
        "tables":          tables,
        "raw":             text,
    }


# ---------------------------------------------------------------------------
# Turtle / .ttl parser
# ---------------------------------------------------------------------------

_TTL_PREFIX_RE  = re.compile(r'@prefix\s+(\w*:)\s*<([^>]+)>', re.I)
_TTL_CLASS_RE   = re.compile(r'\ba\s+([\w:]+Class|owl:Class|rdfs:Class)[\s;,.]', re.I)
_TTL_NAMED_RE   = re.compile(r'([\w]+:[\w]+)\s+a\s+', re.I)
_TTL_PROP_RE    = re.compile(r'([\w]+:[\w]+)\s+(?:rdfs:domain|rdfs:range|owl:onProperty)\s+([\w:]+)', re.I)
_TTL_SUBCLASS_RE = re.compile(r'([\w:]+)\s+rdfs:subClassOf\s+([\w:]+)', re.I)


def parse_turtle(text: str) -> dict[str, Any]:
    """Extract prefixes, class references, and property definitions from Turtle."""
    prefixes: dict[str, str] = {}
    for m in _TTL_PREFIX_RE.finditer(text):
        prefixes[m.group(1)] = m.group(2)

    # Named individuals / class usages
    named_resources = list(dict.fromkeys(_TTL_NAMED_RE.findall(text)))

    # Explicit class declarations
    class_decls = list(dict.fromkeys(_TTL_CLASS_RE.findall(text)))

    # Property domain/range triples
    prop_triples = [{"property": m.group(1), "related": m.group(2)} for m in _TTL_PROP_RE.finditer(text)]

    # SubClass relations
    subclass_relations = [{"child": m.group(1), "parent": m.group(2)} for m in _TTL_SUBCLASS_RE.finditer(text)]

    # All prefixed names referenced
    all_refs = list(dict.fromkeys(re.findall(r'\b[\w]+:[\w]+\b', text)))

    return {
        "prefixes": prefixes,
        "named_resources": named_resources,
        "class_declarations": class_decls,
        "property_triples": prop_triples,
        "subclass_relations": subclass_relations,
        "all_references": all_refs,
    }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def parse_file(filename: str, content: str) -> dict[str, Any]:
    """Dispatch to correct parser based on file extension."""
    lower = filename.lower()
    if lower.endswith('.rq') or lower.endswith('.sparql'):
        return {"type": "sparql", "parsed": parse_sparql(content)}
    elif lower.endswith('.md'):
        return {"type": "markdown", "parsed": parse_markdown(content)}
    elif lower.endswith('.ttl'):
        return {"type": "turtle", "parsed": parse_turtle(content)}
    else:
        return {"type": "unknown", "parsed": {}}
