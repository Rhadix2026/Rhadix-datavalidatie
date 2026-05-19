/**
 * Rhadix — Reconciliation Engine Dashboard
 * Stoplicht-weergave per indicator met drill-down tabel en export.
 *
 * Voeg deze pagina toe aan je React-router:
 *   import ReconciliationDashboard from './pages/reconciliation/ReconciliationDashboard';
 *   <Route path="/reconciliation" element={<ReconciliationDashboard />} />
 */

import React, { useCallback, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Constanten & helpers
// ---------------------------------------------------------------------------

const API_BASE = "/api/reconciliation";

const STATUS_CONFIG = {
  OK:      { color: "#22c55e", bg: "#dcfce7", label: "✓ OK",       icon: "🟢" },
  Warning: { color: "#f59e0b", bg: "#fef3c7", label: "⚠ Waarschuwing", icon: "🟡" },
  Error:   { color: "#ef4444", bg: "#fee2e2", label: "✗ Fout",     icon: "🔴" },
  Unknown: { color: "#94a3b8", bg: "#f1f5f9", label: "? Onbekend", icon: "⚪" },
};

const CATEGORY_LABELS = {
  missing_in_rdf:       "Ontbreekt in RDF",
  extra_in_rdf:         "Extra in RDF",
  wrong_dates:          "Onjuiste datum",
  missing_relationships:"Ontbrekende relatie",
  invalid_codes:        "Ongeldige code",
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

function IndicatorCard({ result, onDrillDown }) {
  const { status } = result;
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.Unknown;
  return (
    <div style={{
      border: `2px solid ${cfg.color}`, borderRadius: 10,
      padding: 16, background: "#fff",
      boxShadow: "0 1px 4px rgba(0,0,0,.07)",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15 }}>{result.indicator_name}</div>
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{result.indicator_id}</div>
        </div>
        <StatusBadge status={status} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginTop: 14 }}>
        <Metric label="Verwacht" value={fmt(result.expected_value)} />
        <Metric label="Werkelijk (SPARQL)" value={fmt(result.actual_value)} />
        <Metric
          label="Afwijking"
          value={result.percentage_difference !== null ? `${fmt(result.percentage_difference)}%` : "—"}
          color={cfg.color}
        />
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
        <div style={{ fontSize: 12, color: "#475569" }}>
          Confidence: <strong>{fmt(result.confidence_score, 1)}%</strong> &bull; {result.reconciliation_score_label}
        </div>
        {result.drill_down?.length > 0 && (
          <button
            onClick={() => onDrillDown(result)}
            style={{
              padding: "4px 12px", borderRadius: 6, border: "1px solid #cbd5e1",
              background: "#f8fafc", cursor: "pointer", fontSize: 12,
            }}
          >
            🔍 Drill-down ({result.drill_down.length})
          </button>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value, color }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.5 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: color || "#1e293b", marginTop: 2 }}>{value}</div>
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
              {items.length > 50 && (
                <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 4 }}>
                  Toont 50 van {items.length} records
                </div>
              )}
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

