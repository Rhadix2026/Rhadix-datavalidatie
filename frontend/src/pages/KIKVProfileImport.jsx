import { useState, useEffect, useMemo } from "react";

// ─── API helpers ──────────────────────────────────────────────────────────────

const API = import.meta.env.VITE_API_URL ?? "";

async function apiGet(path) {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
  return r.json();
}

async function apiPost(path, body) {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
  return r.json();
}

async function apiDelete(path) {
  const r = await fetch(`${API}${path}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
  return r.json();
}

// ─── Small UI atoms ───────────────────────────────────────────────────────────

function Badge({ color, children }) {
  const palettes = {
    green:  { bg: "#d1fae5", text: "#065f46", border: "#6ee7b7" },
    amber:  { bg: "#fef3c7", text: "#92400e", border: "#fcd34d" },
    red:    { bg: "#fee2e2", text: "#991b1b", border: "#fca5a5" },
    blue:   { bg: "#dbeafe", text: "#1e40af", border: "#93c5fd" },
    grey:   { bg: "#f3f4f6", text: "#6b7280", border: "#d1d5db" },
  };
  const p = palettes[color] || palettes.grey;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "2px 8px", borderRadius: 9999, fontSize: 12, fontWeight: 600,
      background: p.bg, color: p.text, border: `1px solid ${p.border}`,
    }}>
      {children}
    </span>
  );
}

function Pill({ present, label }) {
  return present
    ? <Badge color="green">✓ {label}</Badge>
    : <Badge color="grey">– {label}</Badge>;
}

function Spinner() {
  return (
    <span style={{ display: "inline-block", animation: "spin 1s linear infinite", fontSize: 18 }}>
      ⟳
    </span>
  );
}

// ─── Indicator detail row (expandable) ───────────────────────────────────────

function IndicatorRow({ ind, index }) {
  const [open, setOpen] = useState(false);
  const meta = ind.metadata || {};
  const files = ind.files || {};

  const hasSparql   = !!files.sparql;
  const hasMarkdown = !!files.markdown;
  const hasTurtle   = !!files.turtle;

  const selectVars = meta.select_vars || [];
  const predicates = (meta.predicates || []).slice(0, 12);
  const filters    = meta.filters || [];
  const groupBy    = meta.group_by_vars || [];
  const dateLogic  = meta.date_logic || [];
  const params     = (meta.parameters || []).slice(0, 10);
  const rdfClasses = (meta.rdf_classes || []).slice(0, 10);

  return (
    <>
      <tr
        onClick={() => setOpen(o => !o)}
        style={{
          cursor: "pointer",
          background: index % 2 === 0 ? "#fff" : "#f9fafb",
          transition: "background 0.15s",
        }}
        onMouseEnter={e => e.currentTarget.style.background = "#eff6ff"}
        onMouseLeave={e => e.currentTarget.style.background = index % 2 === 0 ? "#fff" : "#f9fafb"}
      >
        <td style={{ ...td, whiteSpace: "nowrap" }}>
          {open ? "▾" : "▸"}
          <span style={{
            marginLeft: 6, fontSize: 11, fontWeight: 700,
            padding: "2px 7px", borderRadius: 9999,
            background: "#eff6ff", color: "#1d4ed8",
            border: "1px solid #bfdbfe",
          }}>{ind.id}</span>
        </td>
        <td style={td}>
          {meta.title
            ? <span style={{ fontWeight: 600, color: "#1e3a5f" }}>{meta.title}</span>
            : <span style={{ color: "#9ca3af", fontStyle: "italic" }}>Geen omschrijving — herlaad profiel</span>}
        </td>
        <td style={{ ...td, textAlign: "center" }}><Pill present={hasMarkdown} label=".md" /></td>
        <td style={{ ...td, textAlign: "center" }}><Pill present={hasSparql}   label=".rq" /></td>
        <td style={{ ...td, textAlign: "center" }}><Pill present={hasTurtle}   label=".ttl" /></td>
        <td style={{ ...td, textAlign: "center" }}>
          {selectVars.length > 0
            ? <Badge color="blue">{selectVars.length} var{selectVars.length !== 1 ? "s" : ""}</Badge>
            : <span style={{ color: "#9ca3af" }}>—</span>}
        </td>
        <td style={{ ...td, textAlign: "center" }}>
          {dateLogic.length > 0
            ? <Badge color="amber">📅 {dateLogic.join(", ")}</Badge>
            : <span style={{ color: "#9ca3af" }}>—</span>}
        </td>
      </tr>

      {open && (
        <tr style={{ background: "#f0f9ff" }}>
          <td colSpan={7} style={{ padding: "12px 20px 16px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>

              {/* SPARQL details */}
              <div>
                <div style={sectionTitle}>SPARQL</div>
                {hasSparql ? (
                  <>
                    <MetaRow label="SELECT vars"   value={selectVars.join(", ") || "—"} />
                    <MetaRow label="Parameters"    value={params.join(", ")     || "—"} />
                    <MetaRow label="Predicaten"    value={predicates.join(", ") || "—"} />
                    <MetaRow label="FILTER"        value={filters.length ? `${filters.length} filter(s)` : "—"} />
                    <MetaRow label="GROUP BY"      value={groupBy.join(", ")    || "—"} />
                    <MetaRow label="Datum-logica"  value={dateLogic.join(", ")  || "—"} />
                    {meta.limit != null && <MetaRow label="LIMIT" value={String(meta.limit)} />}
                  </>
                ) : <span style={{ color: "#9ca3af", fontSize: 13 }}>Geen SPARQL-bestand</span>}
              </div>

              {/* Markdown / description */}
              <div>
                <div style={sectionTitle}>Documentatie</div>
                {hasMarkdown ? (
                  <>
                    <MetaRow label="Titel"        value={meta.title       || "—"} />
                    {meta.description && <MetaRow label="Omschrijving" value={meta.description} />}
                    {meta.sections && meta.sections.length > 0 &&
                      <MetaRow label="Secties" value={meta.sections.join(" · ")} />}
                    {Object.entries(meta.kv_pairs || {}).slice(0, 6).map(([k, v]) => (
                      <MetaRow key={k} label={k} value={v} />
                    ))}
                    {(meta.concepts || []).length > 0 && (
                      <div style={{ marginTop: 8 }}>
                        <div style={{ fontWeight: 600, fontSize: 12, color: "#374151", marginBottom: 4 }}>Concepten:</div>
                        {(meta.concepts || []).slice(0, 6).map((c, i) => (
                          <div key={i} style={{ fontSize: 12, color: "#4b5563", marginBottom: 2 }}>
                            • <a href={c.uri} target="_blank" rel="noreferrer" style={{ color: "#3b82f6" }}>{c.label}</a>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                ) : <span style={{ color: "#9ca3af", fontSize: 13 }}>Geen markdown-bestand</span>}
              </div>

              {/* Turtle / RDF */}
              <div>
                <div style={sectionTitle}>RDF / Turtle</div>
                {hasTurtle ? (
                  <>
                    <MetaRow label="Klassen"      value={rdfClasses.join(", ") || "—"} />
                    {(meta.subclass_relations || []).slice(0, 4).map((r, i) => (
                      <MetaRow key={i} label="subClassOf" value={`${r.child} → ${r.parent}`} />
                    ))}
                  </>
                ) : <span style={{ color: "#9ca3af", fontSize: 13 }}>Geen Turtle-bestand</span>}
              </div>
            </div>

            {/* FILTER details */}
            {filters.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <div style={sectionTitle}>FILTER-expressies</div>
                {filters.map((f, i) => (
                  <code key={i} style={{
                    display: "block", fontSize: 12, background: "#1e293b", color: "#e2e8f0",
                    padding: "4px 8px", borderRadius: 4, marginBottom: 4,
                    fontFamily: "monospace", whiteSpace: "pre-wrap", wordBreak: "break-all",
                  }}>
                    {f}
                  </code>
                ))}
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

function MetaRow({ label, value }) {
  return (
    <div style={{ marginBottom: 4, fontSize: 13 }}>
      <span style={{ fontWeight: 600, color: "#374151", minWidth: 110, display: "inline-block" }}>{label}: </span>
      <span style={{ color: "#4b5563" }}>{value}</span>
    </div>
  );
}

// ─── Profile catalog ──────────────────────────────────────────────────────────
// Bekende KIK-V uitwisselprofielen. Voeg hier nieuwe toe naarmate ze beschikbaar komen.

// Bron: https://kik-v-publicatieplatform.nl/uitwisselprofielen + GitLab kik-v/uitwisselprofielen
const PROFILE_CATALOG = [

  // ── Zorgkantoren ──────────────────────────────────────────────────────────
  {
    id:          "zorgkantoren",
    name:        "Uitwisselprofiel Zorgkantoren Inkoopondersteuning en beleidsontwikkeling",
    short:       "ZK-IB",
    description: "Kwaliteitsindicatoren voor Wlz-uitvoering door zorgkantoren. Dekt medewerker, cliënt, financiën en zorgproces.",
    sector:      "Zorgkantoren",
    sectorColor: "#0ea5e9",
    repo:        "kik-v/uitwisselprofielen/uitwisselprofiel-zorgkantoren",
    ref:         "1.3.4",
    folder:      "Gevalideerde_vragen_technisch",
    icon:        "🏦",
    published:   true,
  },
  {
    id:          "zorgkantoren-clientinformatie",
    name:        "Uitwisselprofiel Zorgkantoren Ondersteuning cliëntkeuze",
    short:       "ZK-CI",
    description: "Ondersteuning van cliëntkeuze bij verpleging en verzorging vanuit zorgkantoorperspectief.",
    sector:      "Zorgkantoren",
    sectorColor: "#0ea5e9",
    repo:        "kik-v/uitwisselprofielen/uitwisselprofiel-zorgkantoren-clientinformatie",
    ref:         "0.0.1",
    folder:      "Gevalideerde_vragen_technisch",
    icon:        "🏦",
    comingSoon:  true,
  },

  // ── IGJ ───────────────────────────────────────────────────────────────────
  {
    id:          "igj-aangekondigd",
    name:        "Uitwisselprofiel IGJ Contextinformatie t.b.v. aangekondigd inspectiebezoek",
    short:       "IGJ-A",
    description: "Contextinformatie voor de Inspectie Gezondheidszorg en Jeugd bij een aangekondigd inspectiebezoek.",
    sector:      "IGJ",
    sectorColor: "#ef4444",
    repo:        "kik-v/uitwisselprofielen/uitwisselprofiel-igj-contextinformatie-aangekondigd-inspectiebezoek",
    ref:         "1.0.0",
    folder:      "Gevalideerde_vragen_technisch",
    icon:        "🔍",
    published:   true,
  },
  {
    id:          "igj-onaangekondigd",
    name:        "Uitwisselprofiel IGJ Contextinformatie t.b.v. onaangekondigd inspectiebezoek",
    short:       "IGJ-O",
    description: "Contextinformatie voor de Inspectie Gezondheidszorg en Jeugd bij een onaangekondigd inspectiebezoek.",
    sector:      "IGJ",
    sectorColor: "#ef4444",
    repo:        "kik-v/uitwisselprofielen/uitwisselprofiel-igj-contextinformatie-onaangekondigd-inspectiebezoek",
    ref:         "1.2.0",
    folder:      "Gevalideerde_vragen_technisch",
    icon:        "🔍",
    published:   true,
  },

  // ── NZa ───────────────────────────────────────────────────────────────────
  {
    id:          "nza-kostenonderzoek",
    name:        "Uitwisselprofiel NZa Basisinformatie kostenonderzoek",
    short:       "NZa-K",
    description: "Basisinformatie voor het kostenonderzoek van de Nederlandse Zorgautoriteit.",
    sector:      "NZa",
    sectorColor: "#f59e0b",
    repo:        "kik-v/uitwisselprofielen/uitwisselprofiel-nza",
    ref:         "1.1.1",
    folder:      "Gevalideerde_vragen_technisch",
    icon:        "📊",
    published:   true,
  },
  {
    id:          "nza-wmg",
    name:        "Uitwisselprofiel NZa Structurele Informatieverstrekking Bedrijfsvoering Wmg",
    short:       "NZa-W",
    description: "Structurele informatieverstrekking over bedrijfsvoering op grond van de Wet marktordening gezondheidszorg.",
    sector:      "NZa",
    sectorColor: "#f59e0b",
    repo:        "kik-v/uitwisselprofielen/uitwisselprofiel-nza-structurele-informatieverstrekking-bedrijfsvoering-wmg",
    ref:         "1.1.1",
    folder:      "Gevalideerde_vragen_technisch",
    icon:        "📊",
    published:   true,
  },

  // ── Ministerie van VWS ────────────────────────────────────────────────────
  {
    id:          "vws-jaarverantwoording",
    name:        "Uitwisselprofiel Ministerie van VWS Jaarverantwoording Zorg",
    short:       "VWS-JV",
    description: "Jaarverantwoording van zorginstellingen aan het Ministerie van Volksgezondheid, Welzijn en Sport.",
    sector:      "VWS",
    sectorColor: "#8b5cf6",
    repo:        "kik-v/uitwisselprofielen/uitwisselprofiel-ministerie-van-vws-jaarverantwoording-zorg",
    ref:         "1.1.1",
    folder:      "Gevalideerde_vragen_technisch",
    icon:        "🏛️",
    published:   true,
  },
  {
    id:          "vws-beleidsontwikkeling",
    name:        "Uitwisselprofiel Ministerie van VWS Beleidsontwikkeling over Macro-Economische Vraagstukken en Arbeidsmarkt",
    short:       "VWS-MEVA",
    description: "Beleidsontwikkeling en -monitoring voor macro-economische vraagstukken en arbeidsmarkt in de zorg.",
    sector:      "VWS",
    sectorColor: "#8b5cf6",
    repo:        "kik-v/uitwisselprofielen/uitwisselprofiel-vws-beleidsinformatie",
    ref:         "1.1.1",
    folder:      "Gevalideerde_vragen_technisch",
    icon:        "🏛️",
    published:   true,
  },

  // ── ActiZ ─────────────────────────────────────────────────────────────────
  {
    id:          "actiz",
    name:        "Uitwisselprofiel ActiZ Belangenbehartiging",
    short:       "ActiZ",
    description: "Kwaliteits- en bedrijfsvoeringsinformatie ten behoeve van belangenbehartiging door ActiZ voor de VVT-sector.",
    sector:      "ActiZ",
    sectorColor: "#10b981",
    repo:        "kik-v/uitwisselprofielen/uitwisselprofiel-actiz-belangenbehartiging",
    ref:         "1.3.0",
    folder:      "Gevalideerde_vragen_technisch",
    icon:        "🤝",
    published:   true,
  },

  // ── Zorginstituut Nederland ───────────────────────────────────────────────
  {
    id:          "odb",
    name:        "Uitwisselprofiel Zorginstituut Openbaarmaking kwaliteitsindicatoren verpleeghuiszorg",
    short:       "ODB",
    description: "Openbaarmaking van kwaliteitsindicatoren voor verpleeghuiszorg door het Zorginstituut Nederland.",
    sector:      "Zorginstituut",
    sectorColor: "#06b6d4",
    repo:        "kik-v/uitwisselprofielen/uitwisselprofiel-odb",
    ref:         "ZIN_ODB_Test",
    folder:      "Gevalideerde_vragen_technisch",
    icon:        "📋",
    comingSoon:  true,
  },
]

// ─── Custom import form (advanced) ────────────────────────────────────────────

function CustomImportForm({ onImported, prefill }) {
  const [repo,   setRepo]   = useState(prefill?.repo   || "");
  const [ref,    setRef]    = useState(prefill?.ref    || "");
  const [folder, setFolder] = useState(prefill?.folder || "Gevalideerde_vragen_technisch");
  const [token,  setToken]  = useState("");
  const [name,   setName]   = useState(prefill?.name   || "");
  const [loading, setLoading] = useState(false);
  const [error,  setError]  = useState(null);

  async function handleImport(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const result = await apiPost("/api/profiles/import-gitlab", {
        repo, ref, folder,
        token: token || null,
        name:  name  || null,
      })
      onImported(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleImport} style={{ marginTop: 12 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
        <label style={labelStyle}>
          Repository pad
          <input style={inputStyle} value={repo} onChange={e => setRepo(e.target.value)} required placeholder="kik-v/uitwisselprofielen/..." />
        </label>
        <label style={labelStyle}>
          Ref / tag
          <input style={inputStyle} value={ref} onChange={e => setRef(e.target.value)} required placeholder="1.0.0" />
        </label>
        <label style={labelStyle}>
          Map in repository
          <input style={inputStyle} value={folder} onChange={e => setFolder(e.target.value)} required />
        </label>
        <label style={labelStyle}>
          Profielnaam
          <input style={inputStyle} value={name} onChange={e => setName(e.target.value)} placeholder="Mijn profiel" />
        </label>
      </div>
      <label style={{ ...labelStyle, marginBottom: 10, display: "block" }}>
        GitLab token (optioneel)
        <input style={inputStyle} type="password" value={token} onChange={e => setToken(e.target.value)} placeholder="glpat-..." />
      </label>
      {error && (
        <div style={{ background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: 6, padding: "8px 12px", marginBottom: 10, color: "#991b1b", fontSize: 12 }}>
          ⚠ {error}
        </div>
      )}
      <button type="submit" disabled={loading} style={{
        background: loading ? "#93c5fd" : "#1d4ed8", color: "#fff",
        border: "none", borderRadius: 7, padding: "9px 20px",
        fontWeight: 700, fontSize: 13, cursor: loading ? "not-allowed" : "pointer",
        display: "flex", alignItems: "center", gap: 8,
      }}>
        {loading ? <><Spinner /> Importeren…</> : "▶ Importeer uit GitLab"}
      </button>
    </form>
  )
}

// ─── Catalog card ─────────────────────────────────────────────────────────────

function CatalogCard({ entry, imported, selected, onImport, onSelect, onDelete, loading }) {
  const isImported = !!imported

  return (
    <div style={{
      background: selected ? "#eff6ff" : "#fff",
      border: `2px solid ${selected ? "#3b82f6" : isImported ? "#bbf7d0" : "#e5e7eb"}`,
      borderRadius: 10, padding: "14px 16px", marginBottom: 10,
      transition: "border-color 0.2s",
      opacity: entry.comingSoon && !isImported ? 0.65 : 1,
    }}>
      {/* Top row: icon + name + sector badge */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 6 }}>
        <span style={{ fontSize: 22, lineHeight: 1 }}>{entry.icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 13, color: "#1e3a5f", lineHeight: 1.3 }}>
            {entry.name}
          </div>
          <div style={{ display: "flex", gap: 6, marginTop: 4, flexWrap: "wrap' " }}>
            <span style={{
              fontSize: 11, fontWeight: 700, padding: "1px 7px", borderRadius: 9999,
              background: entry.sectorColor + "22", color: entry.sectorColor,
              border: `1px solid ${entry.sectorColor}55`,
            }}>{entry.sector}</span>
            {entry.published && !isImported && (
              <span style={{ fontSize: 11, fontWeight: 600, padding: "1px 7px", borderRadius: 9999, background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe" }}>
                Gepubliceerd v{entry.ref}
              </span>
            )}
            {entry.comingSoon && !isImported && (
              <span style={{ fontSize: 11, fontWeight: 600, padding: "1px 7px", borderRadius: 9999, background: "#f3f4f6", color: "#9ca3af", border: "1px solid #e5e7eb" }}>
                In ontwikkeling
              </span>
            )}
            {isImported && (
              <span style={{ fontSize: 11, fontWeight: 600, padding: "1px 7px", borderRadius: 9999, background: "#d1fae5", color: "#065f46", border: "1px solid #6ee7b7" }}>
                ✓ v{imported.version}
              </span>
            )}
          </div>
        </div>
        {isImported && (
          <button
            onClick={e => { e.stopPropagation(); onDelete(imported.filename) }}
            title="Verwijder profiel"
            style={{ background: "none", border: "1px solid #fca5a5", borderRadius: 6, color: "#ef4444", padding: "3px 7px", cursor: "pointer", fontSize: 11, flexShrink: 0 }}
          >✕</button>
        )}
      </div>

      {/* Description */}
      <div style={{ fontSize: 12, color: "#6b7280", lineHeight: 1.5, marginBottom: 10 }}>
        {entry.description}
      </div>

      {/* Footer row */}
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        {isImported ? (
          <>
            <button
              onClick={() => onSelect(imported)}
              style={{
                flex: 1, background: selected ? "#1d4ed8" : "#eff6ff",
                color: selected ? "#fff" : "#1d4ed8",
                border: `1px solid ${selected ? "#1d4ed8" : "#bfdbfe"}`,
                borderRadius: 6, padding: "6px 12px", fontWeight: 700,
                fontSize: 12, cursor: "pointer",
              }}
            >
              {selected ? "✓ Geselecteerd" : "Selecteer"}
            </button>
            <button
              onClick={() => onImport(entry)}
              disabled={loading}
              title="Opnieuw importeren (update)"
              style={{
                background: "none", border: "1px solid #d1d5db", borderRadius: 6,
                color: "#6b7280", padding: "6px 10px", cursor: loading ? "not-allowed" : "pointer",
                fontSize: 12,
              }}
            >
              {loading ? <Spinner /> : "↻ Update"}
            </button>
          </>
        ) : entry.comingSoon ? (
          <span style={{ fontSize: 12, color: "#9ca3af" }}>Nog niet beschikbaar in GitLab</span>
        ) : (
          <button
            onClick={() => onImport(entry)}
            disabled={loading}
            style={{
              flex: 1, background: loading ? "#93c5fd" : "#1d4ed8", color: "#fff",
              border: "none", borderRadius: 6, padding: "6px 12px",
              fontWeight: 700, fontSize: 12, cursor: loading ? "not-allowed" : "pointer",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
            }}
          >
            {loading ? <><Spinner /> Importeren…</> : "▶ Importeer"}
          </button>
        )}
      </div>

      {/* Import date */}
      {isImported && imported.imported_at && (
        <div style={{ fontSize: 11, color: "#9ca3af", marginTop: 6 }}>
          Geïmporteerd op {new Date(imported.imported_at).toLocaleString("nl-NL")}
          &nbsp;· {imported.indicator_count} indicatoren
        </div>
      )}
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function KIKVProfileImport({ onBack, onAnalyze, scanResult }) {
  const [profiles,      setProfiles]      = useState([])
  const [selected,      setSelected]      = useState(null)      // profile summary
  const [fullData,      setFullData]      = useState(null)      // full profile with indicators
  const [loadingFull,   setLoadingFull]   = useState(false)
  const [loadingId,     setLoadingId]     = useState(null)      // catalog entry currently importing
  const [reparsing,     setReparsing]     = useState(false)
  const [search,        setSearch]        = useState("")
  const [showCustom,    setShowCustom]    = useState(false)
  const [pageErr,       setPageErr]       = useState(null)

  // ── Load profile list ──
  useEffect(() => {
    apiGet("/api/profiles/")
      .then(setProfiles)
      .catch(err => setPageErr(err.message))
  }, [])

  // ── Load full profile when summary selected ──
  useEffect(() => {
    if (!selected) { setFullData(null); return }
    setLoadingFull(true)
    setFullData(null)
    apiGet(`/api/profiles/${encodeURIComponent(selected.filename)}`)
      .then(setFullData)
      .catch(err => setPageErr(err.message))
      .finally(() => setLoadingFull(false))
  }, [selected])

  // Match catalog entry → saved profile by repo path or name
  function findImported(entry) {
    return profiles.find(p => {
      // Strongest match: source URL contains the repo path
      if (p.source && p.source.includes(entry.repo)) return true
      // Match by stored source/folder/ref metadata
      if (p.folder && p.ref && p.source &&
          p.source.includes(entry.repo.split("/").pop()) &&
          p.ref === entry.ref) return true
      // Fuzzy name match: normalize both to lowercase, strip punctuation
      const normalize = s => (s || "").toLowerCase().replace(/[^a-z0-9]/g, "")
      if (normalize(p.name) === normalize(entry.name)) return true
      // Short code match for catalog entries with unique short codes
      if (entry.short && normalize(p.name).includes(normalize(entry.short))) return true
      return false
    }) || null
  }

  async function handleCatalogImport(entry) {
    setLoadingId(entry.id)
    setPageErr(null)
    try {
      await apiPost("/api/profiles/import-gitlab", {
        repo:   entry.repo,
        ref:    entry.ref,
        folder: entry.folder,
        name:   entry.name,
        token:  null,
      })
      const updated = await apiGet("/api/profiles/")
      setProfiles(updated)
      // Auto-select the freshly imported profile
      const fresh = updated.find(p =>
        (p.source && p.source.includes(entry.repo)) ||
        (p.name || "").toLowerCase() === entry.name.toLowerCase()
      )
      if (fresh) setSelected(fresh)
    } catch (err) {
      setPageErr(err.message)
    } finally {
      setLoadingId(null)
    }
  }

  async function handleCustomImported() {
    setShowCustom(false)
    const updated = await apiGet("/api/profiles/").catch(() => profiles)
    setProfiles(updated)
  }

  async function handleReparseAll() {
    if (!profiles.length) return
    setReparsing(true)
    setPageErr(null)
    try {
      await Promise.all(
        profiles.map(p => apiPost(`/api/profiles/${encodeURIComponent(p.filename)}/reparse`, {}))
      )
      const updated = await apiGet("/api/profiles/")
      setProfiles(updated)
      // Reload full data if something is selected
      if (selected) {
        const fresh = await apiGet(`/api/profiles/${encodeURIComponent(selected.filename)}`)
        setFullData(fresh)
      }
    } catch (err) {
      setPageErr("Herparse mislukt: " + err.message)
    } finally {
      setReparsing(false)
    }
  }

  function handleDelete(filename) {
    if (!confirm(`Profiel "${filename}" verwijderen?`)) return
    apiDelete(`/api/profiles/${encodeURIComponent(filename)}`)
      .then(() => {
        if (selected?.filename === filename) { setSelected(null); setFullData(null) }
        setProfiles(p => p.filter(x => x.filename !== filename))
      })
      .catch(err => setPageErr(err.message))
  }

  // ── Filter indicators ──
  const indicators = useMemo(() => {
    if (!fullData?.indicators) return []
    const q = search.trim().toLowerCase()
    return Object.values(fullData.indicators).filter(ind => {
      if (!q) return true
      const title = (ind.metadata?.title || "").toLowerCase()
      return ind.id.toLowerCase().includes(q) || title.includes(q)
    })
  }, [fullData, search])

  // ── Stats ──
  const statHasSparql   = indicators.filter(i => !!i.files?.sparql).length
  const statHasMarkdown = indicators.filter(i => !!i.files?.markdown).length
  const statHasTurtle   = indicators.filter(i => !!i.files?.turtle).length
  const statHasDate     = indicators.filter(i => (i.metadata?.date_logic || []).length > 0).length

  // Count imported vs total published profiles
  const publishedCount = PROFILE_CATALOG.filter(e => !e.comingSoon).length
  const importedCount  = PROFILE_CATALOG.filter(e => !e.comingSoon && !!findImported(e)).length

  return (
    <div style={{ maxWidth: 1280, margin: "0 auto", padding: "24px 20px", fontFamily: "Inter, sans-serif" }}>

      {/* ── Header ── */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
        {onBack && <button onClick={onBack} style={backBtn}>← Terug</button>}
        <div style={{ flex: 1 }}>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: "#1e3a5f" }}>
            📚 KIK-V Profielbibliotheek
          </h1>
          <div style={{ fontSize: 13, color: "#6b7280", marginTop: 2 }}>
            Importeer en beheer officiële KIK-V uitwisselprofielen uit GitLab
          </div>
        </div>
        <div style={{ textAlign: "right", display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
          <div>
            <span style={{ fontSize: 22, fontWeight: 800, color: "#1d4ed8" }}>{importedCount}/{publishedCount}</span>
            <div style={{ fontSize: 11, color: "#9ca3af" }}>gepubliceerde profielen geïmporteerd</div>
          </div>
          {profiles.length > 0 && (
            <button
              onClick={handleReparseAll}
              disabled={reparsing}
              title="Verwerk opgeslagen profielen opnieuw met de nieuwe parser (zonder GitLab)"
              style={{
                background: reparsing ? "#f3f4f6" : "#fff",
                border: "1px solid #d1d5db", borderRadius: 7,
                padding: "6px 12px", fontSize: 12, fontWeight: 600,
                color: reparsing ? "#9ca3af" : "#374151",
                cursor: reparsing ? "not-allowed" : "pointer",
                display: "flex", alignItems: "center", gap: 6,
              }}
            >
              {reparsing ? <><Spinner /> Herparseren…</> : "↻ Herparse alle profielen"}
            </button>
          )}
        </div>
      </div>

      {pageErr && (
        <div style={{ background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: 8, padding: "12px 16px", marginBottom: 20, color: "#991b1b" }}>
          ⚠ {pageErr}
          <button onClick={() => setPageErr(null)} style={{ float: "right", background: "none", border: "none", cursor: "pointer", color: "#ef4444" }}>✕</button>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 24, alignItems: "start" }}>

        {/* ── Left: library + catalog ── */}
        <div>
          {/* Catalog section */}
          <div style={{ fontWeight: 700, fontSize: 13, color: "#374151", marginBottom: 10, display: "flex", alignItems: "center", gap: 6 }}>
            <span>Beschikbare profielen</span>
            <span style={{ fontSize: 11, fontWeight: 500, color: "#9ca3af" }}>— klik om te importeren of selecteren</span>
          </div>

          {PROFILE_CATALOG.filter(e => !e.comingSoon).map(entry => {
            const imp = findImported(entry)
            return (
              <CatalogCard
                key={entry.id}
                entry={entry}
                imported={imp}
                selected={selected?.filename === imp?.filename}
                loading={loadingId === entry.id}
                onImport={handleCatalogImport}
                onSelect={setSelected}
                onDelete={handleDelete}
              />
            )
          })}

          {/* Extra (non-catalog) imported profiles */}
          {(() => {
            const catalogFilenames = new Set(
              PROFILE_CATALOG.map(e => findImported(e)?.filename).filter(Boolean)
            )
            const extras = profiles.filter(p => !catalogFilenames.has(p.filename))
            if (!extras.length) return null
            return (
              <>
                <div style={{ fontWeight: 700, fontSize: 13, color: "#374151", margin: "16px 0 10px" }}>
                  Overige geïmporteerde profielen
                </div>
                {extras.map(p => (
                  <div
                    key={p.filename}
                    onClick={() => setSelected(p)}
                    style={{
                      background: selected?.filename === p.filename ? "#eff6ff" : "#fff",
                      border: `2px solid ${selected?.filename === p.filename ? "#3b82f6" : "#e5e7eb"}`,
                      borderRadius: 9, padding: "12px 16px", cursor: "pointer", marginBottom: 8,
                      display: "flex", justifyContent: "space-between", alignItems: "flex-start",
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 13, color: "#1e3a5f" }}>{p.name}</div>
                      <div style={{ fontSize: 12, color: "#6b7280", marginTop: 2 }}>
                        v{p.version} · {p.indicator_count} indicatoren
                      </div>
                    </div>
                    <button onClick={e => { e.stopPropagation(); handleDelete(p.filename) }}
                      style={{ background: "none", border: "1px solid #fca5a5", borderRadius: 6, color: "#ef4444", padding: "3px 7px", cursor: "pointer", fontSize: 11 }}>✕</button>
                  </div>
                ))}
              </>
            )
          })()}

          {/* Custom/advanced import */}
          <div style={{ marginTop: 16, border: "1px solid #e5e7eb", borderRadius: 10, overflow: "hidden" }}>
            <button
              onClick={() => setShowCustom(v => !v)}
              style={{
                width: "100%", background: "#f9fafb", border: "none",
                padding: "10px 16px", textAlign: "left", cursor: "pointer",
                fontWeight: 600, fontSize: 13, color: "#374151",
                display: "flex", justifyContent: "space-between", alignItems: "center",
              }}
            >
              <span>⚙ Aangepast profiel importeren</span>
              <span style={{ fontSize: 16 }}>{showCustom ? "▾" : "▸"}</span>
            </button>
            {showCustom && (
              <div style={{ padding: "16px 16px 20px" }}>
                <CustomImportForm onImported={handleCustomImported} />
              </div>
            )}
          </div>
        </div>

        {/* ── Right: indicator table ── */}
        <div>
          {!selected && (
            <div style={{
              background: "#f9fafb", border: "1px dashed #d1d5db",
              borderRadius: 10, padding: 40, textAlign: "center", color: "#9ca3af",
            }}>
              Selecteer een profiel om de indicatoren te bekijken
            </div>
          )}

          {selected && loadingFull && (
            <div style={{ textAlign: "center", padding: 40, color: "#6b7280" }}>
              <Spinner /> Indicatoren laden…
            </div>
          )}

          {fullData && (
            <>
              {/* Summary bar */}
              <div style={{
                background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10,
                padding: "14px 20px", marginBottom: 16,
                display: "flex", flexWrap: "wrap", gap: 16, alignItems: "center",
              }}>
                <div>
                  <span style={{ fontSize: 28, fontWeight: 800, color: "#1d4ed8" }}>
                    {fullData.indicator_count}
                  </span>
                  <span style={{ fontSize: 13, color: "#6b7280", marginLeft: 6 }}>indicatoren</span>
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <Badge color="green">{statHasMarkdown} .md</Badge>
                  <Badge color="blue">{statHasSparql} .rq</Badge>
                  <Badge color="grey">{statHasTurtle} .ttl</Badge>
                  <Badge color="amber">{statHasDate} datum-logica</Badge>
                  {fullData.parse_errors?.length > 0 &&
                    <Badge color="red">{fullData.parse_errors.length} parseerfout{fullData.parse_errors.length !== 1 ? "en" : ""}</Badge>}
                </div>
                <div style={{ marginLeft: "auto", fontSize: 12, color: "#9ca3af" }}>
                  Bron: <a href={fullData.source} target="_blank" rel="noreferrer" style={{ color: "#3b82f6" }}>{fullData.source}</a>
                  &nbsp;· ref <strong>{fullData.ref}</strong>
                  &nbsp;· map <code style={{ fontSize: 11 }}>{fullData.folder}</code>
                </div>
              </div>

              {/* Parse errors */}
              {fullData.parse_errors?.length > 0 && (
                <details style={{
                  background: "#fffbeb", border: "1px solid #fcd34d",
                  borderRadius: 8, padding: "10px 16px", marginBottom: 14,
                }}>
                  <summary style={{ cursor: "pointer", fontWeight: 700, color: "#92400e", fontSize: 13 }}>
                    ⚠ {fullData.parse_errors.length} bestand{fullData.parse_errors.length !== 1 ? "en" : ""} kon niet worden geparseerd
                  </summary>
                  <div style={{ marginTop: 10 }}>
                    {fullData.parse_errors.map((e, i) => (
                      <div key={i} style={{ fontSize: 12, color: "#78350f", marginBottom: 4 }}>
                        <strong>{e.indicator_id}</strong> / {e.filename}: {e.error}
                      </div>
                    ))}
                  </div>
                </details>
              )}

              {/* Search */}
              <div style={{ marginBottom: 12 }}>
                <input
                  style={{
                    width: "100%", boxSizing: "border-box",
                    border: "1px solid #d1d5db", borderRadius: 7,
                    padding: "8px 12px", fontSize: 13, outline: "none",
                  }}
                  placeholder="Zoek op indicator ID of titel…"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                />
              </div>

              {/* Indicator table */}
              <div style={{
                background: "#fff", border: "1px solid #e5e7eb",
                borderRadius: 10, overflow: "hidden",
              }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: "#f1f5f9", textAlign: "left" }}>
                      <th style={th}>Indicator ID</th>
                      <th style={th}>Titel</th>
                      <th style={{ ...th, textAlign: "center" }}>Docs</th>
                      <th style={{ ...th, textAlign: "center" }}>SPARQL</th>
                      <th style={{ ...th, textAlign: "center" }}>Turtle</th>
                      <th style={{ ...th, textAlign: "center" }}>Uitvoer</th>
                      <th style={{ ...th, textAlign: "center" }}>Datum</th>
                    </tr>
                  </thead>
                  <tbody>
                    {indicators.length === 0 ? (
                      <tr>
                        <td colSpan={7} style={{ padding: 24, textAlign: "center", color: "#9ca3af" }}>
                          Geen indicatoren gevonden{search ? ` voor "${search}"` : ""}
                        </td>
                      </tr>
                    ) : (
                      indicators.map((ind, i) => (
                        <IndicatorRow key={ind.id} ind={ind} index={i} />
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Gereedheid analyse */}
              {onAnalyze && scanResult && (
                <div style={{
                  marginTop: 16,
                  background: "#eff6ff", border: "1px solid #bfdbfe",
                  borderRadius: 8, padding: "12px 16px",
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 13, color: "#1e40af" }}>
                      📊 Gereedheidsmatrix beschikbaar
                    </div>
                    <div style={{ fontSize: 12, color: "#3b82f6", marginTop: 2 }}>
                      Analyseer welke indicatoren ondersteund worden door de huidig geüploade data
                    </div>
                  </div>
                  <button
                    onClick={() => onAnalyze(selected?.filename, fullData)}
                    style={{
                      background: "#1d4ed8", color: "#fff", border: "none",
                      borderRadius: 7, padding: "9px 18px", fontWeight: 700,
                      fontSize: 13, cursor: "pointer", whiteSpace: "nowrap",
                    }}
                  >
                    📊 Analyseer gereedheid →
                  </button>
                </div>
              )}

              {search && (
                <div style={{ fontSize: 12, color: "#9ca3af", marginTop: 6, textAlign: "right" }}>
                  {indicators.length} van {fullData.indicator_count} indicatoren
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

// ─── Shared styles ────────────────────────────────────────────────────────────

const th = {
  padding: "10px 14px", fontWeight: 700, fontSize: 12,
  color: "#374151", borderBottom: "1px solid #e5e7eb",
};
const td = {
  padding: "9px 14px", borderBottom: "1px solid #f3f4f6", verticalAlign: "middle",
};
const sectionTitle = {
  fontWeight: 700, fontSize: 12, color: "#1e3a5f",
  textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6,
};
const labelStyle = {
  display: "flex", flexDirection: "column", gap: 4,
  fontSize: 13, fontWeight: 600, color: "#374151",
};
const inputStyle = {
  border: "1px solid #d1d5db", borderRadius: 6, padding: "7px 10px",
  fontSize: 13, outline: "none", fontFamily: "inherit",
};
const backBtn = {
  background: "#f3f4f6", border: "1px solid #d1d5db",
  borderRadius: 7, padding: "7px 14px", cursor: "pointer",
  fontWeight: 600, fontSize: 13, color: "#374151",
};
