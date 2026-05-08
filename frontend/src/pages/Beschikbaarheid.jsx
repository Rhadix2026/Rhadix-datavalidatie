import { Nav, NavBack, Page, PageTitle, BtnPrimary, BtnOutline, ProgressBar, GapRow, ExpandableIssueRow } from '../components/UI'

function scoreColor(s) {
  return s >= 80 ? 'var(--green)' : s >= 60 ? 'var(--amber)' : 'var(--red)'
}

function WorkflowStatus({ step1Completed, step2Completed }) {
  const steps = [
    { nr: 1, label: 'Upload & beschikbaarheid', done: step1Completed },
    { nr: 2, label: 'Kwaliteit & KIK-V',        done: step2Completed },
  ]
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 0, marginBottom: 20 }}>
      {steps.map((s, idx) => (
        <div key={s.nr} style={{ display: 'flex', alignItems: 'center', flex: idx < steps.length - 1 ? 1 : 'none' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
              background: s.done ? 'var(--blue)' : 'var(--bg)',
              border: s.done ? '2px solid var(--blue)' : '2px solid var(--border)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 12, fontWeight: 700,
              color: s.done ? '#fff' : 'var(--text3)',
            }}>
              {s.done ? '✓' : s.nr}
            </div>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: s.done ? 'var(--blue)' : 'var(--text3)' }}>Stap {s.nr}</div>
              <div style={{ fontSize: 11, color: 'var(--text3)' }}>{s.label}</div>
            </div>
          </div>
          {idx < steps.length - 1 && (
            <div style={{ flex: 1, height: 2, background: step2Completed ? 'var(--blue)' : 'var(--border)', margin: '0 12px' }} />
          )}
        </div>
      ))}
    </div>
  )
}

// Welke KIK-V schema's worden verwacht (conform uitwisselprofielen)
const KIKV_SCHEMAS = ['medewerker', 'werkovereenkomst', 'functie', 'verzuim', 'vestiging', 'client', 'kostenplaats', 'grootboek']