function UploadForm({ indicators, onResult, loading, setLoading }) {
  const [selectedIndicator, setSelectedIndicator] = useState("");
  const [actualValue, setActualValue] = useState("");
  const [sparqlEndpoint, setSparqlEndpoint] = useState("");
  const fileRef = useRef();

  async function handleSubmit(e) {
    e.preventDefault();
    if (!selectedIndicator || !fileRef.current?.files[0]) return;
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("file", fileRef.current.files[0]);
      if (actualValue) fd.append("actual_value", actualValue);
      if (sparqlEndpoint) fd.append("sparql_endpoint", sparqlEndpoint);

      const resp = await fetch(`${API_BASE}/reconcile/${selectedIndicator}`, {
        method: "POST", body: fd,
      });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      onResult(data);
    } catch (err) {
      alert("Fout: " + err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{
      background: "#f8fafc", border: "1px solid #e2e8f0",
      borderRadius: 10, padding: 20, marginBottom: 24,
    }}>
      <h3 style={{ margin: "0 0 16px" }}>Nieuwe reconciliatie starten</h3>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div>
          <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 4 }}>Indicator</label>
          <select
            value={selectedIndicator}
            onChange={e => setSelectedIndicator(e.target.value)}
            style={{ width: "100%", padding: "8px 10px", borderRadius: 6, border: "1px solid #cbd5e1" }}
            required
          >
            <option value="">-- Kies indicator --</option>
            {indicators.map(ind => (
              <option key={ind.indicator_id} value={ind.indicator_id}>{ind.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 4 }}>Bronbestand (CSV/Excel)</label>
          <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls"
            style={{ width: "100%", padding: "6px 0" }} required />
        </div>
        <div>
          <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 4 }}>
            Werkelijke waarde (optioneel, overschrijft SPARQL)
          </label>
          <input
            type="number" step="any" value={actualValue}
            onChange={e => setActualValue(e.target.value)}
            placeholder="bijv. 142"
            style={{ width: "100%", padding: "8px 10px", borderRadius: 6, border: "1px solid #cbd5e1" }}
          />
        </div>
        <div>
          <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 4 }}>SPARQL Endpoint (optioneel)</label>
          <input
            type="url" value={sparqlEndpoint}
            onChange={e => setSparqlEndpoint(e.target.value)}
            placeholder="https://sparql.example.com/query"
            style={{ width: "100%", padding: "8px 10px", borderRadius: 6, border: "1px solid #cbd5e1" }}
          />
        </div>
      </div>
      <button
        type="submit" disabled={loading}
        style={{
          marginTop: 16, padding: "10px 24px", borderRadius: 8,
          background: "#3b82f6", color: "#fff", border: "none",
          fontWeight: 600, cursor: loading ? "wait" : "pointer", fontSize: 14,
        }}
      >
        {loading ? "Bezig…" : "▶ Reconcilieer"}
      </button>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Export helpers
// ---------------------------------------------------------------------------

function exportJSON(results) {
  const blob = new Blob([JSON.stringify(results, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = url; a.download = "reconciliation.json"; a.click();
}

function exportCSV(results) {
  const rows = results.map(r => [
    r.indicator_id, r.indicator_name, r.expected_value ?? "",
    r.actual_value ?? "", r.absolute_difference ?? "",
    r.percentage_difference ?? "", r.status, r.confidence_score,
    r.reconciliation_score_label,
  ]);
  const header = ["indicator_id","name","expected","actual","abs_diff","pct_diff","status","confidence","label"];
  const csv = [header, ...rows].map(r => r.join(";")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = url; a.download = "reconciliation.csv"; a.click();
}

// ---------------------------------------------------------------------------
// Main Dashboard
// ---------------------------------------------------------------------------

export default function ReconciliationDashboard() {
  const [indicators, setIndicators] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [drillTarget, setDrillTarget] = useState(null);

  // Laad indicatoren bij mount
  React.useEffect(() => {
    fetch(`${API_BASE}/indicators`)
      .then(r => r.json())
      .then(setIndicators)
      .catch(console.error);
  }, []);

  const handleResult = useCallback(result => {
    setResults(prev => {
      const updated = prev.filter(r => r.indicator_id !== result.indicator_id);
      return [result, ...updated];
    });
  }, []);

  // Score samenvatting
  const totalOK = results.filter(r => r.status === "OK").length;
  const overallScore = results.length > 0 ? (totalOK / results.length) * 100 : null;

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "24px 16px", fontFamily: "Inter, system-ui, sans-serif" }}>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>🔁 Reconciliation Engine</h2>
          <p style={{ margin: "4px 0 0", color: "#64748b", fontSize: 14 }}>
            Vergelijk brondata-uitkomsten met SPARQL-indicatoren
          </p>
        </div>
        {overallScore !== null && (
          <ScoreGauge score={overallScore} label={results[0]?.reconciliation_score_label || ""} />
        )}
      </div>

      {/* Upload form */}
      <UploadForm
        indicators={indicators}
        onResult={handleResult}
        loading={loading}
        setLoading={setLoading}
      />

      {/* Resultaten */}
      {results.length > 0 && (
        <>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ margin: 0, fontSize: 16 }}>
              Resultaten ({totalOK}/{results.length} OK)
            </h3>
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

      {results.length === 0 && !loading && (
        <div style={{ textAlign: "center", padding: "48px 0", color: "#94a3b8" }}>
          Nog geen resultaten — upload een bronbestand om te beginnen.
        </div>
      )}

      {/* Drill-down modal */}
      <DrillDownModal result={drillTarget} onClose={() => setDrillTarget(null)} />
    </div>
  );
}

const exportBtn = {
  padding: "6px 14px", borderRadius: 6, border: "1px solid #cbd5e1",
  background: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 500,
};
