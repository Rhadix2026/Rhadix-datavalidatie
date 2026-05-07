import { Nav, NavBack, BtnPrimary, Page, PageTitle } from '../components/UI'

function scoreColor(s) {
  return s >= 80 ? 'var(--green)' : s >= 60 ? 'var(--amber)' : 'var(--red)'
}
function scoreLabel(s) {
  return s >= 80 ? 'Goed' : s >= 60 ? 'Voldoende' : 'Aandacht vereist'
}

// ── Berekening kwaliteitsscore uit scanresultaat ──────────────────────────────
function computeKwaliteit(results) {
  if (results?.kwaliteit_score != null) return Math.round(results.kwaliteit_score)
  if (results?.score != null) return Math.round(results.score)
  return null
}

function computeConceptStats(conceptMapping) {
  if (!conceptMapping?.length) return null
  let totalConcepts = 0, matchedConcepts = 0, totalDomains = 0, okDomains = 0
  conceptMapping.forEach(cm => {
    totalConcepts  += cm.total_concepts  || 0
    matchedConcepts+= cm.matched_concepts|| 0;
    (cm.domains || []).forEach(d => {
      totalDomains++
      if ((d.status || '').toLowerCase() === 'volledig') okDomains++
    })
  })
  const score = totalConcepts > 0 ? Math.round(matchedConcepts / totalConcepts * 100) : null
  return { totalConcepts, matchedConcepts, totalDomains, okDomains, score }
}

// ── Stap 2 samenvatting ───────────────────────────────────────────────────────
export default function Stap2Resultaat({ results, onContinue, onBack }) {
  const kwaliteit     = computeKwaliteit(results)
  const conceptStats  = computeConceptStats(results?.concept_mapping)
  const conceptMapping= results?.concept_mapping || []

  const color = kwaliteit != null ? scoreColor(kwaliteit) : 'var(--text3)'
  const label = kwaliteit != null ? scoreLabel(kwaliteit) : '—'

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={<NavBack onClick={onBack} />} />
      <Page>
        <PageTitle
          title="Stap 2 — Kwaliteit & KIK-V analyse"
          sub="Resultaten van de ontologie-koppeling en datakwaliteitscheck"
        />

        {/* Voltooiingsbanner */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '14px 18px', borderRadius: 'var(--radius)',
          background: '#f0fdf4', border: '1px solid #bbf7d0', marginBottom: 20,
        }}>
          <div style={{ fontSize: 22 }}>✅</div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#065f46' }}>
              Stap 2 analyse voltooid — 100%
            </div>
            <div style={{ fontSize: 12, color: '#059669' }}>
              {conceptMapping.length} schema('s) geanalyseerd op KIK-V ontologie
            </div>
          </div>
        </div>

        {/* Score kaart */}
        <div style={{
          background: '#fff', borderRadius: 'var(--radius-xl)',
          border: '1px solid var(--border)', padding: '24px 24px',
          marginBottom: 16, display: 'flex', alignItems: 'center', gap: 28,
        }}>
          <div style={{ textAlign: 'center', minWidth: 80 }}>
            <div style={{ fontSize: 56, fontWeight: 800, color, letterSpacing: '-0.04em', lineHeight: 1 }}>
              {kwaliteit ?? '—'}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 2 }}>van 100</div>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text)', marginBottom: 4 }}>
              Datakwaliteit & KIK-V readiness
            </div>
            <div style={{ fontSize: 13, color, fontWeight: 600, marginBottom: 10 }}>{label}</div>
            <div style={{ height: 8, background: 'var(--border)', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{
                height: '100%', width: `${kwaliteit ?? 0}%`,
                background: color, borderRadius: 4, transition: 'width .6s',
              }} />
            </div>
          </div>
        </div>

        {/* Concept-mapping statistieken */}
        {conceptStats && (
          <div style={{
            background: '#fff', borderRadius: 'var(--radius-xl)',
            border: '1px solid var(--border)', overflow: 'hidden', marginBottom: 16,
          }}>
            <div style={{
              padding: '14px 18px', borderBottom: '1px solid var(--border)',
              display: 'flex', alignItems: 'center', gap: 8,
            }}>
              <span style={{ fontSize: 16 }}>🔗</span>
              <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)' }}>
                KIK-V ontologie-koppeling
              </span>
              <span style={{
                marginLeft: 'auto', fontSize: 12, fontWeight: 700,
                padding: '3px 10px', borderRadius: 20,
                background: conceptStats.score >= 70 ? 'var(--green-light)' : 'var(--amber-light)',
                color: conceptStats.score >= 70 ? 'var(--green)' : 'var(--amber)',
              }}>
                {conceptStats.matchedConcepts}/{conceptStats.totalConcepts} velden gekoppeld
              </span>
            </div>
            <div style={{ display: 'flex', gap: 0 }}>
              {[
                { label: 'Velden gecontroleerd', value: conceptStats.totalConcepts,   color: 'var(--blue)' },
                { label: 'Succesvol gekoppeld',  value: conceptStats.matchedConcepts, color: 'var(--green)' },
                { label: 'Domeinen volledig',    value: `${conceptStats.okDomains}/${conceptStats.totalDomains}`, color: conceptStats.okDomains === conceptStats.totalDomains ? 'var(--green)' : 'var(--amber)' },
              ].map((item, i, arr) => (
                <div key={i} style={{
                  flex: 1, padding: '16px 18px', textAlign: 'center',
                  borderRight: i < arr.length - 1 ? '1px solid var(--border)' : 'none',
                }}>
                  <div style={{ fontSize: 26, fontWeight: 800, color: item.color }}>{item.value}</div>
                  <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4 }}>{item.label}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Per schema */}
        {conceptMapping.length > 0 && (
          <div style={{
            background: '#fff', borderRadius: 'var(--radius-xl)',
            border: '1px solid var(--border)', overflow: 'hidden', marginBottom: 20,
          }}>
            <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)', fontSize: 14, fontWeight: 700, color: 'var(--text)' }}>
              📋 Resultaat per schema
            </div>
            {conceptMapping.map((cm, i) => {
              const pct = cm.total_concepts > 0
                ? Math.round(cm.matched_concepts / cm.total_concepts * 100) : 0
              const col = scoreColor(pct)
              return (
                <div key={i} style={{
                  padding: '13px 18px', display: 'flex', alignItems: 'center', gap: 12,
                  borderBottom: i < conceptMapping.length - 1 ? '1px solid var(--border)' : 'none',
                }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)', textTransform: 'capitalize' }}>
                      {cm.schema_label || cm.schema_key || 'Schema'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 2 }}>
                      {cm.matched_concepts ?? 0} van {cm.total_concepts ?? 0} velden gekoppeld aan KIK-V ontologie
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 20, fontWeight: 800, color: col }}>{pct}%</div>
                    <div style={{ fontSize: 11, color: col }}>{scoreLabel(pct)}</div>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        <BtnPrimary
          onClick={onContinue}
          style={{ width: '100%', justifyContent: 'center', padding: '13px' }}
        >
          Bekijk volledig dashboard →
        </BtnPrimary>
      </Page>
    </div>
  )
}
