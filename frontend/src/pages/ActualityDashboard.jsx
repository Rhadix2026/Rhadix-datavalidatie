import { useState } from 'react'
import { NavBack } from '../components/UI'

// ── Kleur-hulp ────────────────────────────────────────────────────────────────
const scoreColor = (s) =>
  s >= 80 ? '#059669' : s >= 60 ? '#d97706' : '#dc2626'

const scoreLabel = (s) =>
  s >= 80 ? 'Goed' : s >= 60 ? 'Voldoende' : 'Onvoldoende'

// ── KIK-V uitwisselkalender — kleuren synchroon met backend KIKV_ACTUALITY_NORMS
// NZa & VWS: data gaat over het VORIGE boekjaar, deadline aanlevering = 30 juni
// → oudste data (jan 1 vorig jaar) is bij levering ~18 maanden = 548 dagen oud
const PROFILE_META = {
  zorgkantoren: { label: 'Zorgkantoren',        color: '#16a34a', bg: '#f0fdf4', cadence: 'Kwartaal',        icon: '🏥', max: 90  },
  vws:          { label: 'VWS Jaarverantw.',     color: '#7c3aed', bg: '#faf5ff', cadence: 'Jaarlijks (juni)',icon: '🏛️', max: 548 },
  nza:          { label: 'NZa Kostenonderzoek',  color: '#d97706', bg: '#fffbeb', cadence: 'Jaarlijks (juni)',icon: '📊', max: 548 },
  igj:          { label: 'IGJ Inspectiebezoek',  color: '#ea580c', bg: '#fff7ed', cadence: 'Op verzoek',      icon: '🔍', max: 180 },
}

// ── SVG Donut Pie Chart ───────────────────────────────────────────────────────
function PieChart({ actual, outdated, inconsistent }) {
  const total = actual + outdated + inconsistent
  if (total === 0) {
    return (
      <svg viewBox="0 0 120 120" width={120} height={120}>
        <circle cx={60} cy={60} r={40} fill="none" stroke="#e5e7eb" strokeWidth={22} />
        <text x={60} y={64} textAnchor="middle" fontSize={11} fill="#9ca3af">geen data</text>
      </svg>
    )
  }

  const slices = [
    { value: actual,       color: '#059669' },
    { value: outdated,     color: '#f59e0b' },
    { value: inconsistent, color: '#dc2626' },
  ]

  const R = 40
  const CX = 60, CY = 60
  const circumference = 2 * Math.PI * R

  let offset = 0
  const paths = slices.map(({ value, color }, i) => {
    const pct = value / total
    const dash = pct * circumference
    const gap  = circumference - dash
    const el = (
      <circle
        key={i}
        cx={CX} cy={CY} r={R}
        fill="none"
        stroke={color}
        strokeWidth={22}
        strokeDasharray={`${dash} ${gap}`}
        strokeDashoffset={-offset}
        style={{ transform: 'rotate(-90deg)', transformOrigin: `${CX}px ${CY}px` }}
      />
    )
    offset += dash
    return el
  })

  const actPct = Math.round(actual / total * 100)
  return (
    <svg viewBox="0 0 120 120" width={120} height={120}>
      {paths}
      <text x={CX} y={CY - 7} textAnchor="middle" fontSize={18} fontWeight={700} fill={scoreColor(actPct)}>{actPct}%</text>
      <text x={CX} y={CY + 9} textAnchor="middle" fontSize={9}  fill="#6b7280">actueel</text>
    </svg>
  )
}

