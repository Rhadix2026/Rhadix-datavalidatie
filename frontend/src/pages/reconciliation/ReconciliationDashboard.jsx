/**
 * Rhadix — Reconciliation Engine Dashboard
 */

import React, { useCallback, useRef, useState } from "react";
import { Nav } from "../../components/UI";
import { getAuthToken } from "../../services/api";

const API_BASE = "/api/reconciliation";

function authFetch(url, opts = {}) {
  const token = getAuthToken()
  return fetch(url, {
    ...opts,
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(opts.headers || {}) },
  })
}

const STATUS_CONFIG = {
  OK:      { color: "#22c55e", bg: "#dcfce7", label: "✓ OK",           icon: "🟢" },
  Warning: { color: "#f59e0b", bg: "#fef3c7", label: "⚠ Waarschuwing", icon: "🟡" },
  Error:   { color: "#ef4444", bg: "#fee2e2", label: "✗ Fout",         icon: "🔴" },
  Unknown: { color: "#94a3b8", bg: "#f1f5f9", label: "? Onbekend",     icon: "⚪" },
};

const CATEGORY_LABELS = {
  missing_in_rdf:        "Ontbreekt in RDF",
  extra_in_rdf:          "Extra in RDF",
  wrong_dates:           "Onjuiste datum",
  missing_relationships: "Ontbrekende relatie",
  invalid_codes:         "Ongeldige code",
};

function fmt(v, decimals = 2) {
  if (v === null || v === undefined) return "—";
  return typeof v === "number" ? v.toFixed(decimals) : v;
}

function scoreColor(score) {
  if (score >= 100) return "#22c55e";
  if (score >= 95)  return "#84cc16";
  if (score >= 80)  return "#f59e0b";
  return "#ef4444";
}

// ---------------------------------------------------------------------------
// SPARQL Query Modal
// ---------------------------------------------------------------------------

function SparqlQueryModal({ indicatorId, indicatorName, onClose }) {
  const [query, setQuery] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  React.useEffect(() => {
    if (!indicatorId) return;
    authFetch(`${API_BASE}/indicators/${indicatorId}/sparql-query`)
      .then(r => r.ok ? r.json() : r.json().then(e => Promise.reject(e.detail)))
      .then(data => { setQuery(data); setLoading(false); })
      .catch(err => { setError(String(err)); setLoading(false); });
  }, [indicatorId]);

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,.5)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
    }} onClick={onClose}>
      <div style={{
        background: "#fff", borderRadius: 12, padding: 28,
        maxWidth: 700, width: "90%", maxHeight: "80vh", overflowY: "auto",
      }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 16 }}>📋 SPARQL Query</div>
            <div style={{ fontSize: 13, color: "#64748b", marginTop: 2 }}>{indicatorName}</div>
          </div>
          <button onClick={onClose} style={{ border: "none", background: "none", fontSize: 20, cursor: "pointer", color: "#94a3b8" }}>✕</button>
        </div>

        {loading && <div style={{ color: "#94a3b8", padding: "20px 0" }}>Laden…</div>}
        {error && <div style={{ color: "#ef4444", padding: "12px", background: "#fee2e2", borderRadius: 6 }}>{error}</div>}
        {query && (
          <>
            {query.sparql_endpoint && (
              <div style={{ marginBottom: 12, padding: "8px 12px", background: "#f0f9ff", borderRadius: 6, fontSize: 13 }}>
                <strong>Endpoint:</strong> <code style={{ color: "var(--k-blue-strong)" }}>{query.sparql_endpoint}</code>
              </div>
            )}
            <pre style={{
              background: "#1e293b", color: "#e2e8f0", borderRadius: 8,
              padding: "16px 18px", fontSize: 12, lineHeight: 1.6,
              overflowX: "auto", margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word",
            }}>
              {query.sparql_query}
            </pre>
            <button
              onClick={() => navigator.clipboard?.writeText(query.sparql_query)}
              style={{
                marginTop: 10, padding: "6px 14px", borderRadius: 6,
                border: "1px solid #cbd5e1", background: "#f8fafc",
                cursor: "pointer", fontSize: 12, color: "#475569",
              }}
            >
              📋 Kopieer query
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.Unknown;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "2px 10px", borderRadius: 12,
      backgroundColor: cfg.bg, color: cfg.color,
      fontWeight: 600, fontSize: 13,
    }}>
      {cfg.icon} {cfg.label}
    </span>
  );
}

function ScoreGauge({ score, label }) {
  const color = scoreColor(score);
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{
        width: 80, height: 80, borderRadius: "50%",
        border: `6px solid ${color}`, display: "flex",
        flexDirection: "column", alignItems: "center", justifyContent: "center",
        margin: "0 auto",
      }}>
        <span style={{ fontSize: 20, fontWeight: 700, color }}>{fmt(score, 1)}%</span>
      </div>
      <div style={{ marginTop: 6, fontSize: 12, color: "#64748b" }}>{label}</div>
    </div>
  );
}

function Metric({ label, value, color, sub }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.5 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: color || "#1e293b", marginTop: 2 }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function CalcPreviewCard({ calc, indicatorName, onClose }) {
  if (!calc) return null;
  const rows = calc.included_sample || [];
  const cols = rows.length > 0 ? Object.keys(rows[0]).slice(0, 8) : [];

  return (
    <div style={{
      background: "#f0fdf4", border: "1.5px solid #86efac", borderRadius: 10,
      padding: 20, marginBottom: 20,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15, color: "#15803d" }}>
            📄 Brondata-analyse: {indicatorName}
          </div>
          <div style={{ fontSize: 12, color: "#166534", marginTop: 3 }}>
            Berekend uit het geüploade bestand — nog zonder SPARQL-vergelijking
          </div>
        </div>
        <button onClick={onClose} style={{ border: "none", background: "none", cursor: "pointer", fontSize: 18, color: "#94a3b8" }}>✕</button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
        <div style={{ background: "#fff", borderRadius: 8, padding: "12px 16px", textAlign: "center", border: "1px solid #bbf7d0" }}>
          <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.5 }}>Uitkomst (CSV)</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: "#15803d", marginTop: 4 }}>{calc.expected_value ?? "—"}</div>
        </div>
        <div style={{ background: "#fff", borderRadius: 8, padding: "12px 16px", textAlign: "center", border: "1px solid #bbf7d0" }}>
          <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.5 }}>Meegeteld</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: "#1e293b", marginTop: 4 }}>{calc.record_count}</div>
        </div>
        <div style={{ background: "#fff", borderRadius: 8, padding: "12px 16px", textAlign: "center", border: "1px solid #bbf7d0" }}>
          <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.5 }}>Uitgesloten</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: "#f59e0b", marginTop: 4 }}>{calc.excluded_count}</div>
        </div>
      </div>

      {cols.length > 0 && (
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: "#475569", marginBottom: 8 }}>
            Eerste {Math.min(rows.length, 10)} meegetelde rijen:
          </div>
          <div style={{ overflowX: "auto", borderRadius: 6, border: "1px solid #bbf7d0" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ background: "#dcfce7" }}>
                  {cols.map(c => (
                    <th key={c} style={{ padding: "6px 10px", textAlign: "left", fontWeight: 600, color: "#15803d", whiteSpace: "nowrap" }}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 10).map((row, i) => (
                  <tr key={i} style={{ borderTop: "1px solid #dcfce7", background: i % 2 === 0 ? "#fff" : "#f0fdf4" }}>
                    {cols.map(c => (
                      <td key={c} style={{ padding: "5px 10px", color: "#374151" }}>
                        {row[c] === null || row[c] === undefined
                          ? <em style={{ color: "#94a3b8" }}>null</em>
                          : String(row[c])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {rows.length > 10 && (
            <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 4 }}>Toont 10 van {rows.length} meegetelde rijen</div>
          )}
        </div>
      )}
    </div>
  );
}

function IndicatorCard({ result, onDrillDown }) {
  const { status } = result;
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.Unknown;
  const hasSparql = result.actual_value !== null && result.actual_value !== undefined;

  return (
    <div style={{
      border: `2px solid ${cfg.color}`, borderRadius: 10,
      padding: 16, background: "#fff", boxShadow: "0 1px 4px rgba(0,0,0,.07)",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15 }}>{result.indicator_name}</div>
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{result.indicator_id}</div>
        </div>
        <StatusBadge status={status} />
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: hasSparql ? "1fr 1fr 1fr" : "1fr 1fr",
        gap: 8, marginTop: 14,
        background: "#f8fafc", borderRadius: 8, padding: 12,
      }}>
        <Metric label="Brondata (CSV)" value={fmt(result.expected_value)} color="#15803d" sub="berekend uit bestand" />
        {hasSparql ? (
          <>
            <Metric label="SPARQL-uitkomst" value={fmt(result.actual_value)} color="var(--k-blue-strong)" sub="live query" />
            <Metric
              label="Afwijking"
              value={result.percentage_difference !== null ? `${fmt(result.percentage_difference)}%` : "—"}
              color={cfg.color}
              sub={result.absolute_difference !== null ? `absoluut: ${fmt(result.absolute_difference)}` : undefined}
            />
          </>
        ) : (
          <div style={{ textAlign: "center", display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.5 }}>SPARQL</div>
            <div style={{ fontSize: 13, color: "#94a3b8", marginTop: 4, fontStyle: "italic" }}>Geen endpoint opgegeven</div>
          </div>
        )}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
        <div style={{ fontSize: 12, color: "#475569" }}>
          {hasSparql
            ? <>Confidence: <strong>{fmt(result.confidence_score, 1)}%</strong> &bull; {result.reconciliation_score_label}</>
            : <span style={{ color: "#94a3b8" }}>Voeg een SPARQL-endpoint toe voor vergelijking</span>}
        </div>
        {result.drill_down?.length > 0 && (
          <button onClick={() => onDrillDown(result)} style={{
            padding: "4px 12px", borderRadius: 6, border: "1px solid #cbd5e1",
            background: "#f8fafc", cursor: "pointer", fontSize: 12,
          }}>
            🔍 Drill-down ({result.drill_down.length})
          </button>
        )}
      </div>
    </div>
  );
}

