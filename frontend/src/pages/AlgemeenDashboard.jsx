import { useState } from 'react'
import { Nav, NavBack, NavLink, Page } from '../components/UI'

function ScoreBadge({ value, size = 'md' }) {
  const color = value >= 85 ? '#059669' : value >= 65 ? 'var(--blue)' : value >= 50 ? '#f59e0b' : '#ef4444'
  const fontSize = size === 'lg' ? 42 : 22
  return (
    <span style={{ fontWeight: 900, fontSize, color, fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
      {value}
    </span>
  )
}

function IssueRow({ issue }) {
  const [open, setOpen] = useState(false)
  const isError = issue.severity === 'error'
  return (
    <div style={{
      border: `1px solid ${isError ? '#fca5a5' : '#fde68a'}`,
      borderRadius: 'var(--radius)', marginBottom: 6,
      background: isError ? '#fff5f5' : '#fffbeb',
    }}>
      <div
        onClick={() => setOpen(o => !o)}
        style={{ padding: '10px 14px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10 }}
      >
        <span style={{ fontSize: 13 }}>{isError ? '🔴' : '🟡'}</span>
        <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{issue.message}</span>
        <span style={{ fontSize: 12, color: 'var(--text3)', fontWeight: 600 }}>{issue.count}x</span>
        <span style={{ fontSize: 12, color: 'var(--text3)' }}>{open ? '▲' : '▼'}</span>
      </div>
      {open && issue.examples?.length > 0 && (
        <div style={{ padding: '0 14px 12px', borderTop: '1px solid rgba(0,0,0,.05)' }}>
          <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 6, fontWeight: 600 }}>Voorbeelden:</div>
          {issue.examples.map((ex, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 3 }}>
              Rij {ex.row}: <code style={{ background: '#f3f4f6', padding: '1px 6px', borderRadius: 4 }}>{ex.value}</code>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function FileCard({ result }) {
  const [open, setOpen] = useState(false)
  const errors   = result.issues.filter(i => i.severity === 'error')
  const warnings = result.issues.filter(i => i.severity === 'warning')

  return (
    <div style={{
      background: '#fff', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-xl)', marginBottom: 16,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '18px 20px',
        borderLeft: `4px solid ${result.color || '#9ca3af'}`,
        display: 'flex', alignItems: 'center', gap: 14,
      }}>
        <span style={{ fontSize: 24 }}>{result.icon}</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--text)', marginBottom: 2 }}>
            {result.label}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text3)' }}>
            {result.filename} · {result.rows.toLocaleString()} rijen
          </div>
        </div>
        {/* Scores */}
        <div style={{ display: 'flex', gap: 20, textAlign: 'center' }}>
          <div>
            <div style={{ fontSize: 10, color: 'var(--text3)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 2 }}>Volledigheid</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 2 }}>
              <ScoreBadge value={result.completeness} />
              <span style={{ fontSize: 12, color: 'var(--text3)' }}>%</span>
            </div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: 'var(--text3)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 2 }}>Kwaliteit</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 2 }}>
              <ScoreBadge value={result.quality} />
              <span style={{ fontSize: 12, color: 'var(--text3)' }}>%</span>
            </div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: 'var(--text3)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 2 }}>Rhadix Index</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 2 }}>
              <ScoreBadge value={result.rhadix_index} size="lg" />
            </div>
          </div>
        </div>
      </div>

      {/* Aanwezige / ontbrekende velden */}
      <div style={{ padding: '12px 20px', background: 'var(--bg)', borderTop: '1px solid var(--border)', display: 'flex', gap: 24, flexWrap: 'wrap' }}>
        <div>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#059669', textTransform: 'uppercase' }}>✓ Aanwezig: </span>
          <span style={{ fontSize: 12, color: 'var(--text2)' }}>
            {result.present_fields?.join(', ') || '—'}
          </span>
        </div>
        {result.missing_required?.length > 0 && (
          <div>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#ef4444', textTransform: 'uppercase' }}>✗ Ontbreekt: </span>
            <span style={{ fontSize: 12, color: '#ef4444' }}>
              {result.missing_required.join(', ')}
            </span>
          </div>
        )}
      </div>

      {/* Issues */}
      {result.issues.length > 0 && (
        <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border)' }}>
          <div
            onClick={() => setOpen(o => !o)}
            style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, marginBottom: open ? 12 : 0 }}
          >
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>
              {errors.length > 0 && <span style={{ color: '#ef4444' }}>🔴 {errors.length} fout{errors.length !== 1 ? 'en' : ''}</span>}
              {errors.length > 0 && warnings.length > 0 && ' · '}
              {warnings.length > 0 && <span style={{ color: '#f59e0b' }}>🟡 {warnings.length} waarschuwing{warnings.length !== 1 ? 'en' : ''}</span>}
            </span>
            <span style={{ fontSize: 12, color: 'var(--text3)', marginLeft: 'auto' }}>{open ? '▲ Verbergen' : '▼ Tonen'}</span>
          </div>
          {open && (
            <div style={{ marginTop: 8 }}>
              {result.issues.map((issue, i) => <IssueRow key={i} issue={issue} />)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function AlgemeenDashboard({ results, onNewScan }) {
  if (!results) return null
  const { file_results = [], summary = {} } = results

  const indexColor = summary.rhadix_index >= 85 ? '#059669'
    : summary.rhadix_index >= 65 ? 'var(--blue)'
    : summary.rhadix_index >= 50 ? '#f59e0b' : '#ef4444'

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <NavLink onClick={onNewScan}>Nieuwe scan</NavLink>
          {onBack && <NavBack onClick={onBack} />}
        </div>
      } />
      <Page>
        {/* Kop */}
        <div style={{ marginBottom: 28 }}>
          <div style={{
            display: 'inline-flex', background: '#fffbeb', color: '#92400e',
            fontSize: 12, fontWeight: 600, padding: '4px 12px', borderRadius: 20,
            border: '1px solid #fde68a', marginBottom: 12,
          }}>
            🔍 Beschikbaarheid Algemeen — AFAS Profit &amp; Nedap ONS pre-scan
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 32, flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontSize: 28, fontWeight: 900, color: indexColor, lineHeight: 1 }}>
                {summary.rhadix_index} <span style={{ fontSize: 16, color: 'var(--text3)', fontWeight: 600 }}>/100</span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4 }}>Rhadix Index</div>
            </div>
            <div style={{ display: 'flex', gap: 20 }}>
              {[
                { label: 'Volledigheid', value: `${summary.completeness}%` },
                { label: 'Kwaliteit',   value: `${summary.quality}%` },
                { label: 'Rijen',       value: (summary.total_rows || 0).toLocaleString() },
                { label: 'Bestanden',   value: summary.total_files },
                { label: 'Fouten',      value: summary.error_count, color: summary.error_count > 0 ? '#ef4444' : '#059669' },
              ].map((s, i) => (
                <div key={i} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 18, fontWeight: 800, color: s.color || 'var(--text)' }}>{s.value}</div>
                  <div style={{ fontSize: 11, color: 'var(--text3)', fontWeight: 600 }}>{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Per bestand */}
        {file_results.map((result, i) => (
          <FileCard key={i} result={result} />
        ))}

        <button
          onClick={onNewScan}
          style={{
            marginTop: 8, width: '100%', padding: '13px',
            background: '#f59e0b', color: '#fff', border: 'none',
            borderRadius: 'var(--radius)', fontSize: 15, fontWeight: 700,
            cursor: 'pointer', fontFamily: 'var(--font)',
          }}
        >
          Nieuwe scan →
        </button>
      </Page>
    </div>
  )
}
