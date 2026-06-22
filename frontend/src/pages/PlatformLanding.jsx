import { BANNER_HEIGHT } from '../components/EnvironmentBanner'
import { TreeDecoration, ConstellationBg } from '../components/UI'
import { currentBrand, brandLogo } from '../brand'

// Platform-entree: Rhadix-Index-hero met één Inloggen-knop. Daarna volgt het
// loginscherm en de applicatie-portal. Brand-bewust (Rhadix navy / SureSync violet).
export default function PlatformLanding({ onLogin, brand = 'rhadix', onBrandChange }) {
  const suresync = currentBrand() === 'suresync'
  const loginBtn = {
    background: 'var(--rhadix-accent)', color: '#fff', border: 'none',
    borderRadius: 'var(--radius)', padding: '13px 26px', fontSize: 15, fontWeight: 700,
    fontFamily: 'var(--font)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 8,
    boxShadow: '0 6px 20px rgba(0,0,0,.25)',
  }
  return (
    <div style={{
      minHeight: '100vh', background: 'var(--blue-hero)', position: 'relative',
      overflow: 'hidden', isolation: 'isolate', display: 'flex', flexDirection: 'column',
      paddingTop: BANNER_HEIGHT,
    }}>
      {/* Topbar: logo + (staging) SureSync-knop + Inloggen */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '28px 48px 0', position: 'relative', zIndex: 1 }}>
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

      {/* Hero */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center',
        padding: '0 48px 80px', maxWidth: 760, position: 'relative', zIndex: 1 }}>
        <span style={{ display: 'inline-flex', alignSelf: 'flex-start', background: 'rgba(255,255,255,.12)',
          color: 'rgba(255,255,255,.92)', fontSize: 11, fontWeight: 700, letterSpacing: '1.5px',
          padding: '6px 14px', borderRadius: 99, marginBottom: 26, textTransform: 'uppercase' }}>
          Nieuw — de Rhadix Index
        </span>
        <h1 style={{ fontFamily: 'var(--font)', fontWeight: 800, fontSize: 46, color: '#fff',
          lineHeight: 1.15, letterSpacing: '-0.02em', marginBottom: 20, maxWidth: 620 }}>
          Een nieuwe standaard voor{' '}
          <span style={{ color: 'var(--rhadix-accent)' }}>databeschikbaarheid</span> en datakwaliteit
        </h1>
        <p style={{ fontSize: 17, color: 'rgba(255,255,255,.8)', lineHeight: 1.6, maxWidth: 560, marginBottom: 32 }}>
          De Rhadix Index geeft zorginstellingen inzicht in de kwaliteit en beschikbaarheid van hun
          registratiedata — voor KIK-V, ZIB's en meer. Geautomatiseerd, objectief en vergelijkbaar.
        </p>
        <button onClick={onLogin} style={loginBtn}>Inloggen →</button>
      </div>

      {suresync ? <ConstellationBg style={{ zIndex: -1 }} /> : <TreeDecoration opacity={0.1} style={{ transform: 'scale(5)', bottom: -40, right: -20 }} />}
    </div>
  )
}
