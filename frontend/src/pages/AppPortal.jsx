import { Nav, Page, PageTitle } from '../components/UI'
import { MijnTakenWidget } from '../components/TaskUI'

const IS_PROD = (import.meta.env.VITE_RHADIX_ENV || 'production') === 'production'
const UITVRAAG_URL    = import.meta.env.VITE_UITVRAAG_URL    || (IS_PROD ? 'https://uitvraag.rhadix.nl'    : 'https://uitvraag-staging.rhadix.nl')
const DATASTATION_URL = import.meta.env.VITE_DATASTATION_URL || (IS_PROD ? 'https://datastation.rhadix.nl' : 'https://datastation-staging.rhadix.nl')
const DATASTATION_ACTIVE = !!DATASTATION_URL
const CRM_URL = import.meta.env.VITE_CRM_URL || (IS_PROD ? 'https://crm.rhadix.nl' : 'https://crm-staging.rhadix.nl')
const CRM_ACTIVE = true  // CRM live op staging én productie

// Post-login portal: de drie applicaties als kaart-grid (zoals 'Kies een standaard').
export default function AppPortal({ onLogin, brand = 'rhadix', onBrandChange, authUser, onDashboard, onAdmin, onOrgAdmin, onLogout, onTasks, onReconciliation }) {
  const withBrand = (url) => {
    if (brand !== 'kikv' || !url) return url
    try { const u = new URL(url); u.searchParams.set('brand', 'kikv'); return u.toString() }
    catch { return url + (url.includes('?') ? '&' : '?') + 'brand=kikv' }
  }

  const APPS = [
    { id: 'dv', icon: '🏥', label: 'Rhadix Datavalidatie', laag: 'Bij de bron · Datakwaliteit',
      color: '#1F9D6B', bg: '#E8F7F0', border: '#BCEAD5', actie: 'Openen →',
      desc: 'Pre-screening: is de datahuishouding van de zorgaanbieder klaar om gevalideerde vragen te beantwoorden? Berekent de Rhadix Index.' },
    { id: 'u', icon: '📡', label: 'Rhadix Uitvraag', laag: 'Afnemerskant',
      color: 'var(--blue)', bg: 'var(--blue-light)', border: 'var(--blue-mid)', actie: 'Openen →',
      desc: 'Gevalideerde vragen uitzetten aan zorgaanbieders en de antwoorden inzien, vergelijken en analyseren.' },
    { id: 'ds', icon: '🧮', label: 'Rhadix Datastation', laag: 'Bij de bron · Rekenkracht',
      color: '#D98324', bg: '#FDF3E3', border: '#F5D9A8', actie: DATASTATION_ACTIVE ? 'Openen →' : 'Binnenkort',
      desc: 'Berekent het antwoord lokaal (SPARQL/Fuseki) bij de zorgaanbieder; de data blijft bij de bron.' },
    { id: 'crm', icon: '\u{1F91D}', label: 'Rhadix CRM', laag: 'Relatie \u00b7 Krachtenveld',
      color: '#7C3AED', bg: '#F3EEFF', border: '#DDD0FB', actie: CRM_ACTIVE ? 'Openen \u2192' : 'Binnenkort',
      desc: 'Stakeholder- en relatiebeheer rond RSO\u2019s en zorgaanbieders, met krachtenveld-analyse (invloed \u00d7 betrokkenheid).' },
    { id: 'recon', icon: '🔁', label: 'Reconciliation Engine', laag: 'Bij de bron \u00b7 Vergelijking',
      color: '#0E7490', bg: '#ECFEFF', border: '#A5F3FC', actie: 'Openen \u2192',
      desc: 'Vergelijk verwachte indicatorwaarden uit brondata met actuele SPARQL-uitkomsten en analyseer afwijkingen op recordniveau.' },
  ]

  const open = (id) => {
    if (id === 'dv') onLogin()
    else if (id === 'u') window.location.href = withBrand(UITVRAAG_URL)
    else if (id === 'ds' && DATASTATION_ACTIVE) window.location.href = withBrand(DATASTATION_URL)
    else if (id === 'crm' && CRM_ACTIVE) window.location.href = withBrand(CRM_URL)
    else if (id === 'recon' && onReconciliation) onReconciliation()
  }

  const sureSyncToggle = null

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav authUser={authUser} onDashboard={onDashboard} onAdmin={onAdmin} onOrgAdmin={onOrgAdmin}
           onLogout={onLogout} right={sureSyncToggle} />
      <Page>
        <PageTitle title="Kies een applicatie" sub="De Rhadix-applicaties binnen het platform — in dienst van de Rhadix Index." />
        {authUser && onTasks && (
          <div style={{ marginBottom: 20 }}><MijnTakenWidget onOpen={onTasks} /></div>
        )}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16, marginBottom: 32 }}>
          {APPS.map(a => {
            const locked = (a.id === 'ds' && !DATASTATION_ACTIVE) || (a.id === 'crm' && !CRM_ACTIVE)
            return (
              <div key={a.id} onClick={() => !locked && open(a.id)}
                style={{ background: locked ? '#f8fafc' : '#fff', borderRadius: 'var(--radius-xl)',
                  border: `2px solid ${locked ? '#e2e8f0' : 'var(--border)'}`, padding: '28px 24px',
                  cursor: locked ? 'not-allowed' : 'pointer', transition: 'all .15s', opacity: locked ? 0.75 : 1 }}
                onMouseEnter={e => { if (!locked) { e.currentTarget.style.borderColor = a.color; e.currentTarget.style.background = a.bg } }}
                onMouseLeave={e => { if (!locked) { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = '#fff' } }}>
                <div style={{ fontSize: 34, marginBottom: 12 }}>{a.icon}</div>
                <div style={{ fontSize: 11, fontWeight: 700, color: a.color, letterSpacing: '.4px', textTransform: 'uppercase', marginBottom: 4 }}>{a.laag}</div>
                <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em', marginBottom: 10 }}>{a.label}</div>
                <div style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.5, marginBottom: 16 }}>{a.desc}</div>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12.5, fontWeight: 700,
                  color: locked ? 'var(--text3)' : a.color, background: locked ? '#eef1f5' : a.bg,
                  border: `1px solid ${locked ? '#e2e8f0' : a.border}`, padding: '6px 14px', borderRadius: 20 }}>
                  {a.actie}
                </div>
              </div>
            )
          })}
        </div>
      </Page>
    </div>
  )
}
