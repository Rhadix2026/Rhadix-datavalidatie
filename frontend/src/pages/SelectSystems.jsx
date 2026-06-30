import { Nav, NavBack, Page, PageTitle } from '../components/UI'

// ── Bronnen voor de samengevoegde Datavalidatie-flow ──────────────────────────
// Elke bron bepaalt de fase-1 standaard (geen verkeerde-route-keuze meer).
// systemId koppelt aan de source-parameter in Upload (SYSTEM_TO_SOURCE).
const SOURCES = [
  { id: 'afas',     systemId: 'afas_hrm',     standard: 'algemeen', label: 'AFAS Profit', vendor: 'AFAS Software',
    formats: 'XML / JSON', domain: 'Personeel (HR)', icon: '🏢', color: 'var(--blue)', bg: 'var(--blue-light)', border: 'var(--blue-mid)' },
  { id: 'ons',      systemId: 'nedap_ons',     standard: 'algemeen', label: 'Nedap ONS', vendor: 'Nedap',
    formats: 'CSV', domain: 'Personeel (HR)', icon: '📊', color: '#0ea5e9', bg: '#e0f2fe', border: '#bae6fd' },
  { id: 'kikv_csv', systemId: 'kikv_csv',      standard: 'kikv',     label: 'KIK-V CSV', vendor: 'KIK-V-format',
    formats: 'CSV', domain: 'Personeel (HR)', icon: '🏥', color: '#2563eb', bg: '#eff6ff', border: '#bfdbfe' },
  { id: 'epd_ecd',  systemId: 'chipsoft_hix',  standard: 'zib',      label: 'EPD / ECD', vendor: 'ChipSoft · Epic · …',
    formats: 'XML', domain: 'Klinisch (ZIB)', icon: '💊', color: '#059669', bg: '#f0fdf4', border: '#bbf7d0' },
]

// Slug per standard — moet matchen met de in de DB geseede app-slugs
const STANDARD_SLUGS = { kikv: 'kikv-validator', zib: 'zib-validator', algemeen: 'algemeen-validator' }

export default function SelectSystems({ onNext, onBack, authUser }) {
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
    // Door naar upload; de bron bepaalt de fase-1 standaard
    onNext([src.systemId], src.standard)
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={<NavBack onClick={onBack} />} />
      <Page>
        <PageTitle
          title="Datavalidatie — kies je bron"
          sub="Upload je export en geef de bron op. Wij herkennen het formaat en doen eerst een generieke validatie; daarna kun je benchmarken tegen KIK-V of de ZIB's."
        />

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
          {SOURCES.map(src => {
            const locked = !hasAppAccess(src.standard)
            return (
              <div
                key={src.id}
                onClick={() => choose(src)}
                style={{
                  background: locked ? '#f8fafc' : '#fff', borderRadius: 'var(--radius-xl)',
                  border: `2px solid ${locked ? '#e2e8f0' : 'var(--border)'}`, padding: '24px 22px',
                  cursor: locked ? 'not-allowed' : 'pointer', transition: 'all .15s', opacity: locked ? 0.7 : 1,
                  position: 'relative',
                }}
                onMouseEnter={e => { if (!locked) { e.currentTarget.style.borderColor = src.color; e.currentTarget.style.background = src.bg } }}
                onMouseLeave={e => { if (!locked) { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = '#fff' } }}
              >
                {locked && <div style={{ position: 'absolute', top: 14, right: 16, fontSize: 16, opacity: 0.5 }} title="Geen toegang">🔒</div>}
                <div style={{ fontSize: 32, marginBottom: 10 }}>{src.icon}</div>
                <div style={{ fontSize: 19, fontWeight: 800, color: locked ? 'var(--text3)' : src.color, letterSpacing: '-0.02em', marginBottom: 2 }}>{src.label}</div>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text3)', marginBottom: 12 }}>{src.vendor}</div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: src.color, background: src.bg, border: `1px solid ${src.border}`, padding: '4px 10px', borderRadius: 20 }}>{src.formats}</span>
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text3)', background: 'var(--bg2, #f1f5f9)', border: '1px solid var(--border)', padding: '4px 10px', borderRadius: 20 }}>{src.domain}</span>
                </div>
              </div>
            )
          })}
        </div>

        <div style={{ fontSize: 13, color: 'var(--text3)', lineHeight: 1.5 }}>
          Staat je bron er niet bij? De benchmark tegen KIK-V en de ZIB's komt na de eerste validatie beschikbaar, afhankelijk van de bron.
        </div>
      </Page>
    </div>
  )
}
