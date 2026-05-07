import { useState, useEffect } from 'react'
import { Nav, NavBack, Spinner } from '../components/UI'
import { getManagementRapport, exportManagementRapportPdf } from '../services/api'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function scoreColor(s) {
  return s >= 80 ? 'var(--green)' : s >= 60 ? 'var(--amber)' : 'var(--red)'
}
function scoreLabel(s) {
  return s >= 80 ? 'Uitstekend' : s >= 70 ? 'Goed' : s >= 60 ? 'Voldoende' : 'Onvoldoende'
}

const READINESS_CFG = {
  gereed:       { label: 'Gereed',       color: 'var(--green)', bg: 'var(--green-bg)',  icon: '✓' },
  gedeeltelijk: { label: 'Gedeeltelijk', color: 'var(--amber)', bg: 'var(--amber-bg)',  icon: '⚠' },
  niet_gereed:  { label: 'Niet gereed',  color: 'var(--red)',   bg: 'var(--red-bg)',    icon: '✕' },
}

const PRIO_CFG = {
  hoog:     { color: 'var(--red)',   bg: 'var(--red-bg)',   label: 'Hoog' },
  gemiddeld:{ color: 'var(--amber)', bg: 'var(--amber-bg)', label: 'Gemiddeld' },
  laag:     { color: 'var(--green)', bg: 'var(--green-bg)', label: 'Laag' },
}

const IMPACT_CFG = {
  hoog:     { color: 'var(--red)',   label: 'Hoog' },
  gemiddeld:{ color: 'var(--amber)', label: 'Gemiddeld' },
  laag:     { color: 'var(--green)', label: 'Laag' },
}

// ─── Rhadix Index hero ────────────────────────────────────────────────────────

