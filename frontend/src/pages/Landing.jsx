import { useState, useEffect } from 'react'
import { brandLogo } from '../brand'
import { TreeDecoration } from '../components/UI'

function AnimatedCounter() {
  const [count, setCount] = useState(0)

  useEffect(() => {
    let current = 0
    const interval = setInterval(() => {
      current += 1
      if (current > 100) current = 0
      setCount(current)
    }, 100)
    return () => clearInterval(interval)
  }, [])

  const color = count >= 85 ? '#059669' : count >= 65 ? 'var(--blue)' : count >= 50 ? 'var(--amber)' : 'var(--red)'

  return (
    <div style={{
      background: '#fff', borderRadius: 'var(--radius-xl)',
      padding: '20px 24px', marginBottom: 28,
      border: '1px solid var(--border)',
      boxShadow: '0 2px 12px rgba(0,0,0,.06)',
    }}>
      <div style={{
        fontSize: 10, fontWeight: 700, letterSpacing: '0.12em',
        textTransform: 'uppercase', color: 'var(--rhadix-sub)',
        fontFamily: 'var(--font-brand)', marginBottom: 10,
      }}>
        Rhadix Index
      </div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4 }}>
        <span style={{
          fontFamily: 'var(--font)', fontWeight: 900,
          fontSize: 56, lineHeight: 1, color,
          transition: 'color 0.3s ease',
          fontVariantNumeric: 'tabular-nums',
        }}>{String(count).padStart(2, '0')}</span>
        <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--text3)', marginBottom: 8 }}>/100</span>
      </div>
      <div style={{
        marginTop: 10, height: 4, borderRadius: 2,
        background: 'var(--border)', overflow: 'hidden',
      }}>
        <div style={{
          height: '100%', width: `${count}%`,
          background: color,
          transition: 'width 0.1s linear, background 0.3s ease',
          borderRadius: 2,
        }} />
      </div>
    </div>
  )
}

