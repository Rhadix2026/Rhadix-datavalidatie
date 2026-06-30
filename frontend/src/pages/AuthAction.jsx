import { useState, useEffect } from 'react'
import { BANNER_HEIGHT } from '../components/EnvironmentBanner'
import { resetPassword, setPasswordInvite, verifyEmail } from '../services/api'
import { brandLogo } from '../brand'

// Wachtwoordeisen (spiegelt de backend: BIO 9.4.3)
function pwChecks(pw) {
  return [
    { ok: pw.length >= 12,             label: 'minimaal 12 tekens' },
    { ok: /[A-Z]/.test(pw),            label: 'een hoofdletter' },
    { ok: /[a-z]/.test(pw),            label: 'een kleine letter' },
    { ok: /[0-9]/.test(pw),            label: 'een cijfer' },
    { ok: /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(pw), label: 'een speciaal teken' },
  ]
}

const COPY = {
  reset:  { title: 'Nieuw wachtwoord instellen', intro: 'Kies een nieuw wachtwoord voor je Rhadix-account.', cta: 'Wachtwoord opslaan', done: 'Je wachtwoord is ingesteld. Je kunt nu inloggen.' },
  invite: { title: 'Account activeren',          intro: 'Welkom bij Rhadix. Stel een wachtwoord in om je account te activeren.', cta: 'Account activeren', done: 'Je account is geactiveerd. Je kunt nu inloggen.' },
}

const card = {
  width: 460, maxWidth: '92vw', background: '#fff', borderRadius: 16,
  border: '1px solid var(--border)', padding: '40px 44px',
  boxShadow: '0 8px 40px rgba(15,23,42,.08)',
}
const inputStyle = {
  padding: '10px 14px', borderRadius: 'var(--radius)',
  border: '1.5px solid var(--border)', fontSize: 14,
  fontFamily: 'var(--font)', outline: 'none', background: '#fff', width: '100%', boxSizing: 'border-box',
}

export default function AuthAction({ action, token, onDone }) {
  const isVerify = action === 'verify'
  const copy = COPY[action] || COPY.reset

  const [pw, setPw]           = useState('')
  const [pw2, setPw2]         = useState('')
  const [loading, setLoading] = useState(isVerify)
  const [error, setError]     = useState('')
  const [success, setSuccess] = useState('')

  // Verify: meteen uitvoeren bij laden
  useEffect(() => {
    if (!isVerify) return
    let cancelled = false
    ;(async () => {
      try {
        await verifyEmail(token)
        if (!cancelled) setSuccess('Je e-mailadres is bevestigd.')
      } catch (e) {
        if (!cancelled) setError(e.message || 'De verificatielink is ongeldig of verlopen.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [isVerify, token])

  const checks = pwChecks(pw)
  const pwValid = checks.every(c => c.ok)
  const match = pw && pw === pw2

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (!pwValid) { setError('Wachtwoord voldoet nog niet aan alle eisen.'); return }
    if (!match)   { setError('De twee wachtwoorden komen niet overeen.'); return }
    setLoading(true)
    try {
      if (action === 'invite') await setPasswordInvite(token, pw)
      else                     await resetPassword(token, pw)
      setSuccess(copy.done)
    } catch (e) {
      setError(e.message || 'Er ging iets mis. Vraag eventueel een nieuwe link aan.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg)', paddingTop: BANNER_HEIGHT, paddingBottom: 40 }}>
      <div style={card}>
        <img src={brandLogo()} alt="Rhadix" style={{ height: 38, marginBottom: 22 }} />

        {success ? (
          <>
            <h2 style={{ fontSize: 21, fontWeight: 800, color: 'var(--text)', marginBottom: 8 }}>Gelukt</h2>
            <p style={{ fontSize: 14, color: 'var(--text2)', marginBottom: 24 }}>{success}</p>
            <button onClick={onDone} style={{ width: '100%', padding: '12px 0', borderRadius: 'var(--radius)',
              background: 'var(--blue)', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 15, fontWeight: 700 }}>
              Naar inloggen →
            </button>
          </>
        ) : isVerify ? (
          <>
            <h2 style={{ fontSize: 21, fontWeight: 800, color: 'var(--text)', marginBottom: 8 }}>E-mailadres bevestigen</h2>
            {loading && <p style={{ fontSize: 14, color: 'var(--text3)' }}>Bezig met bevestigen…</p>}
            {error && <ErrorBox msg={error} />}
            {!loading && <button onClick={onDone} style={linkBtn}>Naar inloggen →</button>}
          </>
        ) : (
          <form onSubmit={submit}>
            <h2 style={{ fontSize: 21, fontWeight: 800, color: 'var(--text)', marginBottom: 6 }}>{copy.title}</h2>
            <p style={{ fontSize: 14, color: 'var(--text3)', marginBottom: 22 }}>{copy.intro}</p>

            <label style={{ display: 'block', marginBottom: 14 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text2)', display: 'block', marginBottom: 6 }}>Nieuw wachtwoord</span>
              <input type="password" value={pw} onChange={e => setPw(e.target.value)} autoFocus
                placeholder="••••••••••••" style={inputStyle} />
            </label>

            <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 16px', fontSize: 12.5 }}>
              {checks.map((c, i) => (
                <li key={i} style={{ color: c.ok ? '#15803d' : 'var(--text3)', display: 'flex', gap: 6, marginBottom: 2 }}>
                  <span>{c.ok ? '✓' : '○'}</span><span>{c.label}</span>
                </li>
              ))}
            </ul>

            <label style={{ display: 'block', marginBottom: 18 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text2)', display: 'block', marginBottom: 6 }}>Herhaal wachtwoord</span>
              <input type="password" value={pw2} onChange={e => setPw2(e.target.value)}
                placeholder="••••••••••••" style={{ ...inputStyle,
                  borderColor: pw2 && !match ? '#fca5a5' : 'var(--border)' }} />
              {pw2 && !match && <span style={{ fontSize: 12, color: '#dc2626' }}>Komt niet overeen</span>}
            </label>

            {error && <ErrorBox msg={error} />}

            <button type="submit" disabled={loading || !pwValid || !match}
              style={{ width: '100%', padding: '12px 0', borderRadius: 'var(--radius)',
                background: (loading || !pwValid || !match) ? 'var(--text3)' : 'var(--blue)',
                color: '#fff', border: 'none', cursor: (loading || !pwValid || !match) ? 'not-allowed' : 'pointer',
                fontSize: 15, fontWeight: 700 }}>
              {loading ? 'Bezig…' : copy.cta}
            </button>
            <button type="button" onClick={onDone} style={{ ...linkBtn, marginTop: 14 }}>← Terug naar inloggen</button>
          </form>
        )}
      </div>
    </div>
  )
}

const linkBtn = {
  background: 'none', border: 'none', color: 'var(--blue)', cursor: 'pointer',
  fontSize: 13, fontFamily: 'var(--font)', padding: 0,
}

function ErrorBox({ msg }) {
  return (
    <div style={{ padding: '10px 14px', background: '#fef2f2', border: '1px solid #fecaca',
      borderRadius: 'var(--radius)', fontSize: 13, color: '#dc2626', marginBottom: 16 }}>
      {msg}
    </div>
  )
}