// ── Histogram ─────────────────────────────────────────────────────────────────
function Histogram({ data, maxAgeDays = 30, normDays = null }) {
  if (!data || data.length === 0) return null
  const maxCount = Math.max(...data.map(d => d.count), 1)
  const BAR_MAX_H = 80
  const threshold = normDays || maxAgeDays

  return (
    <div style={{ overflowX: 'auto' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, minWidth: 320, height: BAR_MAX_H + 32, padding: '0 4px' }}>
        {data.map((d, i) => {
          const h = Math.max(4, Math.round((d.count / maxCount) * BAR_MAX_H))
          const bucketDays = [3, 10, 22, 45, 75, 135, 270, 500][i] || 500
          const color = bucketDays <= threshold      ? '#059669'
                      : bucketDays <= threshold * 3  ? '#f59e0b'
                      : '#dc2626'
          return (
            <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, minWidth: 28 }}>
              {d.count > 0 && (
                <div style={{ fontSize: 9, color: '#6b7280', marginBottom: 2 }}>{d.count}</div>
              )}
              <div
                title={`${d.label}: ${d.count} rijen`}
                style={{
                  width: '100%', height: h,
                  background: color, borderRadius: '3px 3px 0 0',
                  opacity: d.count === 0 ? 0.15 : 1,
                  transition: 'height 0.3s',
                }}
              />
              <div style={{ fontSize: 8, color: '#9ca3af', marginTop: 3, textAlign: 'center', wordBreak: 'break-all', lineHeight: 1.2 }}>
                {d.label}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Issue Panel ───────────────────────────────────────────────────────────────
function IssuePanel({ title, items, color, icon }) {
  const [open, setOpen] = useState(false)
  if (!items || items.length === 0) return null

  return (
    <div style={{ border: `1px solid ${color}33`, borderRadius: 8, overflow: 'hidden', marginTop: 8 }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', textAlign: 'left', padding: '10px 14px',
          background: `${color}11`, border: 'none', cursor: 'pointer',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}
      >
        <span style={{ fontSize: 13, fontWeight: 600, color }}>
          {icon} {title} <span style={{ fontWeight: 400, color: '#6b7280' }}>({items.length} rijen)</span>
        </span>
        <span style={{ color: '#9ca3af' }}>{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div style={{ maxHeight: 260, overflowY: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: '#f9fafb' }}>
                <th style={{ padding: '6px 10px', textAlign: 'left', color: '#6b7280', fontWeight: 600 }}>Rij</th>
                <th style={{ padding: '6px 10px', textAlign: 'left', color: '#6b7280', fontWeight: 600 }}>Veld</th>
                <th style={{ padding: '6px 10px', textAlign: 'left', color: '#6b7280', fontWeight: 600 }}>Waarde</th>
                <th style={{ padding: '6px 10px', textAlign: 'left', color: '#6b7280', fontWeight: 600 }}>Melding</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, i) => (
                <tr key={i} style={{ borderTop: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '5px 10px', color: '#374151' }}>{item.rowNumber}</td>
                  <td style={{ padding: '5px 10px', color: '#374151', fontFamily: 'monospace', fontSize: 11 }}>{item.field}</td>
                  <td style={{ padding: '5px 10px', color: '#374151' }}>{item.currentValue || '—'}</td>
                  <td style={{ padding: '5px 10px', color }}>{item.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ── Herbereken score bij een bepaalde drempel (vanuit histogram) ──────────────
const BUCKET_UPPER = [7, 14, 30, 60, 90, 180, 365, 9999]

function scoreAtDays(ar, days) {
  if (!ar.age_histogram) return null
  let actual = 0, outdated = 0
  ar.age_histogram.forEach((b, i) => {
    if (BUCKET_UPPER[i] <= days) actual += b.count
    else outdated += b.count
  })
  const total = actual + outdated
  return total > 0 ? Math.round(actual / total * 100) : null
}

// ── KIK-V Norm badge ─────────────────────────────────────────────────────────
function KikvNormBadge({ norm }) {
  if (!norm) return null
  const meta = PROFILE_META[norm.profile_key] || {}

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
      background: meta.bg || '#f9fafb',
      border: `1px solid ${meta.color}30`,
      borderRadius: 8, padding: '8px 12px', marginTop: 10,
    }}>
      <span style={{
        background: meta.color, color: '#fff',
        borderRadius: 20, padding: '2px 10px',
        fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap',
      }}>
        {meta.icon} {norm.label}
      </span>
      <span style={{ fontSize: 12, color: '#6b7280' }}>
        {norm.cadence} · KIK-V norm: max {norm.max_age_days}d oud
      </span>
      <span style={{ fontSize: 11, color: '#9ca3af', flex: 1, minWidth: 180 }}>
        {norm.description}
      </span>
    </div>
  )
}

// ── Bestand-kaart ─────────────────────────────────────────────────────────────
function FileActualityCard({ ar, threshold }) {
  const [open, setOpen] = useState(true)
  const score = ar.score ?? ar.actuality_score
  const hasScore = score !== null && score !== undefined

  const detectedField = ar.primary_col
    || ar.detected_fields?.mutation
    || ar.detected_fields?.start
    || (ar.detected_fields?.all_date_cols || [])[0]
    || null

  const normDays  = ar.kikv_norm?.max_age_days || null
  const normScore = normDays ? scoreAtDays(ar, normDays) : null
  const normCompliant = normScore !== null && normScore >= 80

  return (
    <div style={{
      border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)',
      overflow: 'hidden', marginBottom: 16,
    }}>
      {/* Header */}
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', textAlign: 'left', cursor: 'pointer', border: 'none',
          padding: '14px 20px', background: '#fafafa',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 16 }}>📂</span>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)' }}>{ar.filename}</span>
              {ar.schema_key && (
                <span style={{
                  fontSize: 10, fontWeight: 600, padding: '1px 6px',
                  background: 'var(--blue-light)', color: 'var(--blue)',
                  borderRadius: 4, border: '1px solid var(--border)',
                }}>
                  {ar.schema_key}
                </span>
              )}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 2 }}>
              {ar.total_records} rijen
              {detectedField && <> · datumveld: <code style={{ fontSize: 11 }}>{detectedField}</code></>}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* KIK-V norm compliance indicator */}
          {normScore !== null && (
            <span style={{
              fontSize: 11, fontWeight: 700, padding: '3px 10px',
              borderRadius: 20,
              background: normCompliant ? '#dcfce7' : '#fee2e2',
              color:      normCompliant ? '#059669' : '#dc2626',
              border:     `1px solid ${normCompliant ? '#86efac' : '#fca5a5'}`,
              whiteSpace: 'nowrap',
            }}>
              {normCompliant ? '✓' : '✗'} KIK-V
            </span>
          )}
          {hasScore && (
            <div style={{
              background: `${scoreColor(score)}15`, border: `1px solid ${scoreColor(score)}40`,
              borderRadius: 20, padding: '4px 12px',
              fontSize: 14, fontWeight: 700, color: scoreColor(score),
            }}>
              {score}% — {scoreLabel(score)}
            </div>
          )}
          <span style={{ color: '#9ca3af' }}>{open ? '▲' : '▼'}</span>
        </div>
      </button>

      {open && (
        <div style={{ padding: '16px 20px' }}>
          {!hasScore ? (
            <div style={{ color: '#9ca3af', fontSize: 13 }}>
              Geen datumvelden gevonden — actualiteit kan niet worden bepaald.
            </div>
          ) : (
            <>
              {/* KIK-V norm banner */}
              {ar.kikv_norm && (
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
                  background: normCompliant ? '#f0fdf4' : '#fef2f2',
                  border: `1px solid ${normCompliant ? '#86efac' : '#fca5a5'}`,
                  borderRadius: 8, padding: '10px 14px', marginBottom: 16,
                }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 18,
                    background: normCompliant ? '#dcfce7' : '#fee2e2',
                  }}>
                    {normCompliant ? '✅' : '⚠️'}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: normCompliant ? '#059669' : '#dc2626' }}>
                      {normCompliant
                        ? `Voldoet aan KIK-V norm (${ar.kikv_norm.label})`
                        : `Voldoet niet aan KIK-V norm (${ar.kikv_norm.label})`}
                    </div>
                    <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>
                      {ar.kikv_norm.cadence} · norm: max {normDays}d oud
                      {normScore !== null && ` · score op KIK-V norm: ${normScore}%`}
                    </div>
                  </div>
                </div>
              )}

              {/* Stats + pie naast elkaar */}
              <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <PieChart
                  actual={ar.pie?.actual ?? ar.actual_count}
                  outdated={ar.pie?.outdated ?? ar.outdated_count}
                  inconsistent={ar.pie?.inconsistent ?? ar.inconsistent_count}
                />
                <div style={{ flex: 1, minWidth: 200 }}>
                  {[
                    { label: 'Actuele rijen',       value: ar.actual_count,       color: '#059669' },
                    { label: 'Verouderde rijen',     value: ar.outdated_count,     color: '#f59e0b' },
                    { label: 'Inconsistente rijen',  value: ar.inconsistent_count, color: '#dc2626' },
                  ].map(({ label, value, color }) => (
                    <div key={label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: 10, height: 10, borderRadius: 2, background: color }} />
                        <span style={{ fontSize: 13, color: 'var(--text)' }}>{label}</span>
                      </div>
                      <span style={{ fontSize: 14, fontWeight: 700, color }}>{value}</span>
                    </div>
                  ))}
                  {ar.unparseable_count > 0 && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: 10, height: 10, borderRadius: 2, background: '#9ca3af' }} />
                        <span style={{ fontSize: 13, color: 'var(--text)' }}>Onleesbare datums</span>
                      </div>
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#9ca3af' }}>{ar.unparseable_count}</span>
                    </div>
                  )}
                  <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text3)' }}>
                    Peildatum: {ar.reference_date} · gekozen drempel: {threshold}d
                  </div>
                </div>
              </div>

              {/* Histogram */}
              {ar.age_histogram && ar.age_histogram.some(b => b.count > 0) && (
                <div style={{ marginTop: 20 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text3)', marginBottom: 8 }}>
                    Leeftijdsverdeling records
                    {normDays && (
                      <span style={{ fontWeight: 400, marginLeft: 6, color: '#9ca3af' }}>
                        (groen = binnen KIK-V norm van {normDays}d)
                      </span>
                    )}
                  </div>
                  <Histogram data={ar.age_histogram} maxAgeDays={threshold} normDays={normDays} />
                </div>
              )}

              {/* Issue panels */}
              <IssuePanel title="Verouderde records"           items={ar.outdated}     color="#f59e0b" icon="⏰" />
              <IssuePanel title="Inconsistente records (start > eind)" items={ar.inconsistent} color="#dc2626" icon="⚠️" />
            </>
          )}
        </div>
      )}
    </div>
  )
}

