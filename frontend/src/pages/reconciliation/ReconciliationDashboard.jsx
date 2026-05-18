/**
 * Rhadix — Reconciliation Engine Dashboard
 */

import React, { useCallback, useRef, useState } from "react";

const API_BASE = "/api/reconciliation";

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
    fetch(`${API_BASE}/indicators/${indicatorId}/sparql-query`)
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
                <strong>Endpoint:</strong> <code style={{ color: "#1d4ed8" }}>{query.sparql_endpoint}</code>
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
            <Metric label="SPARQL-uitkomst" value={fmt(result.actual_value)} color="#1d4ed8" sub="live query" />
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
// Upload form
// ---------------------------------------------------------------------------

function UploadForm({ indicators, onResult, onCalcPreview, loading, setLoading }) {
  const [selectedIndicator, setSelectedIndicator] = useState("");
  const [actualValue, setActualValue]             = useState("");
  const [sparqlEndpoint, setSparqlEndpoint]       = useState("");
  const [fileName, setFileName]                   = useState("");
  const fileRef = useRef();

  const selectedInd = indicators.find(i => i.indicator_id === selectedIndicator);
  const hasSparqlQuery = selectedInd?.sparql_query;

  async function handlePreview(e) {
    e.preventDefault();
    if (!selectedIndicator || !fileRef.current?.files[0]) return;
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("file", fileRef.current.files[0]);
      const resp = await fetch(`${API_BASE}/calculate/${selectedIndicator}`, { method: "POST", body: fd });
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
      if (actualValue)    fd.append("actual_value", actualValue);
      if (sparqlEndpoint) fd.append("sparql_endpoint", sparqlEndpoint);
      const resp = await fetch(`${API_BASE}/reconcile/${selectedIndicator}`, { method: "POST", body: fd });
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
      <h3 style={{ margin: "0 0 16px" }}>Nieuwe reconciliatie starten</h3>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, alignItems: "start" }}>

        {/* Indicator */}
        <div style={{ gridColumn: "1 / -1" }}>
          <label style={labelStyle}>Indicator</label>
          <select value={selectedIndicator} onChange={e => setSelectedIndicator(e.target.value)}
            style={inputStyle} required>
            <option value="">-- Kies indicator --</option>
            {indicators.map(ind => (
              <option key={ind.indicator_id} value={ind.indicator_id}>
                {ind.name}{ind.sparql_query ? "  ·  📋 SPARQL" : ""}
              </option>
            ))}
          </select>

          {/* SPARQL query inline tonen zodra indicator geselecteerd */}
          {hasSparqlQuery && (
            <div style={{ marginTop: 10, borderRadius: 8, border: "1px solid #e2e8f0", overflow: "hidden" }}>
              <div style={{
                background: "#1e293b", padding: "8px 14px",
                display: "flex", justifyContent: "space-between", alignItems: "center",
              }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8" }}>
                  📋 SPARQL query — {selectedInd?.name}
                </span>
                <button
                  type="button"
                  onClick={() => navigator.clipboard?.writeText(selectedInd.sparql_query)}
                  style={{ fontSize: 11, padding: "2px 8px", borderRadius: 4,
                    border: "1px solid #475569", background: "transparent",
                    color: "#94a3b8", cursor: "pointer" }}>
                  Kopieer
                </button>
              </div>
              <pre style={{
                background: "#0f172a", color: "#e2e8f0", margin: 0,
                padding: "12px 16px", fontSize: 12, lineHeight: 1.6,
                overflowX: "auto", whiteSpace: "pre-wrap", wordBreak: "break-word",
                maxHeight: 160, overflowY: "auto",
              }}>
                {selectedInd.sparql_query}
              </pre>
            </div>
          )}
        </div>

        {/* Bestand */}
        <div>
          <label style={labelStyle}>Bronbestand (CSV/Excel)</label>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <label style={{
              padding: "8px 14px", borderRadius: 6, border: "1px solid #cbd5e1",
              background: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 500, whiteSpace: "nowrap",
            }}>
              Kies bestand
              <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls" style={{ display: "none" }}
                onChange={e => setFileName(e.target.files[0]?.name || "")} required />
            </label>
            <span style={{ fontSize: 12, color: "#64748b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {fileName || "Geen bestand gekozen"}
            </span>
          </div>
        </div>

        {/* Werkelijke waarde */}
        <div>
          <label style={labelStyle}>Werkelijke waarde (optioneel, overschrijft SPARQL)</label>
          <input type="number" step="any" value={actualValue} onChange={e => setActualValue(e.target.value)}
            placeholder="bijv. 142" style={inputStyle} />
        </div>

        {/* SPARQL Endpoint */}
        <div>
          <label style={labelStyle}>SPARQL Endpoint (optioneel)</label>
          <input type="url" value={sparqlEndpoint} onChange={e => setSparqlEndpoint(e.target.value)}
            placeholder="https://sparql.example.com/query" style={inputStyle} />
          {selectedInd?.sparql_endpoint && !sparqlEndpoint && (
            <button type="button" onClick={() => setSparqlEndpoint(selectedInd.sparql_endpoint)}
              style={{ marginTop: 4, fontSize: 11, padding: "2px 8px", borderRadius: 10,
                border: "1px solid #cbd5e1", background: "#fff", cursor: "pointer", color: "#475569" }}>
              ↩ Gebruik endpoint uit indicator
            </button>
          )}
        </div>
      </div>

      <div style={{ display: "flex", gap: 10, marginTop: 16, flexWrap: "wrap" }}>
        <button type="button" onClick={handlePreview}
          disabled={loading || !selectedIndicator || !fileName}
          style={{
            padding: "10px 20px", borderRadius: 8, background: "#fff", color: "#15803d",
            border: "1.5px solid #86efac", fontWeight: 600, fontSize: 14,
            cursor: (loading || !selectedIndicator || !fileName) ? "not-allowed" : "pointer",
            opacity: (!selectedIndicator || !fileName) ? 0.5 : 1,
          }}>
          {loading ? "Bezig…" : "📄 Bekijk brondata"}
        </button>
        <button type="button" onClick={handleReconcile}
          disabled={loading || !selectedIndicator || !fileName}
          style={{
            padding: "10px 24px", borderRadius: 8, background: "#3b82f6", color: "#fff",
            border: "none", fontWeight: 600, fontSize: 14,
            cursor: (loading || !selectedIndicator || !fileName) ? "not-allowed" : "pointer",
            opacity: (!selectedIndicator || !fileName) ? 0.5 : 1,
          }}>
          {loading ? "Bezig…" : "▶ Reconcilieer"}
        </button>
      </div>
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

export default function ReconciliationDashboard({ onBack }) {
  const [indicators, setIndicators]           = useState([]);
  const [results, setResults]                 = useState([]);
  const [calcPreview, setCalcPreview]         = useState(null);
  const [calcPreviewName, setCalcPreviewName] = useState("");
  const [loading, setLoading]                 = useState(false);
  const [drillTarget, setDrillTarget]         = useState(null);
  React.useEffect(() => {
    fetch(`${API_BASE}/indicators`).then(r => r.json()).then(setIndicators).catch(console.error);
  }, []);

  const handleResult    = useCallback(result => {
    setResults(prev => [result, ...prev.filter(r => r.indicator_id !== result.indicator_id)]);
  }, []);
  const handleCalcPreview = useCallback((calc, name) => { setCalcPreview(calc); setCalcPreviewName(name); }, []);

  const totalOK = results.filter(r => r.status === "OK").length;
  const overallScore = results.length > 0 ? (totalOK / results.length) * 100 : null;

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "24px 16px", fontFamily: "Inter, system-ui, sans-serif" }}>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          {onBack && (
            <button onClick={onBack} style={{ background: "none", border: "none", cursor: "pointer", color: "#64748b", fontSize: 13, marginBottom: 6, padding: 0, display: "block" }}>
              ← Terug
            </button>
          )}
          <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>🔁 Reconciliation Engine</h2>
          <p style={{ margin: "4px 0 0", color: "#64748b", fontSize: 14 }}>
            Vergelijk brondata-uitkomsten met SPARQL-indicatoren
          </p>
        </div>
        {overallScore !== null && (
          <ScoreGauge score={overallScore} label={results[0]?.reconciliation_score_label || ""} />
        )}
      </div>

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
    </div>
  );
}

const exportBtn = {
  padding: "6px 14px", borderRadius: 6, border: "1px solid #cbd5e1",
  background: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 500,
};
