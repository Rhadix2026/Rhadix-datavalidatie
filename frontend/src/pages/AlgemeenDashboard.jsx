import { MaakTakenButton } from '../components/TaskUI'
import { useState } from 'react'
import { Nav, NavBack, NavLink, Page , TruncationWarning } from '../components/UI'
import BenchmarkBar from '../components/BenchmarkBar'

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
          <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 6, fontWeight: 600 }}>
            Voorbeelden{issue.count > issue.examples.length ? ` (eerste ${issue.examples.length} van ${issue.count})` : ''}:
          </div>
          <div style={{ maxHeight: 220, overflowY: 'auto', paddingRight: 4 }}>
            {issue.examples.map((ex, i) => (
              <div key={i} style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 3 }}>
                Rij {ex.row}: <code style={{ background: '#f3f4f6', padding: '1px 6px', borderRadius: 4 }}>{ex.value}</code>
              </div>
            ))}
          </div>
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

// ── Benchmark tegen referentieontwerp ──────────────────────────────────────────

const STATUS_STYLE = {
  covered:      { icon: '✓', color: '#059669', bg: '#ecfdf5', border: '#a7f3d0', label: 'Gedekt' },
  missing:      { icon: '✗', color: '#ef4444', bg: '#fef2f2', border: '#fca5a5', label: 'Ontbreekt' },
  out_of_scope: { icon: '○', color: '#9ca3af', bg: '#f9fafb', border: '#e5e7eb', label: 'Niet in bronontwerp' },
}

function ConceptRow({ c }) {
  const st = STATUS_STYLE[c.status] || STATUS_STYLE.out_of_scope
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 10,
      padding: '8px 12px', borderRadius: 'var(--radius)',
      background: st.bg, border: `1px solid ${st.border}`, marginBottom: 6,
    }}>
      <span style={{ fontSize: 13, color: st.color, fontWeight: 800, lineHeight: '18px' }}>{st.icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{c.concept}</div>
        <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 2 }}>
          {c.afas_attr
            ? <>Bronveld: <code style={{ background: '#f3f4f6', padding: '1px 6px', borderRadius: 4 }}>{c.afas_attr}</code></>
            : <span style={{ fontStyle: 'italic' }}>Geen bronveld in KIK-V-referentieontwerp v6.0</span>}
          {c.transform && <span> · bewerking: {c.transform}</span>}
        </div>
        {c.status === 'covered' && c.present_in?.length > 0 && (
          <div style={{ fontSize: 11, color: '#059669', marginTop: 2 }}>Aangetroffen in: {c.present_in.join(', ')}</div>
        )}
        {c.status === 'missing' && (
          <div style={{ fontSize: 11, color: '#ef4444', marginTop: 2 }}>Niet aanwezig in de geladen export.</div>
        )}
      </div>
      <span style={{ fontSize: 10, fontWeight: 700, color: st.color, textTransform: 'uppercase', whiteSpace: 'nowrap' }}>{st.label}</span>
    </div>
  )
}

function ElementCard({ el }) {
  const [open, setOpen] = useState(el.missing > 0)
  return (
    <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)', marginBottom: 12, overflow: 'hidden' }}>
      <div onClick={() => setOpen(o => !o)}
        style={{ padding: '14px 18px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--text)' }}>{el.label}</div>
          <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 2 }}>
            <span style={{ color: '#059669', fontWeight: 600 }}>{el.covered} gedekt</span>
            {el.missing > 0 && <> · <span style={{ color: '#ef4444', fontWeight: 600 }}>{el.missing} ontbreekt</span></>}
            {el.out_of_scope > 0 && <> · <span style={{ color: '#9ca3af' }}>{el.out_of_scope} niet in bronontwerp</span></>}
          </div>
        </div>
        {el.coverage !== null && (
          <div style={{ textAlign: 'center' }}>
            <ScoreBadge value={el.coverage} />
            <span style={{ fontSize: 11, color: 'var(--text3)' }}>%</span>
          </div>
        )}
        <span style={{ fontSize: 12, color: 'var(--text3)' }}>{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div style={{ padding: '0 18px 16px' }}>
          {el.concepts.map((c, i) => <ConceptRow key={i} c={c} />)}
        </div>
      )}
    </div>
  )
}

