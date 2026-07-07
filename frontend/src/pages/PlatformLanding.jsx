import { useState, useEffect } from 'react'
import { BANNER_HEIGHT } from '../components/EnvironmentBanner'
import { TreeDecoration, ConstellationBg } from '../components/UI'
import { currentBrand, brandLogo } from '../brand'

// Rhadix Index-teller (geanimeerd, puur visueel) — de blikvanger.
function IndexCounter() {
  const [count, setCount] = useState(0)
  useEffect(() => {
    let c = 0
    const t = setInterval(() => { c += 1; if (c > 100) c = 0; setCount(c) }, 90)
    return () => clearInterval(t)
  }, [])
  const color = count >= 85 ? '#059669' : count >= 65 ? 'var(--blue)' : count >= 50 ? 'var(--amber)' : 'var(--red)'
  return (
    <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', padding: '24px 28px',
      border: '1px solid var(--border)', boxShadow: '0 2px 12px rgba(0,0,0,.06)' }}>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase',
        color: 'var(--rhadix-sub)', marginBottom: 10 }}>Rhadix Index</div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4 }}>
        <span style={{ fontWeight: 900, fontSize: 64, lineHeight: 1, color, transition: 'color .3s ease',
          fontVariantNumeric: 'tabular-nums' }}>{String(count).padStart(2, '0')}</span>
        <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--text3)', marginBottom: 10 }}>/100</span>
      </div>
      <div style={{ marginTop: 12, height: 5, borderRadius: 3, background: 'var(--border)', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${count}%`, background: color, transition: 'width .1s linear, background .3s ease', borderRadius: 3 }} />
      </div>
    </div>
  )
}

export default function PlatformLanding({ onLogin, brand = 'rhadix', onBrandChange }) {
  const suresync = currentBrand() === 'suresync'
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', paddingTop: BANNER_HEIGHT }}>
      {/* Nav: logo + (staging) SureSync + Inloggen */}
      <header style={{ background: 'var(--blue-dark)', borderBottom: '1px solid rgba(255,255,255,.12)',
        padding: '0 32px', height: 64, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        position: 'sticky', top: 0, zIndex: 100, boxShadow: '0 2px 12px rgba(0,0,0,.35)', flexShrink: 0 }}>
        <a href="https://rhadix.nl" style={{ display: 'flex', alignItems: 'center', textDecoration: 'none' }}>
          <img src={brandLogo()} alt="logo" style={{ height: 44, width: 'auto', objectFit: 'contain' }} />
        </a>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {import.meta.env.VITE_RHADIX_ENV !== 'production' && onBrandChange && (
            <button onClick={() => onBrandChange(suresync ? 'rhadix' : 'suresync')}
              title="White-label demo (alleen staging)" style={{
                background: 'rgba(255,255,255,.1)', border: '1px solid rgba(255,255,255,.2)',
                borderRadius: 99, padding: '6px 14px', color: '#fff', fontSize: 12.5, fontWeight: 700,
                cursor: 'pointer', fontFamily: 'var(--font)' }}>{suresync ? '← Rhadix' : 'SureSync ↗'}</button>
          )}
          <button onClick={onLogin} style={{
            background: 'var(--rhadix-accent)', border: 'none', borderRadius: 'var(--radius)',
            padding: '8px 20px', color: '#fff', fontSize: 14, fontWeight: 700, cursor: 'pointer',
            fontFamily: 'var(--font)' }}>Inloggen →</button>
        </div>
      </header>

      {/* Content: hero links + Rhadix Index rechts */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'stretch' }}>
        <div style={{ flex: 1, background: 'var(--blue-hero)', position: 'relative', overflow: 'hidden',
          isolation: 'isolate', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '0 56px' }}>
          <span style={{ display: 'inline-flex', alignSelf: 'flex-start', background: 'rgba(255,255,255,.12)',
            color: 'rgba(255,255,255,.92)', fontSize: 11, fontWeight: 700, letterSpacing: '1.5px',
            padding: '6px 14px', borderRadius: 99, marginBottom: 22, textTransform: 'uppercase', position: 'relative', zIndex: 1 }}>
            De Rhadix Index
          </span>
          <h1 style={{ fontWeight: 800, fontSize: 44, color: '#fff', lineHeight: 1.15, letterSpacing: '-0.02em',
            marginBottom: 18, maxWidth: 560, position: 'relative', zIndex: 1 }}>
            Inzicht in <span style={{ color: 'var(--rhadix-accent)' }}>databeschikbaarheid</span> en datakwaliteit voor de zorg
          </h1>
          <p style={{ fontSize: 16, color: 'rgba(255,255,255,.8)', lineHeight: 1.6, maxWidth: 520,
            marginBottom: 30, position: 'relative', zIndex: 1 }}>
            De Rhadix Index maakt objectief en vergelijkbaar hoe klaar de registratiedata van een
            zorginstelling is voor uitwisseling — voor KIK-V, ZIB's en meer. Eén platform, in dienst van die index.
          </p>
          <button onClick={onLogin} style={{ alignSelf: 'flex-start', background: 'var(--rhadix-accent)',
            color: '#fff', border: 'none', borderRadius: 'var(--radius)', padding: '13px 28px', fontSize: 15,
            fontWeight: 700, cursor: 'pointer', fontFamily: 'var(--font)', position: 'relative', zIndex: 1,
            boxShadow: '0 6px 20px rgba(0,0,0,.25)' }}>Inloggen →</button>
          {suresync ? <ConstellationBg style={{ zIndex: -1 }} /> : <TreeDecoration opacity={0.1} style={{ transform: 'scale(5)', bottom: -40, right: -20 }} />}
        </div>
        <div style={{ width: 360, background: '#fff', padding: '48px 36px', display: 'flex',
          flexDirection: 'column', justifyContent: 'center', borderLeft: '1px solid var(--border)' }}>
          <IndexCounter />
        </div>
      </div>
    </div>
  )
}
