import { BANNER_HEIGHT } from '../components/EnvironmentBanner'
import { TreeDecoration, ConstellationBg } from '../components/UI'
import { currentBrand, brandLogo } from '../brand'

// Platform-entree: de Rhadix Index als kern (claim to fame); de drie applicaties
// staan daar in dienst van. Eén Inloggen-knop leidt naar het loginscherm.
const APPS = [
  { mark: 'DV', accent: '#27AE7A', naam: 'Datavalidatie', desc: 'Is de datahuishouding klaar voor uitwisseling? De readiness-scan die de Rhadix Index berekent.' },
  { mark: 'U',  accent: 'var(--rhadix-accent)', naam: 'Uitvraag', desc: 'Gevalideerde vragen uitzetten aan zorgaanbieders en de antwoorden inzien en vergelijken.' },
  { mark: 'DS', accent: '#E0902A', naam: 'Datastation', desc: 'Berekent het antwoord lokaal bij de bron (SPARQL/Fuseki); de data blijft bij de zorgaanbieder.' },
]

export default function PlatformLanding({ onLogin, brand = 'rhadix', onBrandChange }) {
  const suresync = currentBrand() === 'suresync'
  const loginBtn = {
    background: 'var(--rhadix-accent)', color: '#fff', border: 'none',
    borderRadius: 'var(--radius)', padding: '13px 28px', fontSize: 15, fontWeight: 700,
    fontFamily: 'var(--font)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 8,
    boxShadow: '0 6px 20px rgba(0,0,0,.25)',
  }
  return (
    <div style={{ minHeight: '100vh', background: 'var(--blue-hero)', position: 'relative',
      overflow: 'hidden', isolation: 'isolate', display: 'flex', flexDirection: 'column', paddingTop: BANNER_HEIGHT }}>

      {/* Topbar: logo + (staging) SureSync + Inloggen */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '24px 48px 0', position: 'relative', zIndex: 1 }}>
        <a href="https://rhadix.nl" style={{ display: 'inline-block', textDecoration: 'none' }} title="Naar rhadix.nl">
          <img src={brandLogo()} alt="logo" style={{ height: 44, width: 'auto', objectFit: 'contain' }} />
        </a>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {import.meta.env.VITE_RHADIX_ENV !== 'production' && onBrandChange && (
            <button onClick={() => onBrandChange(suresync ? 'rhadix' : 'suresync')}
              title="White-label demo (alleen staging)" style={{
                background: 'rgba(255,255,255,.12)', border: '1px solid rgba(255,255,255,.35)',
                borderRadius: 99, padding: '6px 14px', color: '#fff', fontSize: 12.5, fontWeight: 700,
                cursor: 'pointer', fontFamily: 'var(--font)',
              }}>{suresync ? '← Rhadix' : 'SureSync ↗'}</button>
          )}
          <button onClick={onLogin} style={{
            background: 'rgba(255,255,255,.12)', border: '1px solid rgba(255,255,255,.4)',
            borderRadius: 'var(--radius)', padding: '8px 18px', color: '#fff', fontSize: 14,
            fontWeight: 700, cursor: 'pointer', fontFamily: 'var(--font)',
          }}>Inloggen →</button>
        </div>
      </div>

      {/* Hero — de Rhadix Index */}
      <div style={{ padding: '56px 48px 24px', maxWidth: 820, position: 'relative', zIndex: 1 }}>
        <span style={{ display: 'inline-flex', alignSelf: 'flex-start', background: 'rgba(255,255,255,.12)',
          color: 'rgba(255,255,255,.92)', fontSize: 11, fontWeight: 700, letterSpacing: '1.5px',
          padding: '6px 14px', borderRadius: 99, marginBottom: 22, textTransform: 'uppercase' }}>
          De Rhadix Index
        </span>
        <h1 style={{ fontFamily: 'var(--font)', fontWeight: 800, fontSize: 46, color: '#fff',
          lineHeight: 1.14, letterSpacing: '-0.02em', marginBottom: 18, maxWidth: 680 }}>
          Eén objectieve maat voor{' '}
          <span style={{ color: 'var(--rhadix-accent)' }}>databeschikbaarheid</span> en datakwaliteit in de zorg
        </h1>
        <p style={{ fontSize: 17, color: 'rgba(255,255,255,.8)', lineHeight: 1.6, maxWidth: 600, marginBottom: 28 }}>
          De Rhadix Index geeft zorginstellingen inzicht in hoe klaar hun registratiedata is voor uitwisseling —
          voor KIK-V, ZIB's en meer. Geautomatiseerd, objectief en vergelijkbaar. De applicaties hieronder staan
          daar in dienst van.
        </p>
        <button onClick={onLogin} style={loginBtn}>Inloggen →</button>
      </div>

      {/* Applicaties — in dienst van de Rhadix Index */}
      <div style={{ padding: '8px 48px 56px', position: 'relative', zIndex: 1 }}>
        <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase',
          color: 'rgba(255,255,255,.55)', marginBottom: 14 }}>In dienst van de index</div>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          {APPS.map(a => (
            <button key={a.mark} onClick={onLogin} style={{
              flex: '1 1 240px', minWidth: 240, textAlign: 'left', cursor: 'pointer',
              background: 'rgba(255,255,255,.06)', border: '1px solid rgba(255,255,255,.14)',
              borderRadius: 'var(--radius-lg)', padding: '18px 20px', fontFamily: 'var(--font)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                <span style={{ width: 34, height: 34, borderRadius: 9, background: a.accent, color: '#fff',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 800 }}>{a.mark}</span>
                <span style={{ fontSize: 16, fontWeight: 700, color: '#fff' }}>Rhadix {a.naam}</span>
              </div>
              <p style={{ fontSize: 13, color: 'rgba(255,255,255,.7)', lineHeight: 1.5, margin: 0 }}>{a.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {suresync ? <ConstellationBg style={{ zIndex: -1 }} /> : <TreeDecoration opacity={0.08} style={{ transform: 'scale(5)', bottom: -60, right: -30 }} />}
    </div>
  )
}
