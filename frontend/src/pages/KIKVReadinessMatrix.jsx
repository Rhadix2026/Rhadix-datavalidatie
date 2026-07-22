import { useState, useMemo } from "react";

// ─── Constants ────────────────────────────────────────────────────────────────

const DOMAINS = ["medewerker", "werkovereenkomst", "functie", "verzuim"];
const DOMAIN_LABELS = {
  medewerker:      "Medewerker",
  werkovereenkomst:"WerkOvereenkomst",
  functie:         "Functie",
  verzuim:         "Verzuim",
};

const READINESS_COLORS = {
  fully:     { bg: "#d1fae5", text: "#065f46", border: "#6ee7b7", label: "Volledig" },
  partially: { bg: "#fef3c7", text: "#92400e", border: "#fcd34d", label: "Gedeeltelijk" },
  blocked:   { bg: "#fee2e2", text: "#991b1b", border: "#fca5a5", label: "Geblokkeerd" },
};

const HEATMAP_CELL = {
  required_present: { bg: "#d1fae5", text: "#065f46", symbol: "✓" },
  required_missing: { bg: "#fee2e2", text: "#991b1b", symbol: "✕" },
  not_required:     { bg: "#f9fafb", text: "#d1d5db", symbol: "·" },
};

// ─── Mini atoms ───────────────────────────────────────────────────────────────

function Badge({ color = "grey", children, small }) {
  const p = READINESS_COLORS[color] || { bg: "#f3f4f6", text: "#6b7280", border: "#d1d5db" };
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      padding: small ? "1px 6px" : "3px 9px",
      borderRadius: 9999, fontSize: small ? 11 : 12, fontWeight: 600,
      background: p.bg, color: p.text, border: `1px solid ${p.border}`,
    }}>
      {children}
    </span>
  );
}

function ScoreRing({ score, size = 80, strokeWidth = 8 }) {
  const r = (size - strokeWidth) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const color = score >= 70 ? "#10b981" : score >= 40 ? "#f59e0b" : "#ef4444";
  return (
    <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#e5e7eb" strokeWidth={strokeWidth} />
      <circle
        cx={size/2} cy={size/2} r={r} fill="none"
        stroke={color} strokeWidth={strokeWidth}
        strokeDasharray={circ} strokeDashoffset={offset}
        strokeLinecap="round"
        style={{ transition: "stroke-dashoffset 0.6s ease" }}
      />
      <text
        x="50%" y="50%"
        textAnchor="middle" dominantBaseline="central"
        style={{ transform: "rotate(90deg)", transformOrigin: "center", fontSize: size * 0.22, fontWeight: 700, fill: color }}
      >
        {score ?? "—"}
      </text>
    </svg>
  );
}

function ScoreBar({ label, value, max = 100, color }) {
  if (value == null) return null;
  const pct = Math.round((value / max) * 100);
  const bg = color || (pct >= 70 ? "#10b981" : pct >= 40 ? "#f59e0b" : "#ef4444");
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 3 }}>
        <span style={{ color: "#374151", fontWeight: 500 }}>{label}</span>
        <span style={{ color: bg, fontWeight: 700 }}>{pct}%</span>
      </div>
      <div style={{ height: 6, background: "#e5e7eb", borderRadius: 99 }}>
        <div style={{ height: "100%", width: `${pct}%`, background: bg, borderRadius: 99, transition: "width 0.5s ease" }} />
      </div>
    </div>
  );
}

// ─── Summary panel ────────────────────────────────────────────────────────────

