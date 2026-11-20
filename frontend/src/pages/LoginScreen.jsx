import { useState } from 'react'
import { BANNER_HEIGHT } from '../components/EnvironmentBanner'
import { TreeDecoration, ConstellationBg } from '../components/UI'
import { currentBrand, brandLogo } from '../brand'
import { forgotPassword } from '../services/api'

// `merk` (optioneel): merkvariant voor een rechtstreekse ingang (lib/directeToegang.js, MERKEN).
// Alleen opmaak: eigen logo, kleuren en lettertype; formulier en authenticatie blijven gelijk.
export default function LoginScreen({ onLogin, onBack, brand = 'rhadix', onBrandChange, appNaam = 'Rhadix Datavalidatie', merk = null }) {
  const [email,      setEmail]      = useState('')
  const [password,   setPassword]   = useState('')
  const [loading,    setLoading]    = useState(false)
  const [error,      setError]      = useState('')
  const [showForgot, setShowForgot] = useState(false)
  const [forgotEmail, setForgotEmail] = useState('')
  const [forgotSent,  setForgotSent]  = useState(false)
  const [forgotBusy,  setForgotBusy]  = useState(false)

  async function submitForgot(e) {
    e.preventDefault()
    setForgotBusy(true)
    try { await forgotPassword((forgotEmail || email).trim()) } catch { /* geen enumeratie tonen */ }
    finally { setForgotBusy(false); setForgotSent(true) }
  }

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

  // Merkvariant: de bestaande CSS-variabelen alleen binnen dit scherm overschrijven.
  const merkStijl = merk ? {
    '--blue': merk.donker, '--text': merk.donker, '--text2': merk.donker, '--text3': '#5B6773',
    '--border': '#C9C6B6', '--radius': '4px', '--font': "'Inter', -apple-system, 'Segoe UI', sans-serif",
    fontFamily: "'Inter', -apple-system, 'Segoe UI', sans-serif", background: merk.donker,
  } : {}

  return (
    <div className={merk ? 'merk-login' : undefined} style={{
      minHeight: '100vh', display: 'flex', alignItems: 'stretch',
      background: 'var(--bg)',
      paddingTop: BANNER_HEIGHT,   /* ruimte voor staging/dev banner */
      ...merkStijl,
    }}>
      {merk && <MerkStijlen merk={merk} />}

      {/* ── Left — branding (merkvariant: logo van het kantoor) ─────────── */}
      {merk ? <MerkPaneel merk={merk} /> : (
      <div style={{
        flex: 1, background: 'var(--blue-hero)',
        display: 'flex', flexDirection: 'column',
        position: 'relative', overflow: 'hidden', isolation: 'isolate',
      }}>

        {/* Logo linksboven + (op staging) SureSync white-label-knop */}
        <div style={{ padding: '32px 48px 0', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative', zIndex: 1 }}>
          <a href="https://rhadix.nl" style={{ display: 'inline-block', textDecoration: 'none' }} title="Terug naar rhadix.nl">
            <img src={brandLogo()} alt="logo" style={{ height: 44, width: 'auto', objectFit: 'contain' }} />
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
        <TreeDecoration />
      </div>
      )}

      {/* ── Right — login form ────────────────────────────────────────────── */}
      <div className={merk ? 'merk-formulier' : undefined} style={{
        width: 440, background: '#fff',
        display: 'flex', flexDirection: 'column',
        justifyContent: 'center', padding: '56px 48px',
        borderLeft: merk ? 'none' : '1px solid var(--border)',
      }}>
        {merk && <MerkKopMobiel merk={merk} />}
        <div style={{ marginBottom: 36 }}>
          {onBack && (
            <button type="button" onClick={onBack} style={{
              background: 'none', border: 'none', padding: 0, marginBottom: 14, cursor: 'pointer',
              color: 'var(--text3)', fontSize: 13, fontFamily: 'var(--font)',
            }}>← Terug naar appkeuze</button>
          )}
          {merk ? (<>
            <h2 style={{ fontSize: 30, fontWeight: 400, color: 'var(--text)', marginBottom: 8, letterSpacing: '-0.01em' }}>Inloggen</h2>
            <p style={{ fontSize: 15, color: 'var(--text3)', lineHeight: 1.5 }}>Log in met uw account om naar uw woningprojecten te gaan.</p>
          </>) : (<>
            <h2 style={{ fontSize: 24, fontWeight: 800, color: 'var(--text)', marginBottom: 6 }}>Inloggen bij {appNaam}</h2>
            <p style={{ fontSize: 14, color: 'var(--text3)' }}>Voer uw e-mailadres en wachtwoord in.</p>
          </>)}
        </div>

        {/* ── Demo-inloggegevens (alleen buiten productie) ── */}
        {!merk && (import.meta.env.VITE_RHADIX_ENV || 'production') !== 'production' && (
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
              padding: '14px 16px', background: 'var(--k-blue-light)',
              border: '1px solid var(--k-blue-mid)', borderRadius: 'var(--radius)',
              fontSize: 13, color: 'var(--k-blue-strong)', lineHeight: 1.55,
            }}>
              {forgotSent ? (
                <span>Als <strong>{(forgotEmail || email).trim() || 'dit adres'}</strong> bij ons bekend is, ontvang je een e-mail met een link om je wachtwoord opnieuw in te stellen. Check ook je spamfolder.</span>
              ) : (
                <>
                  <strong>Wachtwoord vergeten?</strong>
                  <p style={{ margin: '4px 0 10px', color: 'var(--k-blue-strong)' }}>Vul je e-mailadres in; je ontvangt een resetlink per e-mail.</p>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <input
                      type="email"
                      value={forgotEmail || email}
                      onChange={e => setForgotEmail(e.target.value)}
                      placeholder="naam@organisatie.nl"
                      style={{ ...inputStyle, flex: 1, padding: '8px 12px' }}
                    />
                    <button type="button" onClick={submitForgot} disabled={forgotBusy}
                      style={{ background: 'var(--blue)', color: '#fff', border: 'none', borderRadius: 'var(--radius)',
                        padding: '8px 14px', fontSize: 13, fontWeight: 700, cursor: forgotBusy ? 'wait' : 'pointer', whiteSpace: 'nowrap' }}>
                      {forgotBusy ? 'Bezig…' : 'Verstuur link'}
                    </button>
                  </div>
                </>
              )}
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
              boxShadow: merk ? `inset 0 -3px 0 ${merk.accent}` : undefined,
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

        {merk ? (
          <p style={{ marginTop: 40, fontSize: 11, color: '#8A939C', textAlign: 'center', letterSpacing: '.14em', textTransform: 'uppercase' }}>
            Powered by Rhadix
          </p>
        ) : (
        <p style={{ marginTop: 12, fontSize: 11, color: 'var(--text3)', textAlign: 'center' }}>
          <a href="https://rhadix.nl" style={{ color: 'var(--text3)', textDecoration: 'underline' }}>
            ← Terug naar rhadix.nl
          </a>
        </p>
        )}
      </div>
    </div>
  )
}

// ── Merkvariant ────────────────────────────────────────────────────────────
// Lettertype Inter (OFL) lokaal uit public/merken/fonts; mobiel: logo in een band boven het formulier.
function MerkStijlen({ merk }) {
  const css = [400, 500, 600, 700].map(w =>
    `@font-face{font-family:'Inter';font-style:normal;font-weight:${w};font-display:swap;src:url('/merken/fonts/inter-latin-${w}-normal.woff2') format('woff2')}`).join('')
    + `.merk-login,.merk-login h1,.merk-login h2,.merk-login p,.merk-login label,.merk-login span,.merk-login input,.merk-login button{font-family:var(--font) !important}`
    + `.merk-login .merk-mobiel{display:none}`
    + `@media (max-width: 760px){.merk-login .merk-paneel{display:none !important}.merk-login .merk-formulier{width:100% !important;padding:0 24px 40px !important;justify-content:flex-start !important}`
    + `.merk-login .merk-mobiel{display:block;background:${merk.donker};margin:0 -24px 32px;padding:36px 24px 28px;text-align:center;border-bottom:3px solid ${merk.accent}}}`
  return <style>{css}</style>
}

function MerkPaneel({ merk }) {
  return (
    <div className="merk-paneel" style={{
      flex: 1, background: merk.donker, display: 'flex', flexDirection: 'column',
      justifyContent: 'center', alignItems: 'center', gap: 36, padding: '56px 64px',
    }}>
      <img src={merk.logo} alt={merk.logoAlt} style={{ width: 'min(340px, 70%)', height: 'auto' }} />
      <div aria-hidden="true" style={{ width: 56, height: 2, background: merk.accent }} />
      <div style={{ color: '#fff', fontSize: 13, letterSpacing: '.32em', textTransform: 'uppercase', opacity: 0.85 }}>{merk.label}</div>
    </div>
  )
}

function MerkKopMobiel({ merk }) {
  return (
    <div className="merk-mobiel">
      <img src={merk.logo} alt={merk.logoAlt} style={{ width: 180, height: 'auto', display: 'block', margin: '0 auto' }} />
      <div style={{ color: '#fff', fontSize: 11, letterSpacing: '.3em', textTransform: 'uppercase', marginTop: 14, opacity: 0.85 }}>{merk.label}</div>
    </div>
  )
}