export default function Landing({ onStart, onProfiles, onReconciliation,
                                  onAdmin, onOrgAdmin,
                                  onDashboard, onOrgDashboard, onPlatformDashboard,
                                  authUser, onLogout }) {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Banner nav met logo — zichtbaar over de volle breedte */}
      <header style={{
        background: 'var(--blue-dark)', borderBottom: '1px solid rgba(255,255,255,.12)',
        padding: '0 32px', height: 64, display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        position: 'sticky', top: 0, zIndex: 100,
        boxShadow: '0 2px 12px rgba(0,0,0,.35)',
        flexShrink: 0,
      }}>
        <a href="https://rhadix.nl" style={{ display: 'flex', alignItems: 'center', textDecoration: 'none' }}>
          <img src={brandLogo()} alt="logo" style={{ height: 44, width: 'auto', objectFit: 'contain' }} />
        </a>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {authUser && onDashboard && (
            <button onClick={onDashboard} style={{
              background: 'rgba(255,255,255,.1)', border: '1px solid rgba(255,255,255,.2)',
              borderRadius: 'var(--radius)', padding: '6px 14px',
              color: '#fff', fontSize: 13, cursor: 'pointer', fontFamily: 'var(--font)',
            }}>Dashboard</button>
          )}
          {authUser?.role === 'RHADIX_ADMIN' && onAdmin && (
            <button onClick={onAdmin} style={{
              background: 'rgba(255,255,255,.1)', border: '1px solid rgba(255,255,255,.2)',
              borderRadius: 'var(--radius)', padding: '6px 14px',
              color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer', fontFamily: 'var(--font)',
            }}>Beheer</button>
          )}
          {authUser?.role === 'ORG_ADMIN' && onOrgAdmin && (
            <button onClick={onOrgAdmin} style={{
              background: 'rgba(255,255,255,.1)', border: '1px solid rgba(255,255,255,.2)',
              borderRadius: 'var(--radius)', padding: '6px 14px',
              color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer', fontFamily: 'var(--font)',
            }}>Beheer</button>
          )}
          {onLogout && (
            <button onClick={onLogout} style={{
              background: 'transparent', border: '1px solid rgba(255,255,255,.15)',
              borderRadius: 'var(--radius)', padding: '6px 14px',
              color: 'rgba(255,255,255,.7)', fontSize: 13, cursor: 'pointer', fontFamily: 'var(--font)',
            }}>← Terug</button>
          )}
        </div>
      </header>

      <div style={{ flex: 1, display: 'flex', alignItems: 'stretch' }}>
        {/* Left hero */}
        <div style={{
          flex: 1, background: 'var(--blue-hero)',
          padding: '72px 64px', display: 'flex',
          flexDirection: 'column', justifyContent: 'center',
          position: 'relative', overflow: 'hidden',
        }}>
          <TreeDecoration />
          {/* Logo placeholder verwijderd — logo staat in de header */}

          <div style={{
            display: 'inline-flex', background: 'rgba(111,168,208,.25)',
            color: 'var(--rhadix-accent)', fontSize: 12, fontWeight: 600,
            padding: '6px 14px', borderRadius: 20, marginBottom: 24,
            alignSelf: 'flex-start', border: '1px solid rgba(111,168,208,.3)',
          }}>
            De readiness scan voor zorgdata
          </div>

          <h1 style={{
            fontFamily: 'var(--font)',
            fontSize: 38, fontWeight: 800, color: '#fff',
            lineHeight: 1.2, letterSpacing: '-0.02em', marginBottom: 20, maxWidth: 480,
          }}>
            Inzicht in data-gereedheid voor zorginstellingen
          </h1>

          <p style={{ fontSize: 15, color: 'rgba(168,197,224,.85)', lineHeight: 1.65, marginBottom: 40, maxWidth: 460 }}>
            Analyseer de gereedheid van uw zorgdata voor uitwisseling via moderne standaarden. Van mapping tot implementatie in weken in plaats van maanden.
          </p>

          <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
            <button onClick={onStart} style={{
              background: 'var(--rhadix-accent)', color: '#fff',
              border: 'none', borderRadius: 'var(--radius)', padding: '13px 28px',
              fontSize: 15, fontWeight: 700, cursor: 'pointer', fontFamily: 'var(--font)',
              display: 'flex', alignItems: 'center', gap: 8,
              boxShadow: '0 4px 16px rgba(111,168,208,.35)',
            }}>
              Start nieuwe scan →
            </button>
            {onReconciliation && (
              <button onClick={onReconciliation} style={{
                background: 'transparent', color: 'rgba(168,197,224,.9)',
                border: '1.5px solid rgba(168,197,224,.4)', borderRadius: 'var(--radius)',
                padding: '13px 28px', fontSize: 15, fontWeight: 600,
                cursor: 'pointer', fontFamily: 'var(--font)',
                display: 'flex', alignItems: 'center', gap: 8,
              }}>
                🔁 Reconciliation Engine
              </button>
            )}
          </div>
        </div>

        {/* Right: Index + Hoe het werkt */}
        <div style={{
          width: 340, background: '#fff', padding: '48px 36px',
          display: 'flex', flexDirection: 'column', justifyContent: 'center',
          borderLeft: '1px solid var(--border)',
        }}>
          <AnimatedCounter />

          <div style={{
            fontSize: 10, fontWeight: 700, letterSpacing: '0.12em',
            textTransform: 'uppercase', color: 'var(--rhadix-sub)', marginBottom: 20,
            fontFamily: 'var(--font-brand)',
          }}>
            Hoe het werkt
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            {[
              { step: '1', icon: '🗂️', label: 'Kies gegevensstandaard & bronsysteem' },
              { step: '2', icon: '⬆️', label: 'Upload uw brondata' },
              { step: '3', icon: '📊', label: 'Bekijk beschikbaarheidsrapport' },
              { step: '4', icon: '💡', label: 'Ontvang advies & actiepunten' },
            ].map((s, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                <div style={{
                  width: 34, height: 34, borderRadius: '50%', flexShrink: 0,
                  background: 'var(--blue-light)', border: '1.5px solid var(--blue-mid)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 16,
                }}>{s.icon}</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--blue)', letterSpacing: '0.04em' }}>Stap {s.step}</span>
                  <span style={{ fontSize: 13, color: 'var(--text2)', fontWeight: 500, lineHeight: 1.35 }}>{s.label}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
