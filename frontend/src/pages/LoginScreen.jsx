import { useState } from 'react'
import { BANNER_HEIGHT } from '../components/EnvironmentBanner'
import { TreeDecoration, ConstellationBg } from '../components/UI'
import { currentBrand } from '../brand'

export default function LoginScreen({ onLogin, onBack }) {
  const [email,      setEmail]      = useState('')
  const [password,   setPassword]   = useState('')
  const [loading,    setLoading]    = useState(false)
  const [error,      setError]      = useState('')
  const [showForgot, setShowForgot] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await onLogin(email.trim(), password)
    } catch (err) {
      let msg = 'Inloggen mislukt'
      try {
        const parsed = JSON.parse(err.message)
        msg = parsed?.detail || msg
      } catch {}
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    padding: '10px 14px', borderRadius: 'var(--radius)',
    border: '1.5px solid var(--border)', fontSize: 14,
    fontFamily: 'var(--font)', outline: 'none',
    transition: 'border-color .15s', background: '#fff',
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'stretch',
      background: 'var(--bg)',
      paddingTop: BANNER_HEIGHT,   /* ruimte voor staging/dev banner */
    }}>

      {/* ── Left — branding ─────────────────────────────────────────────── */}
      <div style={{
        flex: 1, background: 'var(--blue-hero)',
        display: 'flex', flexDirection: 'column',
        position: 'relative', overflow: 'hidden', isolation: 'isolate',
      }}>

        {/* Logo linksboven — klikbaar, terug naar rhadix.nl */}
        <div style={{ padding: '32px 48px 0', flexShrink: 0 }}>
          <a
            href="https://rhadix.nl"
            style={{ display: 'inline-block', textDecoration: 'none' }}
            title="Terug naar rhadix.nl"
          >
            <img src="/rhadix-logo.jpg" alt="Rhadix" style={{ height: 44, width: 'auto', objectFit: 'contain' }} />
          </a>
        </div>

        {/* Tekst — verticaal gecentreerd in resterende ruimte */}
        <div style={{
          flex: 1, display: 'flex', flexDirection: 'column',
          justifyContent: 'center', padding: '0 48px 100px',
        }}>
          <span style={{
            display: 'inline-flex', alignSelf: 'flex-start',
            background: 'rgba(111,168,208,.25)', color: 'rgba(168,197,224,.95)',
            fontSize: 11, fontWeight: 700, letterSpacing: '1.5px',
            padding: '5px 12px', borderRadius: 99, marginBottom: 24,
            textTransform: 'uppercase',
          }}>
            NIEUW — DE RHADIX INDEX
          </span>

          <h1 style={{
            fontFamily: 'var(--font)', fontWeight: 800, fontSize: 36,
            color: '#fff', lineHeight: 1.2, letterSpacing: '-0.02em',
            marginBottom: 18, maxWidth: 440,
          }}>
            Een nieuwe standaard voor{' '}
            <span style={{ color: '#6fa8d0' }}>databeschikbaarheid</span>{' '}
            en datakwaliteit
          </h1>
          <p style={{ fontSize: 15, color: 'rgba(168,197,224,.8)', lineHeight: 1.65, maxWidth: 400 }}>
            Analyseer de gereedheid van uw zorgdata voor uitwisseling via moderne standaarden.
          </p>
        </div>

        {/* Decoratie rechtonder (constellatie bij SureSync, anders boom) */}
        {currentBrand() === 'suresync'
          ? <ConstellationBg style={{ zIndex: -1 }} />
          : <TreeDecoration />}
      </div>

      {/* ── Right — login form ────────────────────────────────────────────── */}
      <div style={{
        width: 440, background: '#fff',
        display: 'flex', flexDirection: 'column',
        justifyContent: 'center', padding: '56px 48px',
        borderLeft: '1px solid var(--border)',
      }}>
        <div style={{ marginBottom: 36 }}>
          {onBack && (
            <button type="button" onClick={onBack} style={{
              background: 'none', border: 'none', padding: 0, marginBottom: 14, cursor: 'pointer',
              color: 'var(--text3)', fontSize: 13, fontFamily: 'var(--font)',
            }}>← Terug naar appkeuze</button>
          )}
          <h2 style={{ fontSize: 24, fontWeight: 800, color: 'var(--text)', marginBottom: 6 }}>Inloggen bij Rhadix Datavalidatie</h2>
          <p style={{ fontSize: 14, color: 'var(--text3)' }}>Voer uw e-mailadres en wachtwoord in.</p>
        </div>

        {/* ── Demo-inloggegevens (alleen buiten productie) ── */}
        {(import.meta.env.VITE_RHADIX_ENV || 'production') !== 'production' && (
        <div style={{
          background: '#f0fdf4', border: '1px solid #bbf7d0',
          borderRadius: 'var(--radius)', padding: '12px 14px',
          marginBottom: 20, fontSize: 13,
        }}>
          <div style={{ fontWeight: 700, color: '#15803d', marginBottom: 6 }}>
            🎯 Demo toegang
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, color: '#166534' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>E-mail: <code style={{ fontFamily: 'monospace', fontWeight: 600 }}>demo1@rhadix.nl</code></span>
              <button type="button" onClick={() => { setEmail('demo1@rhadix.nl'); setPassword('Demogebruiker1!') }} style={{
                fontSize: 11, background: '#15803d', color: '#fff', border: 'none',
                borderRadius: 4, padding: '3px 8px', cursor: 'pointer', fontFamily: 'var(--font)', fontWeight: 600,
              }}>Invullen</button>
            </div>
            <div>Wachtwoord: <code style={{ fontFamily: 'monospace', fontWeight: 600 }}>Demogebruiker1!</code></div>
          </div>
        </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text2)' }}>E-mailadres</span>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoFocus
              placeholder="naam@organisatie.nl"
              style={inputStyle}
              onFocus={e => e.target.style.borderColor = 'var(--blue)'}
              onBlur={e  => e.target.style.borderColor = 'var(--border)'}
            />
          </label>

          <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text2)' }}>Wachtwoord</span>
              <button
                type="button"
                onClick={() => setShowForgot(v => !v)}
                style={{
                  fontSize: 12, color: 'var(--blue)', background: 'none',
                  border: 'none', cursor: 'pointer', padding: 0, fontFamily: 'var(--font)',
                  textDecoration: showForgot ? 'none' : 'underline',
                }}
              >
                Wachtwoord vergeten?
              </button>
            </div>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              placeholder="••••••••••••"
              style={inputStyle}
              onFocus={e => e.target.style.borderColor = 'var(--blue)'}
              onBlur={e  => e.target.style.borderColor = 'var(--border)'}
            />
          </label>

          {showForgot && (
            <div style={{
              padding: '12px 14px', background: '#eff6ff',
              border: '1px solid #bfdbfe', borderRadius: 'var(--radius)',
              fontSize: 13, color: '#1d4ed8', lineHeight: 1.55,
            }}>
              <strong>Wachtwoord vergeten?</strong><br />
              Neem contact op met de beheerder van uw organisatie. Uw beheerder kan via het beheerpaneel een nieuw wachtwoord voor u instellen.
            </div>
          )}

          {error && (
            <div style={{
              padding: '10px 14px', background: '#fef2f2',
              border: '1px solid #fecaca', borderRadius: 'var(--radius)',
              fontSize: 13, color: '#dc2626',
            }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: 4,
              padding: '12px 0', borderRadius: 'var(--radius)',
              background: loading ? 'var(--text3)' : 'var(--blue)',
              color: '#fff', border: 'none', cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: 15, fontWeight: 700, fontFamily: 'var(--font)',
              transition: 'background .15s',
            }}
          >
            {loading ? 'Bezig met inloggen…' : 'Inloggen →'}
          </button>
        </form>

        <p style={{ marginTop: 32, fontSize: 12, color: 'var(--text3)', textAlign: 'center', lineHeight: 1.6 }}>
          Geen account? Neem contact op met uw Rhadix-beheerder.
        </p>

        <p style={{ marginTop: 12, fontSize: 11, color: 'var(--text3)', textAlign: 'center' }}>
          <a href="https://rhadix.nl" style={{ color: 'var(--text3)', textDecoration: 'underline' }}>
            ← Terug naar rhadix.nl
          </a>
        </p>
      </div>
    </div>
  )
}