function DrillDownModal({ result, onClose }) {
  if (!result) return null;
  const categories = {};
  (result.drill_down || []).forEach(item => {
    const cat = item.category || "other";
    if (!categories[cat]) categories[cat] = [];
    categories[cat].push(item);
  });

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,.45)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
    }} onClick={onClose}>
      <div style={{
        background: "#fff", borderRadius: 12, padding: 28,
        maxWidth: 760, width: "90%", maxHeight: "80vh", overflowY: "auto",
      }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>Drill-down: {result.indicator_name}</h3>
          <button onClick={onClose} style={{ border: "none", background: "none", fontSize: 20, cursor: "pointer" }}>✕</button>
        </div>
        {Object.entries(categories).map(([cat, items]) => (
          <div key={cat} style={{ marginBottom: 20 }}>
            <div style={{ fontWeight: 600, marginBottom: 8, color: "#475569" }}>
              {CATEGORY_LABELS[cat] || cat} ({items.length})
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ background: "#f1f5f9" }}>
                    {Object.keys(items[0]?.record || {}).slice(0, 8).map(k => (
                      <th key={k} style={{ padding: "6px 8px", textAlign: "left", borderBottom: "1px solid #e2e8f0" }}>{k}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {items.slice(0, 50).map((item, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid #f1f5f9" }}>
                      {Object.values(item.record || {}).slice(0, 8).map((v, j) => (
                        <td key={j} style={{ padding: "5px 8px", color: "#374151" }}>
                          {v === null || v === undefined ? <em style={{ color: "#94a3b8" }}>null</em> : String(v)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {items.length > 50 && <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 4 }}>Toont 50 van {items.length} records</div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SPARQL Indicator Picker (used inside UploadForm)
// ---------------------------------------------------------------------------

function SparqlPicker({ selectedQuery, onSelect }) {
  const [domains, setDomains]           = useState([]);
  const [selectedDomain, setSelectedDomain] = useState("");
  const [domainIndicators, setDomainIndicators] = useState([]);
  const [loadingDomain, setLoadingDomain] = useState(false);
  const [previewQuery, setPreviewQuery]  = useState(null);
  const [filterText, setFilterText]      = useState("");

  React.useEffect(() => {
    authFetch("/api/profiles/")
      .then(r => r.json())
      .then(data => setDomains(Array.isArray(data) ? data : []))
      .catch(console.error);
  }, []);

  async function handleDomainChange(filename) {
    setSelectedDomain(filename);
    setDomainIndicators([]);
    setFilterText("");
    if (!filename) return;
    setLoadingDomain(true);
    try {
      const r = await authFetch(`/api/profiles/${filename}`);
      const data = await r.json();
      // indicators kan een dict zijn {"1.1.1": {id, files, metadata}} of een lijst
      const raw = data.indicators || {};
      let inds;
      if (Array.isArray(raw)) {
        // Lijst-formaat: normaliseer sparql_query veld
        inds = raw
          .map(i => ({
            id: i.id || i.indicator_id,
            title: i.title || i.metadata?.title || i.id,
            sparql_query: i.sparql_query || i.files?.sparql?.raw || null,
          }))
          .filter(i => i.sparql_query);
      } else {
        // Dict-formaat: {"1.1.1": {id, files, metadata}}
        inds = Object.entries(raw)
          .filter(([k]) => k !== '-INDEX')
          .map(([k, v]) => ({
            id: k,
            title: v.metadata?.title || k,
            sparql_query: v.files?.sparql?.raw || null,
          }))
          .filter(i => i.sparql_query);
      }
      setDomainIndicators(inds);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingDomain(false);
    }
  }

  const filtered = filterText
    ? domainIndicators.filter(i =>
        (i.title || i.id || "").toLowerCase().includes(filterText.toLowerCase()) ||
        (i.id || "").toLowerCase().includes(filterText.toLowerCase()))
    : domainIndicators;

  return (
    <div>
      {/* Domein dropdown */}
      <div style={{ marginBottom: 10 }}>
        <label style={labelStyle}>Domein</label>
        <select
          value={selectedDomain}
          onChange={e => handleDomainChange(e.target.value)}
          style={inputStyle}
        >
          <option value="">-- Kies domein --</option>
          {domains.map(d => (
            <option key={d.filename} value={d.filename}>
              {d.name || d.filename} ({d.indicator_count} indicatoren)
            </option>
          ))}
        </select>
      </div>

      {/* Huidige selectie badge */}
      {selectedQuery && (
        <div style={{
          marginBottom: 10, padding: "8px 12px", borderRadius: 6,
          background: "var(--k-blue-light)", border: "1px solid var(--k-blue-mid)",
          display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8,
        }}>
          <div style={{ fontSize: 12, color: "var(--k-blue-strong)", fontWeight: 600 }}>
            ✓ SPARQL-query geselecteerd ({selectedQuery.id})
          </div>
          <button
            type="button"
            onClick={() => onSelect(null)}
            style={{ fontSize: 11, padding: "2px 8px", borderRadius: 4,
              border: "1px solid var(--k-blue-mid)", background: "transparent",
              color: "var(--k-blue-strong)", cursor: "pointer" }}
          >
            Verwijder
          </button>
        </div>
      )}

      {/* Indicator tabel */}
      {selectedDomain && (
        <div style={{
          border: "1px solid #e2e8f0", borderRadius: 8, overflow: "hidden",
          marginTop: 4,
        }}>
          {/* Tabel header */}
          <div style={{
            background: "#f1f5f9", padding: "8px 12px",
            display: "flex", justifyContent: "space-between", alignItems: "center",
            borderBottom: "1px solid #e2e8f0",
          }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: "#475569" }}>
              {loadingDomain ? "Laden…" : `${domainIndicators.length} SPARQL-indicatoren`}
            </span>
            {domainIndicators.length > 5 && (
              <input
                type="text"
                placeholder="Zoek indicator…"
                value={filterText}
                onChange={e => setFilterText(e.target.value)}
                style={{
                  padding: "4px 10px", borderRadius: 6, border: "1px solid #cbd5e1",
                  fontSize: 12, width: 180,
                }}
              />
            )}
          </div>

          {loadingDomain && (
            <div style={{ padding: "20px", textAlign: "center", color: "#94a3b8", fontSize: 13 }}>
              Laden…
            </div>
          )}

          {!loadingDomain && domainIndicators.length === 0 && selectedDomain && (
            <div style={{ padding: "20px", textAlign: "center", color: "#94a3b8", fontSize: 13 }}>
              Geen indicatoren met SPARQL-query gevonden in dit domein.
            </div>
          )}

          {!loadingDomain && filtered.length > 0 && (
            <div style={{ maxHeight: 260, overflowY: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#f8fafc", position: "sticky", top: 0 }}>
                    <th style={thStyle}>Indicator ID</th>
                    <th style={thStyle}>Titel</th>
                    <th style={{ ...thStyle, textAlign: "center" }}>SPARQL</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((ind, i) => {
                    const isSelected = selectedQuery?.id === ind.id;
                    return (
                      <tr key={ind.id || i} style={{
                        borderTop: "1px solid #f1f5f9",
                        background: isSelected ? "var(--k-blue-light)" : (i % 2 === 0 ? "#fff" : "#fafafa"),
                      }}>
                        <td style={{ ...tdStyle, fontFamily: "monospace", fontSize: 11, color: "#64748b" }}>
                          {ind.id || "—"}
                        </td>
                        <td style={{ ...tdStyle, fontWeight: isSelected ? 600 : 400, color: isSelected ? "var(--k-blue-strong)" : "#1e293b" }}>
                          {ind.title || ind.id || "—"}
                        </td>
                        <td style={{ ...tdStyle, textAlign: "center" }}>
                          <div style={{ display: "flex", gap: 4, justifyContent: "center" }}>
                            <button
                              type="button"
                              onClick={() => setPreviewQuery(previewQuery?.id === ind.id ? null : ind)}
                              style={{
                                padding: "3px 8px", borderRadius: 4, fontSize: 11,
                                border: "1px solid #cbd5e1", cursor: "pointer",
                                background: previewQuery?.id === ind.id ? "#1e293b" : "#f8fafc",
                                color: previewQuery?.id === ind.id ? "#e2e8f0" : "#475569",
                              }}
                            >
                              👁 Bekijk
                            </button>
                            <button
                              type="button"
                              onClick={() => { onSelect(ind); setPreviewQuery(null); }}
                              style={{
                                padding: "3px 10px", borderRadius: 4, fontSize: 11,
                                border: isSelected ? "1px solid var(--k-blue)" : "1px solid #cbd5e1",
                                cursor: "pointer",
                                background: isSelected ? "var(--k-blue)" : "#fff",
                                color: isSelected ? "#fff" : "#374151",
                                fontWeight: isSelected ? 600 : 400,
                              }}
                            >
                              {isSelected ? "✓ Geselecteerd" : "Gebruik"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* SPARQL preview inline */}
          {previewQuery && (
            <div style={{ borderTop: "1px solid #e2e8f0" }}>
              <div style={{
                background: "#1e293b", padding: "8px 14px",
                display: "flex", justifyContent: "space-between", alignItems: "center",
              }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8" }}>
                  📋 {previewQuery.title || previewQuery.id}
                </span>
                <div style={{ display: "flex", gap: 6 }}>
                  <button type="button"
                    onClick={() => navigator.clipboard?.writeText(previewQuery.sparql_query)}
                    style={{ fontSize: 11, padding: "2px 8px", borderRadius: 4,
                      border: "1px solid #475569", background: "transparent",
                      color: "#94a3b8", cursor: "pointer" }}>
                    Kopieer
                  </button>
                  <button type="button" onClick={() => setPreviewQuery(null)}
                    style={{ fontSize: 14, border: "none", background: "none",
                      color: "#64748b", cursor: "pointer", lineHeight: 1 }}>
                    ✕
                  </button>
                </div>
              </div>
              <pre style={{
                background: "#0f172a", color: "#e2e8f0", margin: 0,
                padding: "12px 16px", fontSize: 11, lineHeight: 1.6,
                overflowX: "auto", whiteSpace: "pre-wrap", wordBreak: "break-word",
                maxHeight: 200, overflowY: "auto",
              }}>
                {previewQuery.sparql_query}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const thStyle = { padding: "6px 12px", textAlign: "left", fontWeight: 600, fontSize: 12, color: "#64748b", borderBottom: "1px solid #e2e8f0" };
const tdStyle = { padding: "7px 12px" };

// ---------------------------------------------------------------------------
// Upload form
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// SPARQL loslaten op de data — kolom→concept mapping + triple store
// ---------------------------------------------------------------------------

const TYPE_OPTIONS = [
  { v: "string",   label: "Tekst" },
  { v: "date",     label: "Datum" },
  { v: "decimal",  label: "Getal" },
  { v: "integer",  label: "Geheel getal" },
  { v: "boolean",  label: "Ja/nee" },
  { v: "resource", label: "Verwijzing (URI)" },
];

function SparqlOnDataPanel({ fileRef, fileName, sparqlQuery, sparqlLabel, calcRuleId }) {
  const [concepts, setConcepts]   = useState({ classes: [], properties: [] });
  const [columns, setColumns]     = useState([]);
  const [sampleRows, setSample]   = useState([]);
  const [mapping, setMapping]     = useState({});   // col -> {concept_uri, type}
  const [classUri, setClassUri]   = useState("");
  const [idField, setIdField]     = useState("");
  const [loadingCols, setLoadCols] = useState(false);
  const [running, setRunning]     = useState(false);
  const [result, setResult]       = useState(null);
  const [error, setError]         = useState(null);
  const [open, setOpen]           = useState(false);

  React.useEffect(() => {
    authFetch(`${API_BASE}/concepts`)
      .then(r => r.ok ? r.json() : Promise.reject("kon concepten niet laden"))
      .then(setConcepts)
      .catch(() => {});
  }, []);

  async function loadColumns() {
    const file = fileRef.current?.files?.[0];
    if (!file) { alert("Kies eerst een bronbestand."); return; }
    setLoadCols(true); setError(null); setResult(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const resp = await authFetch(`${API_BASE}/preview-columns`, { method: "POST", body: fd });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      setColumns(data.columns || []);
      setSample(data.sample_rows || []);
      // prefill mapping uit server-suggesties
      const sug = data.suggested_mapping || {};
      const m = {};
      (data.columns || []).forEach(col => {
        if (sug[col]) {
          const s = sug[col];
          m[col] = { concept_uri: s.concept_uri, type: s.kind === "resource" ? "resource" : (s.datatype || "string") };
        } else {
          m[col] = { concept_uri: "", type: "string" };
        }
      });
      setMapping(m);
      // raad ID-kolom
      const guess = (data.columns || []).find(c => /(^|_)id$|nummer$/i.test(c)) || (data.columns || [])[0] || "";
      setIdField(guess);
      setOpen(true);
    } catch (err) {
      setError("Kon kolommen niet lezen: " + err.message);
    } finally {
      setLoadCols(false);
    }
  }

  function setColMap(col, patch) {
    setMapping(prev => ({ ...prev, [col]: { ...prev[col], ...patch } }));
  }

  async function run() {
    const file = fileRef.current?.files?.[0];
    if (!file)        { alert("Kies eerst een bronbestand."); return; }
    if (!sparqlQuery) { alert("Selecteer eerst een SPARQL-query uit het uitwisselprofiel."); return; }
    // bouw mapping-payload: alleen kolommen met concept
    const payload = {};
    Object.entries(mapping).forEach(([col, cfg]) => {
      if (cfg.concept_uri) {
        payload[col] = {
          concept_uri: cfg.concept_uri,
          kind: cfg.type === "resource" ? "resource" : "literal",
          datatype: cfg.type === "resource" ? "string" : cfg.type,
        };
      }
    });
    if (Object.keys(payload).length === 0) {
      alert("Koppel minstens één kolom aan een concept."); return;
    }
    setRunning(true); setError(null); setResult(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("sparql_query", sparqlQuery);
      fd.append("mapping", JSON.stringify(payload));
      if (classUri) fd.append("class_uri", classUri);
      if (idField)  fd.append("id_field", idField);
      if (calcRuleId) fd.append("indicator_id", calcRuleId);
      const resp = await authFetch(`${API_BASE}/sparql-reconcile`, { method: "POST", body: fd });
      if (!resp.ok) throw new Error(await resp.text());
      setResult(await resp.json());
    } catch (err) {
      setError("Fout bij uitvoeren: " + err.message);
    } finally {
      setRunning(false);
    }
  }

  const sectionStyle = { background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, padding: 16, marginBottom: 16 };
  const small = { fontSize: 12, fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 12 };

  return (
    <div style={{ ...sectionStyle, borderColor: "#c7d2fe", background: "#f5f7ff" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ ...small, marginBottom: 0, color: "#4338ca" }}>
          🧩 SPARQL loslaten op de data (triple store)
        </div>
        <button type="button" onClick={loadColumns} disabled={loadingCols || !fileName}
          style={{ padding: "6px 14px", borderRadius: 6, background: "#fff", color: "#4338ca",
                   border: "1.5px solid #c7d2fe", fontWeight: 600, fontSize: 13,
                   cursor: (!fileName || loadingCols) ? "not-allowed" : "pointer", opacity: !fileName ? 0.5 : 1 }}>
          {loadingCols ? "Bezig…" : "1 · Laad kolommen uit bestand"}
        </button>
      </div>

      <div style={{ fontSize: 12, color: "#64748b", marginTop: 6 }}>
        Koppel elke kolom aan een KIK-V-concept. De brondata wordt omgezet naar RDF-triples,
        in de triple store geladen en de geselecteerde SPARQL-query wordt erop uitgevoerd.
        {sparqlLabel
          ? <span> Geselecteerde query: <strong>{sparqlLabel}</strong>.</span>
          : <span style={{ color: "#b45309" }}> Selecteer eerst een SPARQL-query hierboven.</span>}
      </div>

      {open && columns.length > 0 && (
        <div style={{ marginTop: 14 }}>
          {/* record-class + id-kolom */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
            <div>
              <label style={labelStyle}>Record-type (rdf:type per rij)</label>
              <select value={classUri} onChange={e => setClassUri(e.target.value)} style={inputStyle}>
                <option value="">-- geen / kies class --</option>
                {concepts.classes.map(c => (
                  <option key={c.uri} value={c.uri}>
                    {c.common ? "★ " : ""}{c.label}{c.module ? ` (${c.module})` : ""}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label style={labelStyle}>ID-kolom (bepaalt de node-URI)</label>
              <select value={idField} onChange={e => setIdField(e.target.value)} style={inputStyle}>
                <option value="">-- rij-index --</option>
                {columns.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>

          {/* mapping-tabel */}
          <div style={{ border: "1px solid #e2e8f0", borderRadius: 8, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "var(--k-blue-light)", textAlign: "left" }}>
                  <th style={{ padding: "8px 10px" }}>Kolom</th>
                  <th style={{ padding: "8px 10px" }}>Voorbeeld</th>
                  <th style={{ padding: "8px 10px" }}>Concept (predicaat)</th>
                  <th style={{ padding: "8px 10px", width: 150 }}>Type</th>
                </tr>
              </thead>
              <tbody>
                {columns.map(col => {
                  const ex = sampleRows[0] ? String(sampleRows[0][col] ?? "") : "";
                  const cfg = mapping[col] || { concept_uri: "", type: "string" };
                  return (
                    <tr key={col} style={{ borderTop: "1px solid #e2e8f0" }}>
                      <td style={{ padding: "6px 10px", fontWeight: 600 }}>{col}</td>
                      <td style={{ padding: "6px 10px", color: "#94a3b8", maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{ex}</td>
                      <td style={{ padding: "6px 10px" }}>
                        <select value={cfg.concept_uri} onChange={e => setColMap(col, { concept_uri: e.target.value })}
                          style={{ ...inputStyle, padding: "5px 8px" }}>
                          <option value="">— negeer kolom —</option>
                          {concepts.properties.map(p => (
                            <option key={p.uri} value={p.uri}>
                              {p.kikv ? "★ " : ""}{p.label}{p.module ? ` (${p.module})` : ""}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td style={{ padding: "6px 10px" }}>
                        <select value={cfg.type} onChange={e => setColMap(col, { type: e.target.value })}
                          style={{ ...inputStyle, padding: "5px 8px" }}>
                          {TYPE_OPTIONS.map(t => <option key={t.v} value={t.v}>{t.label}</option>)}
                        </select>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <button type="button" onClick={run} disabled={running || !sparqlQuery}
            style={{ marginTop: 14, padding: "10px 22px", borderRadius: 8, background: "#4338ca", color: "#fff",
                     border: "none", fontWeight: 600, fontSize: 14,
                     cursor: (running || !sparqlQuery) ? "not-allowed" : "pointer", opacity: !sparqlQuery ? 0.5 : 1 }}>
            {running ? "Triples bouwen & query draaien…" : "2 · ▶ Genereer triples & draai SPARQL"}
          </button>
        </div>
      )}

      {error && <div style={{ marginTop: 12, color: "#b91c1c", fontSize: 13 }}>{error}</div>}

      {result && <SparqlOnDataResult result={result} />}
    </div>
  );
}

function SparqlOnDataResult({ result }) {
  const sr = result.sparql_result || {};
  const recon = result.reconciliation;
  const calc = result.calculation;
  const backendBadge = sr.backend === "fuseki"
    ? { label: "Fuseki", color: "#0e7490", bg: "#cffafe" }
    : { label: "rdflib (in-memory)", color: "#7c3aed", bg: "#ede9fe" };

  return (
    <div style={{ marginTop: 16, background: "#fff", border: "1px solid #c7d2fe", borderRadius: 8, padding: 16 }}>
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 12 }}>
        <strong style={{ color: "#3730a3" }}>SPARQL-resultaat</strong>
        <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 999, color: backendBadge.color, background: backendBadge.bg }}>
          {backendBadge.label}
        </span>
        <span style={{ fontSize: 12, color: "#64748b" }}>{sr.triple_count} triples · {result.row_count} rijen</span>
        {sr.fuseki_error && <span style={{ fontSize: 11, color: "#b45309" }}>Fuseki niet bereikbaar — fallback gebruikt</span>}
      </div>

      {sr.query_error
        ? <div style={{ color: "#b91c1c", fontSize: 13 }}>Query-fout: {sr.query_error}</div>
        : (sr.rows && sr.rows.length > 0
          ? (
            <table style={{ borderCollapse: "collapse", fontSize: 13, marginBottom: 8 }}>
              <thead><tr style={{ background: "#f1f5f9" }}>
                {sr.columns.map(c => <th key={c} style={{ padding: "6px 12px", textAlign: "left" }}>{c}</th>)}
              </tr></thead>
              <tbody>
                {sr.rows.slice(0, 20).map((row, i) => (
                  <tr key={i} style={{ borderTop: "1px solid #e2e8f0" }}>
                    {sr.columns.map(c => <td key={c} style={{ padding: "6px 12px" }}>{String(row[c] ?? "")}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          )
          : <div style={{ color: "#64748b", fontSize: 13 }}>Query gaf geen resultaten. Controleer de kolom→concept mapping en het record-type.</div>
        )}

      {recon && calc && (
        <div style={{ marginTop: 12, borderTop: "1px solid #e2e8f0", paddingTop: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#64748b", textTransform: "uppercase", marginBottom: 8 }}>
            Vergelijking met berekeningsregel
          </div>
          <div style={{ display: "flex", gap: 18, flexWrap: "wrap", alignItems: "center" }}>
            <Metric label="CSV-uitkomst" value={fmt(calc.expected_value)} color="#0891b2" />
            <Metric label="SPARQL-uitkomst" value={fmt(sr.scalar)} color="#4338ca" />
            <Metric label="Verschil" value={fmt(recon.absolute_difference)} color="#64748b" />
            <StatusBadge status={recon.status} />
            <span style={{ fontSize: 13, color: "#64748b" }}>Score: <strong style={{ color: scoreColor(recon.confidence_score) }}>{fmt(recon.confidence_score)}</strong></span>
          </div>
        </div>
      )}
    </div>
  );
}

function UploadForm({ indicators, onResult, onCalcPreview, loading, setLoading }) {
  const [selectedIndicator, setSelectedIndicator] = useState("");
  const [selectedSparqlInd, setSelectedSparqlInd] = useState(null);
  const [actualValue, setActualValue]             = useState("");
  const [fileName, setFileName]                   = useState("");
  const fileRef = useRef();

  const canPreview    = selectedIndicator && fileName;
  const canReconcile  = selectedIndicator && fileName;

  const selectedInd = indicators.find(i => i.indicator_id === selectedIndicator);

  async function handlePreview(e) {
    e.preventDefault();
    if (!selectedIndicator || !fileRef.current?.files[0]) return;
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("file", fileRef.current.files[0]);
      const resp = await authFetch(`${API_BASE}/calculate/${selectedIndicator}`, { method: "POST", body: fd });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      onCalcPreview(data, selectedInd?.name || selectedIndicator);
    } catch (err) {
      alert("Fout bij brondata-analyse: " + err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleReconcile(e) {
    e.preventDefault();
    if (!selectedIndicator || !fileRef.current?.files[0]) return;
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("file", fileRef.current.files[0]);
      if (actualValue)                  fd.append("actual_value", actualValue);
      if (selectedSparqlInd?.sparql_query) fd.append("sparql_query", selectedSparqlInd.sparql_query);
      const resp = await authFetch(`${API_BASE}/reconcile/${selectedIndicator}`, { method: "POST", body: fd });
      if (!resp.ok) throw new Error(await resp.text());
      onResult(await resp.json());
    } catch (err) {
      alert("Fout: " + err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form style={{
      background: "#f8fafc", border: "1px solid #e2e8f0",
      borderRadius: 10, padding: 20, marginBottom: 24,
    }}>
      <h3 style={{ margin: "0 0 18px" }}>Nieuwe reconciliatie starten</h3>

      {/* ── Sectie 1: Domein + SPARQL-query ─────────────────────────── */}
      <div style={{
        background: "#fff", border: "1px solid #e2e8f0",
        borderRadius: 8, padding: 16, marginBottom: 16,
      }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 12 }}>
          📡 Referentie (SPARQL uit uitwisselprofiel)
        </div>
        <SparqlPicker selectedQuery={selectedSparqlInd} onSelect={setSelectedSparqlInd} />
        {!selectedSparqlInd && (
          <div style={{ marginTop: 10 }}>
            <label style={labelStyle}>Of voer werkelijke waarde handmatig in</label>
            <input type="number" step="any" value={actualValue} onChange={e => setActualValue(e.target.value)}
              placeholder="bijv. 142" style={{ ...inputStyle, maxWidth: 200 }} />
          </div>
        )}
        {selectedSparqlInd && (
          <div style={{ marginTop: 10 }}>
            <label style={labelStyle}>Werkelijke waarde (optioneel — overschrijft SPARQL-uitkomst)</label>
            <input type="number" step="any" value={actualValue} onChange={e => setActualValue(e.target.value)}
              placeholder="bijv. 142" style={{ ...inputStyle, maxWidth: 200 }} />
          </div>
        )}
      </div>

      {/* ── Sectie 2: Bronbestand + berekeningsregel ─────────────────── */}
      <div style={{
        background: "#fff", border: "1px solid #e2e8f0",
        borderRadius: 8, padding: 16, marginBottom: 16,
        display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, alignItems: "start",
      }}>
        <div style={{ gridColumn: "1 / -1", fontSize: 12, fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5 }}>
          📄 Brondata (CSV/Excel)
        </div>

        {/* Bestand */}
        <div>
          <label style={labelStyle}>Kies bestand</label>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <label style={{
              padding: "8px 14px", borderRadius: 6, border: "1px solid #cbd5e1",
              background: "#f8fafc", cursor: "pointer", fontSize: 13, fontWeight: 500, whiteSpace: "nowrap",
            }}>
              Bladeren…
              <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls,.xml,.json" style={{ display: "none" }}
                onChange={e => setFileName(e.target.files[0]?.name || "")} />
            </label>
            <span style={{ fontSize: 12, color: "#64748b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {fileName || "Geen bestand gekozen"}
            </span>
          </div>
        </div>

        {/* Berekeningsregel */}
        <div>
          <label style={labelStyle}>Berekeningsregel</label>
          <select value={selectedIndicator} onChange={e => setSelectedIndicator(e.target.value)}
            style={inputStyle}>
            <option value="">-- Kies regel --</option>
            {indicators.map(ind => (
              <option key={ind.indicator_id} value={ind.indicator_id}>
                {ind.name}
              </option>
            ))}
          </select>
          <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 3 }}>
            Bepaalt hoe de brondata berekend wordt (aggregatie + filters)
          </div>
        </div>
      </div>

      {/* ── Actieknoppen ─────────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <button type="button" onClick={handlePreview}
          disabled={loading || !canPreview}
          style={{
            padding: "10px 20px", borderRadius: 8, background: "#fff", color: "#15803d",
            border: "1.5px solid #86efac", fontWeight: 600, fontSize: 14,
            cursor: (!canPreview || loading) ? "not-allowed" : "pointer",
            opacity: !canPreview ? 0.5 : 1,
          }}>
          {loading ? "Bezig…" : "📄 Bekijk brondata"}
        </button>
        <button type="button" onClick={handleReconcile}
          disabled={loading || !canReconcile}
          style={{
            padding: "10px 24px", borderRadius: 8, background: "var(--k-blue)", color: "#fff",
            border: "none", fontWeight: 600, fontSize: 14,
            cursor: (!canReconcile || loading) ? "not-allowed" : "pointer",
            opacity: !canReconcile ? 0.5 : 1,
          }}>
          {loading ? "Bezig…" : "▶ Reconcilieer"}
        </button>
      </div>

      {/* ── SPARQL loslaten op de data (triple store) ─────────────────── */}
      <SparqlOnDataPanel
        fileRef={fileRef}
        fileName={fileName}
        sparqlQuery={selectedSparqlInd?.sparql_query}
        sparqlLabel={selectedSparqlInd?.title || selectedSparqlInd?.id}
        calcRuleId={selectedIndicator}
      />
    </form>
  );
}

const labelStyle = { fontSize: 13, fontWeight: 600, display: "block", marginBottom: 4 };
const inputStyle = { width: "100%", padding: "8px 10px", borderRadius: 6, border: "1px solid #cbd5e1", boxSizing: "border-box" };

// ---------------------------------------------------------------------------
// Export helpers
// ---------------------------------------------------------------------------

function exportCSV(results) {
  const header = ["indicator_id","naam","brondata","sparql","abs_diff","pct_diff","status","confidence","label"];
  const rows = results.map(r => [
    r.indicator_id, r.indicator_name, r.expected_value ?? "",
    r.actual_value ?? "", r.absolute_difference ?? "",
    r.percentage_difference ?? "", r.status, r.confidence_score, r.reconciliation_score_label,
  ]);
  const csv = [header, ...rows].map(r => r.join(";")).join("\n");
  Object.assign(document.createElement("a"), {
    href: URL.createObjectURL(new Blob([csv], { type: "text/csv" })),
    download: "reconciliation.csv",
  }).click();
}

function exportJSON(results) {
  Object.assign(document.createElement("a"), {
    href: URL.createObjectURL(new Blob([JSON.stringify(results, null, 2)], { type: "application/json" })),
    download: "reconciliation.json",
  }).click();
}

// ---------------------------------------------------------------------------
// Main Dashboard
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Happy Flow Tab
// ---------------------------------------------------------------------------

const DATASET_LABELS = {
  // ── ONS / AFAS CSV-formaten ──────────────────────────────────────────────
  "medewerker_ons.csv":             { label: "Medewerkers ONS",              icon: "👤", color: "var(--k-blue)" },
  "medewerker_afas_hrm.csv":        { label: "Medewerkers AFAS HRM",         icon: "👤", color: "#6366f1" },
  "werkovereenkomst_ons.csv":       { label: "Werkovereenkomsten ONS",        icon: "📋", color: "#0891b2" },
  "werkovereenkomst_afas_hrm.csv":  { label: "Werkovereenkomsten AFAS HRM",   icon: "📋", color: "#0e7490" },
  "client_ons.csv":                 { label: "Cliënten ONS",                  icon: "🏥", color: "#16a34a" },
  "verzuim_ons.csv":                { label: "Verzuim ONS",                   icon: "🤒", color: "#dc2626" },
  "verzuim_afas_hrm.csv":           { label: "Verzuim AFAS HRM",              icon: "🤒", color: "#b91c1c" },
  "financieleboeking_afas_fin.csv": { label: "Financiële boekingen AFAS",     icon: "💶", color: "#d97706" },
  "grootboekrubriek_afas_fin.csv":  { label: "Grootboekrubrieken AFAS",       icon: "📊", color: "#b45309" },
  "vestiging_ons.csv":              { label: "Vestigingen ONS",               icon: "🏢", color: "#7c3aed" },
  "wlzkostenplaats_afas_fin.csv":   { label: "WLZ-kostenplaatsen AFAS",       icon: "💰", color: "#a16207" },
  "functie_ons.csv":                { label: "Functies ONS",                  icon: "🎓", color: "#0369a1" },
  // ── AFAS Profit GET-connector XML-formaten ───────────────────────────────
  "Profit_Employees_150_voorbeeld.xml":       { label: "Profit Employees (XML)",        icon: "👤", color: "#7c3aed" },
  "Profit_Employees_basic_150_voorbeeld.xml": { label: "Profit Employees Basic (XML)",  icon: "👤", color: "#6d28d9" },
  "Profit_Illness_150_voorbeeld.xml":         { label: "Profit Illness / Verzuim (XML)", icon: "🤒", color: "#dc2626" },
  "Profit_Timetable_150_voorbeeld.xml":       { label: "Profit Timetable (XML)",        icon: "📋", color: "#0891b2" },
};

function SparqlViewModal({ indicator, sparqls, onClose }) {
  const [selected, setSelected] = React.useState(null);
  const sparqlList = Object.values(sparqls || {});

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,.5)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
    }} onClick={onClose}>
      <div style={{
        background: "#fff", borderRadius: 12, padding: 24,
        maxWidth: 760, width: "92%", maxHeight: "85vh", overflowY: "auto",
      }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 16 }}>📡 Koppel SPARQL-indicator</div>
            <div style={{ fontSize: 13, color: "#64748b", marginTop: 2 }}>{indicator?.indicator_name}</div>
          </div>
          <button onClick={onClose} style={{ border: "none", background: "none", fontSize: 20, cursor: "pointer", color: "#94a3b8" }}>✕</button>
        </div>

        {sparqlList.length === 0 && (
          <div style={{ padding: "20px", textAlign: "center", color: "#94a3b8" }}>
            Geen profiel geselecteerd of geen SPARQL-queries beschikbaar.
            <br />
            <span style={{ fontSize: 12, marginTop: 6, display: "block" }}>
              Selecteer eerst een uitwisselprofiel in het formulier hierboven.
            </span>
          </div>
        )}

        {sparqlList.length > 0 && (
          <div style={{ maxHeight: 420, overflowY: "auto", border: "1px solid #e2e8f0", borderRadius: 8 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f8fafc", position: "sticky", top: 0 }}>
                  <th style={thStyle}>ID</th>
                  <th style={thStyle}>Titel</th>
                  <th style={{ ...thStyle, textAlign: "center" }}>Actie</th>
                </tr>
              </thead>
              <tbody>
                {sparqlList.map((s, i) => (
                  <tr key={s.id} style={{
                    borderTop: "1px solid #f1f5f9",
                    background: selected?.id === s.id ? "var(--k-blue-light)" : (i % 2 === 0 ? "#fff" : "#fafafa"),
                  }}>
                    <td style={{ ...tdStyle, fontFamily: "monospace", fontSize: 11, color: "#64748b" }}>{s.id}</td>
                    <td style={{ ...tdStyle, color: selected?.id === s.id ? "var(--k-blue-strong)" : "#1e293b", fontWeight: selected?.id === s.id ? 600 : 400 }}>
                      {s.title}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "center" }}>
                      <button
                        onClick={() => setSelected(selected?.id === s.id ? null : s)}
                        style={{
                          padding: "3px 10px", borderRadius: 4, fontSize: 11, cursor: "pointer",
                          border: selected?.id === s.id ? "1px solid var(--k-blue)" : "1px solid #cbd5e1",
                          background: selected?.id === s.id ? "var(--k-blue)" : "#fff",
                          color: selected?.id === s.id ? "#fff" : "#374151",
                        }}
                      >
                        {selected?.id === s.id ? "✓ Geselecteerd" : "Bekijk"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {selected && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#475569", marginBottom: 6 }}>
              📋 SPARQL query: {selected.title}
            </div>
            <pre style={{
              background: "#1e293b", color: "#e2e8f0", borderRadius: 8,
              padding: "14px 16px", fontSize: 11, lineHeight: 1.6,
              overflowX: "auto", margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word",
              maxHeight: 250, overflowY: "auto",
            }}>
              {selected.sparql_query}
            </pre>
            <button
              onClick={() => navigator.clipboard?.writeText(selected.sparql_query)}
              style={{ marginTop: 8, padding: "5px 12px", borderRadius: 6, border: "1px solid #cbd5e1", background: "#f8fafc", cursor: "pointer", fontSize: 12, color: "#475569" }}
            >
              📋 Kopieer query
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function HappyFlowResultCard({ result, sparqls, onViewSparql }) {
  const ds = result.source_dataset || "";
  const dsInfo = DATASET_LABELS[ds] || { label: ds, icon: "📄", color: "#64748b" };
  const hasError = result.metadata?.error;

  return (
    <div style={{
      background: "#fff", border: "1px solid #e2e8f0", borderRadius: 10,
      padding: "14px 16px", boxShadow: "0 1px 3px rgba(0,0,0,.06)",
      borderLeft: `4px solid ${hasError ? "#ef4444" : dsInfo.color}`,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 14, color: "#1e293b" }}>{result.indicator_name}</div>
          <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2, fontFamily: "monospace" }}>{result.indicator_id}</div>
        </div>
        <div style={{
          padding: "3px 10px", borderRadius: 12, fontSize: 12, fontWeight: 600, flexShrink: 0, marginLeft: 10,
          background: hasError ? "#fee2e2" : "#f0f9ff",
          color: hasError ? "#dc2626" : dsInfo.color,
        }}>
          {dsInfo.icon} {dsInfo.label}
        </div>
      </div>

      {hasError ? (
        <div style={{ fontSize: 12, color: "#ef4444", padding: "6px 10px", background: "#fee2e2", borderRadius: 6 }}>
          ⚠ Fout: {result.metadata.error}
        </div>
      ) : (
        <div style={{
          display: "grid", gridTemplateColumns: "1fr 1fr 1fr auto",
          gap: 10, alignItems: "center",
          background: "#f8fafc", borderRadius: 8, padding: "10px 14px",
        }}>
          <div>
            <div style={{ fontSize: 10, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.5 }}>Uitkomst (CSV)</div>
            <div style={{ fontSize: 22, fontWeight: 800, color: dsInfo.color, marginTop: 2 }}>
              {result.expected_value !== null && result.expected_value !== undefined
                ? (typeof result.expected_value === "number" && !Number.isInteger(result.expected_value)
                  ? result.expected_value.toLocaleString("nl-NL", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                  : result.expected_value.toLocaleString("nl-NL"))
                : "—"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.5 }}>Meegeteld</div>
            <div style={{ fontSize: 18, fontWeight: 700, color: "#1e293b", marginTop: 2 }}>{(result.record_count ?? 0).toLocaleString("nl-NL")}</div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.5 }}>Totaal rijen</div>
            <div style={{ fontSize: 18, fontWeight: 700, color: "#64748b", marginTop: 2 }}>{(result.total_rows ?? 0).toLocaleString("nl-NL")}</div>
          </div>
          <button
            onClick={() => onViewSparql(result)}
            style={{
              padding: "6px 12px", borderRadius: 6, border: "1px solid var(--k-blue-mid)",
              background: "var(--k-blue-light)", cursor: "pointer", fontSize: 12, fontWeight: 500,
              color: "var(--k-blue-strong)", whiteSpace: "nowrap",
            }}
          >
            📡 SPARQL
          </button>
        </div>
      )}
    </div>
  );
}

function HappyFlowTab() {
  const [files, setFiles]                   = useState([]);
  const [dragOver, setDragOver]             = useState(false);
  const [loading, setLoading]               = useState(false);
  const [batchResult, setBatchResult]       = useState(null);
  const [profiles, setProfiles]             = useState([]);
  const [selectedProfile, setSelectedProfile] = useState("");
  const [sparqlModal, setSparqlModal]       = useState(null); // result voor modal
  const [filterTag, setFilterTag]           = useState("all");
  const fileInputRef = React.useRef();

  React.useEffect(() => {
    authFetch("/api/profiles/")
      .then(r => r.json())
      .then(d => setProfiles(Array.isArray(d) ? d : []))
      .catch(console.error);
  }, []);

  function handleFileChange(e) {
    const newFiles = Array.from(e.target.files || []);
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name));
      return [...prev, ...newFiles.filter(f => !existing.has(f.name))];
    });
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const newFiles = Array.from(e.dataTransfer.files || []).filter(f => /\.(csv|xlsx|xls|xml)$/i.test(f.name));
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name));
      return [...prev, ...newFiles.filter(f => !existing.has(f.name))];
    });
  }

  function removeFile(name) {
    setFiles(prev => prev.filter(f => f.name !== name));
  }

  async function handleRun() {
    if (files.length === 0) return;
    setLoading(true);
    setBatchResult(null);
    try {
      const fd = new FormData();
      files.forEach(f => fd.append("files", f, f.name));
      if (selectedProfile) fd.append("profile_filename", selectedProfile);
      const resp = await authFetch(`${API_BASE}/happy-flow/batch`, { method: "POST", body: fd });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || resp.statusText);
      }
      setBatchResult(await resp.json());
    } catch (err) {
      alert("Fout: " + err.message);
    } finally {
      setLoading(false);
    }
  }

  // KIK-V implementatie-twin: synthetische happy-flow voorbeeldset (AVG-proof).
  const KIKV_VOORBEELDSET = [
    "medewerker_afas_hrm.csv","medewerker_ons.csv",
    "werkovereenkomst_afas_hrm.csv","werkovereenkomst_ons.csv",
    "verzuim_afas_hrm.csv","verzuim_ons.csv",
    "client_ons.csv","clienten.csv","contracten.csv","medewerkers.csv",
    "vestiging_ons.csv","functie_ons.csv",
    "financieleboeking_afas_fin.csv","grootboekrubriek_afas_fin.csv","wlzkostenplaats_afas_fin.csv",
  ];
  async function loadVoorbeeldset() {
    setLoading(true); setBatchResult(null);
    try {
      const fetched = await Promise.all(KIKV_VOORBEELDSET.map(async name => {
        const r = await fetch(`/kikv-voorbeeldset/${name}`);
        if (!r.ok) throw new Error(`kon ${name} niet laden`);
        return new File([await r.blob()], name, { type: "text/csv" });
      }));
      setFiles(fetched);
      const fd = new FormData();
      fetched.forEach(f => fd.append("files", f, f.name));
      if (selectedProfile) fd.append("profile_filename", selectedProfile);
      const resp = await authFetch(`${API_BASE}/happy-flow/batch`, { method: "POST", body: fd });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || resp.statusText);
      }
      setBatchResult(await resp.json());
    } catch (err) {
      alert("Fout bij laden voorbeeldset: " + err.message);
    } finally { setLoading(false); }
  }

  function exportHappyFlowCSV() {
    if (!batchResult) return;
    const header = ["indicator_id", "naam", "dataset", "uitkomst", "meegeteld", "totaal_rijen"];
    const rows = (batchResult.all_results || []).map(r => [
      r.indicator_id, r.indicator_name, r.source_dataset,
      r.expected_value ?? "", r.record_count ?? "", r.total_rows ?? "",
    ]);
    const csv = [header, ...rows].map(r => r.join(";")).join("\n");
    Object.assign(document.createElement("a"), {
      href: URL.createObjectURL(new Blob([csv], { type: "text/csv" })),
      download: "happy-flow-resultaten.csv",
    }).click();
  }

  const knownFiles = new Set(Object.keys(DATASET_LABELS));
  const recognizedFiles = files.filter(f => knownFiles.has(f.name));
  const unknownFiles    = files.filter(f => !knownFiles.has(f.name));

  // Resultaten filteren op tag
  const allResults = batchResult?.all_results || [];
  const tagGroups = ["all", "medewerkers", "werkovereenkomsten", "clienten", "verzuim", "financieel", "vestigingen", "functies", "kostenplaatsen"];
  const filteredResults = filterTag === "all"
    ? allResults
    : allResults.filter(r => (r.tags || []).includes(filterTag));

  // Groepeer per dataset voor weergave
  const datasets = batchResult?.datasets || {};

  return (
    <div>
      {/* ── Upload sectie ──────────────────────────────────────────────── */}
      <div style={{
        background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 10,
        padding: 20, marginBottom: 20,
      }}>
        <h3 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 700 }}>Happy Flow — Batch upload</h3>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginBottom: 16 }}>
          <button onClick={loadVoorbeeldset} disabled={loading}
            style={{ background: "var(--blue)", color: "#fff", border: "none", borderRadius: 8,
                     padding: "9px 16px", fontSize: 13, fontWeight: 700, cursor: "pointer" }}>
            {loading ? "Bezig…" : "Laad KIK-V voorbeeldset"}
          </button>
          <a href="/kikv-voorbeeldset.zip" download
            style={{ border: "1.5px solid var(--blue)", color: "var(--blue)", borderRadius: 8,
                     padding: "8px 16px", fontSize: 13, fontWeight: 700, textDecoration: "none" }}>
            Download voorbeeldset (ZIP)
          </a>
          <span style={{ fontSize: 12, color: "#64748b" }}>Synthetische implementatie-twin — geen echte cliëntgegevens.</span>
        </div>

        {/* Profiel dropdown */}
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Uitwisselprofiel (optioneel — voor SPARQL-koppelingen)</label>
          <select
            value={selectedProfile}
            onChange={e => setSelectedProfile(e.target.value)}
            style={{ ...inputStyle, maxWidth: 420 }}
          >
            <option value="">— Geen profiel (alleen CSV-berekeningen) —</option>
            {profiles.map(p => (
              <option key={p.filename} value={p.filename}>
                {p.name || p.filename} ({p.indicator_count} indicatoren)
              </option>
            ))}
          </select>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={e => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${dragOver ? "var(--k-blue)" : "#cbd5e1"}`,
            borderRadius: 10, padding: "28px 20px", textAlign: "center",
            cursor: "pointer", background: dragOver ? "var(--k-blue-light)" : "#fff",
            transition: "all 0.15s", marginBottom: 14,
          }}
        >
          <div style={{ fontSize: 28, marginBottom: 6 }}>📂</div>
          <div style={{ fontWeight: 600, fontSize: 14, color: "#475569" }}>
            Sleep CSV- of XML-bestanden hiernaartoe of klik om te bladeren
          </div>
          <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
            medewerker_ons.csv, Profit_Employees_basic_150_voorbeeld.xml, …
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,.xls,.xml,.json"
            multiple
            style={{ display: "none" }}
            onChange={handleFileChange}
          />
        </div>

        {/* Bestandenlijst */}
        {files.length > 0 && (
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: "#475569", marginBottom: 6 }}>
              {files.length} bestand{files.length !== 1 ? "en" : ""} geselecteerd
              {recognizedFiles.length > 0 && <span style={{ color: "#16a34a" }}> — {recognizedFiles.length} herkend</span>}
              {unknownFiles.length > 0 && <span style={{ color: "#f59e0b" }}> — {unknownFiles.length} onbekend (worden overgeslagen)</span>}
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {files.map(f => {
                const known = knownFiles.has(f.name);
                const dsInfo = DATASET_LABELS[f.name] || { icon: "📄", color: "#94a3b8" };
                return (
                  <div key={f.name} style={{
                    display: "inline-flex", alignItems: "center", gap: 6,
                    padding: "4px 10px", borderRadius: 16,
                    background: known ? "#f0fdf4" : "#fef9c3",
                    border: `1px solid ${known ? "#86efac" : "#fde68a"}`,
                    fontSize: 12,
                  }}>
                    <span>{dsInfo.icon}</span>
                    <span style={{ color: known ? "#15803d" : "#92400e" }}>{f.name}</span>
                    <button
                      onClick={e => { e.stopPropagation(); removeFile(f.name); }}
                      style={{ border: "none", background: "none", cursor: "pointer", color: "#94a3b8", fontSize: 13, padding: 0, lineHeight: 1 }}
                    >✕</button>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <button
            onClick={handleRun}
            disabled={loading || recognizedFiles.length === 0}
            style={{
              padding: "10px 24px", borderRadius: 8,
              background: (loading || recognizedFiles.length === 0) ? "#cbd5e1" : "var(--k-blue)",
              color: "#fff", border: "none", fontWeight: 600, fontSize: 14,
              cursor: (loading || recognizedFiles.length === 0) ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "⏳ Bezig met berekenen…" : `▶ Bereken ${recognizedFiles.length} bestand${recognizedFiles.length !== 1 ? "en" : ""}`}
          </button>
          {files.length > 0 && (
            <button
              onClick={() => { setFiles([]); setBatchResult(null); }}
              style={{ padding: "10px 16px", borderRadius: 8, background: "#fff", border: "1px solid #e2e8f0", cursor: "pointer", fontSize: 13, color: "#64748b" }}
            >
              Wis alles
            </button>
          )}
        </div>
      </div>

      {/* ── Resultaten ─────────────────────────────────────────────────── */}
      {batchResult && (
        <>
          {/* Samenvatting */}
          <div style={{
            display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12,
            marginBottom: 20,
          }}>
            {[
              { label: "Indicatoren berekend", value: batchResult.total_indicators, color: "var(--k-blue)" },
              { label: "Datasets verwerkt", value: batchResult.total_datasets, color: "#16a34a" },
              { label: "Bestanden overgeslagen", value: (batchResult.skipped_files || []).length, color: "#f59e0b" },
              { label: "SPARQL-queries beschikbaar", value: batchResult.profile_sparqls_available || 0, color: "#8b5cf6" },
            ].map(m => (
              <div key={m.label} style={{
                background: "#fff", border: "1px solid #e2e8f0", borderRadius: 10,
                padding: "14px 16px", textAlign: "center",
              }}>
                <div style={{ fontSize: 10, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.5 }}>{m.label}</div>
                <div style={{ fontSize: 26, fontWeight: 800, color: m.color, marginTop: 4 }}>{m.value}</div>
              </div>
            ))}
          </div>

          {/* Overgeslagen bestanden melding */}
          {batchResult.skipped_files?.length > 0 && (
            <div style={{ marginBottom: 16, padding: "10px 14px", background: "#fef9c3", border: "1px solid #fde68a", borderRadius: 8, fontSize: 13, color: "#92400e" }}>
              ⚠ Geen regels gevonden voor: {batchResult.skipped_files.join(", ")}
            </div>
          )}

          {/* Filter tabs */}
          {allResults.length > 0 && (
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 16, alignItems: "center" }}>
              <span style={{ fontSize: 12, color: "#64748b", marginRight: 4 }}>Filter:</span>
              {tagGroups.map(tag => {
                const count = tag === "all" ? allResults.length : allResults.filter(r => (r.tags || []).includes(tag)).length;
                if (count === 0 && tag !== "all") return null;
                return (
                  <button
                    key={tag}
                    onClick={() => setFilterTag(tag)}
                    style={{
                      padding: "4px 12px", borderRadius: 12, fontSize: 12, cursor: "pointer",
                      border: filterTag === tag ? "1.5px solid var(--k-blue)" : "1px solid #cbd5e1",
                      background: filterTag === tag ? "var(--k-blue-light)" : "#fff",
                      color: filterTag === tag ? "var(--k-blue-strong)" : "#475569",
                      fontWeight: filterTag === tag ? 600 : 400,
                    }}
                  >
                    {tag === "all" ? "Alles" : tag.charAt(0).toUpperCase() + tag.slice(1)} ({count})
                  </button>
                );
              })}
              <button onClick={exportHappyFlowCSV} style={{ marginLeft: "auto", ...exportBtn }}>⬇ CSV exporteren</button>
            </div>
          )}

          {/* Resultatenlijst */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {filteredResults.map(r => (
              <HappyFlowResultCard
                key={r.indicator_id}
                result={r}
                sparqls={batchResult.profile_sparqls || {}}
                onViewSparql={result => setSparqlModal(result)}
              />
            ))}
          </div>

          {filteredResults.length === 0 && (
            <div style={{ textAlign: "center", padding: "32px 0", color: "#94a3b8" }}>
              Geen indicatoren voor dit filter.
            </div>
          )}
        </>
      )}

      {!batchResult && !loading && (
        <div style={{ textAlign: "center", padding: "48px 0", color: "#94a3b8" }}>
          <div style={{ fontSize: 32, marginBottom: 10 }}>📂</div>
          Upload de happy flow CSV-bestanden om de indicatoren te berekenen.
          <br />
          <span style={{ fontSize: 12, marginTop: 8, display: "block" }}>
            Bestanden worden automatisch herkend op basis van bestandsnaam
          </span>
        </div>
      )}

      {sparqlModal && (
        <SparqlViewModal
          indicator={sparqlModal}
          sparqls={batchResult?.profile_sparqls || {}}
          onClose={() => setSparqlModal(null)}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Dashboard
// ---------------------------------------------------------------------------

export default function ReconciliationDashboard({ onBack, authUser, onLogout }) {
  const [activeTab, setActiveTab]              = useState("happy-flow");
  const [indicators, setIndicators]           = useState([]);
  const [results, setResults]                 = useState([]);
  const [calcPreview, setCalcPreview]         = useState(null);
  const [calcPreviewName, setCalcPreviewName] = useState("");
  const [loading, setLoading]                 = useState(false);
  const [drillTarget, setDrillTarget]         = useState(null);
  React.useEffect(() => {
    authFetch(`${API_BASE}/indicators`).then(r => r.json()).then(setIndicators).catch(console.error);
  }, []);

  const handleResult    = useCallback(result => {
    setResults(prev => [result, ...prev.filter(r => r.indicator_id !== result.indicator_id)]);
  }, []);
  const handleCalcPreview = useCallback((calc, name) => { setCalcPreview(calc); setCalcPreviewName(name); }, []);

  const totalOK = results.filter(r => r.status === "OK").length;
  const overallScore = results.length > 0 ? (totalOK / results.length) * 100 : null;

  const tabs = [
    { id: "happy-flow", label: "🚀 Happy Flow batch" },
    { id: "manual",     label: "🔧 Handmatig per indicator" },
  ];

  return (
    <>
    <Nav authUser={authUser} onLogout={onLogout} onHome={onBack} onBack={onBack} />
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "24px 16px", fontFamily: "var(--font)" }}>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>🔁 Reconciliation Engine</h2>
          <p style={{ margin: "4px 0 0", color: "#64748b", fontSize: 14 }}>
            Vergelijk brondata-uitkomsten met SPARQL-indicatoren uit het uitwisselprofiel
          </p>
        </div>
        {activeTab === "manual" && overallScore !== null && (
          <ScoreGauge score={overallScore} label={results[0]?.reconciliation_score_label || ""} />
        )}
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 2, marginBottom: 24, borderBottom: "2px solid #e2e8f0" }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: "10px 20px", border: "none", cursor: "pointer",
              background: "none", fontWeight: activeTab === tab.id ? 700 : 400,
              fontSize: 14, color: activeTab === tab.id ? "var(--k-blue-strong)" : "#64748b",
              borderBottom: activeTab === tab.id ? "2px solid var(--k-blue-strong)" : "2px solid transparent",
              marginBottom: -2,
              transition: "all 0.15s",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab inhoud */}
      {activeTab === "happy-flow" && <HappyFlowTab />}

      {activeTab === "manual" && (
        <>
          <UploadForm
            indicators={indicators}
            onResult={handleResult}
            onCalcPreview={handleCalcPreview}
            loading={loading}
            setLoading={setLoading}
          />

          {calcPreview && (
            <CalcPreviewCard calc={calcPreview} indicatorName={calcPreviewName} onClose={() => setCalcPreview(null)} />
          )}

          {results.length > 0 && (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <h3 style={{ margin: 0, fontSize: 16 }}>Vergelijkingsresultaten ({totalOK}/{results.length} OK)</h3>
                <div style={{ display: "flex", gap: 8 }}>
                  <button onClick={() => exportCSV(results)} style={exportBtn}>⬇ CSV</button>
                  <button onClick={() => exportJSON(results)} style={exportBtn}>⬇ JSON</button>
                </div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {results.map(r => (
                  <IndicatorCard key={r.indicator_id} result={r} onDrillDown={setDrillTarget} />
                ))}
              </div>
            </>
          )}

          {results.length === 0 && !calcPreview && !loading && (
            <div style={{ textAlign: "center", padding: "48px 0", color: "#94a3b8" }}>
              Kies een indicator en upload een bronbestand om te beginnen.
              <br />
              <span style={{ fontSize: 12, marginTop: 8, display: "block" }}>
                "📄 Bekijk brondata" toont de CSV-uitkomst &nbsp;·&nbsp; "▶ Reconcilieer" vergelijkt met SPARQL
              </span>
            </div>
          )}

          <DrillDownModal result={drillTarget} onClose={() => setDrillTarget(null)} />
        </>
      )}
    </div>
    </>
  );
}

const exportBtn = {
  padding: "6px 14px", borderRadius: 6, border: "1px solid #cbd5e1",
  background: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 500,
};
