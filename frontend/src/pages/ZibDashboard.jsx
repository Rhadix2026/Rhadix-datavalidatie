import { useState } from 'react'
import { Nav, NavLink, Page, BtnPrimary, ProgressBar, StatusBadge, ExpandableIssueRow, GapRow, NavBack } from '../components/UI'

const ZIB_DOMAINS = [
  { key: 'patient',           icon: '🧑',  label: 'Patiënt / Cliënt',  schema: 'patient',           zib: 'nl.zorg.Patient' },
  { key: 'probleem',          icon: '🩺',  label: 'Probleem / Diagnose', schema: 'probleem',          zib: 'nl.zorg.Probleem' },
  { key: 'medicatieafspraak', icon: '💊',  label: 'Medicatie',           schema: 'medicatieafspraak', zib: 'nl.zorg.MedicatieAfspraak' },
  { key: 'allergie',          icon: '⚠️', label: 'Allergie',             schema: 'allergie',          zib: 'nl.zorg.AllergieIntolerantie' },
]

function domainFile(domain, results) {
  return (results?.file_results || []).find(f => f.schema_key === domain.schema)
}

function domainStatus(domain, results) {
  const file = domainFile(domain, results)
  if (!file) return 'grey'
  const issues = file.issues || []
  if (issues.some(i => i.severity === 'error'))   return 'red'
  if (issues.some(i => i.severity === 'warning')) return 'amber'
  return 'green'
}

function ScoreRing({ score, size = 64, label }) {
  const color = score >= 80 ? 'var(--green)' : score >= 60 ? 'var(--amber)' : 'var(--red)'
  const bg    = score >= 80 ? 'var(--green-light)' : score >= 60 ? 'var(--amber-light)' : 'var(--red-light)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <div style={{
        width: size, height: size, borderRadius: '50%', flexShrink: 0,
        background: bg, color, display: 'flex', alignItems: 'center',
        justifyContent: 'center', fontSize: size * 0.28, fontWeight: 800,
      }}>
        {score}
      </div>
      {label && <div style={{ fontSize: 12, color: 'var(--text3)', fontWeight: 500 }}>{label}</div>}
    </div>
  )
}

