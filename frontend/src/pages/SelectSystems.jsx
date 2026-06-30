import { Nav, NavBack, Page, PageTitle } from '../components/UI'

const _taakBtn = { background:'rgba(255,255,255,.1)', border:'1px solid rgba(255,255,255,.2)', borderRadius:'var(--radius)', padding:'5px 12px', color:'#fff', fontSize:12, fontWeight:700, cursor:'pointer', fontFamily:'var(--font)', letterSpacing:'.03em' }

// ── Bronsystemen voor de samengevoegde Datavalidatie-flow ─────────────────────
// De bron bepaalt de fase-1 validatie; de benchmark (KIK-V/ZIB) volgt in fase 2.
// Reactief bijgehouden: nieuw formaat/export -> eerst analyseren + import/export
// aanpassen, dan toevoegen.
const SOURCES = [
  { id: 'afas_hrm',  systemId: 'afas_hrm',        standard: 'algemeen', label: 'AFAS Profit HRM',       vendor: 'AFAS Software', formats: 'XML / JSON', domain: 'Personeel (HR)', benchmark: 'KIK-V',        color: 'var(--blue)', bg: 'var(--blue-light)', border: 'var(--blue-mid)' },
  { id: 'ons',       systemId: 'nedap_ons',       standard: 'algemeen', label: 'Nedap/ONS',             vendor: 'Nedap',         formats: 'CSV',        domain: 'HR + klinisch', benchmark: 'KIK-V / ZIB',  color: '#0ea5e9', bg: '#e0f2fe', border: '#bae6fd' },
  { id: 'exact',     systemId: 'exact_fin',       standard: 'algemeen', label: 'Exact Financial',       vendor: 'Exact Software',formats: 'n.t.b.',     domain: 'Financieel',    benchmark: 'KIK-V',        color: '#10b981', bg: '#ecfdf5', border: '#bbf7d0' },
  { id: 'afas_fin',  systemId: 'afas_profit_fin', standard: 'algemeen', label: 'AFAS Profit Financieel',vendor: 'AFAS Software', formats: 'XML / JSON', domain: 'Financieel',    benchmark: 'KIK-V',        color: '#f59e0b', bg: '#fffbeb', border: '#fde68a' },
  { id: 'visma',     systemId: 'visma_puur',      standard: 'algemeen', label: 'Visma PUUR',            vendor: 'Visma',         formats: 'n.t.b.',     domain: 'Personeel (HR)', benchmark: 'KIK-V',       color: '#8b5cf6', bg: '#f5f3ff', border: '#ddd6fe' },
  { id: 'chipsoft',  systemId: 'chipsoft_hix',    standard: 'zib',      label: 'ChipSoft HiX',          vendor: 'ChipSoft',      formats: 'XML',        domain: 'Klinisch',      benchmark: 'ZIB',          color: '#059669', bg: '#f0fdf4', border: '#bbf7d0' },
  { id: 'epic',      systemId: 'epic',            standard: 'zib',      label: 'Epic',                  vendor: 'Epic',          formats: 'XML',        domain: 'Klinisch',      benchmark: 'ZIB',          color: '#2563eb', bg: '#eff6ff', border: '#bfdbfe' },
]

const STANDARD_SLUGS = { kikv: 'kikv-validator', zib: 'zib-validator', algemeen: 'algemeen-validator' }

export default function SelectSystems({ onNext, onBack, authUser, onTasks, onDashboard, onAdmin, onOrgAdmin, onOrgDashboard, onPlatformDashboard, onLogout }) {
  const hasAppAccess = (std) => {
    if (!authUser) return true
    const slug = STANDARD_SLUGS[std]
    if (!slug) return true
    return (authUser.assigned_app_slugs || []).includes(slug)
  }

  const choose = (src) => {
    if (!hasAppAccess(src.standard)) {
      alert('U heeft geen toegang tot deze module. Neem contact op met uw organisatiebeheerder.')
      return
    }
    onNext([src.systemId], src.standard)
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav
        right={<>
          {onTasks && <button onClick={onTasks} style={_taakBtn}>✓ Mijn taken</button>}
          <NavBack onClick={onBack} />
        </>}
        authUser={authUser}
        onLogout={onLogout}
        onDashboard={onDashboard}
        onAdmin={onAdmin}
        onOrgAdmin={onOrgAdmin}
        onOrgDashboard={onOrgDashboard}
        onPlatformDashboard={onPlatformDashboard}
      />
      <Page>
        <PageTitle
          title="Datavalidatie — kies je bron"
          sub="Kies het bronsysteem waaruit je data afkomstig is. Wij doen eerst een generieke validatie; daarna kun je benchmarken tegen KIK-V of de ZIB's."
        />

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 22 }}>
          {SOURCES.map(src => {
            const locked = !hasAppAccess(src.standard)
            return (
              <div
                key={src.id}
                onClick={() => choose(src)}
                style={{
                  background: locked ? '#f8fafc' : '#fff', borderRadius: 'var(--radius-xl)',
                  border: `2px solid ${locked ? '#e2e8f0' : 'var(--border)'}`, padding: '20px 20px',
                  cursor: locked ? 'not-allowed' : 'pointer', transition: 'all .15s', opacity: locked ? 0.7 : 1,
                  position: 'relative',
                }}
                onMouseEnter={e => { if (!locked) { e.currentTarget.style.borderColor = src.color; e.currentTarget.style.background = src.bg } }}
                onMouseLeave={e => { if (!locked) { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = '#fff' } }}
              >
                {locked && <div style={{ position: 'absolute', top: 12, right: 14, fontSize: 15, opacity: 0.5 }} title="Geen toegang">🔒</div>}
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 2, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 17, fontWeight: 800, color: locked ? 'var(--text3)' : src.color, letterSpacing: '-0.02em' }}>{src.label}</span>
                  <span style={{ fontSize: 11, color: 'var(--text4)' }}>{src.vendor}</span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text3)', marginBottom: 12 }}>{src.domain}</div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 11, fontWeight: 600, color: src.color, background: src.bg, border: `1px solid ${src.border}`, padding: '3px 9px', borderRadius: 20 }}>{src.formats}</span>
                  <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text3)', background: '#f1f5f9', border: '1px solid var(--border)', padding: '3px 9px', borderRadius: 20 }}>benchmark: {src.benchmark}</span>
                </div>
              </div>
            )
          })}
        </div>

        <div style={{ fontSize: 12, color: 'var(--text3)', lineHeight: 1.5 }}>
          Bron of formaat staat er niet bij? We voegen die toe nadat we de export hebben geanalyseerd en op het Rhadix-model hebben gematcht.
        </div>
      </Page>
    </div>
  )
}
