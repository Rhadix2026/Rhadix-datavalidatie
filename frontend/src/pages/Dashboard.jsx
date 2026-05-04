import { useState } from 'react'
import { Nav, NavLink, Page, BtnPrimary, ProgressBar, StatusBadge, StatusIcon, ExpandableIssueRow, GapRow } from '../components/UI'

const DOMAINS = ['Mens', 'Werkovereenkomst', 'Verzuim']

function domainIssues(domain, results) {
  if (!results) return []
  const domainMap = {
    Mens: ['medewerker'],
    Werkovereenkomst: ['werkovereenkomst', 'functie'],
    Verzuim: ['verzuim'],
  }
  const keys = domainMap[domain] || []
  return (results.file_results || [])
    .filter(f => keys.includes(f.schema_key))
    .flatMap(f => f.issues || [])
}

function domainStatus(domain, results) {
  const issues = domainIssues(domain, results)
  if (issues.some(i => i.severity === 'error')) return 'red'
  if (issues.some(i => i.severity === 'warning')) return 'amber'
  return 'green'
}

const DOT_COLORS = { red: 'var(--red)', amber: 'var(--amber)', green: 'var(--green)' }

export default function Dashboard({ results, scanHistory = [], step1Completed, step2Completed, onNewScan, onAdvies, onBeschikbaarheidsRapport, onKikvRapport, onManagementRapport }) {
  const [activeDomain, setActiveDomain] = useState('Werkovereenkomst')

  // Guard: toon nooit placeholder-data als er geen actief scanresultaat is
  if (!results) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
        <Nav right={<NavLink onClick={onNewScan}>Nieuwe scan</NavLink>} />
        <Page>
          <div style={{ textAlign: 'center', padding: '80px 24px' }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>📋</div>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text)', marginBottom: 8 }}>Geen actief scanresultaat</h2>
            <p style={{ fontSize: 14, color: 'var(--text3)', marginBottom: 24 }}>Start een nieuwe scan om resultaten te zien.</p>
            <BtnPrimary onClick={onNewScan}>Start nieuwe scan</BtnPrimary>
          </div>
        </Page>
      </div>
    )
  }

  const score1 = results?.score ?? 0
  const score2 = Math.max(0, score1 - 26)
  const radixIndex = Math.round((score1 + score2) / 2)

  const domainMap = { Mens: ['medewerker'], Werkovereenkomst: ['werkovereenkomst','functie'], Verzuim: ['verzuim'] }
  const activeFiles = (results?.file_results || []).filter(f => (domainMap[activeDomain] || []).includes(f.schema_key))
  const activeIssues = activeFiles.flatMap(f => f.issues || [])

  // Splits issues by severity for domain detail panel
  const errorIssues   = activeIssues.filter(i => i.severity === 'error')
  const warningIssues = activeIssues.filter(i => i.severity === 'warning')
  const allClean      = activeIssues.length === 0

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={
        <>
          <NavLink onClick={onNewScan}>Nieuwe scan</NavLink>
          <NavLink>Profiel</NavLink>
        </>
      } />

      <Page>
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em', marginBottom: 4 }}>Dashboard Overzicht</h1>
          <p style={{ fontSize: 14, color: 'var(--text3)' }}>Twee-staps verificatie resultaten</p>
        </div>

        {/* Rhadix Index hero card */}
        <div style={{
          background: 'linear-gradient(135deg, #2d3eb8 0%, #1e3a8a 100%)',
          borderRadius: 'var(--radius-xl)', padding: '28px 32px',
          marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <span style={{ fontSize: 16 }}>🎯</span>
              <span style={{ fontSize: 16, fontWeight: 700, color: '#fff' }}>Rhadix Index</span>
            </div>
            <div style={{ fontSize: 13, color: 'rgba(255,255,255,.7)', marginBottom: 14 }}>Gecombineerde score (Stap 1 + Stap 2)</div>
            <div style={{
              display: 'inline-flex', background: 'rgba(255,255,255,.15)', color: '#fff',
              fontSize: 13, fontWeight: 600, padding: '6px 14px', borderRadius: 20,
            }}>
              → {radixIndex >= 80 ? 'Uitstekend' : radixIndex >= 65 ? 'Goed, kleine gaps' : 'Voldoende, actie nodig'}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 64, fontWeight: 800, color: '#fff', letterSpacing: '-0.04em', lineHeight: 1 }}>{radixIndex}</div>
            <div style={{ fontSize: 13, color: 'rgba(255,255,255,.6)', marginTop: 4 }}>van 100</div>
          </div>
        </div>

        {/* Stap scores */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
          {[
            { num: 1, title: 'Rhadix Beschikbaarheid', sub: 'Leverancier matching', score: score1 },
            { num: 2, title: 'Rhadix Kwaliteit',       sub: 'KIK-V readiness',      score: score2 },
          ].map(s => {
            const color = s.score >= 80 ? 'var(--green)' : s.score >= 60 ? 'var(--amber)' : 'var(--red)'
            const label = s.score >= 80 ? 'Goed' : s.score >= 60 ? 'Voldoende' : 'Onvoldoende'
            return (
              <div key={s.num} style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '20px 24px', boxShadow: 'var(--shadow)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <div style={{ width: 24, height: 24, borderRadius: '50%', background: 'var(--blue-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, color: 'var(--blue)' }}>{s.num}</div>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{s.title}</div>
                    <div style={{ fontSize: 11, color: 'var(--text3)' }}>{s.sub}</div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 10 }}>
                  <span style={{ fontSize: 36, fontWeight: 800, color: 'var(--blue)', letterSpacing: '-0.03em' }}>{s.score}</span>
                  <StatusBadge status={label} />
                </div>
                <ProgressBar value={s.score} color={color} />
              </div>
            )
          })}
        </div>

        {/* Rapporten card — alle 3 rapporten, per stap gelabeld */}
        {results?.run_id && (
          <div style={{
            background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)',
            padding: '20px 24px', marginBottom: 16, boxShadow: 'var(--shadow)',
          }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', marginBottom: 14 }}>📑 Rapporten</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[
                {
                  icon: '📄',
                  label: 'Beschikbaarheidsrapport',
                  sub: 'Stap 1 — veld-voor-veld toelichting, scores en vervolgstappen',
                  stepLabel: 'Stap 1',
                  enabled: step1Completed,
                  onClick: onBeschikbaarheidsRapport,
                },
                {
                  icon: '📊',
                  label: 'KIK-V Readiness rapport',
                  sub: 'Stap 2 — per-indicator analyse, kwaliteitsscores',
                  stepLabel: 'Stap 2',
                  enabled: step2Completed,
                  onClick: onKikvRapport,
                },
                {
                  icon: '📋',
                  label: 'Gecombineerd managementrapport',
                  sub: 'Stap 2 — Rhadix Index, risico\'s, actieplan en advies',
                  stepLabel: 'Stap 2',
                  enabled: step2Completed,
                  onClick: onManagementRapport,
                },
              ].map(r => (
                <div key={r.label} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
                  padding: '12px 14px', borderRadius: 'var(--radius)',
                  background: r.enabled ? 'var(--blue-light)' : '#fafafa',
                  border: r.enabled ? '1px solid var(--blue-mid)' : '1px solid var(--border)',
                  opacity: r.enabled ? 1 : 0.65,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 18 }}>{r.icon}</span>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ fontSize: 13, fontWeight: 700, color: r.enabled ? 'var(--blue)' : 'var(--text2)' }}>{r.label}</span>
                        <span style={{
                          fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 20,
                          background: r.enabled ? 'var(--blue)' : 'var(--border)',
                          color: r.enabled ? '#fff' : 'var(--text3)',
                        }}>{r.stepLabel}</span>
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 1 }}>{r.sub}</div>
                    </div>
                  </div>
                  <button
                    onClick={r.enabled ? r.onClick : undefined}
                    disabled={!r.enabled}
                    title={!r.enabled ? 'Voer eerst stap 2 uit om kwaliteit en KIK-V readiness te rapporteren.' : undefined}
                    style={{
                      flexShrink: 0,
                      background: r.enabled ? 'var(--blue)' : 'var(--border)',
                      color: r.enabled ? '#fff' : 'var(--text3)',
                      border: 'none', borderRadius: 'var(--radius)',
                      padding: '8px 14px', fontSize: 12, fontWeight: 600,
                      cursor: r.enabled ? 'pointer' : 'not-allowed',
                      fontFamily: 'var(--font)', whiteSpace: 'nowrap',
                    }}
                  >
                    {r.enabled ? `${r.icon} Bekijk` : '🔒 Stap 2 vereist'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Domains + detail */}
        <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: 12 }}>
          {/* Domain list */}
          <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '16px', boxShadow: 'var(--shadow)' }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', marginBottom: 12 }}>Domeinen</div>
            {DOMAINS.map(d => {
              const status = domainStatus(d, results)
              const active = activeDomain === d
              return (
                <div key={d} onClick={() => setActiveDomain(d)} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '10px 12px', borderRadius: 'var(--radius)', cursor: 'pointer',
                  background: active ? 'var(--blue-light)' : 'transparent',
                  border: active ? '1px solid var(--blue-mid)' : '1px solid transparent',
                  marginBottom: 4, transition: 'all .1s',
                }}>
                  <span style={{ fontSize: 13, fontWeight: active ? 600 : 400, color: active ? 'var(--blue)' : 'var(--text2)' }}>{d}</span>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: DOT_COLORS[status] }} />
                </div>
              )
            })}
          </div>

          {/* Domain detail */}
          <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '20px 24px', boxShadow: 'var(--shadow)' }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)', marginBottom: 14 }}>{activeDomain} — Details</div>

            <div style={{ marginBottom: 16 }}>
              {allClean ? (
                <GapRow icon="✓" title="Geen issues gevonden" sub="Alle velden conform standaard" status="Conform" color="green" />
              ) : (
                <>
                  {errorIssues.map((issue, i) => (
                    <ExpandableIssueRow
                      key={`e${i}`}
                      icon="✕"
                      title={issue.label}
                      sub={issue.detail || `${issue.count} rijen`}
                      status="Onvolledig veld"
                      color="red"
                      issue={issue}
                    />
                  ))}
                  {warningIssues.map((issue, i) => (
                    <ExpandableIssueRow
                      key={`w${i}`}
                      icon="⚠"
                      title={issue.label}
                      sub={issue.detail || `${issue.count} rijen`}
                      status="Gedeeltelijk"
                      color="amber"
                      issue={issue}
                    />
                  ))}
                </>
              )}
            </div>

            <BtnPrimary onClick={() => onAdvies(activeDomain)} style={{ width: '100%', justifyContent: 'center', padding: '11px' }}>
              Bekijk advies
            </BtnPrimary>
          </div>
        </div>
      </Page>
    </div>
  )
}
