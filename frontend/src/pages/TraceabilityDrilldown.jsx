import { useState, useMemo } from 'react'
import { NavBack, Page } from '../components/UI'

// ─── Constanten ──────────────────────────────────────────────────────────────
const LAYER_LABELS = {
  prescan:          'Pre-scan',
  availability:     'Beschikbaarheid',
  quality:          'Kwaliteit',
  concept_mapping:  'Ontologie',
  actuality:        'Actualiteit',
  zib_availability: 'ZIB Beschikbaarheid',
  zib_quality:      'ZIB Kwaliteit',
}

const SEV_COLOR = { error: '#dc2626', warning: '#d97706', info: '#6b7280' }
const SEV_BG    = { error: '#fef2f2', warning: '#fffbeb', info: '#f9fafb' }

const PAGE_SIZE = 50

// ─── Hulpcomponenten ─────────────────────────────────────────────────────────
function Badge({ text, color = '#6b7280', bg = '#f3f4f6' }) {
  if (!text) return null
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 10,
      fontSize: 11, fontWeight: 600, color, background: bg,
      border: `1px solid ${color}33`,
    }}>{text}</span>
  )
}

function FilterSelect({ label, value, onChange, options }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1, minWidth: 140 }}>
      <span style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{
          padding: '7px 10px', borderRadius: 6, border: '1px solid #d1d5db',
          fontSize: 13, color: '#374151', background: '#fff', cursor: 'pointer',
        }}
      >
        <option value="">Alle</option>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    </label>
  )
}

function SearchBox({ value, onChange }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 2, minWidth: 200 }}>
      <span style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Zoek</span>
      <input
        type="text"
        placeholder="Bestand, kolom, waarde, melding…"
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{
          padding: '7px 10px', borderRadius: 6, border: '1px solid #d1d5db',
          fontSize: 13, color: '#374151',
        }}
      />
    </label>
  )
}