// ── Uitwisselkalender legenda ─────────────────────────────────────────────────
function UitwisselkalenderLegend() {
  return (
    <div style={{
      background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)',
      padding: '16px 20px', marginBottom: 24,
    }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', marginBottom: 12 }}>
        📅 KIK-V Uitwisselkalender — actualiteitseisen per uitwisselprofiel
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {Object.entries(PROFILE_META).map(([key, p]) => (
          <div key={key} style={{
            display: 'flex', alignItems: 'center', gap: 8,
            background: p.bg, border: `1px solid ${p.color}30`,
            borderRadius: 8, padding: '8px 14px', flex: '1 1 180px',
          }}>
            <div style={{
              width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
              background: p.color, color: '#fff',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14,
            }}>
              {p.icon}
            </div>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: p.color }}>{p.label}</div>
              <div style={{ fontSize: 11, color: '#6b7280' }}>{p.cadence} · max {p.max}d</div>
            </div>
          </div>
        ))}
      </div>
      <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 10, lineHeight: 1.5 }}>
        Bron: KIK-V Afsprakenset v3.1.0 — Uitwisselkalender.{' '}
        <strong>Zorgkantoren:</strong> kwartaalcycli (max 90 d).{' '}
        <strong>VWS &amp; NZa:</strong> jaarverantwoording over het voorgaande boekjaar, deadline 30 juni —
        oudste records (~jan) zijn bij aanlevering max 18 maanden (548 d) oud.{' '}
        <strong>IGJ:</strong> bezoekafhankelijk (richtlijn 180 d).
      </div>
    </div>
  )
}

