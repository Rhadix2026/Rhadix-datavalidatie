import { useState, useEffect } from 'react'
import { Nav, NavBack, Spinner } from '../components/UI'
import { getKikvReadinessRapport, exportKikvReadinessRapportPdf } from '../services/api'

// ─── Helpers ──────────────────────────────────────────────────────────────────
// ReadinessStatus waarden: "gereed" | "gedeeltelijk" | "niet_gereed"

const READINESS_CONFIG = {
  gereed:       { label: 'Gereed',           color: 'var(--green)', bg: 'var(--green-bg)',  icon: '✓' },
  gedeeltelijk: { label: 'Gedeeltelijk',     color: 'var(--amber)', bg: 'var(--amber-bg)',  icon: '⚠' },
  niet_gereed:  { label: 'Niet gereed',      color: 'var(--red)',   bg: 'var(--red-bg)',    icon: '✕' },
}

function scoreColor(s) {
  return s >= 80 ? 'var(--green)' : s >= 60 ? 'var(--amber)' : 'var(--red)'
}

function scoreLabel(s) {
  return s >= 80 ? 'Uitstekend' : s >= 60 ? 'Voldoende' : 'Aandacht vereist'
}

function ReadinessBadge({ status }) {
  const cfg = READINESS_CONFIG[status] || READINESS_CONFIG.niet_gereed
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      fontSize: 11, fontWeight: 700, padding: '3px 10px',
      borderRadius: 20, whiteSpace: 'nowrap',
      background: cfg.bg, color: cfg.color,
    }}>
      {cfg.icon} {cfg.label}
    </span>
  )
}

// ─── Score card met formule-uitleg ────────────────────────────────────────────