function BenchmarkSection({ benchmark }) {
  if (!benchmark) return null
  if (!benchmark.applicable) {
    return (
      <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 'var(--radius-xl)', padding: 18, marginBottom: 16 }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: '#92400e', marginBottom: 4 }}>KIK-V-benchmark niet beschikbaar</div>
        <div style={{ fontSize: 13, color: 'var(--text2)' }}>
          Het KIK-V-referentieontwerp is specifiek voor AFAS Profit HRM. Er zijn geen AFAS-bestanden in deze scan herkend,
          dus er valt niets te benchmarken.
        </div>
      </div>
    )
  }

  const { reference = {}, summary = {}, elementen = [], profielen = {}, extra_fields = [], afas_files = [] } = benchmark
  const covColor = summary.coverage >= 85 ? '#059669' : summary.coverage >= 65 ? 'var(--blue)' : summary.coverage >= 50 ? '#f59e0b' : '#ef4444'

  return (
    <div style={{ marginTop: 8 }}>
      {/* Kop */}
      <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)', padding: '18px 20px', marginBottom: 16 }}>
        <div style={{ fontSize: 12, color: 'var(--text3)', fontWeight: 600, marginBottom: 6 }}>
          📐 Benchmark tegen KIK-V — {reference.title || 'referentieontwerp'}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 28, flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: 28, fontWeight: 900, color: covColor, lineHeight: 1 }}>
              {summary.coverage}<span style={{ fontSize: 15, color: 'var(--text3)', fontWeight: 600 }}>%</span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4 }}>Conceptdekking</div>
          </div>
          <div style={{ display: 'flex', gap: 20 }}>
            {[
              { label: 'Gedekt',             value: summary.concepts_covered,     color: '#059669' },
              { label: 'Ontbreekt',          value: summary.concepts_missing,     color: summary.concepts_missing > 0 ? '#ef4444' : '#059669' },
              { label: 'Niet in bronontwerp', value: summary.concepts_out_of_scope, color: '#9ca3af' },
            ].map((s, i) => (
              <div key={i} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 18, fontWeight: 800, color: s.color }}>{s.value}</div>
                <div style={{ fontSize: 11, color: 'var(--text3)', fontWeight: 600 }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>
        <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 10 }}>
          {reference.leverancier} {reference.source_system} · KIK-V-referentieontwerp v{reference.version} · vergeleken met: {afas_files.join(', ')}
        </div>
      </div>

      {/* Per gegevenselement */}
      {elementen.map((el, i) => <ElementCard key={i} el={el} />)}

      {/* Extra velden */}
      {extra_fields.length > 0 && (
        <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)', padding: '14px 18px', marginBottom: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text2)', marginBottom: 4 }}>
            Aangeleverd maar niet in het KIK-V-referentieontwerp ({extra_fields.length})
          </div>
          <div style={{ fontSize: 12, color: 'var(--text3)' }}>{extra_fields.join(', ')}</div>
        </div>
      )}

      {/* Uitwisselprofielen */}
      {profielen.items?.length > 0 && (
        <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)', padding: '14px 18px', marginBottom: 12 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', marginBottom: 6 }}>Uitwisselprofielen</div>
          <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 10, fontStyle: 'italic' }}>{profielen.note}</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {profielen.items.map((p, i) => (
              <span key={i} title={p.omschrijving}
                style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)', background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 20, padding: '4px 12px' }}>
                {p.code}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function CrossCheckRow({ check }) {
  const isError = check.severity === 'error'
  return (
    <div style={{ padding: '10px 14px', borderTop: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{
          fontSize: 10, fontWeight: 700, textTransform: 'uppercase', whiteSpace: 'nowrap',
          color: isError ? '#ef4444' : '#f59e0b',
        }}>{isError ? '● fout' : '▲ let op'}</span>
        <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{check.label}</span>
        <span style={{ fontSize: 12, color: 'var(--text3)', fontWeight: 600 }}>{check.count}x</span>
      </div>
      {check.detail && (
        <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4 }}>{check.detail}</div>
      )}
    </div>
  )
}

function CrossChecksSection({ checks }) {
  if (!checks || checks.length === 0) return null
  return (
    <div style={{
      background: 'var(--card)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius)', marginBottom: 16, overflow: 'hidden',
    }}>
      <div style={{ padding: '12px 14px', fontSize: 14, fontWeight: 700, color: 'var(--text)' }}>
        🔗 Cross-checks tussen bronnen
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text3)', marginLeft: 8 }}>
          gap-analyse over de aangeleverde bestanden heen
        </span>
      </div>
      {checks.map((c, i) => <CrossCheckRow key={c.id || i} check={c} />)}
    </div>
  )
}