export default function ZibDashboard({ results, onNewScan, onActuality, onTraceability, onProfiles, onBack }) {
  const [activeDomain, setActiveDomain] = useState('patient')

  if (!results) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
        <Nav right={
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {onActuality && (
              <button
                onClick={onActuality}
                style={{
                  background: 'var(--blue-light)', border: '1px solid var(--blue-mid)',
                  borderRadius: 'var(--radius)', padding: '6px 14px', cursor: 'pointer',
                  fontSize: 13, color: 'var(--blue)', fontWeight: 600,
                  display: 'flex', alignItems: 'center', gap: 6,
                }}
              >⏱ Actualiteit</button>
            )}
            {onTraceability && (
              <button
                onClick={onTraceability}
                style={{
                  background: 'var(--blue-light)', border: '1px solid var(--blue-mid)',
                  borderRadius: 'var(--radius)', padding: '6px 14px', cursor: 'pointer',
                  fontSize: 13, color: 'var(--blue)', fontWeight: 600,
                  display: 'flex', alignItems: 'center', gap: 6,
                }}
              >🔍 Traceerbaarheid</button>
            )}
            <NavLink onClick={onNewScan}>Nieuwe scan</NavLink>
          </div>
        } />
        <Page>
          <div style={{ textAlign: 'center', padding: '80px 24px' }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>💊</div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Geen ZIB-scanresultaat</h2>
            <p style={{ fontSize: 14, color: 'var(--text3)', marginBottom: 24 }}>Start een nieuwe ZIB-scan om resultaten te zien.</p>
            <BtnPrimary onClick={onNewScan}>Nieuwe scan</BtnPrimary>
          </div>
        </Page>
      </div>
    )
  }

  // Rhadix Index = Databeschikbaarheid × Datakwaliteit (berekend in backend)
  const beschikbaarheid = results.beschikbaarheid_score ?? results.score ?? 0
  const kwaliteit       = results.kwaliteit_score ?? results.score ?? 0
  const radixIndex      = results.rhadix_index ?? Math.round(beschikbaarheid * kwaliteit / 100)
  const dataverzuim     = results.dataverzuim   ?? Math.round(100 - radixIndex)
  const scoreLabel      = radixIndex >= 80 ? 'Uitstekend' : radixIndex >= 65 ? 'Goed' : 'Verbetering nodig'

  const activeDef   = ZIB_DOMAINS.find(d => d.key === activeDomain) || ZIB_DOMAINS[0]
  const activeFile  = domainFile(activeDef, results)
  const activeIssues = activeFile?.issues || []
  const errorIssues   = activeIssues.filter(i => i.severity === 'error')
  const warningIssues = activeIssues.filter(i => i.severity === 'warning')
  const allClean      = activeIssues.length === 0

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <NavLink onClick={onNewScan}>Nieuwe scan</NavLink>
          {onBack && <NavBack onClick={onBack} />}
        </div>
      } />

      <Page>
        {/* Header */}
        <div style={{ marginBottom: 20 }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            background: '#f0fdf4', border: '1px solid #bbf7d0',
            color: '#059669', fontSize: 12, fontWeight: 700,
            padding: '5px 12px', borderRadius: 20, marginBottom: 12,
          }}>
            💊 ZIB's — Nictiz 2020
          </div>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em', marginBottom: 4 }}>ZIB Dashboard</h1>
          <p style={{ fontSize: 14, color: 'var(--text3)' }}>Validatieresultaten cliëntdata — Zorginformatiebouwstenen</p>
        </div>

        {/* Score hero */}
        <div style={{
          background: 'linear-gradient(135deg, #065f46 0%, #047857 100%)',
          borderRadius: 'var(--radius-xl)', padding: '28px 32px',
          marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <span style={{ fontSize: 16 }}>🎯</span>
              <span style={{ fontSize: 16, fontWeight: 700, color: '#fff' }}>Rhadix Index</span>
            </div>
            <div style={{ fontSize: 13, color: 'rgba(255,255,255,.7)', marginBottom: 14 }}>
              Databeschikbaarheid × Datakwaliteit — {(results.file_results || []).length} bestand(en)
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <div style={{
                display: 'inline-flex', background: 'rgba(255,255,255,.15)', color: '#fff',
                fontSize: 13, fontWeight: 600, padding: '6px 14px', borderRadius: 20,
              }}>
                → {scoreLabel}
              </div>
              <div style={{
                display: 'inline-flex', background: 'rgba(255,255,255,.1)', color: 'rgba(255,255,255,.8)',
                fontSize: 12, fontWeight: 500, padding: '6px 14px', borderRadius: 20,
              }}>
                Dataverzuim: {dataverzuim}%
              </div>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 64, fontWeight: 800, color: '#fff', letterSpacing: '-0.04em', lineHeight: 1 }}>
              {radixIndex}
            </div>
            <div style={{ fontSize: 13, color: 'rgba(255,255,255,.6)', marginTop: 4 }}>van 100</div>
          </div>
        </div>

        {/* Rhadix formule */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          fontSize: 13, color: 'var(--text3)', marginBottom: 16, flexWrap: 'wrap',
        }}>
          <span style={{ fontWeight: 600, color: 'var(--text2)' }}>Databeschikbaarheid</span>
          <span style={{ fontWeight: 700, color: '#059669', fontSize: 15 }}>{beschikbaarheid}%</span>
          <span style={{ color: 'var(--text4)' }}>×</span>
          <span style={{ fontWeight: 600, color: 'var(--text2)' }}>Datakwaliteit</span>
          <span style={{ fontWeight: 700, color: '#059669', fontSize: 15 }}>{kwaliteit}%</span>
          <span style={{ color: 'var(--text4)' }}>=</span>
          <span style={{ fontWeight: 800, color: '#065f46', fontSize: 15 }}>Rhadix Index {radixIndex}%</span>
        </div>

        {/* Beschikbaarheid + Kwaliteit kaarten */}
        <div className="score-grid" style={{ marginBottom: 16 }}>
          {[
            { num: 1, label: 'Databeschikbaarheid', sub: 'Aanwezige verplichte velden', score: beschikbaarheid },
            { num: 2, label: 'Datakwaliteit',        sub: 'Kwalitatief goedgekeurde velden', score: kwaliteit },
          ].map(s => {
            const color = s.score >= 80 ? 'var(--green)' : s.score >= 60 ? 'var(--amber)' : 'var(--red)'
            const badge = s.score >= 80 ? 'Goed' : s.score >= 60 ? 'Voldoende' : 'Onvoldoende'
            return (
              <div key={s.num} style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '20px 24px', boxShadow: 'var(--shadow)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <div style={{ width: 24, height: 24, borderRadius: '50%', background: '#f0fdf4', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, color: '#059669' }}>{s.num}</div>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{s.label}</div>
                    <div style={{ fontSize: 11, color: 'var(--text3)' }}>{s.sub}</div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 10 }}>
                  <span style={{ fontSize: 36, fontWeight: 800, color, letterSpacing: '-0.03em' }}>{s.score}</span>
                  <StatusBadge status={badge} />
                </div>
                <ProgressBar value={s.score} color={color} />
              </div>
            )
          })}
            {onProfiles && (
              <button
                onClick={onProfiles}
                style={{ padding: '8px 16px', borderRadius: 7, border: '1px solid #d1d5db', background: '#f9fafb', cursor: 'pointer', fontWeight: 600, fontSize: 13 }}
              >
                📋 KIK-V Profielimport
              </button>
            )}
        </div>

        {/* Per-schema scores (Rhadix Index per ZIB) */}
        <div className="score-grid" style={{ marginBottom: 16 }}>
          {ZIB_DOMAINS.map(d => {
            const file   = domainFile(d, results)
            const sc     = file?.rhadix_index ?? file?.score ?? null
            const bsc    = file?.beschikbaarheid_score ?? null
            const ksc    = file?.kwaliteit_score ?? null
            const status = domainStatus(d, results)
            const color  = { red: 'var(--red)', amber: 'var(--amber)', green: 'var(--green)', grey: 'var(--text4)' }[status]
            const label  = sc === null ? 'Niet geüpload' : sc >= 80 ? 'Goed' : sc >= 60 ? 'Voldoende' : 'Onvoldoende'
            return (
              <div key={d.key} style={{
                background: '#fff', borderRadius: 'var(--radius-xl)',
                border: '1px solid var(--border)', padding: '20px 24px',
                boxShadow: 'var(--shadow)', opacity: sc === null ? 0.5 : 1,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <span style={{ fontSize: 18 }}>{d.icon}</span>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{d.label}</div>
                    <div style={{ fontSize: 10, color: 'var(--text4)', fontFamily: 'monospace' }}>{d.zib}</div>
                  </div>
                </div>
                {sc !== null ? (
                  <>
                    <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 10 }}>
                      <span style={{ fontSize: 36, fontWeight: 800, color, letterSpacing: '-0.03em' }}>{sc}</span>
                      <StatusBadge status={label} />
                    </div>
                    <ProgressBar value={sc} color={color} />
                    {bsc !== null && ksc !== null && (
                      <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
                        <span style={{ fontSize: 11, color: 'var(--text3)' }}>📋 Beschikbaar: <strong>{bsc}%</strong></span>
                        <span style={{ fontSize: 11, color: 'var(--text3)' }}>✓ Kwaliteit: <strong>{ksc}%</strong></span>
                      </div>
                    )}
                  </>
                ) : (
                  <div style={{ fontSize: 13, color: 'var(--text4)', fontStyle: 'italic' }}>Geen bestand geüpload</div>
                )}
              </div>
            )
          })}
        </div>

        {/* Domeinen + detail */}
        <div className="domain-grid">
          {/* Linker kolom: ZIB-domeinen */}
          <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: 16, boxShadow: 'var(--shadow)' }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', marginBottom: 12 }}>ZIB-domeinen</div>
            {ZIB_DOMAINS.map(d => {
              const status   = domainStatus(d, results)
              const hasData  = !!domainFile(d, results)
              const active   = activeDomain === d.key
              const dotColor = { red: 'var(--red)', amber: 'var(--amber)', green: 'var(--green)', grey: '#d1d5db' }[status]
              return (
                <div key={d.key} onClick={() => setActiveDomain(d.key)} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '9px 12px', borderRadius: 'var(--radius)', cursor: 'pointer',
                  background: active ? '#f0fdf4' : 'transparent',
                  border: active ? '1px solid #bbf7d0' : '1px solid transparent',
                  marginBottom: 3, transition: 'all .1s',
                  opacity: hasData ? 1 : 0.45,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                    <span style={{ fontSize: 14 }}>{d.icon}</span>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: active ? 700 : 500, color: active ? '#059669' : 'var(--text2)', lineHeight: 1.2 }}>{d.label}</div>
                      <div style={{ fontSize: 10, color: 'var(--text4)', lineHeight: 1, fontFamily: 'monospace' }}>{d.zib.split('.').pop()}</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    {!hasData && <span style={{ fontSize: 9, color: 'var(--text4)', fontStyle: 'italic' }}>n.v.t.</span>}
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: dotColor, flexShrink: 0 }} />
                  </div>
                </div>
              )
            })}
          </div>

          {/* Rechter kolom: domein-detail */}
          <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '20px 24px', boxShadow: 'var(--shadow)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
              <span style={{ fontSize: 18 }}>{activeDef.icon}</span>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)', lineHeight: 1.2 }}>{activeDef.label} — Details</div>
                <div style={{ fontSize: 10, color: 'var(--text4)', fontFamily: 'monospace' }}>{activeDef.zib}</div>
              </div>
            </div>

            {!activeFile ? (
              <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--text3)', fontSize: 13 }}>
                Geen bestand geüpload voor dit ZIB-domein.<br />
                <span style={{ fontSize: 12, color: 'var(--text4)' }}>Upload een bestand met naam «{activeDef.schema}» om dit domein te valideren.</span>
              </div>
            ) : allClean ? (
              <GapRow icon="✓" title="Geen issues gevonden" sub="Alle ZIB-velden conform standaard" status="Conform" color="green" />
            ) : (
              <>
                {errorIssues.map((issue, i) => (
                  <ExpandableIssueRow key={`e${i}`} icon="✕" title={issue.label}
                    sub={issue.detail || `${issue.count} rijen`} status="Onvolledig veld" color="red" issue={issue} />
                ))}
                {warningIssues.map((issue, i) => (
                  <ExpandableIssueRow key={`w${i}`} icon="⚠" title={issue.label}
                    sub={issue.detail || `${issue.count} rijen`} status="Gedeeltelijk" color="amber" issue={issue} />
                ))}
              </>
            )}
          </div>
        </div>
      </Page>
    </div>
  )
}