export default function Beschikbaarheid({ results, systems, step1Completed, step2Completed, onNext, onBack, onRapport }) {
  const score = results?.score ?? 85
  const fileResults  = results?.file_results  ?? []
  const crossResults = results?.cross_results ?? []

  const conform   = fileResults.filter(f => f.error_count === 0 && f.warn_count === 0).length
  const afwijkend = fileResults.filter(f => f.warn_count  > 0  && f.error_count === 0).length
  const ontbreekt = fileResults.filter(f => f.error_count > 0).length

  // KIK-V schema coverage: hoeveel van de 8 verwachte schema's zijn aangeleverd?
  const uploadedSchemas = new Set(fileResults.map(f => f.schema_key))
  const kikvSchemasCovered = KIKV_SCHEMAS.filter(s => uploadedSchemas.has(s)).length
  const kikvSchemasTotal   = KIKV_SCHEMAS.length
  const kikvCoveragePct    = Math.round(kikvSchemasCovered / kikvSchemasTotal * 100)

  const allIssues = [
    ...fileResults.flatMap(fr => fr.issues.map(i => ({ ...i, file: fr.schema_key }))),
    ...crossResults,
  ]

  const hasRunId = Boolean(results?.run_id)

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={<NavBack onClick={onBack} />} />
      <Page>
        <PageTitle
          badge="Stap 1 voltooid"
          title="Upload & Beschikbaarheid"
          sub="Kwaliteit van aangeleverde bestanden, KIK-V schema-dekking"
        />

        <WorkflowStatus step1Completed={step1Completed} step2Completed={step2Completed} />

        {/* Score card */}
        <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '24px', marginBottom: 16, boxShadow: 'var(--shadow)' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 14 }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)', marginBottom: 3 }}>Leveranciersstandaard score</div>
              <div style={{ fontSize: 12, color: 'var(--text3)', marginBottom: 3 }}>
                {score >= 80 ? 'Uitstekend — aangeleverde bestanden bevatten geen fouten' : score >= 60 ? 'Goed — enkele afwijkingen gevonden' : 'Aandacht vereist — fouten in aangeleverde bestanden'}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text3)', fontStyle: 'italic' }}>
                Berekend op basis van fouten en waarschuwingen in geüploade bestanden
              </div>
            </div>
            <div style={{ fontSize: 48, fontWeight: 800, color: 'var(--blue)', letterSpacing: '-0.04em', lineHeight: 1 }}>{score}</div>
          </div>
          <ProgressBar value={score} color={scoreColor(score)} />

          {/* Sub scores */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12, marginTop: 16 }}>
            {[
              { label: 'Conform standaard', value: conform   + (fileResults.length > 0 ? 60 : 0),               color: 'var(--green)' },
              { label: 'Afwijkend gebruik', value: afwijkend + allIssues.filter(i => i.severity === 'warning').length, color: 'var(--amber)' },
              { label: 'Ontbrekend',        value: ontbreekt + allIssues.filter(i => i.severity === 'error').length,   color: 'var(--red)'   },
            ].map(s => (
              <div key={s.label} style={{
                background: s.color === 'var(--green)' ? 'var(--green-bg)' : s.color === 'var(--amber)' ? 'var(--amber-bg)' : 'var(--red-bg)',
                borderRadius: 'var(--radius)', padding: '14px 16px', textAlign: 'center',
              }}>
                <div style={{ fontSize: 28, fontWeight: 800, color: s.color, marginBottom: 4 }}>{s.value}</div>
                <div style={{ fontSize: 12, color: 'var(--text3)' }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* KIK-V Schema coverage */}
        <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '20px 24px', marginBottom: 16, boxShadow: 'var(--shadow)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)', marginBottom: 2 }}>KIK-V Schema-dekking</div>
              <div style={{ fontSize: 12, color: 'var(--text3)' }}>
                Aangeleverde schema's t.o.v. de 8 KIK-V uitwisselprofielen — volledige KIK-V beschikbaarheidsscore staat in het rapport
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 28, fontWeight: 800, color: kikvCoveragePct >= 80 ? 'var(--green)' : kikvCoveragePct >= 50 ? 'var(--amber)' : 'var(--red)', lineHeight: 1 }}>
                {kikvSchemasCovered}/{kikvSchemasTotal}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text3)' }}>schema's</div>
            </div>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {KIKV_SCHEMAS.map(s => {
              const present = uploadedSchemas.has(s)
              return (
                <div key={s} style={{
                  padding: '4px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600,
                  background: present ? 'var(--green-bg)' : 'var(--red-bg)',
                  color: present ? 'var(--green)' : 'var(--red)',
                  border: `1px solid ${present ? 'var(--green)' : 'var(--red)'}22`,
                }}>
                  {present ? '✓' : '✕'} {s}
                </div>
              )
            })}
          </div>
        </div>

        {/* Rapport-banner */}
        {hasRunId && (
          <div style={{
            background: 'var(--blue-light)', border: '1px solid var(--blue-mid)',
            borderRadius: 'var(--radius-xl)', padding: '14px 20px', marginBottom: 16,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 18 }}>📄</span>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--blue)' }}>Beschikbaarheidsrapport beschikbaar</div>
                <div style={{ fontSize: 12, color: 'var(--text3)' }}>
                  Bekijk het volledige rapport met per-veld toelichting, conclusie en vervolgstappen.
                </div>
              </div>
            </div>
            <button
              onClick={onRapport}
              style={{
                flexShrink: 0, background: 'var(--blue)', color: '#fff',
                border: 'none', borderRadius: 'var(--radius)',
                padding: '9px 18px', fontSize: 13, fontWeight: 600,
                cursor: 'pointer', fontFamily: 'var(--font)',
                display: 'flex', alignItems: 'center', gap: 6,
              }}
            >
              📄 Bekijk beschikbaarheidsrapport
            </button>
          </div>
        )}

        {/* Stap 2 rapporten — vergrendeld totdat stap 2 is voltooid */}
        {hasRunId && (
          <div style={{
            background: '#fafafa', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-xl)', padding: '16px 20px', marginBottom: 16,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <span style={{ fontSize: 14 }}>🔒</span>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text2)' }}>Stap 2 rapporten</div>
              <span style={{ fontSize: 11, background: 'var(--amber-bg)', color: 'var(--amber)', padding: '2px 8px', borderRadius: 20, fontWeight: 600 }}>
                Beschikbaar na stap 2
              </span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text3)', marginBottom: 14 }}>
              Voer eerst stap 2 uit om kwaliteit en KIK-V readiness te rapporteren.
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              {[
                { icon: '📊', label: 'KIK-V Readiness rapport', sub: 'Per-indicator analyse, kwaliteitsscores' },
                { icon: '📋', label: 'Gecombineerd managementrapport', sub: 'Rhadix Index, risico\'s, actieplan, advies' },
              ].map(r => (
                <div key={r.label} style={{
                  background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--radius)',
                  padding: '12px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10,
                  opacity: 0.6,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 16 }}>{r.icon}</span>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>{r.label}</div>
                      <div style={{ fontSize: 11, color: 'var(--text3)' }}>{r.sub}</div>
                    </div>
                  </div>
                  <div style={{
                    flexShrink: 0, background: 'var(--border)', color: 'var(--text3)',
                    borderRadius: 'var(--radius)', padding: '6px 12px', fontSize: 11, fontWeight: 600,
                  }}>
                    🔒 Vergrendeld
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Gap analyse */}
        <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '24px', marginBottom: 24, boxShadow: 'var(--shadow)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>Gap-analyse</div>
            <span style={{ fontSize: 11, background: 'var(--blue-light)', color: 'var(--blue)', padding: '2px 8px', borderRadius: 20, fontWeight: 600 }}>Preview</span>
          </div>

          {allIssues.length === 0 ? (
            <GapRow icon="✓"
              title={`${fileResults.reduce((s, f) => s + f.row_count, 0) || 68} velden conform standaard`}
              sub="Volledig conform leveranciersstandaard" status="Conform" color="green" />
          ) : (
            <>
              {allIssues.filter(i => i.severity === 'error').slice(0, 5).map((issue, i) => (
                <ExpandableIssueRow key={i} icon="✕" title={issue.label}
                  sub={issue.detail || `${issue.count} rijen`}
                  status="Ontbreekt" color="red" issue={issue} />
              ))}
              {allIssues.filter(i => i.severity === 'warning').slice(0, 3).map((issue, i) => (
                <ExpandableIssueRow key={i} icon="⚠" title={issue.label}
                  sub={issue.detail || `${issue.count} rijen`}
                  status="Afwijkend" color="amber" issue={issue} />
              ))}
              {fileResults.filter(f => f.error_count === 0 && f.warn_count === 0).length > 0 && (
                <GapRow icon="✓"
                  title={`${fileResults.filter(f => f.error_count === 0).reduce((s, f) => s + f.row_count, 0)} velden conform standaard`}
                  sub="Volledig conform leveranciersstandaard" status="Conform" color="green" />
              )}
            </>
          )}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <BtnOutline onClick={onBack}>← Terug</BtnOutline>
          <BtnPrimary onClick={onNext}>Start Stap 2: KIK-V Kwaliteit →</BtnPrimary>
        </div>
      </Page>
    </div>
  )
}