export default function AlgemeenDashboard({ results, onNewScan, onHome, onBack, authUser }) {
  const [showBenchmark, setShowBenchmark] = useState(false)
  if (!results) return null
  const { file_results = [], summary = {}, benchmark = null, cross_checks = [] } = results

  const indexColor = summary.rhadix_index >= 85 ? '#059669'
    : summary.rhadix_index >= 65 ? 'var(--blue)'
    : summary.rhadix_index >= 50 ? '#f59e0b' : '#ef4444'

  // Benchmark mag pas wanneer de pre-scan zonder blokkerende fouten is doorlopen.
  const checksPassed = (summary.error_count || 0) === 0

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav onHome={onHome} right={
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <NavLink onClick={onNewScan}>Nieuwe scan</NavLink>
          {onBack && <NavBack onClick={onBack} />}
        </div>
      } />
      <Page>
        <TruncationWarning truncation={results.truncation} />
        {/* Kop */}
        <div style={{ marginBottom: 28 }}>
          <div style={{
            display: 'inline-flex', background: '#fffbeb', color: '#92400e',
            fontSize: 12, fontWeight: 600, padding: '4px 12px', borderRadius: 20,
            border: '1px solid #fde68a', marginBottom: 12,
          }}>
            🔍 Datakwaliteit — AFAS Profit &amp; Nedap ONS
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

        {authUser && (file_results.some(r => (r.issues||[]).length > 0) || cross_checks.length > 0) && (
          <div style={{ marginBottom: 24, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <MaakTakenButton
              buttonLabel="✓ Maak taken van bevindingen"
              sourceType="afas_validatie"
              sourceRef={results?.run_id || null}
              items={[
                ...file_results.flatMap(r => (r.issues || []).map(iss => ({
                  title: iss.message,
                  description: [
                    `Bestand: ${r.filename || r.label || 'onbekend'}`,
                    iss.count ? `Aantal: ${iss.count}` : null,
                    (iss.examples || []).length
                      ? 'Voorbeelden' + (iss.count > (iss.examples || []).length
                          ? ` (eerste ${(iss.examples || []).length} van ${iss.count})` : '') + ':'
                      : null,
                    ...(iss.examples || []).map(e => `  rij ${e.row}: ${e.value}`),
                  ].filter(Boolean).join('\n'),
                  source_label: `${r.label || r.filename || 'bestand'}${iss.count ? ' — ' + iss.count + '×' : ''}`,
                  priority: iss.severity === 'error' ? 'HOOG' : 'NORMAAL',
                }))),
                ...cross_checks.map(c => ({
                  title: c.label,
                  description: [
                    c.count ? `Aantal: ${c.count}` : null,
                    c.detail || null,
                  ].filter(Boolean).join('\n'),
                  source_label: `Cross-check${c.count ? ' — ' + c.count + '×' : ''}`,
                  priority: c.severity === 'error' ? 'HOOG' : 'NORMAAL',
                })),
              ]}
            />
            <span style={{ fontSize: 13, color: 'var(--text3)' }}>Zet bevindingen om in taken en wijs ze toe aan een collega.</span>
          </div>
        )}

        {/* Per bestand */}
        {file_results.map((result, i) => (
          <FileCard key={i} result={result} />
        ))}

        {/* Cross-checks tussen bronnen (gap-analyse) */}
        <CrossChecksSection checks={cross_checks} />

        {/* Fase 2 — benchmark tegen een standaard */}
        <BenchmarkBar result={results} />

        {/* Benchmark tegen referentieontwerp */}
        {benchmark && (
          <div style={{ marginTop: 8, marginBottom: 8 }}>
            <button
              onClick={() => setShowBenchmark(s => !s)}
              disabled={!checksPassed}
              title={checksPassed ? '' : 'Beschikbaar zodra de pre-scan zonder fouten is doorlopen'}
              style={{
                width: '100%', padding: '13px',
                background: checksPassed ? 'var(--blue)' : '#cbd5e1',
                color: '#fff', border: 'none', borderRadius: 'var(--radius)',
                fontSize: 15, fontWeight: 700,
                cursor: checksPassed ? 'pointer' : 'not-allowed',
                fontFamily: 'var(--font)',
              }}
            >
              {showBenchmark ? '▲ Benchmark verbergen' : '📐 Benchmark tegen referentieontwerp'}
            </button>
            {!checksPassed && (
              <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 6, textAlign: 'center' }}>
                Beschikbaar zodra de data zonder blokkerende fouten door de checks is.
              </div>
            )}
            {showBenchmark && checksPassed && (
              <div style={{ marginTop: 16 }}>
                <BenchmarkSection benchmark={benchmark} />
              </div>
            )}
          </div>
        )}

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