function SummaryPanel({ matrix }) {
  const { profile_readiness_score: prs, fully_computable: full, partially_computable: part,
          blocked, total_indicators: total, availability_score, structural_score,
          relational_score, use_case_score, uploaded_domains } = matrix;

  const tiles = [
    { label: "Volledig",      value: full,    color: "#10b981", icon: "✓" },
    { label: "Gedeeltelijk",  value: part,    color: "#f59e0b", icon: "◑" },
    { label: "Geblokkeerd",   value: blocked, color: "#ef4444", icon: "✕" },
    { label: "Totaal",        value: total,   color: "var(--k-blue)", icon: "Σ" },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: 24, marginBottom: 24 }}>
      {/* Score ring */}
      <div style={{
        background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12,
        padding: "24px 28px", display: "flex", flexDirection: "column",
        alignItems: "center", gap: 8, minWidth: 160,
      }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.08em" }}>
          Profiel gereedheid
        </div>
        <ScoreRing score={Math.round(prs ?? 0)} size={100} />
        <div style={{ fontSize: 12, color: "#6b7280" }}>
          {profile_name_tag(prs)}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Count tiles */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
          {tiles.map(t => (
            <div key={t.label} style={{
              background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10,
              padding: "14px 16px", textAlign: "center",
            }}>
              <div style={{ fontSize: 28, fontWeight: 800, color: t.color }}>{t.value}</div>
              <div style={{ fontSize: 12, color: "#6b7280", marginTop: 2 }}>{t.icon} {t.label}</div>
            </div>
          ))}
        </div>

        {/* Score bars */}
        <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: "16px 20px" }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#374151", marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.07em" }}>
            Rhadix scores — huidig scan
          </div>
          <ScoreBar label="Beschikbaarheid"   value={availability_score} />
          <ScoreBar label="Structureel (OWL)"  value={structural_score} />
          <ScoreBar label="Relationeel (FK)"   value={relational_score} />
          <ScoreBar label="Use-case (SPARQL)"  value={use_case_score} />

          {uploaded_domains?.length > 0 && (
            <div style={{ marginTop: 10, fontSize: 12 }}>
              <span style={{ color: "#6b7280" }}>Geüploade bronnen: </span>
              {uploaded_domains.map(d => (
                <span key={d} style={{
                  display: "inline-block", background: "var(--k-blue-light)", color: "var(--k-blue-strong)",
                  padding: "1px 8px", borderRadius: 9999, fontSize: 11, fontWeight: 600,
                  marginLeft: 4,
                }}>{DOMAIN_LABELS[d] || d}</span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function profile_name_tag(score) {
  if (score == null) return "—";
  if (score >= 80) return "Hoog — klaar voor uitwisseling";
  if (score >= 50) return "Matig — kritieke gaps aanwezig";
  return "Laag — basisdata ontbreekt";
}

// ─── Top-10 blocking panels ───────────────────────────────────────────────────

function TopBlockingPanel({ title, icon, items, keyProp, countProp }) {
  return (
    <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, overflow: "hidden" }}>
      <div style={{
        background: "#fef2f2", borderBottom: "1px solid #fecaca",
        padding: "10px 16px", fontWeight: 700, fontSize: 13, color: "#991b1b",
        display: "flex", alignItems: "center", gap: 6,
      }}>
        {icon} {title}
      </div>
      {items.length === 0
        ? <div style={{ padding: 16, color: "#9ca3af", fontSize: 13 }}>Geen blokkerende items</div>
        : items.map((item, i) => {
            const count = item[countProp];
            const maxCount = items[0][countProp] || 1;
            const pct = (count / maxCount) * 100;
            return (
              <div key={i} style={{
                padding: "8px 16px",
                borderBottom: i < items.length - 1 ? "1px solid #f3f4f6" : "none",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <code style={{ fontSize: 12, color: "#374151" }}>{item[keyProp]}</code>
                  <span style={{ fontSize: 12, fontWeight: 700, color: "#ef4444" }}>
                    {count} indicator{count !== 1 ? "en" : ""}
                  </span>
                </div>
                <div style={{ height: 4, background: "#fee2e2", borderRadius: 99 }}>
                  <div style={{ height: "100%", width: `${pct}%`, background: "#ef4444", borderRadius: 99 }} />
                </div>
              </div>
            );
          })}
    </div>
  );
}

// ─── Heatmap ─────────────────────────────────────────────────────────────────

function Heatmap({ rows, onSelect, selectedId }) {
  return (
    <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, overflow: "hidden" }}>
      <div style={{ background: "#f8fafc", borderBottom: "1px solid #e5e7eb", padding: "10px 16px" }}>
        <span style={{ fontWeight: 700, fontSize: 13, color: "#374151" }}>
          Heatmap — indicatoren × brondomein
        </span>
        <span style={{ fontSize: 12, color: "#9ca3af", marginLeft: 12 }}>
          Klik op een rij voor details
        </span>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr style={{ background: "#f1f5f9" }}>
              <th style={{ ...th, width: 110, textAlign: "left" }}>Indicator</th>
              <th style={{ ...th, maxWidth: 260, textAlign: "left" }}>Titel</th>
              <th style={{ ...th, textAlign: "center", width: 80 }}>Status</th>
              {DOMAINS.map(d => (
                <th key={d} style={{ ...th, textAlign: "center", width: 110 }}>
                  {DOMAIN_LABELS[d]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const rc = READINESS_COLORS[row.readiness] || {};
              const isSelected = selectedId === row.indicator_id;
              return (
                <tr
                  key={row.indicator_id}
                  onClick={() => onSelect(isSelected ? null : row.indicator_id)}
                  style={{
                    cursor: "pointer",
                    background: isSelected ? "var(--k-blue-light)" : (i % 2 === 0 ? "#fff" : "#f9fafb"),
                    outline: isSelected ? "2px solid var(--k-blue)" : "none",
                    outlineOffset: -2,
                  }}
                  onMouseEnter={e => !isSelected && (e.currentTarget.style.background = "#f0f9ff")}
                  onMouseLeave={e => !isSelected && (e.currentTarget.style.background = i % 2 === 0 ? "#fff" : "#f9fafb")}
                >
                  <td style={{ ...td, fontWeight: 700, color: "#1e3a5f" }}>{row.indicator_id}</td>
                  <td style={{ ...td, color: "#374151", maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {row.title}
                  </td>
                  <td style={{ ...td, textAlign: "center" }}>
                    <span style={{
                      display: "inline-block", padding: "2px 8px", borderRadius: 9999,
                      fontSize: 11, fontWeight: 600,
                      background: rc.bg, color: rc.text,
                    }}>
                      {rc.label || row.readiness}
                    </span>
                  </td>
                  {DOMAINS.map(d => {
                    const cell = HEATMAP_CELL[row[d]] || HEATMAP_CELL.not_required;
                    return (
                      <td key={d} style={{ ...td, textAlign: "center" }}>
                        <span style={{
                          display: "inline-flex", alignItems: "center", justifyContent: "center",
                          width: 28, height: 28, borderRadius: 6,
                          background: cell.bg, color: cell.text,
                          fontWeight: 700, fontSize: 14,
                        }}>
                          {cell.symbol}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div style={{
        display: "flex", gap: 20, padding: "10px 16px",
        borderTop: "1px solid #e5e7eb", background: "#f8fafc",
      }}>
        {Object.entries(HEATMAP_CELL).map(([k, c]) => (
          <div key={k} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11 }}>
            <span style={{
              display: "inline-flex", alignItems: "center", justifyContent: "center",
              width: 20, height: 20, borderRadius: 4,
              background: c.bg, color: c.text, fontWeight: 700, fontSize: 12,
            }}>{c.symbol}</span>
            <span style={{ color: "#6b7280" }}>
              {k === "required_present" ? "Vereist & aanwezig"
               : k === "required_missing" ? "Vereist & ontbreekt"
               : "Niet vereist"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Indicator detail panel ───────────────────────────────────────────────────

function IndicatorDetail({ ind }) {
  const rc = READINESS_COLORS[ind.readiness] || {};
  return (
    <div style={{
      background: "#fff", border: `2px solid ${rc.border || "#e5e7eb"}`,
      borderRadius: 12, overflow: "hidden",
    }}>
      {/* Header */}
      <div style={{
        background: rc.bg, padding: "14px 20px",
        display: "flex", justifyContent: "space-between", alignItems: "center",
        borderBottom: `1px solid ${rc.border}`,
      }}>
        <div>
          <div style={{ fontWeight: 800, fontSize: 16, color: rc.text }}>{ind.id}</div>
          <div style={{ fontSize: 13, color: rc.text, opacity: 0.85, marginTop: 2 }}>{ind.title}</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <ScoreRing score={ind.readiness_score} size={70} strokeWidth={7} />
          <span style={{
            background: rc.bg, color: rc.text, border: `1px solid ${rc.border}`,
            padding: "4px 12px", borderRadius: 9999, fontWeight: 700, fontSize: 13,
          }}>
            {rc.label}
          </span>
        </div>
      </div>

      <div style={{ padding: 20, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* Required domains */}
        <DetailSection title="Vereiste brondomein" icon="🗂">
          {ind.required_domains.length === 0
            ? <Muted>Geen specifieke domeinen gevonden</Muted>
            : ind.required_domains.map(d => (
                <div key={d} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  {ind.missing_domains.includes(d)
                    ? <span style={{ color: "#ef4444", fontWeight: 700 }}>✕</span>
                    : <span style={{ color: "#10b981", fontWeight: 700 }}>✓</span>}
                  <span style={{ fontSize: 13 }}>{DOMAIN_LABELS[d] || d}</span>
                  {ind.missing_domains.includes(d) &&
                    <span style={{ fontSize: 11, color: "#ef4444" }}>(niet geüpload)</span>}
                </div>
              ))}
        </DetailSection>

        {/* Required fields */}
        <DetailSection title="Vereiste velden" icon="📋">
          {Object.keys(ind.required_fields).length === 0
            ? <Muted>Geen velden geëxtraheerd</Muted>
            : Object.entries(ind.required_fields).map(([domain, fields]) => (
                <div key={domain} style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "#6b7280", textTransform: "uppercase", marginBottom: 3 }}>
                    {DOMAIN_LABELS[domain] || domain}
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {fields.map(f => {
                      const isMissing = (ind.missing_fields[domain] || []).includes(f);
                      return (
                        <code key={f} style={{
                          fontSize: 11, padding: "2px 7px", borderRadius: 4,
                          background: isMissing ? "#fee2e2" : "#d1fae5",
                          color: isMissing ? "#991b1b" : "#065f46",
                          fontFamily: "monospace",
                        }}>
                          {isMissing ? "✕ " : "✓ "}{f}
                        </code>
                      );
                    })}
                  </div>
                </div>
              ))}
        </DetailSection>

        {/* Required relationships */}
        <DetailSection title="Vereiste relaties (FK)" icon="🔗">
          {ind.required_relationships.length === 0
            ? <Muted>Geen relaties vereist</Muted>
            : ind.required_relationships.map((rel, i) => (
                <div key={i} style={{ fontSize: 13, marginBottom: 6, display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ color: "#6366f1" }}>↔</span>
                  <code style={{ fontSize: 12 }}>{rel.from_domain}.{rel.from_field}</code>
                  <span style={{ color: "#9ca3af" }}>→</span>
                  <code style={{ fontSize: 12 }}>{rel.target_domain}</code>
                </div>
              ))}
        </DetailSection>

        {/* SPARQL pass rate */}
        <DetailSection title="SPARQL use-case resultaat" icon="⚡">
          {ind.sparql_pass_rate != null
            ? (
                <>
                  <ScoreBar
                    label="Slaagpercentage"
                    value={ind.sparql_pass_rate * 100}
                    color={ind.sparql_pass_rate >= 0.9 ? "#10b981" : ind.sparql_pass_rate >= 0.5 ? "#f59e0b" : "#ef4444"}
                  />
                  <div style={{ fontSize: 12, color: "#6b7280" }}>
                    {ind.sparql_pass_rate >= 0.9
                      ? "✓ Drempel gehaald (90%)"
                      : `⚠ Onder drempel (${(ind.sparql_pass_rate * 100).toFixed(0)}% van vereiste 90%)`}
                  </div>
                </>
              )
            : <Muted>Geen SPARQL-testresultaat beschikbaar</Muted>}
        </DetailSection>
      </div>

      {/* Blocking issues */}
      {ind.blocking_issues.length > 0 && (
        <IssueList
          items={ind.blocking_issues}
          type="blocking"
          title="Blokkerende problemen"
        />
      )}
      {ind.warnings.length > 0 && (
        <IssueList
          items={ind.warnings}
          type="warning"
          title="Waarschuwingen"
        />
      )}
    </div>
  );
}

function DetailSection({ title, icon, children }) {
  return (
    <div>
      <div style={{ fontWeight: 700, fontSize: 12, color: "#374151", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 10, display: "flex", alignItems: "center", gap: 5 }}>
        {icon} {title}
      </div>
      {children}
    </div>
  );
}

function Muted({ children }) {
  return <span style={{ fontSize: 13, color: "#9ca3af" }}>{children}</span>;
}

function IssueList({ items, type, title }) {
  const styles = type === "blocking"
    ? { bg: "#fef2f2", border: "#fecaca", text: "#991b1b", dot: "#ef4444", icon: "✕" }
    : { bg: "#fffbeb", border: "#fde68a", text: "#92400e", dot: "#f59e0b", icon: "⚠" };
  return (
    <div style={{
      margin: "0 20px 20px",
      background: styles.bg, border: `1px solid ${styles.border}`,
      borderRadius: 8, padding: "12px 16px",
    }}>
      <div style={{ fontWeight: 700, fontSize: 12, color: styles.text, marginBottom: 8, textTransform: "uppercase" }}>
        {styles.icon} {title}
      </div>
      {items.map((issue, i) => (
        <div key={i} style={{ fontSize: 13, color: styles.text, marginBottom: 4, display: "flex", gap: 6 }}>
          <span style={{ color: styles.dot, flexShrink: 0 }}>•</span>
          {issue}
        </div>
      ))}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function KIKVReadinessMatrix({ matrix, onBack, profileName }) {
  const [selectedId, setSelectedId]     = useState(null);
  const [filterStatus, setFilterStatus] = useState("all");
  const [search, setSearch]             = useState("");

  const indResults = matrix?.indicator_results || {};

  const filteredIndicators = useMemo(() => {
    const q = search.toLowerCase();
    return Object.values(indResults).filter(ind => {
      const matchStatus = filterStatus === "all" || ind.readiness === filterStatus;
      const matchSearch = !q ||
        ind.id.toLowerCase().includes(q) ||
        (ind.title || "").toLowerCase().includes(q) ||
        ind.blocking_issues.some(b => b.toLowerCase().includes(q));
      return matchStatus && matchSearch;
    });
  }, [indResults, filterStatus, search]);

  const selectedInd = selectedId ? indResults[selectedId] : null;

  if (!matrix) {
    return (
      <div style={{ padding: 40, textAlign: "center", color: "#9ca3af", fontFamily: "Inter, sans-serif" }}>
        Geen readiness-data beschikbaar
      </div>
    );
  }

  const filterBtns = [
    { key: "all",       label: `Alles (${matrix.total_indicators})`,          color: "#374151" },
    { key: "fully",     label: `Volledig (${matrix.fully_computable})`,        color: "#10b981" },
    { key: "partially", label: `Gedeeltelijk (${matrix.partially_computable})`,color: "#f59e0b" },
    { key: "blocked",   label: `Geblokkeerd (${matrix.blocked})`,              color: "#ef4444" },
  ];

  return (
    <div style={{ maxWidth: 1300, margin: "0 auto", padding: "24px 20px", fontFamily: "Inter, sans-serif" }}>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
        <NavBack onClick={onBack} dark />
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: "#1e3a5f" }}>
            KIK-V Gereedheidsmatrix
          </h1>
          <div style={{ fontSize: 13, color: "#6b7280", marginTop: 2 }}>
            {profileName || matrix.profile_name} v{matrix.profile_version}
          </div>
        </div>
      </div>

      {/* Summary */}
      <SummaryPanel matrix={matrix} />

      {/* Top-10 blocking panels */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 24 }}>
        <TopBlockingPanel
          title="Top blokkerende velden"
          icon="📋"
          items={matrix.top_blocking_fields || []}
          keyProp="field"
          countProp="blocked_indicators"
        />
        <TopBlockingPanel
          title="Top blokkerende relaties"
          icon="🔗"
          items={matrix.top_blocking_relationships || []}
          keyProp="relationship"
          countProp="blocked_indicators"
        />
      </div>

      {/* Heatmap */}
      <div style={{ marginBottom: 24 }}>
        <Heatmap
          rows={matrix.heatmap || []}
          onSelect={setSelectedId}
          selectedId={selectedId}
        />
      </div>

      {/* Selected indicator detail */}
      {selectedInd && (
        <div style={{ marginBottom: 24 }}>
          <IndicatorDetail ind={selectedInd} />
        </div>
      )}

      {/* Full indicator list with filter */}
      <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, overflow: "hidden" }}>
        <div style={{
          padding: "14px 16px", borderBottom: "1px solid #e5e7eb",
          display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap",
        }}>
          <span style={{ fontWeight: 700, fontSize: 13, color: "#374151", marginRight: 4 }}>Indicatoren</span>
          {filterBtns.map(b => (
            <button
              key={b.key}
              onClick={() => setFilterStatus(b.key)}
              style={{
                padding: "5px 12px", borderRadius: 9999, fontSize: 12, fontWeight: 600,
                border: filterStatus === b.key ? `2px solid ${b.color}` : "1px solid #e5e7eb",
                background: filterStatus === b.key ? b.color + "18" : "#fff",
                color: filterStatus === b.key ? b.color : "#6b7280",
                cursor: "pointer",
              }}
            >
              {b.label}
            </button>
          ))}
          <input
            style={{
              marginLeft: "auto", border: "1px solid #d1d5db", borderRadius: 7,
              padding: "6px 12px", fontSize: 13, outline: "none", minWidth: 220,
            }}
            placeholder="Zoek indicator of blokkade…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "#f8fafc" }}>
              <th style={th}>ID</th>
              <th style={th}>Titel</th>
              <th style={{ ...th, textAlign: "center" }}>Score</th>
              <th style={{ ...th, textAlign: "center" }}>Status</th>
              <th style={th}>Ontbrekende velden</th>
              <th style={th}>Blokkades</th>
            </tr>
          </thead>
          <tbody>
            {filteredIndicators.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: 24, textAlign: "center", color: "#9ca3af" }}>
                  Geen indicatoren{search ? ` voor "${search}"` : ""}
                </td>
              </tr>
            ) : filteredIndicators.map((ind, i) => {
              const rc = READINESS_COLORS[ind.readiness] || {};
              const isSelected = selectedId === ind.id;
              const missingCount = Object.values(ind.missing_fields).reduce((s, f) => s + f.length, 0);
              return (
                <tr
                  key={ind.id}
                  onClick={() => {
                    setSelectedId(isSelected ? null : ind.id);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                  style={{
                    cursor: "pointer",
                    background: isSelected ? "var(--k-blue-light)" : i % 2 === 0 ? "#fff" : "#f9fafb",
                    borderLeft: isSelected ? "3px solid var(--k-blue)" : "3px solid transparent",
                  }}
                  onMouseEnter={e => !isSelected && (e.currentTarget.style.background = "#f0f9ff")}
                  onMouseLeave={e => !isSelected && (e.currentTarget.style.background = i % 2 === 0 ? "#fff" : "#f9fafb")}
                >
                  <td style={{ ...td, fontWeight: 700 }}>{ind.id}</td>
                  <td style={{ ...td, maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {ind.title}
                  </td>
                  <td style={{ ...td, textAlign: "center" }}>
                    <span style={{
                      fontWeight: 700, fontSize: 14,
                      color: ind.readiness_score >= 70 ? "#10b981" : ind.readiness_score >= 40 ? "#f59e0b" : "#ef4444",
                    }}>
                      {ind.readiness_score}
                    </span>
                  </td>
                  <td style={{ ...td, textAlign: "center" }}>
                    <span style={{
                      display: "inline-block", padding: "2px 9px", borderRadius: 9999,
                      fontSize: 11, fontWeight: 600,
                      background: rc.bg, color: rc.text,
                    }}>
                      {rc.label}
                    </span>
                  </td>
                  <td style={td}>
                    {missingCount > 0
                      ? <span style={{ color: "#ef4444", fontSize: 12 }}>
                          {missingCount} veld{missingCount !== 1 ? "en" : ""}
                        </span>
                      : <span style={{ color: "#10b981", fontSize: 12 }}>✓ Compleet</span>}
                  </td>
                  <td style={td}>
                    {ind.blocking_issues.length > 0
                      ? <span style={{ color: "#ef4444", fontSize: 12 }}>
                          {ind.blocking_issues.length} blokkade{ind.blocking_issues.length !== 1 ? "s" : ""}
                        </span>
                      : ind.warnings.length > 0
                        ? <span style={{ color: "#f59e0b", fontSize: 12 }}>
                            {ind.warnings.length} waarschuwing{ind.warnings.length !== 1 ? "en" : ""}
                          </span>
                        : <span style={{ color: "#10b981", fontSize: 12 }}>✓ Schoon</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filteredIndicators.length > 0 && (
          <div style={{ padding: "8px 16px", fontSize: 12, color: "#9ca3af", borderTop: "1px solid #f3f4f6", textAlign: "right" }}>
            {filteredIndicators.length} van {matrix.total_indicators} indicatoren
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Shared styles ────────────────────────────────────────────────────────────

const th = {
  padding: "9px 14px", fontWeight: 700, fontSize: 12,
  color: "#374151", borderBottom: "1px solid #e5e7eb", textAlign: "left",
};
const td = {
  padding: "9px 14px", borderBottom: "1px solid #f3f4f6", verticalAlign: "middle",
};
const backBtn = {
  background: "#f3f4f6", border: "1px solid #d1d5db",
  borderRadius: 7, padding: "7px 14px", cursor: "pointer",
  fontWeight: 600, fontSize: 13, color: "#374151",
};
