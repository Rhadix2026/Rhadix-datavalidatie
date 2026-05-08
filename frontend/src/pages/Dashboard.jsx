import { useState, useCallback } from 'react'
import { Nav, NavLink, Page, BtnPrimary, ProgressBar, StatusBadge, StatusIcon, ExpandableIssueRow, GapRow } from '../components/UI'

// ── Rhadix Index uitleg ───────────────────────────────────────────────────────
function RhadixUitleg({ score1, score2, radixIndex }) {
  const [open, setOpen] = useState(false)
  const RANGES = [
    { min: 85, label: 'Uitstekend',        color: '#059669', bg: '#f0fdf4', border: '#bbf7d0', desc: 'Data is volledig beschikbaar en van hoge kwaliteit. Klaar voor KIK-V uitwisseling.' },
    { min: 65, label: 'Goed',              color: 'var(--blue)', bg: 'var(--blue-light)', border: 'var(--blue-mid)', desc: 'Data is grotendeels op orde. Kleine verbeteringen verbeteren de index verder.' },
    { min: 50, label: 'Voldoende',         color: 'var(--amber)', bg: 'var(--amber-light)', border: '#fcd34d', desc: 'Actie nodig. Haal ontbrekende velden binnen en los kwaliteitsfouten op.' },
    { min: 0,  label: 'Onvoldoende',       color: 'var(--red)',   bg: 'var(--red-bg)',     border: 'var(--red-light)', desc: 'Significante hiaten in beschikbaarheid of kwaliteit. Directe actie vereist.' },
  ]
  const current = RANGES.find(r => radixIndex >= r.min) || RANGES[RANGES.length - 1]

  return (
    <span style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}>
      <button
        onClick={() => setOpen(o => !o)}
        title="Hoe wordt de Rhadix Index berekend?"
        style={{
          background: 'var(--blue-light)', border: '1px solid var(--blue-mid)',
          borderRadius: '50%', width: 20, height: 20, cursor: 'pointer',
          fontSize: 11, fontWeight: 700, color: 'var(--blue)',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          marginLeft: 6, flexShrink: 0,
        }}
      >ℹ</button>

      {open && (
        <div style={{
          position: 'absolute', top: 28, left: '50%', transform: 'translateX(-50%)',
          zIndex: 200, width: 340, background: '#fff',
          border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)',
          boxShadow: '0 8px 32px rgba(0,0,0,.12)', padding: 20,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)' }}>📊 Rhadix Index — uitleg</div>
            <button onClick={() => setOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, color: 'var(--text3)', lineHeight: 1 }}>×</button>
          </div>

          {/* Formule */}
          <div style={{ background: 'var(--blue-light)', border: '1px solid var(--blue-mid)', borderRadius: 'var(--radius)', padding: '12px 14px', marginBottom: 14 }}>
            <div style={{ fontSize: 12, color: 'var(--blue)', fontWeight: 700, marginBottom: 6 }}>Berekening</div>
            <div style={{ fontSize: 13, color: 'var(--text)', display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
              <span style={{ fontWeight: 600 }}>Beschikbaarheid</span>
              <span style={{ color: 'var(--blue)', fontWeight: 800 }}>{score1}%</span>
              <span style={{ color: 'var(--text3)' }}>×</span>
              <span style={{ fontWeight: 600 }}>Kwaliteit</span>
              <span style={{ color: 'var(--blue)', fontWeight: 800 }}>{score2}%</span>
              <span style={{ color: 'var(--text3)' }}>=</span>
              <span style={{ fontWeight: 800, color: '#1e3a8a' }}>Rhadix Index {radixIndex}%</span>
            </div>
          </div>

          {/* Componenten */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text3)', marginBottom: 8 }}>Wat meten de componenten?</div>
            {[
              { label: 'Databeschikbaarheid (Stap 1)', score: score1, desc: 'Welk % van de vereiste KIK-V velden is aanwezig in de aangeleverde bestanden.' },
              { label: 'Datakwaliteit (Stap 2)',        score: score2, desc: 'Hoe correct zijn de aanwezige waarden: formaat, toegestane waarden, ontologie-koppeling.' },
            ].map((c, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 8, alignItems: 'flex-start' }}>
                <div style={{
                  minWidth: 36, height: 36, borderRadius: 8,
                  background: c.score >= 80 ? 'var(--green-light)' : c.score >= 60 ? 'var(--amber-light)' : 'var(--red-bg)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 13, fontWeight: 800,
                  color: c.score >= 80 ? 'var(--green)' : c.score >= 60 ? 'var(--amber)' : 'var(--red)',
                }}>{c.score}%</div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>{c.label}</div>
                  <div style={{ fontSize: 11, color: 'var(--text3)', lineHeight: 1.4 }}>{c.desc}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Score ranges */}
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text3)', marginBottom: 8 }}>Score-interpretatie</div>
            {RANGES.map((r, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6,
                padding: '6px 10px', borderRadius: 8,
                background: r.label === current.label ? r.bg : 'transparent',
                border: r.label === current.label ? `1px solid ${r.border}` : '1px solid transparent',
              }}>
                <span style={{
                  fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 10,
                  background: r.bg, color: r.color, border: `1px solid ${r.border}`, whiteSpace: 'nowrap',
                }}>
                  {i === 0 ? '85–100' : i === 1 ? '65–84' : i === 2 ? '50–64' : '0–49'} — {r.label}
                  {r.label === current.label ? ' ◀ nu' : ''}
                </span>
                <span style={{ fontSize: 11, color: 'var(--text3)', lineHeight: 1.3 }}>{r.desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </span>
  )
}

// Alle bekende KIK-V domeinen — gebaseerd op de ONZ-ontologie modules
// icon: visuele indicatie, schemas: welke geüploade schema's horen erbij
const ALL_DOMAINS = [
  { key: 'Mens',                icon: '👤', schemas: ['medewerker'],                    module: 'onz-pers' },
  { key: 'Werkovereenkomst',    icon: '📄', schemas: ['werkovereenkomst'],              module: 'onz-pers' },
  { key: 'Functie',             icon: '🎓', schemas: ['functie','kwalificatieniveau'],  module: 'onz-pers' },
  { key: 'Verzuim',             icon: '🏥', schemas: ['verzuim'],                       module: 'onz-pers' },
  { key: 'Organisatie',         icon: '🏢', schemas: ['vestiging','organisatie'],       module: 'onz-org'  },
  { key: 'Zorg',                icon: '💊', schemas: ['client','zorgovereenkomst'],     module: 'onz-zorg' },
  { key: 'Financiën',           icon: '💶', schemas: ['kostenplaats','grootboek'],      module: 'onz-fin'  },
]

function domainIssues(domain, results) {
  if (!results) return []
  const def = ALL_DOMAINS.find(d => d.key === domain)
  const keys = def?.schemas || []
  return (results.file_results || [])
    .filter(f => keys.includes(f.schema_key))
    .flatMap(f => f.issues || [])
}

function domainHasData(domain, results) {
  if (!results) return false
  const def = ALL_DOMAINS.find(d => d.key === domain)
  const keys = def?.schemas || []
  return (results.file_results || []).some(f => keys.includes(f.schema_key))
}

function domainStatus(domain, results) {
  if (!domainHasData(domain, results)) return 'grey'
  const issues = domainIssues(domain, results)
  if (issues.some(i => i.severity === 'error')) return 'red'
  if (issues.some(i => i.severity === 'warning')) return 'amber'
  return 'green'
}

const DOT_COLORS = { red: 'var(--red)', amber: 'var(--amber)', green: 'var(--green)' }

export default function Dashboard({ results, scanHistory = [], step1Completed, step2Completed, onNewScan, onAdvies, onBeschikbaarheidsRapport, onKikvRapport, onManagementRapport, onConceptMapping, onActuality, onTraceability, onProfiles }) {
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
  // Stap 2: gebruik echte concept-mapping score als beschikbaar, anders schatting
  const conceptMapping = results?.concept_mapping || []
  const score2 = conceptMapping.length
    ? Math.round(conceptMapping.reduce((s, r) => s + (r.summary?.mapping_score ?? 0), 0) / conceptMapping.length)
    : Math.max(0, score1 - 26)
  // Rhadix Index = Databeschikbaarheid × Datakwaliteit
  const radixIndex  = Math.round(score1 * score2 / 100)
  const dataverzuim = 100 - radixIndex
  const hasConceptMapping = conceptMapping.length > 0

  const activeDomainDef = ALL_DOMAINS.find(d => d.key === activeDomain) || ALL_DOMAINS[0]
  const activeFiles = (results?.file_results || []).filter(f => (activeDomainDef.schemas || []).includes(f.schema_key))
  const activeIssues = activeFiles.flatMap(f => f.issues || [])

  // Splits issues by severity for domain detail panel
  const errorIssues   = activeIssues.filter(i => i.severity === 'error')
  const warningIssues = activeIssues.filter(i => i.severity === 'warning')
  // allClean = geen errors of warnings (info-only telt als schoon)
  const allClean      = errorIssues.length === 0 && warningIssues.length === 0

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={
        <>
          <NavLink onClick={onProfiles}>📚 Profielen</NavLink>
          <NavLink onClick={onNewScan}>Nieuwe scan</NavLink>
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
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <div style={{
                display: 'inline-flex', background: 'rgba(255,255,255,.15)', color: '#fff',
                fontSize: 13, fontWeight: 600, padding: '6px 14px', borderRadius: 20,
              }}>
                → {radixIndex >= 80 ? 'Uitstekend' : radixIndex >= 65 ? 'Goed, kleine gaps' : 'Voldoende, actie nodig'}
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
            <div style={{ fontSize: 64, fontWeight: 800, color: '#fff', letterSpacing: '-0.04em', lineHeight: 1 }}>{radixIndex}</div>
            <div style={{ fontSize: 13, color: 'rgba(255,255,255,.6)', marginTop: 4 }}>van 100</div>
          </div>
        </div>

        {/* Rhadix formule */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          fontSize: 13, color: 'var(--text3)', marginBottom: 16, flexWrap: 'wrap',
        }}>
          <span style={{ fontWeight: 600, color: 'var(--text2)' }}>Databeschikbaarheid</span>
          <span style={{ fontWeight: 700, color: 'var(--blue)', fontSize: 15 }}>{score1}%</span>
          <span style={{ color: 'var(--text4)' }}>×</span>
          <span style={{ fontWeight: 600, color: 'var(--text2)' }}>Datakwaliteit</span>
          <span style={{ fontWeight: 700, color: 'var(--blue)', fontSize: 15 }}>{score2}%</span>
          <span style={{ color: 'var(--text4)' }}>=</span>
          <span style={{ fontWeight: 800, color: '#1e3a8a', fontSize: 15 }}>Rhadix Index {radixIndex}%</span>
          <RhadixUitleg score1={score1} score2={score2} radixIndex={radixIndex} />
        </div>

        {/* Stap scores */}
        <div className="score-grid">
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
            <div className="rapport-grid">
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
                  icon: '🔗',
                  label: 'Concept-mapping rapport',
                  sub: 'Stap 2 — ontologiekoppeling per veld (KIK-V ONZ)',
                  stepLabel: 'Stap 2',
                  enabled: hasConceptMapping,
                  onClick: onConceptMapping,
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
                {
                  icon: '⏱',
                  label: 'Data Actualiteit Score',
                  sub: 'Tijdsdimensie — hoe recent zijn de records in uw bestanden?',
                  stepLabel: 'Nieuw',
                  enabled: step1Completed,
                  onClick: onActuality,
                },
                {
                  icon: '🔍',
                  label: 'Traceerbaarheid — alle problemen',
                  sub: 'Drilldown per rij · KIK-V klasse · indicator · uitwisselprofiel',
                  stepLabel: 'Nieuw',
                  enabled: step1Completed,
                  onClick: onTraceability,
                },
                {
                  icon: '📋',
                  label: 'KIK-V Profielimport',
                  sub: 'Importeer officiële KIK-V indicatoren uit GitLab',
                  stepLabel: 'Nieuw',
                  enabled: true,
                  onClick: onProfiles,
                },
              ].map(r => (
                <div key={r.label} style={{
                  display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: 12,
                  padding: '14px 16px', borderRadius: 'var(--radius)',
                  background: r.enabled ? 'var(--blue-light)' : '#fafafa',
                  border: r.enabled ? '1px solid var(--blue-mid)' : '1px solid var(--border)',
                  opacity: r.enabled ? 1 : 0.65,
                }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                    <span style={{ fontSize: 20, lineHeight: 1 }}>{r.icon}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: 13, fontWeight: 700, color: r.enabled ? 'var(--blue)' : 'var(--text2)' }}>{r.label}</span>
                        <span style={{
                          fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 20,
                          background: r.enabled ? 'var(--blue)' : 'var(--border)',
                          color: r.enabled ? '#fff' : 'var(--text3)',
                          whiteSpace: 'nowrap',
                        }}>{r.stepLabel}</span>
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 3, lineHeight: 1.4 }}>{r.sub}</div>
                    </div>
                  </div>
                  <button
                    onClick={r.enabled ? r.onClick : undefined}
                    disabled={!r.enabled}
                    title={!r.enabled ? 'Voer eerst stap 2 uit om kwaliteit en KIK-V readiness te rapporteren.' : undefined}
                    style={{
                      width: '100%',
                      background: r.enabled ? 'var(--blue)' : 'var(--border)',
                      color: r.enabled ? '#fff' : 'var(--text3)',
                      border: 'none', borderRadius: 'var(--radius)',
                      padding: '9px 14px', fontSize: 12, fontWeight: 600,
                      cursor: r.enabled ? 'pointer' : 'not-allowed',
                      fontFamily: 'var(--font)',
                    }}
                  >
                    {r.enabled ? 'Bekijk' : '🔒 Stap 2 vereist'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Domains + detail */}
        <div className="domain-grid">
          {/* Domain list */}
          <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '16px', boxShadow: 'var(--shadow)' }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', marginBottom: 12 }}>Domeinen</div>
            {ALL_DOMAINS.map(d => {
              const status  = domainStatus(d.key, results)
              const hasData = domainHasData(d.key, results)
              const active  = activeDomain === d.key
              const dotColor = { red: 'var(--red)', amber: 'var(--amber)', green: 'var(--green)', grey: '#d1d5db' }[status]
              return (
                <div key={d.key} onClick={() => setActiveDomain(d.key)} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '9px 12px', borderRadius: 'var(--radius)', cursor: 'pointer',
                  background: active ? 'var(--blue-light)' : 'transparent',
                  border: active ? '1px solid var(--blue-mid)' : '1px solid transparent',
                  marginBottom: 3, transition: 'all .1s',
                  opacity: hasData ? 1 : 0.7,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                    <span style={{ fontSize: 14 }}>{d.icon}</span>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: active ? 700 : 500, color: active ? 'var(--blue)' : 'var(--text2)', lineHeight: 1.2 }}>{d.key}</div>
                      <div style={{ fontSize: 10, color: 'var(--text4)', lineHeight: 1 }}>{d.module}</div>
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

          {/* Domain detail */}
          <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '20px 24px', boxShadow: 'var(--shadow)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
              <span style={{ fontSize: 18 }}>{activeDomainDef.icon}</span>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)', lineHeight: 1.2 }}>{activeDomain} — Details</div>
                <div style={{ fontSize: 11, color: 'var(--text4)' }}>{activeDomainDef.module}</div>
              </div>
            </div>

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