// ─── Tabel-rij ───────────────────────────────────────────────────────────────
function IssueRow({ issue, idx }) {
  const [open, setOpen] = useState(false)
  const sev = issue.severity || 'info'
  const color = SEV_COLOR[sev] || '#6b7280'
  const bg    = SEV_BG[sev]   || '#f9fafb'

  return (
    <>
      <tr
        onClick={() => setOpen(o => !o)}
        style={{
          background: idx % 2 === 0 ? '#fff' : '#f9fafb',
          cursor: 'pointer',
          borderBottom: '1px solid #f3f4f6',
        }}
      >
        <td style={{ padding: '8px 10px', fontSize: 11, color: '#9ca3af', fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
          {issue.source_row ?? '—'}
        </td>
        <td style={{ padding: '8px 10px' }}>
          <Badge
            text={LAYER_LABELS[issue.validation_layer] || issue.validation_layer || '—'}
            color="var(--blue)" bg="var(--blue-light)"
          />
        </td>
        <td style={{ padding: '8px 10px' }}>
          <span style={{
            display: 'inline-block', padding: '2px 8px', borderRadius: 10,
            fontSize: 11, fontWeight: 700, color, background: bg,
            border: `1px solid ${color}33`,
          }}>{sev}</span>
        </td>
        <td style={{ padding: '8px 10px', fontSize: 12, color: '#374151', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
            title={issue.source_file}>
          {issue.source_file || '—'}
        </td>
        <td style={{ padding: '8px 10px', fontSize: 12, fontFamily: 'monospace', color: '#374151' }}>
          {issue.source_column || '—'}
        </td>
        <td style={{ padding: '8px 10px', fontSize: 12, color: '#374151', maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
            title={issue.current_value}>
          {issue.current_value || '—'}
        </td>
        <td style={{ padding: '8px 10px', fontSize: 12, color: '#374151' }}>
          {issue.kikv_domain || '—'}
        </td>
        <td style={{ padding: '8px 10px', fontSize: 12, color: '#6b7280', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
            title={issue.issue_description}>
          {issue.issue_description || '—'}
        </td>
        <td style={{ padding: '8px 10px', fontSize: 11, color: '#9ca3af' }}>
          {open ? '▲' : '▼'}
        </td>
      </tr>

      {open && (
        <tr style={{ background: '#f8faff', borderBottom: '1px solid #e0e7ff' }}>
          <td colSpan={9} style={{ padding: '12px 16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 10 }}>
              {[
                ['Issue ID',              issue.issue_id],
                ['Regel ID',              issue.rule_id],
                ['Validatielaag',         issue.validation_layer_label || issue.validation_layer],
                ['Bestand',               issue.source_file],
                ['Kolom',                 issue.source_column],
                ['Rij',                   issue.source_row],
                ['Huidige waarde',        issue.current_value],
                ['Leveranciersobject',    issue.supplier_reference_object],
                ['Leveranciersveld',      issue.supplier_reference_field],
                ['KIK-V domein',          issue.kikv_domain],
                ['KIK-V klasse',          issue.kikv_class],
                ['KIK-V property',        issue.kikv_property],
                ['Impact op score',       issue.impact_on_score],
                ['Melding',               issue.issue_description],
                ['Aanbevolen actie',      issue.suggested_fix],
                ['Uitwisselprofielen',    Array.isArray(issue.impacted_exchange_profiles) ? issue.impacted_exchange_profiles.join(', ') : issue.impacted_exchange_profiles],
                ['Indicatoren',           Array.isArray(issue.impacted_indicators) ? issue.impacted_indicators.join(', ') : issue.impacted_indicators],
              ].map(([label, val]) => (
                <div key={label} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
                  <span style={{ fontSize: 12, color: val ? '#1f2937' : '#d1d5db', wordBreak: 'break-word' }}>{val || 'n.v.t.'}</span>
                </div>
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

// ─── Hoofdcomponent ──────────────────────────────────────────────────────────
export default function TraceabilityDrilldown({ results, onBack }) {
  const allIssues = results?.all_issues || []

  // ── Filter-state ──────────────────────────────────────────────────────────
  const [filterLayer,     setFilterLayer]     = useState('')
  const [filterSeverity,  setFilterSeverity]  = useState('')
  const [filterFile,      setFilterFile]      = useState('')
  const [filterDomain,    setFilterDomain]    = useState('')
  const [filterIndicator, setFilterIndicator] = useState('')
  const [search,          setSearch]          = useState('')
  const [page,            setPage]            = useState(1)

  // ── Unieke waarden voor filter-dropdowns ──────────────────────────────────
  const layers     = useMemo(() => [...new Set(allIssues.map(i => i.validation_layer).filter(Boolean))].sort(), [allIssues])
  const severities = useMemo(() => [...new Set(allIssues.map(i => i.severity).filter(Boolean))].sort(), [allIssues])
  const files      = useMemo(() => [...new Set(allIssues.map(i => i.source_file).filter(Boolean))].sort(), [allIssues])
  const domains    = useMemo(() => [...new Set(allIssues.map(i => i.kikv_domain).filter(Boolean))].sort(), [allIssues])
  const indicators = useMemo(() => {
    const set = new Set()
    allIssues.forEach(i => (i.impacted_indicators || []).forEach(ind => set.add(ind)))
    return [...set].sort()
  }, [allIssues])

  // ── Gefilterde issues ─────────────────────────────────────────────────────
  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return allIssues.filter(i => {
      if (filterLayer     && i.validation_layer !== filterLayer)     return false
      if (filterSeverity  && i.severity          !== filterSeverity)  return false
      if (filterFile      && i.source_file        !== filterFile)      return false
      if (filterDomain    && i.kikv_domain        !== filterDomain)    return false
      if (filterIndicator && !(i.impacted_indicators || []).includes(filterIndicator)) return false
      if (q && ![i.source_file, i.source_column, i.current_value, i.issue_description, i.rule_id]
               .some(f => (f || '').toLowerCase().includes(q))) return false
      return true
    })
  }, [allIssues, filterLayer, filterSeverity, filterFile, filterDomain, filterIndicator, search])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const paginated  = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const resetFilters = () => {
    setFilterLayer(''); setFilterSeverity(''); setFilterFile('')
    setFilterDomain(''); setFilterIndicator(''); setSearch(''); setPage(1)
  }

  // ── Samenvattingstellers ──────────────────────────────────────────────────
  const errCount  = filtered.filter(i => i.severity === 'error').length
  const warnCount = filtered.filter(i => i.severity === 'warning').length

  const handlePrint = () => window.print()

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      {/* Sticky topbalk */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 100,
        background: '#fff', borderBottom: '1px solid var(--border)',
        padding: '0 32px', height: 56,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
          <NavBack onClick={onBack} dark />
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--blue)' }}>Rhadix</span>
            <span style={{ color: 'var(--border2)' }}>›</span>
            <span style={{ fontSize: 14, color: 'var(--text2)', fontWeight: 500 }}>Traceerbaarheid</span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
          <button onClick={handlePrint} style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: 'var(--blue)', color: '#fff', border: 'none',
            borderRadius: 'var(--radius)', padding: '9px 16px', fontSize: 13, fontWeight: 600,
            cursor: 'pointer', fontFamily: 'var(--font)', whiteSpace: 'nowrap',
          }}>
            ⬇ Exporteer PDF
          </button>
        </div>
      </div>

      <div style={{ padding: '28px 32px', flex: 1 }}>

      {/* Titel */}
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, color: 'var(--text)', marginBottom: 4 }}>
          🔍 Traceerbaarheid — alle validatieproblemen
        </h1>
        <p style={{ fontSize: 14, color: 'var(--text3)' }}>
          Elk validatieprobleem uit alle lagen, volledig traceerbaar naar bestand, rij, KIK-V klasse en uitwisselprofiel.
        </p>
      </div>

      {/* Samenvatting */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        {[
          { label: 'Totaal (gefilterd)',  value: filtered.length,  color: 'var(--text)' },
          { label: 'Fouten',              value: errCount,          color: '#dc2626' },
          { label: 'Waarschuwingen',      value: warnCount,         color: '#d97706' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{
            padding: '10px 18px', borderRadius: 'var(--radius)', border: '1px solid var(--border)',
            background: '#fff', minWidth: 110,
          }}>
            <div style={{ fontSize: 22, fontWeight: 800, color }}>{value}</div>
            <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 2 }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Filterbar */}
      <div style={{
        background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)',
        padding: '14px 18px', marginBottom: 16,
      }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <SearchBox value={search} onChange={v => { setSearch(v); setPage(1) }} />
          <FilterSelect label="Laag"       value={filterLayer}     onChange={v => { setFilterLayer(v);     setPage(1) }} options={layers.map(l => LAYER_LABELS[l] || l)} />
          <FilterSelect label="Ernst"      value={filterSeverity}  onChange={v => { setFilterSeverity(v);  setPage(1) }} options={severities} />
          <FilterSelect label="Bestand"    value={filterFile}      onChange={v => { setFilterFile(v);      setPage(1) }} options={files} />
          <FilterSelect label="KIK-V domein" value={filterDomain}  onChange={v => { setFilterDomain(v);   setPage(1) }} options={domains} />
          <FilterSelect label="Indicator"  value={filterIndicator} onChange={v => { setFilterIndicator(v); setPage(1) }} options={indicators} />
          <button
            onClick={resetFilters}
            style={{
              alignSelf: 'flex-end', padding: '8px 14px', borderRadius: 6,
              border: '1px solid var(--border)', background: '#f9fafb',
              fontSize: 12, color: 'var(--text3)', cursor: 'pointer',
            }}
          >✕ Wis filters</button>
        </div>
      </div>

      {/* Tabel */}
      {paginated.length === 0 ? (
        <div style={{
          textAlign: 'center', padding: '48px 24px', color: 'var(--text3)',
          background: '#f9fafb', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)',
        }}>
          {allIssues.length === 0
            ? 'Geen validatieproblemen gevonden — data lijkt schoon!'
            : 'Geen resultaten voor de huidige filters.'}
        </div>
      ) : (
        <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, minWidth: 900 }}>
            <thead>
              <tr style={{ background: '#f3f4f6', borderBottom: '1px solid var(--border)' }}>
                {['Rij', 'Laag', 'Ernst', 'Bestand', 'Kolom', 'Waarde', 'KIK-V domein', 'Melding', ''].map(h => (
                  <th key={h} style={{ padding: '10px 10px', textAlign: 'left', fontWeight: 700, color: '#6b7280', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginated.map((issue, i) => (
                <IssueRow key={issue.issue_id || i} issue={issue} idx={i} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Paginering */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8, marginTop: 16 }}>
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            style={{ padding: '6px 14px', borderRadius: 6, border: '1px solid var(--border)', background: '#fff', cursor: page === 1 ? 'not-allowed' : 'pointer', color: page === 1 ? '#d1d5db' : 'var(--text)' }}>
            ← Vorige
          </button>
          <span style={{ fontSize: 13, color: 'var(--text3)' }}>Pagina {page} van {totalPages} ({filtered.length} problemen)</span>
          <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
            style={{ padding: '6px 14px', borderRadius: 6, border: '1px solid var(--border)', background: '#fff', cursor: page === totalPages ? 'not-allowed' : 'pointer', color: page === totalPages ? '#d1d5db' : 'var(--text)' }}>
            Volgende →
          </button>
        </div>
      )}

      {/* Legenda */}
      <div style={{
        marginTop: 24, padding: 14, background: 'var(--blue-light)', border: '1px solid var(--blue-mid)',
        borderRadius: 'var(--radius)', fontSize: 12, color: 'var(--text3)', lineHeight: 1.7,
      }}>
        <strong style={{ color: 'var(--blue)', display: 'block', marginBottom: 4 }}>📋 Veldlegenda</strong>
        Klik op een rij voor alle traceervelden: <em>issue_id</em>, <em>rule_id</em>, <em>supplier_reference_object/field</em>,
        <em> kikv_class</em>, <em>kikv_property</em>, <em>impact_on_score</em>, <em>suggested_fix</em>,
        <em> impacted_exchange_profiles</em> en <em>impacted_indicators</em>.
      </div>

      </div>
    </div>
  )
}