function ScoreCard({ label, score, formula, icon }) {
  const [showFormula, setShowFormula] = useState(false)
  const color = scoreColor(score)

  return (
    <div style={{
      background: '#fff', borderRadius: 'var(--radius-xl)',
      border: '1px solid var(--border)', padding: '20px 22px',
      boxShadow: 'var(--shadow)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <span style={{ fontSize: 18 }}>{icon}</span>
        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text2)' }}>{label}</span>
        <button
          onClick={() => setShowFormula(v => !v)}
          style={{
            marginLeft: 'auto', background: 'var(--blue-light)', border: 'none',
            borderRadius: 20, padding: '2px 10px', fontSize: 11, color: 'var(--blue)',
            fontWeight: 600, cursor: 'pointer', fontFamily: 'var(--font)',
          }}
        >
          {showFormula ? 'Verberg' : 'ƒ Formule'}
        </button>
      </div>
      <div style={{ fontSize: 44, fontWeight: 800, color, letterSpacing: '-0.04em', lineHeight: 1, marginBottom: 6 }}>
        {Math.round(score)}
      </div>
      <div style={{ height: 5, background: 'var(--border)', borderRadius: 3, overflow: 'hidden', marginBottom: 6 }}>
        <div style={{ height: '100%', width: `${Math.min(100, score)}%`, background: color, borderRadius: 3, transition: 'width .6s' }} />
      </div>
      <div style={{ fontSize: 12, color, fontWeight: 600 }}>{scoreLabel(score)}</div>
      {showFormula && (
        <div style={{
          marginTop: 12, background: 'var(--bg)', borderRadius: 'var(--radius)',
          padding: '10px 12px', fontSize: 12, color: 'var(--text2)', lineHeight: 1.6,
          fontFamily: 'var(--font-mono, monospace)',
        }}>
          {formula}
        </div>
      )}
    </div>
  )
}

// ─── Per-indicator accordion ──────────────────────────────────────────────────
// indicator model: { indicator_id, indicator_name, exchange_profile, description,
//   required_fields: string[], available_fields: string[], missing_fields: string[],
//   data_quality_score, readiness_status, blocking_issues: string[] }

function IndicatorCard({ indicator }) {
  const [open, setOpen] = useState(false)
  const status = indicator.readiness_status   // "gereed" | "gedeeltelijk" | "niet_gereed"
  const cfg    = READINESS_CONFIG[status] || READINESS_CONFIG.niet_gereed

  const nReq   = indicator.required_fields?.length  ?? 0
  const nAvail = indicator.available_fields?.length  ?? 0
  const nMiss  = indicator.missing_fields?.length    ?? 0

  // Bereken scores die niet direct op het indicator-object staan
  const availScore     = nReq > 0 ? (nAvail / nReq) * 100 : 0
  const qualScore      = indicator.data_quality_score ?? 0
  const readinessScore = (nAvail / Math.max(nReq, 1)) * 60 + (qualScore / 100) * 40

  return (
    <div style={{
      borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)',
      marginBottom: 12, overflow: 'hidden', boxShadow: 'var(--shadow)',
    }}>
      {/* Header */}
      <div
        onClick={() => setOpen(v => !v)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 20px', background: cfg.bg,
          cursor: 'pointer', userSelect: 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 20, fontWeight: 800, color: cfg.color }}>{cfg.icon}</span>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)' }}>
              {indicator.indicator_name}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 2 }}>
              {indicator.exchange_profile}
              {nMiss > 0 && ` · ${nMiss} veld${nMiss === 1 ? '' : 'en'} ontbreekt`}
              {indicator.blocking_issues?.length > 0 &&
                ` · ${indicator.blocking_issues.length} blokkade${indicator.blocking_issues.length === 1 ? '' : 's'}`}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 22, fontWeight: 800, color: scoreColor(readinessScore), lineHeight: 1 }}>
              {Math.round(readinessScore)}
            </div>
            <div style={{ fontSize: 10, color: 'var(--text3)' }}>readiness</div>
          </div>
          <ReadinessBadge status={status} />
          <span style={{ fontSize: 14, color: 'var(--text3)' }}>{open ? '▲' : '▼'}</span>
        </div>
      </div>

      {/* Detail */}
      {open && (
        <div style={{ background: '#fff', padding: '20px 20px 16px' }}>

          {/* Drie mini-scores */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10, marginBottom: 18 }}>
            {[
              { label: 'Beschikbaarheid', value: availScore,     formula: `${nAvail}/${nReq} velden aanwezig` },
              { label: 'Kwaliteit',       value: qualScore,      formula: `data_quality_score uit scan` },
              { label: 'Readiness',       value: readinessScore, formula: `0.6 × beschikbaarheid + 0.4 × kwaliteit` },
            ].map(s => (
              <div key={s.label} style={{
                background: 'var(--bg)', borderRadius: 'var(--radius)',
                padding: '12px 14px', textAlign: 'center',
              }} title={`Formule: ${s.formula}`}>
                <div style={{ fontSize: 22, fontWeight: 800, color: scoreColor(s.value) }}>{Math.round(s.value)}</div>
                <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 2 }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Veldentabel */}
          {nReq > 0 && (
            <div style={{ marginBottom: 18 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
                Velden in dit profiel
              </div>
              <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
                <div style={{
                  display: 'grid', gridTemplateColumns: '1fr 100px',
                  padding: '7px 14px', background: 'var(--bg)',
                  fontSize: 11, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase',
                  borderBottom: '1px solid var(--border)',
                }}>
                  <span>Veld (schema.veld)</span>
                  <span>Status</span>
                </div>
                {indicator.required_fields.map((ref, idx) => {
                  const isAvail   = indicator.available_fields?.includes(ref)
                  const isMissing = indicator.missing_fields?.includes(ref)
                  const rowBg     = idx % 2 === 0 ? '#fff' : 'var(--bg)'
                  const parts     = ref.split('.')
                  const schemaLbl = parts[0]?.charAt(0).toUpperCase() + parts[0]?.slice(1)
                  const fieldLbl  = parts[1] ?? ref
                  return (
                    <div key={ref} style={{
                      display: 'grid', gridTemplateColumns: '1fr 100px',
                      padding: '8px 14px', background: rowBg,
                      borderBottom: idx < nReq - 1 ? '1px solid var(--border)' : 'none',
                      alignItems: 'center',
                    }}>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>{fieldLbl}</div>
                        <div style={{ fontSize: 10, color: 'var(--text4)', fontFamily: 'var(--font-mono, monospace)' }}>{schemaLbl}</div>
                      </div>
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', gap: 4,
                        fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 10,
                        background: isAvail ? 'var(--green-bg)' : 'var(--red-bg)',
                        color: isAvail ? 'var(--green)' : 'var(--red)',
                      }}>
                        {isAvail ? '✓ Aanwezig' : '✕ Ontbreekt'}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Blocking issues (strings) */}
          {indicator.blocking_issues && indicator.blocking_issues.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
                Blokkerende factoren
              </div>
              {indicator.blocking_issues.map((b, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'flex-start', gap: 8,
                  padding: '8px 12px', borderRadius: 'var(--radius)',
                  background: 'var(--red-bg)', marginBottom: 5,
                  fontSize: 12, color: 'var(--red)',
                }}>
                  <span style={{ fontWeight: 800, flexShrink: 0 }}>⛔</span>
                  <span>{b}</span>
                </div>
              ))}
            </div>
          )}

          {/* Beschrijving */}
          {indicator.description && (
            <div style={{
              padding: '10px 14px', borderRadius: 'var(--radius)',
              background: 'var(--bg)', borderLeft: `3px solid ${cfg.color}`,
              fontSize: 13, color: 'var(--text2)', lineHeight: 1.5,
            }}>
              {indicator.description}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Issues-tabel ─────────────────────────────────────────────────────────────
// ReportIssue model: { issue_id, severity, category, schema_key, schema_label,
//   field, field_label, label, count, detail, rows: RowDetail[], allowed_values, source }
// RowDetail: { rowNumber, personId, field, currentValue, expectedValue, message }

function IssuesTable({ issues }) {
  const [openRows, setOpenRows] = useState({})
  if (!issues || issues.length === 0) return null

  const errors   = issues.filter(i => i.severity === 'error')
  const warnings = issues.filter(i => i.severity === 'warning')

  function Group({ title, items, color, bg }) {
    if (items.length === 0) return null
    return (
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color, marginBottom: 10 }}>
          {color === 'var(--red)' ? '✕' : '⚠'} {title} ({items.length})
        </div>
        <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
          <div style={{
            display: 'grid', gridTemplateColumns: '1.6fr 0.9fr 56px 1.1fr',
            padding: '8px 14px', background: 'var(--bg)',
            fontSize: 11, fontWeight: 700, color: 'var(--text3)',
            textTransform: 'uppercase', letterSpacing: '0.05em',
            borderBottom: '1px solid var(--border)',
          }}>
            <span>Veld / omschrijving</span><span>Schema</span><span style={{ textAlign: 'center' }}>Rijen</span><span>Detail</span>
          </div>
          {items.map((issue, idx) => {
            const key    = `${color}-${idx}`
            const isOpen = !!openRows[key]
            const hasRows= issue.rows && issue.rows.length > 0
            const rowBg  = idx % 2 === 0 ? '#fff' : 'var(--bg)'
            return (
              <div key={idx}>
                <div
                  onClick={hasRows ? () => setOpenRows(s => ({ ...s, [key]: !s[key] })) : undefined}
                  style={{
                    display: 'grid', gridTemplateColumns: '1.6fr 0.9fr 56px 1.1fr',
                    padding: '10px 14px',
                    background: isOpen ? 'var(--blue-light)' : rowBg,
                    borderBottom: '1px solid var(--border)',
                    alignItems: 'center',
                    cursor: hasRows ? 'pointer' : 'default',
                    userSelect: 'none',
                  }}
                >
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text)', display: 'flex', alignItems: 'center', gap: 5 }}>
                      <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: '50%', background: bg, border: `2px solid ${color}`, flexShrink: 0 }} />
                      {issue.field_label || issue.label}
                      {hasRows && <span style={{ fontSize: 10, color: 'var(--text4)' }}>{isOpen ? '▲' : '▼'}</span>}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text4)', marginTop: 1 }}>{issue.label}</div>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text3)' }}>{issue.schema_label}</div>
                  <div style={{ textAlign: 'center', fontSize: 13, fontWeight: 700, color }}>{issue.count}</div>
                  <div style={{ fontSize: 11, color: 'var(--text3)', lineHeight: 1.4 }}>{issue.detail || '—'}</div>
                </div>

                {/* Per-rij detail */}
                {isOpen && hasRows && (
                  <div style={{ padding: '12px 14px 14px', background: 'var(--blue-light)', borderBottom: '1px solid var(--border)' }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
                      Rij-detail (max. 10)
                    </div>
                    <div style={{ overflowX: 'auto' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                        <thead>
                          <tr style={{ background: 'rgba(0,0,0,.04)' }}>
                            {['Rij', 'Persoon/ID', 'Huidige waarde', 'Verwachte waarde', 'Bericht'].map(h => (
                              <th key={h} style={{ padding: '5px 8px', textAlign: 'left', fontWeight: 700, color: 'var(--text3)', borderBottom: '1px solid var(--border)', whiteSpace: 'nowrap' }}>{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {issue.rows.slice(0, 10).map((row, ri) => (
                            <tr key={ri} style={{ background: ri % 2 === 0 ? 'transparent' : 'rgba(0,0,0,.02)' }}>
                              <td style={{ padding: '5px 8px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text2)' }}>{row.rowNumber ?? ri + 1}</td>
                              <td style={{ padding: '5px 8px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text2)' }}>{row.personId ?? '—'}</td>
                              <td style={{ padding: '5px 8px', fontFamily: 'var(--font-mono, monospace)', color, fontWeight: 600 }}>{row.currentValue ?? '—'}</td>
                              <td style={{ padding: '5px 8px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--green)' }}>{row.expectedValue ?? '—'}</td>
                              <td style={{ padding: '5px 8px', color: 'var(--text3)' }}>{row.message ?? '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <section style={{ marginBottom: 28 }}>
      <h2 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em', marginBottom: 4 }}>
        Gedetailleerd issue-overzicht
      </h2>
      <p style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 16, lineHeight: 1.5 }}>
        Klik op een rij om per-rij details te bekijken (rijnummer, persoon-ID, huidige waarde, verwachte waarde).
      </p>
      <Group title="Fouten" items={errors} color="var(--red)" bg="var(--red-bg)" />
      <Group title="Waarschuwingen" items={warnings} color="var(--amber)" bg="var(--amber-bg)" />
    </section>
  )
}

// ─── Scoreverantwoording ──────────────────────────────────────────────────────

function Scoreverantwoording() {
  const [open, setOpen] = useState(false)
  return (
    <div style={{
      background: 'var(--blue-light)', border: '1px solid var(--blue-mid)',
      borderRadius: 'var(--radius-xl)', padding: '14px 18px', marginBottom: 24,
    }}>
      <div onClick={() => setOpen(v => !v)} style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', userSelect: 'none' }}>
        <span style={{ fontSize: 16 }}>🧮</span>
        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--blue)' }}>Scoreverantwoording — hoe worden de scores berekend?</span>
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--blue)' }}>{open ? '▲ Verberg' : '▼ Toon'}</span>
      </div>
      {open && (
        <div style={{ marginTop: 12, fontSize: 13, color: 'var(--text2)', lineHeight: 1.7 }}>
          <div style={{ marginBottom: 8 }}><strong>Beschikbaarheidsscore (per indicator):</strong><br />Beschikbare velden / vereiste velden × 100</div>
          <div style={{ marginBottom: 8 }}>
            <strong>Kwaliteitsscore (per indicator):</strong><br />
            <code style={{ background: 'rgba(0,0,0,.06)', padding: '1px 5px', borderRadius: 4 }}>100 − ((fouten × 2 + waarschuwingen) / rijen × 100)</code>
          </div>
          <div style={{ marginBottom: 8 }}>
            <strong>KIK-V Readiness (per indicator):</strong><br />
            <code style={{ background: 'rgba(0,0,0,.06)', padding: '1px 5px', borderRadius: 4 }}>0.6 × beschikbaarheidsscore + 0.4 × kwaliteitsscore</code>
          </div>
          <div><strong>Totale KIK-V Readiness:</strong><br />Gewogen gemiddelde (gereed = 100p, gedeeltelijk = 50p, niet gereed = 0p) over alle indicatoren.</div>
        </div>
      )}
    </div>
  )
}

// ─── Hoofd component ──────────────────────────────────────────────────────────

export default function KikvReadinessRapport({ results, systems, onBack }) {
  const [rapport,     setRapport]     = useState(null)
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState(null)
  const [orgName,     setOrgName]     = useState('')
  const [exporting,   setExporting]   = useState(false)
  const [exportError, setExportError] = useState(null)
  const [editingOrg,  setEditingOrg]  = useState(false)

  const runId      = results?.run_id
  const systemsStr = (systems || []).join(',')
  const orgParam   = orgName || 'Zorginstelling'

  useEffect(() => {
    if (!runId) { setError('Geen scan-ID beschikbaar.'); setLoading(false); return }
    setLoading(true)
    getKikvReadinessRapport(runId, orgParam, systemsStr)
      .then(data => { setRapport(data); setLoading(false) })
      .catch(e   => { setError(e.message); setLoading(false) })
  }, [runId, orgParam, systemsStr])  // eslint-disable-line

  const handleExport = async () => {
    setExporting(true); setExportError(null)
    try { await exportKikvReadinessRapportPdf(runId, orgParam, systemsStr) }
    catch { setExportError('PDF-export mislukt. Controleer of de backend bereikbaar is.') }
    finally { setExporting(false) }
  }

  if (loading) return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={<NavBack onClick={onBack} />} /><Spinner />
    </div>
  )
  if (error) return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={<NavBack onClick={onBack} />} />
      <div style={{ maxWidth: 740, margin: '40px auto', padding: '0 24px' }}>
        <div style={{ background: 'var(--red-bg)', border: '1px solid var(--red-light)', borderRadius: 'var(--radius-xl)', padding: 24, color: 'var(--red)' }}>
          <strong>Fout bij laden rapport:</strong> {error}
        </div>
      </div>
    </div>
  )

  // Veldnamen zoals ze uit de backend komen:
  // rapport.availability_summary.availability_score
  // rapport.quality_summary.quality_score
  // rapport.kikv_readiness_summary.readiness_score + .indicators (KikvIndicator[])
  // rapport.issues (ReportIssue[])
  // rapport.recommendations (ReportRecommendation[])

  const avail = rapport.availability_summary
  const qual  = rapport.quality_summary
  const rs    = rapport.kikv_readiness_summary
  const meta  = rapport.meta
  const issues = rapport.issues || []

  const scanDate = meta.scan_date
    ? new Date(meta.scan_date).toLocaleDateString('nl-NL', { day: 'numeric', month: 'long', year: 'numeric' })
    : new Date().toLocaleDateString('nl-NL', { day: 'numeric', month: 'long', year: 'numeric' })

  const overallStatus = rs.readiness_score >= 80 ? 'gereed' : rs.readiness_score >= 50 ? 'gedeeltelijk' : 'niet_gereed'
  const overallCfg    = READINESS_CONFIG[overallStatus]

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>

      {/* Sticky topbalk */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 100,
        background: '#fff', borderBottom: '1px solid var(--border)',
        padding: '0 32px', height: 56,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <NavBack onClick={onBack} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--blue)' }}>Rhadix</span>
            <span style={{ color: 'var(--border2)' }}>›</span>
            <span style={{ fontSize: 14, color: 'var(--text2)', fontWeight: 500 }}>KIK-V Readiness rapport</span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {exportError && <span style={{ fontSize: 12, color: 'var(--red)' }}>{exportError}</span>}
          <button onClick={handleExport} disabled={exporting} style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: exporting ? 'var(--border)' : 'var(--blue)',
            color: '#fff', border: 'none', borderRadius: 'var(--radius)',
            padding: '9px 18px', fontSize: 13, fontWeight: 600,
            cursor: exporting ? 'not-allowed' : 'pointer', fontFamily: 'var(--font)',
          }}>
            {exporting ? '⏳ Exporteren…' : '⬇ Exporteer KIK-V readiness rapport'}
          </button>
        </div>
      </div>

      {/* Rapportinhoud */}
      <div style={{ maxWidth: 900, margin: '0 auto', padding: '36px 24px 60px', width: '100%' }}>

        {/* Kop */}
        <div style={{
          background: 'linear-gradient(135deg, #2d3eb8 0%, #1e3a8a 100%)',
          borderRadius: 'var(--radius-xl)', padding: '32px 36px', marginBottom: 24, color: '#fff',
        }}>
          <div style={{
            display: 'inline-flex', background: 'rgba(255,255,255,.18)',
            color: '#fff', fontSize: 11, fontWeight: 700,
            padding: '4px 12px', borderRadius: 20, marginBottom: 14, letterSpacing: '0.08em',
          }}>
            STAP 2 — KIK-V READINESS
          </div>
          <h1 style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 8, color: '#fff' }}>
            Rhadix KIK-V Readiness rapport
          </h1>
          <p style={{ fontSize: 14, color: 'rgba(255,255,255,.75)', margin: '0 0 16px', lineHeight: 1.5 }}>
            Databeschikbaarheid én datakwaliteit getoetst aan de KIK-V Modelgegevensset v1.0
          </p>

          {/* Meta-rij */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20 }}>
            {[
              { label: 'Organisatie', value: editingOrg ? null : orgParam, edit: true },
              { label: 'Bronsysteem', value: systems?.join(', ') || meta.systems?.join(', ') || '—' },
              { label: 'Scan',        value: meta.scan_label || '—' },
              { label: 'Datum',       value: scanDate },
              { label: 'Regelset',    value: 'KIK-V v1.0' },
            ].map(item => (
              <div key={item.label}>
                <div style={{ fontSize: 10, fontWeight: 700, color: 'rgba(255,255,255,.55)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 3 }}>
                  {item.label}
                </div>
                {item.edit && editingOrg ? (
                  <input autoFocus defaultValue={orgName}
                    onBlur={e => { setOrgName(e.target.value); setEditingOrg(false) }}
                    onKeyDown={e => { if (e.key === 'Enter') { setOrgName(e.target.value); setEditingOrg(false) } }}
                    style={{ fontSize: 14, fontWeight: 600, background: 'rgba(255,255,255,.15)', border: '1px solid rgba(255,255,255,.4)', borderRadius: 6, color: '#fff', padding: '2px 8px', fontFamily: 'var(--font)' }}
                  />
                ) : (
                  <div onClick={item.edit ? () => setEditingOrg(true) : undefined}
                    style={{ fontSize: 14, fontWeight: 600, color: '#fff', cursor: item.edit ? 'text' : 'default', borderBottom: item.edit ? '1px dashed rgba(255,255,255,.4)' : 'none', paddingBottom: item.edit ? 1 : 0 }}
                    title={item.edit ? 'Klik om organisatienaam in te stellen' : undefined}
                  >
                    {item.value}{item.edit && <span style={{ fontSize: 10, marginLeft: 5, opacity: 0.6 }}>✏</span>}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Scoreverantwoording */}
        <Scoreverantwoording />

        {/* Drie scorecards */}
        <section style={{ marginBottom: 24 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 14, marginBottom: 16 }}>
            <ScoreCard label="Beschikbaarheidsscore" score={avail.availability_score} icon="📂"
              formula="Aanwezig / totaal vereiste velden × 100 — gewogen over schema's" />
            <ScoreCard label="Kwaliteitsscore" score={qual.quality_score} icon="🔍"
              formula="100 − ((fouten×2 + waarschuwingen) / rijen × 100)" />
            <ScoreCard label="KIK-V Readiness" score={rs.readiness_score} icon="🎯"
              formula="Gewogen gemiddelde: gereed=100p, gedeeltelijk=50p, niet gereed=0p" />
          </div>

          {/* Overall-banner */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12,
            background: overallCfg.bg, border: `1px solid ${overallCfg.color}33`,
            borderRadius: 'var(--radius-xl)', padding: '14px 20px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontSize: 24 }}>{overallCfg.icon}</span>
              <div>
                <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text)' }}>
                  Oordeel: <span style={{ color: overallCfg.color }}>{overallCfg.label}</span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 2 }}>
                  {rs.readiness_score >= 80 ? 'Data voldoet aan de KIK-V drempelwaarden.'
                   : rs.readiness_score >= 50 ? 'Data voldoet deels. Los gemarkeerde issues op.'
                   : 'Data voldoet niet. Substantieel herstelwerk vereist.'}
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 12 }}>
              {[
                { label: 'Gereed',       value: rs.indicators_ready,     color: 'var(--green)' },
                { label: 'Deels gereed', value: rs.indicators_partial,   color: 'var(--amber)' },
                { label: 'Niet gereed',  value: rs.indicators_not_ready, color: 'var(--red)'   },
              ].map(s => (
                <div key={s.label} style={{ textAlign: 'center', minWidth: 60 }}>
                  <div style={{ fontSize: 22, fontWeight: 800, color: s.color }}>{s.value}</div>
                  <div style={{ fontSize: 10, color: 'var(--text3)' }}>{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Per-indicator */}
        <section style={{ marginBottom: 28 }}>
          <h2 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em', marginBottom: 4 }}>
            KIK-V uitwisselindicatoren
          </h2>
          <p style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 16, lineHeight: 1.5 }}>
            Klik op een indicator om veldenstatus, blokkades en toelichting te bekijken.
          </p>
          {(rs.indicators || []).map(ind => (
            <IndicatorCard key={ind.indicator_id} indicator={ind} />
          ))}
        </section>

        {/* Issues */}
        <IssuesTable issues={issues} />

        {/* Aanbevelingen */}
        {rapport.recommendations && rapport.recommendations.length > 0 && (
          <section style={{ marginBottom: 28 }}>
            <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '24px', boxShadow: 'var(--shadow)' }}>
              <h2 style={{ fontSize: 16, fontWeight: 800, color: 'var(--text)', marginBottom: 16 }}>Aanbevelingen</h2>
              {rapport.recommendations.map((rec, i) => {
                const c = rec.impact === 'hoog' ? 'var(--red)' : rec.impact === 'gemiddeld' ? 'var(--amber)' : 'var(--blue)'
                const bg = rec.impact === 'hoog' ? 'var(--red-bg)' : rec.impact === 'gemiddeld' ? 'var(--amber-bg)' : 'var(--blue-light)'
                return (
                  <div key={rec.recommendation_id || i} style={{ display: 'flex', gap: 14, marginBottom: 12, padding: '14px 16px', borderRadius: 'var(--radius)', background: bg }}>
                    <div style={{ flexShrink: 0, width: 28, height: 28, borderRadius: '50%', background: c, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 800 }}>{i + 1}</div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', marginBottom: 3 }}>{rec.title}</div>
                      <div style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.5 }}>{rec.rationale}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </section>
        )}

        {/* Footer */}
        <div style={{ textAlign: 'center', fontSize: 12, color: 'var(--text4)', paddingTop: 20, borderTop: '1px solid var(--border)' }}>
          Rhadix KIK-V Readiness rapport · gegenereerd op {new Date().toLocaleDateString('nl-NL')} · KIK-V Modelgegevensset v1.0
        </div>
      </div>
    </div>
  )
}