// ── Hoofd-component ───────────────────────────────────────────────────────────
function recomputeFromHistogram(ar, maxDays) {
  if (!ar.age_histogram) return { score: ar.actuality_score, actual: ar.actual_count, outdated: ar.outdated_count }
  let actual = 0, outdated = 0
  ar.age_histogram.forEach((b, i) => {
    if (BUCKET_UPPER[i] <= maxDays) actual += b.count
    else outdated += b.count
  })
  const total = actual + outdated
  return {
    score: total > 0 ? Math.round(actual / total * 100) : null,
    actual,
    outdated,
  }
}

export default function ActualityDashboard({ results, onBack }) {
  const [threshold, setThreshold] = useState(90)
  const actuality = results?.actuality || []

  const recomputed = actuality.map(ar => ({
    ...ar,
    ...recomputeFromHistogram(ar, threshold),
  }))

  const scored = recomputed.filter(ar => ar.score !== null && ar.score !== undefined)
  const avgScore = scored.length > 0
    ? Math.round(scored.reduce((s, ar) => s + ar.score, 0) / scored.length)
    : null

  // KIK-V norm compliance tally
  const filesWithNorm   = recomputed.filter(ar => ar.kikv_norm)
  const compliantFiles  = filesWithNorm.filter(ar => {
    const nd = ar.kikv_norm?.max_age_days
    if (!nd) return false
    const ns = scoreAtDays(ar, nd)
    return ns !== null && ns >= 80
  })

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
            <span style={{ fontSize: 14, color: 'var(--text2)', fontWeight: 500 }}>Data Actualiteit</span>
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

        {/* Kopje */}
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: 'var(--text)', marginBottom: 4 }}>
            ⏱ Data Actualiteit Score
          </h1>
          <p style={{ fontSize: 14, color: 'var(--text3)', maxWidth: 640 }}>
            Hoe recent zijn de records? Per bestand wordt de mutatiedatum getoetst aan de KIK-V
            actualiteitsnorm van het bijbehorende uitwisselprofiel (Afsprakenset v3.1.0).
          </p>
        </div>

        {/* KIK-V Uitwisselkalender legenda */}
        <UitwisselkalenderLegend />

        {/* KIK-V compliance samenvatting */}
        {filesWithNorm.length > 0 && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 16,
            background: compliantFiles.length === filesWithNorm.length ? '#f0fdf4' : '#fef9c3',
            border: `1px solid ${compliantFiles.length === filesWithNorm.length ? '#bbf7d0' : '#fef08a'}`,
            borderRadius: 'var(--radius-xl)', padding: '14px 20px', marginBottom: 20,
            flexWrap: 'wrap',
          }}>
            <div style={{
              width: 44, height: 44, borderRadius: '50%', flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20,
              background: compliantFiles.length === filesWithNorm.length ? '#dcfce7' : '#fef9c3',
            }}>
              {compliantFiles.length === filesWithNorm.length ? '✅' : '⚠️'}
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)' }}>
                KIK-V norm: {compliantFiles.length}/{filesWithNorm.length} bestanden voldoen
              </div>
              <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 2 }}>
                {compliantFiles.length === filesWithNorm.length
                  ? 'Alle bestanden voldoen aan de KIK-V actualiteitsnorm van hun uitwisselprofiel.'
                  : `${filesWithNorm.length - compliantFiles.length} bestand(en) voldoen niet — mutatiedatums zijn te oud voor het uitwisselprofiel.`}
              </div>
            </div>
          </div>
        )}

        {/* Drempel-selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 13, color: 'var(--text3)', fontWeight: 600 }}>Analyseer op drempel:</span>
          {[30, 60, 90, 180, 365, 548].map(d => (
            <button
              key={d}
              onClick={() => setThreshold(d)}
              style={{
                padding: '5px 14px', borderRadius: 20, cursor: 'pointer', fontSize: 13, fontWeight: 600,
                background: threshold === d ? 'var(--blue)' : 'var(--blue-light)',
                color:      threshold === d ? '#fff' : 'var(--blue)',
                border: `1px solid ${threshold === d ? 'var(--blue)' : 'var(--blue-mid)'}`,
                position: 'relative',
              }}
            >
              {d}d
              {d === 90  && <span style={{ fontSize: 9, position: 'absolute', top: -7, right: -4, background: '#16a34a', color: '#fff', borderRadius: 10, padding: '1px 5px', lineHeight: 1.6 }}>Zorgkantoren</span>}
              {d === 548 && <span style={{ fontSize: 9, position: 'absolute', top: -7, right: -4, background: '#d97706', color: '#fff', borderRadius: 10, padding: '1px 5px', lineHeight: 1.6 }}>NZa/VWS</span>}
            </button>
          ))}
          <span style={{ fontSize: 11, color: 'var(--text3)' }}>
            (herberekend vanuit histogram — zonder nieuwe upload)
          </span>
        </div>

        {/* Samenvatting-banner */}
        {avgScore !== null && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 24,
            background: `${scoreColor(avgScore)}0d`,
            border: `1px solid ${scoreColor(avgScore)}40`,
            borderRadius: 'var(--radius-xl)', padding: '16px 24px', marginBottom: 24,
            flexWrap: 'wrap',
          }}>
            <div>
              <div style={{ fontSize: 36, fontWeight: 900, color: scoreColor(avgScore), lineHeight: 1 }}>{avgScore}%</div>
              <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 2 }}>Gemiddelde score (drempel: {threshold}d)</div>
            </div>
            <div style={{ flex: 1, minWidth: 200 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: scoreColor(avgScore) }}>{scoreLabel(avgScore)}</div>
              <div style={{ fontSize: 13, color: 'var(--text3)', marginTop: 4 }}>
                {avgScore >= 80
                  ? 'Data is grotendeels actueel en klaar voor KIK-V uitwisseling.'
                  : avgScore >= 60
                  ? 'Een deel van de records is verouderd. Controleer mutatiedatums.'
                  : 'Veel records zijn verouderd. Datakwaliteit vereist directe aandacht.'}
              </div>
            </div>
          </div>
        )}

        {actuality.length === 0 ? (
          <div style={{
            background: '#f9fafb', border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)',
            padding: 32, textAlign: 'center', color: 'var(--text3)', fontSize: 14,
          }}>
            Geen actualiteitsdata beschikbaar. Voer een nieuwe scan uit.
          </div>
        ) : (
          recomputed.map((ar, i) => <FileActualityCard key={i} ar={ar} threshold={threshold} />)
        )}

        {/* Methodiek-uitleg */}
        <div style={{
          marginTop: 24, padding: 16, background: 'var(--blue-light)',
          border: '1px solid var(--blue-mid)', borderRadius: 'var(--radius)',
          fontSize: 12, color: 'var(--text3)', lineHeight: 1.6,
        }}>
          <strong style={{ color: 'var(--blue)', display: 'block', marginBottom: 4 }}>📐 Methodiek</strong>
          Actualiteitsscore = actuele rijen ÷ (actuele + verouderde rijen) × 100. Een record is actueel als de
          mutatiedatum (of startdatum als fallback) binnen de gekozen drempel valt. De KIK-V norm per uitwisselprofiel
          is gebaseerd op de officiële Uitwisselkalender (KIK-V Afsprakenset v3.1.0): Zorgkantoren en VWS hanteren
          kwartaalcycli (90 d), NZa een jaarlijks kostenonderzoek (365 d), IGJ is bezoekafhankelijk (richtlijn 180 d).
          Inconsistente records (einddatum vóór startdatum) worden apart geteld.
        </div>

      </div>
    </div>
  )
}