function RhadixHero({ index, availScore, qualScore, readinessScore, indicators }) {
  const c = scoreColor(index)
  return (
    <div style={{
      background: 'linear-gradient(135deg, #1e3a8a 0%, #2d3eb8 100%)',
      borderRadius: 'var(--radius-xl)', padding: '28px 32px', marginBottom: 20,
      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24, flexWrap: 'wrap',
    }}>
      <div>
        <div style={{ fontSize: 12, fontWeight: 700, color: 'rgba(255,255,255,.6)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8 }}>
          🎯 Rhadix Index
        </div>
        <div style={{ fontSize: 72, fontWeight: 800, color: '#fff', letterSpacing: '-0.05em', lineHeight: 1 }}>{index}</div>
        <div style={{ fontSize: 13, color: 'rgba(255,255,255,.7)', marginTop: 6 }}>{scoreLabel(index)}</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12 }}>
        {[
          { label: 'Beschikbaarheid', value: availScore,     sub: 'Stap 1' },
          { label: 'Kwaliteit',       value: qualScore,      sub: 'Stap 2' },
          { label: 'KIK-V Readiness', value: readinessScore, sub: `${indicators.ready}/${indicators.total} gereed` },
        ].map(s => (
          <div key={s.label} style={{ background: 'rgba(255,255,255,.12)', borderRadius: 'var(--radius)', padding: '14px 18px', textAlign: 'center', minWidth: 100 }}>
            <div style={{ fontSize: 30, fontWeight: 800, color: '#fff', letterSpacing: '-0.03em', lineHeight: 1 }}>
              {Math.round(s.value)}
            </div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,.6)', marginTop: 2 }}>van 100</div>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'rgba(255,255,255,.85)', marginTop: 6 }}>{s.label}</div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,.5)', marginTop: 2 }}>{s.sub}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Section wrapper ──────────────────────────────────────────────────────────

function Section({ nr, title, children }) {
  return (
    <section style={{ marginBottom: 32 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
        <div style={{
          width: 28, height: 28, borderRadius: '50%', background: 'var(--blue)',
          color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 13, fontWeight: 800, flexShrink: 0,
        }}>{nr}</div>
        <h2 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em', margin: 0 }}>{title}</h2>
      </div>
      {children}
    </section>
  )
}

// ─── Risico-tabel ─────────────────────────────────────────────────────────────

function buildRisks(avail, qual, kikv, actions) {
  const risks = []
  const totalHours = actions.reduce((s, a) => s + (a.estimated_hours || 0), 0)

  if (avail.schemas_uploaded < avail.total_schemas) {
    risks.push({
      type: 'implementatie',
      risico: `${avail.total_schemas - avail.schemas_uploaded} schema('s) niet aangeleverd`,
      impact: 'hoog',
      mitigatie: 'Upload ontbrekende bestanden en hervalideer.',
    })
  }
  if (qual.total_errors > 0) {
    risks.push({
      type: 'implementatie',
      risico: `${qual.total_errors} kritieke fouten in data`,
      impact: qual.total_errors > 20 ? 'hoog' : 'gemiddeld',
      mitigatie: 'Corrigeer kritieke datavelden vóór oplevering.',
    })
  }
  if (kikv.indicators_not_ready > 0) {
    risks.push({
      type: 'gegevensuitwisseling',
      risico: `${kikv.indicators_not_ready} KIK-V indicator(en) niet gereed`,
      impact: 'hoog',
      mitigatie: 'Vul ontbrekende velden aan en hervalideer.',
    })
  }
  if (kikv.indicators_partial > 0) {
    risks.push({
      type: 'gegevensuitwisseling',
      risico: `${kikv.indicators_partial} indicator(en) deels gereed`,
      impact: 'gemiddeld',
      mitigatie: 'Los kwaliteitsissues op; hervalideer na correcties.',
    })
  }
  if (totalHours > 0) {
    risks.push({
      type: 'planning',
      risico: `Geschatte hersteltijd: ${totalHours.toFixed(0)} uur`,
      impact: totalHours > 10 ? 'hoog' : 'gemiddeld',
      mitigatie: 'Plan herstelsprint vóór KIK-V aanleverdatum.',
    })
  }
  return risks
}

// ─── Hoofd component ──────────────────────────────────────────────────────────

export default function ManagementRapport({ results, systems, onBack }) {
  const [rapport,     setRapport]     = useState(null)
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState(null)
  const [orgName,     setOrgName]     = useState('')
  const [exporting,   setExporting]   = useState(false)
  const [exportError, setExportError] = useState(null)
  const [editingOrg,  setEditingOrg]  = useState(false)
  const [openActions, setOpenActions] = useState({})

  const runId      = results?.run_id
  const systemsStr = (systems || []).join(',')
  const orgParam   = orgName || 'Zorginstelling'

  useEffect(() => {
    if (!runId) { setError('Geen scan-ID beschikbaar.'); setLoading(false); return }
    setLoading(true)
    getManagementRapport(runId, orgParam, systemsStr)
      .then(data => { setRapport(data); setLoading(false) })
      .catch(e   => { setError(e.message); setLoading(false) })
  }, [runId, orgParam, systemsStr])  // eslint-disable-line

  const handleExport = async () => {
    setExporting(true); setExportError(null)
    try { await exportManagementRapportPdf(runId, orgParam, systemsStr) }
    catch { setExportError('PDF-export mislukt. Controleer of de backend bereikbaar is.') }
    finally { setExporting(false) }
  }

  if (loading) return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={<NavBack onClick={onBack} dark />} /><Spinner />
    </div>
  )
  if (error) return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={<NavBack onClick={onBack} dark />} />
      <div style={{ maxWidth: 740, margin: '40px auto', padding: '0 24px' }}>
        <div style={{ background: 'var(--red-bg)', border: '1px solid var(--red-light)', borderRadius: 'var(--radius-xl)', padding: 24, color: 'var(--red)' }}>
          <strong>Fout bij laden rapport:</strong> {error}
        </div>
      </div>
    </div>
  )

  const avail  = rapport.availability_summary
  const qual   = rapport.quality_summary
  const rs     = rapport.kikv_readiness_summary
  const meta   = rapport.meta
  const risks  = buildRisks(avail, qual, rs, rapport.actions || [])
  const totalHours = (rapport.actions || []).reduce((s, a) => s + (a.estimated_hours || 0), 0)

  const highActions = (rapport.actions || []).filter(a => a.priority === 'hoog')
  const midActions  = (rapport.actions || []).filter(a => a.priority === 'gemiddeld')
  const lowActions  = (rapport.actions || []).filter(a => a.priority === 'laag')

  const scanDate = meta.scan_date
    ? new Date(meta.scan_date).toLocaleDateString('nl-NL', { day: 'numeric', month: 'long', year: 'numeric' })
    : new Date().toLocaleDateString('nl-NL', { day: 'numeric', month: 'long', year: 'numeric' })

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
            <span style={{ fontSize: 14, color: 'var(--text2)', fontWeight: 500 }}>Managementrapport</span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
          {exportError && <span style={{ fontSize: 12, color: 'var(--red)' }}>{exportError}</span>}
          <button onClick={handleExport} disabled={exporting} style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: exporting ? 'var(--border)' : 'var(--blue)',
            color: '#fff', border: 'none', borderRadius: 'var(--radius)',
            padding: '9px 16px', fontSize: 13, fontWeight: 600,
            cursor: exporting ? 'not-allowed' : 'pointer', fontFamily: 'var(--font)', whiteSpace: 'nowrap',
          }}>
            {exporting ? '⏳ Exporteren…' : '⬇ Exporteer PDF'}
          </button>
        </div>
      </div>

      {/* Rapportinhoud */}
      <div style={{ maxWidth: 960, margin: '0 auto', padding: '36px 24px 60px', width: '100%' }}>

        {/* Rapportkop */}
        <div style={{ marginBottom: 6 }}>
          <div style={{
            display: 'inline-flex', background: 'var(--blue-light)', color: 'var(--blue)',
            fontSize: 11, fontWeight: 700, padding: '4px 12px', borderRadius: 20, marginBottom: 10, letterSpacing: '0.08em',
          }}>
            GECOMBINEERD MANAGEMENTRAPPORT — STAP 1 + STAP 2
          </div>
          <h1 style={{ fontSize: 30, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.03em', marginBottom: 4 }}>
            Rhadix Managementrapport
          </h1>

          {/* Org-naam inline edit */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
            {editingOrg ? (
              <input autoFocus defaultValue={orgName}
                onBlur={e => { setOrgName(e.target.value); setEditingOrg(false) }}
                onKeyDown={e => { if (e.key === 'Enter') { setOrgName(e.target.value); setEditingOrg(false) } }}
                style={{ fontSize: 14, fontWeight: 600, border: '1px solid var(--blue-mid)', borderRadius: 6, padding: '3px 10px', fontFamily: 'var(--font)', color: 'var(--blue)' }}
              />
            ) : (
              <span onClick={() => setEditingOrg(true)} title="Klik om organisatienaam aan te passen"
                style={{ fontSize: 14, fontWeight: 600, color: 'var(--blue)', cursor: 'text', borderBottom: '1px dashed var(--blue-mid)', paddingBottom: 1 }}>
                {orgParam} <span style={{ fontSize: 10, opacity: 0.6 }}>✏</span>
              </span>
            )}
            <span style={{ fontSize: 13, color: 'var(--text3)' }}>·</span>
            <span style={{ fontSize: 13, color: 'var(--text3)' }}>Bronsysteem: {systems?.join(', ') || meta.systems?.join(', ') || '—'}</span>
            <span style={{ fontSize: 13, color: 'var(--text3)' }}>·</span>
            <span style={{ fontSize: 13, color: 'var(--text3)' }}>Scandatum: {scanDate}</span>
          </div>
        </div>

        {/* Rhadix Index hero */}
        <RhadixHero
          index={rapport.rhadix_index}
          availScore={avail.availability_score}
          qualScore={qual.quality_score}
          readinessScore={rs.readiness_score}
          indicators={{ ready: rs.indicators_ready, total: rs.indicators_total }}
        />

        {/* ── 1. Management Samenvatting ────────────────────────────────────── */}
        <Section nr={1} title="Management Samenvatting">
          <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '22px 26px', boxShadow: 'var(--shadow)' }}>
            {rapport.executive_summary ? (
              <p style={{ fontSize: 14, color: 'var(--text)', lineHeight: 1.75, margin: 0 }}>
                {rapport.executive_summary}
              </p>
            ) : (
              <p style={{ fontSize: 14, color: 'var(--text3)', margin: 0 }}>Geen samenvatting beschikbaar.</p>
            )}
          </div>
        </Section>

        {/* ── 2. Analyse Databeschikbaarheid ───────────────────────────────── */}
        <Section nr={2} title="Analyse Databeschikbaarheid">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            {/* Overzichtskaart */}
            <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '20px 24px', boxShadow: 'var(--shadow)' }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text2)', marginBottom: 16 }}>Beschikbaarheid totaal</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Schema\'s aangeleverd', value: `${avail.schemas_uploaded}/${avail.total_schemas}`,  color: avail.schemas_uploaded < avail.total_schemas ? 'var(--red)' : 'var(--green)' },
                  { label: 'Velden aanwezig',       value: `${avail.fields_present}/${avail.total_fields}`,    color: scoreColor(avail.availability_score) },
                  { label: 'Verplicht ontbreekt',   value: avail.required_missing,                              color: avail.required_missing > 0 ? 'var(--red)' : 'var(--green)' },
                  { label: 'Deels beschikbaar',     value: avail.fields_ambiguous,                              color: avail.fields_ambiguous > 0 ? 'var(--amber)' : 'var(--text3)' },
                ].map(s => (
                  <div key={s.label} style={{ background: 'var(--bg)', borderRadius: 'var(--radius)', padding: '12px 14px' }}>
                    <div style={{ fontSize: 22, fontWeight: 800, color: s.color }}>{s.value}</div>
                    <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 2 }}>{s.label}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Per-schema chips */}
            <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '20px 24px', boxShadow: 'var(--shadow)' }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text2)', marginBottom: 14 }}>Status per schema</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {avail.schemas.map(s => {
                  const c = scoreColor(s.availability_score)
                  return (
                    <div key={s.schema_key} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
                        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>{s.schema_label}</span>
                        {!s.file_uploaded && (
                          <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--red)', background: 'var(--red-bg)', padding: '1px 6px', borderRadius: 8 }}>Niet aangeleverd</span>
                        )}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: 80, height: 5, background: 'var(--border)', borderRadius: 3, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${Math.min(100, s.availability_score)}%`, background: c, borderRadius: 3 }} />
                        </div>
                        <span style={{ fontSize: 12, fontWeight: 700, color: c, minWidth: 34, textAlign: 'right' }}>{Math.round(s.availability_score)}%</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Verplichte ontbrekende velden */}
          {avail.required_missing > 0 && (
            <div style={{ marginTop: 12, background: 'var(--red-bg)', border: '1px solid var(--red-light)', borderRadius: 'var(--radius-xl)', padding: '14px 18px' }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--red)', marginBottom: 8 }}>
                ⚠ {avail.required_missing} verplichte velden ontbreken
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {avail.schemas.flatMap(s => s.fields || [])
                  .filter(f => f.is_required && f.status === 'ontbreekt')
                  .slice(0, 10)
                  .map((f, i) => (
                    <span key={i} style={{ fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 10, background: 'var(--red-light)', color: 'var(--red)' }}>
                      {f.field_label}
                    </span>
                  ))}
                {avail.required_missing > 10 && (
                  <span style={{ fontSize: 11, color: 'var(--text3)' }}>+ {avail.required_missing - 10} meer…</span>
                )}
              </div>
            </div>
          )}
        </Section>

        {/* ── 3. Analyse Datakwaliteit ──────────────────────────────────────── */}
        <Section nr={3} title="Analyse Datakwaliteit">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 14 }}>
            {/* Score kaart */}
            <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '20px 24px', boxShadow: 'var(--shadow)', textAlign: 'center' }}>
              <div style={{ fontSize: 52, fontWeight: 800, color: scoreColor(qual.quality_score), letterSpacing: '-0.04em', lineHeight: 1 }}>
                {Math.round(qual.quality_score)}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text3)', marginBottom: 12 }}>kwaliteitsscore</div>
              <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--red)' }}>{qual.total_errors}</div>
                  <div style={{ fontSize: 11, color: 'var(--text3)' }}>fouten</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--amber)' }}>{qual.total_warnings}</div>
                  <div style={{ fontSize: 11, color: 'var(--text3)' }}>waarschuwingen</div>
                </div>
              </div>
              <div style={{ marginTop: 12, fontSize: 12, color: scoreColor(qual.quality_score), fontWeight: 600 }}>
                Impact: {qual.quality_score < 70 ? 'Hoog — corrigeer vóór aanlevering' : qual.quality_score < 85 ? 'Gemiddeld — herstel aanbevolen' : 'Laag — voldoet grotendeels'}
              </div>
            </div>

            {/* Top issues */}
            <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '20px 24px', boxShadow: 'var(--shadow)' }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text2)', marginBottom: 14 }}>Kritieke bevindingen</div>
              {rapport.issues && rapport.issues.length > 0 ? (
                rapport.issues.slice(0, 6).map((issue, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '9px 0', borderBottom: i < Math.min(rapport.issues.length - 1, 5) ? '1px solid var(--border)' : 'none' }}>
                    <span style={{ fontSize: 13, color: issue.severity === 'error' ? 'var(--red)' : 'var(--amber)', flexShrink: 0, fontWeight: 700 }}>
                      {issue.severity === 'error' ? '✕' : '⚠'}
                    </span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
                        {issue.field_label || issue.label}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text3)' }}>
                        {issue.schema_label} · {issue.count} rijen {issue.detail ? `· ${issue.detail}` : ''}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div style={{ fontSize: 13, color: 'var(--green)', fontWeight: 600 }}>✓ Geen kritieke kwaliteitsfouten gevonden</div>
              )}
            </div>
          </div>
        </Section>

        {/* ── 4. KIK-V Readiness ───────────────────────────────────────────── */}
        <Section nr={4} title="KIK-V Readiness">
          <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '20px 24px', boxShadow: 'var(--shadow)', marginBottom: 14 }}>
            {/* Indicator-tabel */}
            <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.8fr 80px 80px 120px', padding: '8px 16px', background: 'var(--blue)', fontSize: 11, fontWeight: 700, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                <span>Indicator</span><span>Uitwisselprofiel</span><span style={{ textAlign: 'center' }}>Velden</span><span style={{ textAlign: 'center' }}>Kwaliteit</span><span style={{ textAlign: 'center' }}>Status</span>
              </div>
              {(rs.indicators || []).map((ind, idx) => {
                const nReq   = ind.required_fields?.length ?? 0
                const nAvail = ind.available_fields?.length ?? 0
                const cfg    = READINESS_CFG[ind.readiness_status] || READINESS_CFG.niet_gereed
                const rowBg  = idx % 2 === 0 ? '#fff' : 'var(--bg)'
                return (
                  <div key={ind.indicator_id} style={{
                    display: 'grid', gridTemplateColumns: '2fr 1.8fr 80px 80px 120px',
                    padding: '10px 16px', background: rowBg,
                    borderTop: '1px solid var(--border)', alignItems: 'center',
                  }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{ind.indicator_name}</div>
                    <div style={{ fontSize: 12, color: 'var(--text3)' }}>{ind.exchange_profile}</div>
                    <div style={{ textAlign: 'center', fontSize: 13, fontWeight: 700, color: nAvail < nReq ? 'var(--red)' : 'var(--green)' }}>{nAvail}/{nReq}</div>
                    <div style={{ textAlign: 'center', fontSize: 13, fontWeight: 700, color: scoreColor(ind.data_quality_score) }}>{Math.round(ind.data_quality_score)}%</div>
                    <div style={{ textAlign: 'center' }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 20, background: cfg.bg, color: cfg.color }}>
                        {cfg.icon} {cfg.label}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Blokkades samenvatting */}
            {rs.indicators && rs.indicators.some(i => i.blocking_issues?.length > 0) && (
              <div style={{ marginTop: 14, padding: '12px 16px', background: 'var(--red-bg)', borderRadius: 'var(--radius)' }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--red)', marginBottom: 6 }}>⛔ Blokkerende factoren</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {rs.indicators.flatMap(i => i.blocking_issues || []).slice(0, 8).map((b, bi) => (
                    <span key={bi} style={{ fontSize: 11, color: 'var(--red)', background: 'rgba(220,38,38,.1)', padding: '2px 8px', borderRadius: 8 }}>{b}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Section>

        {/* ── 5. Risico's ──────────────────────────────────────────────────── */}
        <Section nr={5} title="Risico's">
          {risks.length === 0 ? (
            <div style={{ background: 'var(--green-bg)', border: '1px solid var(--green-light)', borderRadius: 'var(--radius-xl)', padding: '16px 20px', fontSize: 14, color: 'var(--green)', fontWeight: 600 }}>
              ✓ Geen significante risico's geïdentificeerd — data is in goede staat.
            </div>
          ) : (
            <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', boxShadow: 'var(--shadow)', overflow: 'hidden' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '120px 2fr 90px 2fr', padding: '8px 16px', background: 'var(--blue)', fontSize: 11, fontWeight: 700, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                <span>Categorie</span><span>Risico</span><span>Impact</span><span>Mitigatie</span>
              </div>
              {risks.map((r, i) => {
                const ic = IMPACT_CFG[r.impact] || IMPACT_CFG.gemiddeld
                return (
                  <div key={i} style={{ display: 'grid', gridTemplateColumns: '120px 2fr 90px 2fr', padding: '12px 16px', background: i % 2 === 0 ? '#fff' : 'var(--bg)', borderTop: '1px solid var(--border)', alignItems: 'flex-start' }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text3)', textTransform: 'capitalize' }}>{r.type}</div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{r.risico}</div>
                    <div>
                      <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 10, color: ic.color, background: ic.color === 'var(--red)' ? 'var(--red-bg)' : ic.color === 'var(--amber)' ? 'var(--amber-bg)' : 'var(--green-bg)' }}>
                        {ic.label}
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text2)' }}>{r.mitigatie}</div>
                  </div>
                )
              })}
            </div>
          )}
        </Section>

        {/* ── 6. Actieplan ─────────────────────────────────────────────────── */}
        <Section nr={6} title="Actieplan">
          {rapport.actions && rapport.actions.length > 0 ? (
            <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', boxShadow: 'var(--shadow)', overflow: 'hidden' }}>
              {/* Statistieken */}
              <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--border)' }}>
                {[
                  { label: 'Totale uren', value: `${totalHours.toFixed(0)} uur`, color: 'var(--blue)' },
                  { label: 'Hoge prioriteit', value: highActions.length, color: 'var(--red)' },
                  { label: 'Gemiddeld', value: midActions.length, color: 'var(--amber)' },
                  { label: 'Laag', value: lowActions.length, color: 'var(--green)' },
                ].map((s, i, arr) => (
                  <div key={s.label} style={{ flex: 1, padding: '14px 18px', borderRight: i < arr.length - 1 ? '1px solid var(--border)' : 'none', textAlign: 'center' }}>
                    <div style={{ fontSize: 22, fontWeight: 800, color: s.color }}>{s.value}</div>
                    <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 2 }}>{s.label}</div>
                  </div>
                ))}
              </div>

              {/* Actietabel header */}
              <div style={{ display: 'grid', gridTemplateColumns: '90px 2.5fr 110px 70px 1fr', padding: '8px 16px', background: 'var(--bg)', fontSize: 11, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: '1px solid var(--border)' }}>
                <span>Prioriteit</span><span>Actie</span><span>Categorie</span><span style={{ textAlign: 'center' }}>Uren</span><span>Impact</span>
              </div>

              {rapport.actions.map((act, i) => {
                const pc      = PRIO_CFG[act.priority] || PRIO_CFG.gemiddeld
                const isOpen  = !!openActions[i]
                return (
                  <div key={i} style={{ borderTop: '1px solid var(--border)' }}>
                    <div
                      onClick={() => setOpenActions(s => ({ ...s, [i]: !s[i] }))}
                      style={{
                        display: 'grid', gridTemplateColumns: '90px 2.5fr 110px 70px 1fr',
                        padding: '12px 16px', alignItems: 'center',
                        background: isOpen ? 'var(--blue-light)' : i % 2 === 0 ? '#fff' : 'var(--bg)',
                        cursor: 'pointer', userSelect: 'none',
                      }}
                    >
                      <div>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 20, background: pc.bg, color: pc.color }}>
                          {pc.label}
                        </span>
                      </div>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', display: 'flex', alignItems: 'center', gap: 6 }}>
                          {act.title}
                          <span style={{ fontSize: 10, color: 'var(--text4)' }}>{isOpen ? '▲' : '▼'}</span>
                        </div>
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text3)' }}>{act.category}</div>
                      <div style={{ textAlign: 'center', fontSize: 13, fontWeight: 700, color: 'var(--blue)' }}>{act.estimated_hours}u</div>
                      <div style={{ fontSize: 12, color: 'var(--text2)' }}>
                        {act.priority === 'hoog' ? 'Vereist voor KIK-V aanlevering' : act.priority === 'gemiddeld' ? 'Aanbevolen voor kwaliteit' : 'Optionele verbetering'}
                      </div>
                    </div>

                    {/* Uitklap: stappen */}
                    {isOpen && (
                      <div style={{ padding: '12px 16px 16px', background: 'var(--blue-light)', borderTop: '1px solid var(--border)' }}>
                        <div style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 10, lineHeight: 1.5 }}>{act.description}</div>
                        {act.steps && act.steps.length > 0 && (
                          <div>
                            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Uitvoeringsstappen</div>
                            {act.steps.map((step, si) => (
                              <div key={si} style={{ display: 'flex', gap: 8, marginBottom: 5 }}>
                                <span style={{ width: 20, height: 20, borderRadius: '50%', background: 'var(--blue)', color: '#fff', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 700, flexShrink: 0 }}>{si + 1}</span>
                                <span style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.4 }}>{step}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            <div style={{ background: 'var(--green-bg)', border: '1px solid var(--green-light)', borderRadius: 'var(--radius-xl)', padding: '16px 20px', fontSize: 14, color: 'var(--green)', fontWeight: 600 }}>
              ✓ Geen acties vereist — data is conform KIK-V standaard.
            </div>
          )}
        </Section>

        {/* ── 7. Advies ────────────────────────────────────────────────────── */}
        <Section nr={7} title="Advies">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
            {/* Nu oppakken */}
            <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '20px 24px', boxShadow: 'var(--shadow)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
                <span style={{ width: 24, height: 24, borderRadius: '50%', background: 'var(--red)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 800 }}>!</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>Pak nu op</span>
              </div>
              {highActions.length > 0 ? highActions.slice(0, 4).map((a, i) => (
                <div key={i} style={{ fontSize: 13, color: 'var(--text2)', padding: '5px 0', borderBottom: i < Math.min(highActions.length - 1, 3) ? '1px solid var(--border)' : 'none', lineHeight: 1.4 }}>
                  → {a.title} <span style={{ color: 'var(--text3)', fontSize: 11 }}>({a.estimated_hours}u)</span>
                </div>
              )) : (
                <div style={{ fontSize: 13, color: 'var(--text3)' }}>Geen acties van hoge prioriteit.</div>
              )}
            </div>

            {/* Kan later */}
            <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '20px 24px', boxShadow: 'var(--shadow)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
                <span style={{ width: 24, height: 24, borderRadius: '50%', background: 'var(--amber)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 800 }}>~</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>Kan later</span>
              </div>
              {midActions.length > 0 ? midActions.slice(0, 4).map((a, i) => (
                <div key={i} style={{ fontSize: 13, color: 'var(--text2)', padding: '5px 0', borderBottom: i < Math.min(midActions.length - 1, 3) ? '1px solid var(--border)' : 'none', lineHeight: 1.4 }}>
                  → {a.title} <span style={{ color: 'var(--text3)', fontSize: 11 }}>({a.estimated_hours}u)</span>
                </div>
              )) : (
                <div style={{ fontSize: 13, color: 'var(--text3)' }}>Geen acties van gemiddelde prioriteit.</div>
              )}
            </div>
          </div>

          {/* Aanbevolen vervolgstap */}
          <div style={{ background: 'var(--blue-light)', border: '1px solid var(--blue-mid)', borderRadius: 'var(--radius-xl)', padding: '16px 20px', marginBottom: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--blue)', marginBottom: 8 }}>🚀 Aanbevolen vervolgstap</div>
            <div style={{ fontSize: 14, color: 'var(--text2)', lineHeight: 1.6 }}>
              {rs.readiness_score >= 80
                ? 'Data is grotendeels KIK-V-gereed. Verifieer de resterende kleine issues en start de KIK-V-aanlevering via uw gecertificeerde softwareleverancier.'
                : rs.readiness_score >= 50
                ? 'Los de acties van hoge prioriteit op en plan een hervalidatie in Rhadix. Stem de planning af met de KIK-V-aanleverdatum.'
                : 'Substantieel herstelwerk is vereist. Begin met verplichte velden en kritieke kwaliteitsfouten. Hervalideer na elke ronde correcties.'}
            </div>
          </div>

          {/* Strategische aanbevelingen */}
          {rapport.recommendations && rapport.recommendations.length > 0 && (
            <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '20px 24px', boxShadow: 'var(--shadow)' }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text2)', marginBottom: 14 }}>Strategische aanbevelingen</div>
              {rapport.recommendations.slice(0, 5).map((rec, i) => {
                const ic = IMPACT_CFG[rec.impact] || IMPACT_CFG.gemiddeld
                return (
                  <div key={rec.recommendation_id || i} style={{ display: 'flex', gap: 12, padding: '10px 0', borderBottom: i < Math.min(rapport.recommendations.length - 1, 4) ? '1px solid var(--border)' : 'none' }}>
                    <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 10, background: ic.color === 'var(--red)' ? 'var(--red-bg)' : ic.color === 'var(--amber)' ? 'var(--amber-bg)' : 'var(--blue-light)', color: ic.color, height: 'fit-content', whiteSpace: 'nowrap' }}>
                      {ic.label}
                    </span>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', marginBottom: 3 }}>{rec.title}</div>
                      <div style={{ fontSize: 12, color: 'var(--text2)', lineHeight: 1.5 }}>{rec.rationale}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </Section>

        {/* Footer */}
        <div style={{ textAlign: 'center', fontSize: 12, color: 'var(--text4)', paddingTop: 20, borderTop: '1px solid var(--border)' }}>
          Rhadix Gecombineerd Managementrapport · {orgParam} · gegenereerd op {new Date().toLocaleDateString('nl-NL')} · KIK-V Modelgegevensset v1.0
        </div>
      </div>
    </div>
  )
}
