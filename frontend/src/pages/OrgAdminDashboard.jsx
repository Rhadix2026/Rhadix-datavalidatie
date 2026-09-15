/**
 * OrgAdminDashboard — ORG_ADMIN screen for managing users and app assignments.
 *
 * Features:
 *   - Create new users
 *   - Deactivate / reactivate users
 *   - Delete users
 *   - Reset user passwords
 *   - Assign / revoke applications per user
 */
import { useState, useEffect } from 'react'
import { Nav, NavBack } from '../components/UI'
import AppToewijzing from '../components/AppToewijzing'
import { NIVEAU_GEBRUIKER } from '../lib/appToewijzing'
import { gebruikTekst, isVol, maxUsersTekst } from '../lib/licentieweergave'
import {
  getMyTenantApps, getOrgUsers, getUserApps, assignAppToUser, revokeAppFromUser,
  createOrgUser, toggleUserActive, deleteOrgUser, resetOrgUserPassword,
  changeOwnPassword, updateOrgUser, getOwnLicense,
} from '../services/api'

// ── Shared styles ─────────────────────────────────────────────────────────────
const card       = { background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)', overflow: 'hidden' }
const thStyle    = { padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.08em', borderBottom: '1px solid var(--border)', background: 'var(--bg)' }
const btnPrimary = { padding: '7px 16px', background: 'var(--blue)', color: '#fff', border: 'none', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 13, fontWeight: 700, fontFamily: 'var(--font)' }
const btnGhost   = { padding: '6px 12px', background: 'none', color: 'var(--blue)', border: '1.5px solid var(--blue)', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 12, fontWeight: 600, fontFamily: 'var(--font)' }
const btnDanger  = { padding: '6px 12px', background: 'none', color: '#dc2626', border: '1.5px solid #fecaca', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 12, fontWeight: 600, fontFamily: 'var(--font)' }
const btnWarn    = { padding: '6px 12px', background: 'none', color: '#92400e', border: '1.5px solid #fde68a', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 12, fontWeight: 600, fontFamily: 'var(--font)' }
const inputStyle = { padding: '9px 12px', border: '1.5px solid var(--border)', borderRadius: 'var(--radius)', fontSize: 14, fontFamily: 'var(--font)', width: '100%', boxSizing: 'border-box', outline: 'none' }
const overlayStyle = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }

function ErrBox({ msg }) {
  if (!msg) return null
  return <div style={{ padding: '9px 13px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 'var(--radius)', fontSize: 13, color: '#dc2626', marginBottom: 12 }}>{msg}</div>
}

// ── Create User Modal ─────────────────────────────────────────────────────────

function CreateUserModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ email: '', full_name: '', password: '', role: 'ORG_USER' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault(); setError(''); setLoading(true)
    try { const u = await createOrgUser(form); onCreated(u); onClose() }
    catch (err) { let m = 'Aanmaken mislukt'; try { m = JSON.parse(err.message)?.detail || m } catch {} setError(m) }
    finally { setLoading(false) }
  }

  return (
    <div style={overlayStyle}>
      <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', padding: '36px 40px', width: 460, maxWidth: '90vw' }}>
        <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 24 }}>Nieuwe gebruiker aanmaken</h3>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {[
            { k: 'email',     label: 'E-mailadres',  type: 'email',    ph: 'gebruiker@organisatie.nl', req: true },
            { k: 'full_name', label: 'Naam',          type: 'text',     ph: 'Jan de Vries',             req: false },
            { k: 'password',  label: 'Wachtwoord',   type: 'password', ph: 'min. 12 tekens',           req: true },
          ].map(({ k, label, type, ph, req }) => (
            <label key={k} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>{label}</span>
              <input type={type} required={req} placeholder={ph} value={form[k]}
                onChange={e => setForm(f => ({ ...f, [k]: e.target.value }))} style={inputStyle} />
            </label>
          ))}
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>Rol</span>
            <select value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))} style={inputStyle}>
              <option value="ORG_USER">Gebruiker</option>
              <option value="ORG_ADMIN">Beheerder</option>
            </select>
          </label>
          <ErrBox msg={error} />
          <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
            <button type="button" onClick={onClose} style={{ flex: 1, ...btnGhost }}>Annuleren</button>
            <button type="submit" disabled={loading} style={{ flex: 2, ...btnPrimary }}>{loading ? 'Aanmaken…' : 'Aanmaken →'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Reset Password Modal ──────────────────────────────────────────────────────

function ResetPasswordModal({ user, onClose, onDone }) {
  const [password, setPassword] = useState('')
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')

  async function handleSubmit(e) {
    e.preventDefault(); setError(''); setLoading(true)
    try { await resetOrgUserPassword(user.id, password); onDone(); onClose() }
    catch (err) { let m = 'Reset mislukt'; try { m = JSON.parse(err.message)?.detail || m } catch {} setError(m) }
    finally { setLoading(false) }
  }

  return (
    <div style={overlayStyle}>
      <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', padding: '32px 36px', width: 420, maxWidth: '90vw' }}>
        <h3 style={{ fontSize: 16, fontWeight: 800, marginBottom: 6 }}>Wachtwoord resetten</h3>
        <p style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 20 }}>
          Stel een nieuw wachtwoord in voor <strong>{user.email}</strong>.
        </p>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>Nieuw wachtwoord (min. 12 tekens)</span>
            <input type="password" required placeholder="••••••••••••" value={password}
              onChange={e => setPassword(e.target.value)} style={inputStyle} autoFocus />
          </label>
          <ErrBox msg={error} />
          <div style={{ display: 'flex', gap: 12 }}>
            <button type="button" onClick={onClose} style={{ flex: 1, ...btnGhost }}>Annuleren</button>
            <button type="submit" disabled={loading} style={{ flex: 2, ...btnPrimary }}>{loading ? 'Resetten…' : 'Wachtwoord instellen'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Rol wijzigen ──────────────────────────────────────────────────────────────
//
// Een organisatiebeheerder kon een rol alleen bij het AANMAKEN zetten; daarna was er
// geen weg meer (bevinding 14). Bewust alleen de twee rollen die binnen een organisatie
// bestaan: Rhadix- en RSO-beheerder worden een niveau hoger beheerd, en de backend
// weigert ze hier ook.

function RolModal({ user, onClose, onDone }) {
  const [rol,     setRol]     = useState(user.role)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  const ongewijzigd = rol === user.role

  async function handleSubmit(e) {
    e.preventDefault(); setError(''); setLoading(true)
    try { await updateOrgUser(user.id, { role: rol }); onDone(rol); onClose() }
    catch (err) {
      let m = 'Wijzigen mislukt'
      try { m = JSON.parse(err.message)?.detail || m } catch { /* laat de standaardtekst staan */ }
      setError(m)
    }
    finally { setLoading(false) }
  }

  return (
    <div style={overlayStyle}>
      <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', padding: '32px 36px', width: 420, maxWidth: '90vw' }}>
        <h3 style={{ fontSize: 16, fontWeight: 800, marginBottom: 6 }}>Rol wijzigen</h3>
        <p style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 20 }}>
          Voor <strong>{user.full_name || user.email}</strong>.
        </p>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>Rol</span>
            <select value={rol} onChange={e => setRol(e.target.value)} style={inputStyle}>
              <option value="ORG_USER">Gebruiker</option>
              <option value="ORG_ADMIN">Beheerder</option>
            </select>
          </label>
          <div style={{ fontSize: 12, color: 'var(--text3)' }}>
            Een beheerder kan gebruikers aanmaken, applicaties toewijzen en wachtwoorden
            opnieuw instellen binnen deze organisatie.
          </div>
          <ErrBox msg={error} />
          <div style={{ display: 'flex', gap: 12 }}>
            <button type="button" onClick={onClose} style={{ flex: 1, ...btnGhost }}>Annuleren</button>
            <button type="submit" disabled={loading || ongewijzigd} style={{ flex: 2, ...btnPrimary, opacity: (loading || ongewijzigd) ? 0.6 : 1 }}>
              {loading ? 'Opslaan…' : 'Opslaan'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Eigen wachtwoord wijzigen ─────────────────────────────────────────────────
//
// Voor het eigen account is de beheerdersreset niet de juiste route: die zet een
// wachtwoord voor een ánder en vraagt niet om het huidige. Voor jezelf bestaat al de
// zelfbedieningsroute (PATCH /auth/me/password), die het huidige wachtwoord wél
// controleert. Deze modal gebruikt die route; er komt geen nieuwe inlogweg bij.

function EigenWachtwoordModal({ user, onClose }) {
  const [huidig,  setHuidig]  = useState('')
  const [nieuw,   setNieuw]   = useState('')
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')
  const [klaar,   setKlaar]   = useState(false)

  async function handleSubmit(e) {
    e.preventDefault(); setError(''); setLoading(true)
    try { await changeOwnPassword(huidig, nieuw); setKlaar(true) }
    catch (err) {
      let m = 'Wijzigen mislukt'
      try { m = JSON.parse(err.message)?.detail || err.message || m } catch { m = err.message || m }
      setError(m === 'Current password is incorrect' ? 'Het huidige wachtwoord klopt niet.' : m)
    }
    finally { setLoading(false) }
  }

  return (
    <div style={overlayStyle}>
      <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', padding: '32px 36px', width: 420, maxWidth: '90vw' }}>
        <h3 style={{ fontSize: 16, fontWeight: 800, marginBottom: 6 }}>Eigen wachtwoord wijzigen</h3>
        {klaar ? (
          <>
            <p style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 20 }}>
              Het wachtwoord van <strong>{user.email}</strong> is gewijzigd.
            </p>
            <button onClick={onClose} style={{ width: '100%', ...btnPrimary }}>Sluiten</button>
          </>
        ) : (
          <>
            <p style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 20 }}>
              U wijzigt het wachtwoord van uw eigen account (<strong>{user.email}</strong>).
              Ter controle vragen we eerst uw huidige wachtwoord.
            </p>
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>Huidig wachtwoord</span>
                <input type="password" required placeholder="••••••••••••" value={huidig}
                  onChange={e => setHuidig(e.target.value)} style={inputStyle} autoFocus />
              </label>
              <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>Nieuw wachtwoord (min. 12 tekens)</span>
                <input type="password" required placeholder="••••••••••••" value={nieuw}
                  onChange={e => setNieuw(e.target.value)} style={inputStyle} />
              </label>
              <ErrBox msg={error} />
              <div style={{ display: 'flex', gap: 12 }}>
                <button type="button" onClick={onClose} style={{ flex: 1, ...btnGhost }}>Annuleren</button>
                <button type="submit" disabled={loading} style={{ flex: 2, ...btnPrimary }}>
                  {loading ? 'Wijzigen…' : 'Wachtwoord wijzigen'}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  )
}

// ── User row ──────────────────────────────────────────────────────────────────

function UserRow({ user: initialUser, tenantApps, index, onRefresh, isSelf }) {
  const [user,       setUser]      = useState(initialUser)
  const [userApps,   setUserApps]  = useState(null)
  const [expanded,   setExpanded]  = useState(false)
  const [loading,    setLoading]   = useState(false)
  const [error,      setError]     = useState('')
  const [showReset,  setShowReset] = useState(false)
  const [showEigen,  setShowEigen] = useState(false)
  const [showRol,    setShowRol]   = useState(false)
  const [confirming, setConfirming] = useState(false)

  async function toggle() {
    if (!expanded && userApps === null) {
      setLoading(true)
      try { setUserApps(await getUserApps(user.id)) } catch (e) { setError(e.message) }
      finally { setLoading(false) }
    }
    setExpanded(e => !e)
  }

  async function handleToggleActive() {
    setLoading(true); setError('')
    try { const updated = await toggleUserActive(user.id); setUser(u => ({ ...u, is_active: updated.is_active })) }
    catch (err) { let m = 'Fout'; try { m = JSON.parse(err.message)?.detail || m } catch {} setError(m) }
    finally { setLoading(false) }
  }

  async function handleDelete() {
    setLoading(true); setError('')
    try { await deleteOrgUser(user.id); onRefresh() }
    catch (err) { let m = 'Verwijderen mislukt'; try { m = JSON.parse(err.message)?.detail || m } catch {} setError(m); setLoading(false) }
  }

  async function handleAssign(appId) {
    setLoading(true); setError('')
    try { await assignAppToUser(user.id, appId); setUserApps(await getUserApps(user.id)) }
    catch (err) { let m = 'Toewijzing mislukt'; try { m = JSON.parse(err.message)?.detail || m } catch {} setError(m) }
    finally { setLoading(false) }
  }

  async function handleRevoke(appId) {
    setLoading(true); setError('')
    try { await revokeAppFromUser(user.id, appId); setUserApps(await getUserApps(user.id)) }
    catch (err) { let m = 'Intrekken mislukt'; try { m = JSON.parse(err.message)?.detail || m } catch {} setError(m) }
    finally { setLoading(false) }
  }

  const rowBg = index % 2 === 0 ? '#fff' : 'var(--bg)'

  return (
    <>
      {showReset && (
        <ResetPasswordModal user={user} onClose={() => setShowReset(false)} onDone={() => {}} />
      )}
      {showEigen && (
        <EigenWachtwoordModal user={user} onClose={() => setShowEigen(false)} />
      )}
      {showRol && (
        <RolModal user={user} onClose={() => setShowRol(false)}
                  onDone={(rol) => setUser(u => ({ ...u, role: rol }))} />
      )}

      <tr style={{ background: rowBg, opacity: loading ? 0.7 : 1 }}>
        <td style={{ padding: '12px 16px', fontWeight: 600, fontSize: 14, borderBottom: expanded ? 'none' : '1px solid var(--border)' }}>
          {user.full_name || '—'}
        </td>
        <td style={{ padding: '12px 16px', fontSize: 13, color: 'var(--text3)', borderBottom: expanded ? 'none' : '1px solid var(--border)' }}>
          {user.email}
        </td>
        <td style={{ padding: '12px 16px', borderBottom: expanded ? 'none' : '1px solid var(--border)' }}>
          <span style={{ display: 'inline-flex', padding: '3px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, background: user.is_active ? '#dcfce7' : '#fee2e2', color: user.is_active ? '#166534' : '#991b1b' }}>
            {user.is_active ? 'Actief' : 'Inactief'}
          </span>
        </td>
        <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text3)', borderBottom: expanded ? 'none' : '1px solid var(--border)' }}>
          {user.role === 'ORG_ADMIN' ? 'Beheerder' : 'Gebruiker'}
        </td>
        <td style={{ padding: '12px 16px', borderBottom: expanded ? 'none' : '1px solid var(--border)' }}>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <button onClick={toggle} style={btnGhost} disabled={loading}>
              {expanded ? '▲ Apps' : '▼ Apps'}
            </button>
            <button onClick={() => setShowRol(true)} style={btnGhost} disabled={loading}
                    title="Rol wijzigen tussen gebruiker en beheerder">
              👤 Rol
            </button>
            {isSelf ? (
              <button onClick={() => setShowEigen(true)} style={btnWarn} disabled={loading}
                      title="Uw eigen wachtwoord wijzigen — vraagt om uw huidige wachtwoord">
                🔑 Wachtwoord wijzigen
              </button>
            ) : (
              <button onClick={() => setShowReset(true)} style={btnWarn} disabled={loading} title="Wachtwoord resetten">
                🔑 Reset
              </button>
            )}
            {!isSelf && (
              <button onClick={handleToggleActive} style={user.is_active ? btnDanger : btnGhost} disabled={loading}>
                {user.is_active ? 'Deactiveer' : 'Activeer'}
              </button>
            )}
            {!isSelf && !confirming && (
              <button onClick={() => setConfirming(true)} style={btnDanger} disabled={loading} title="Verwijderen">
                🗑️
              </button>
            )}
            {confirming && (
              <>
                <button onClick={handleDelete} style={{ ...btnDanger, background: '#dc2626', color: '#fff' }} disabled={loading}>
                  Ja, verwijder
                </button>
                <button onClick={() => setConfirming(false)} style={btnGhost}>Annuleer</button>
              </>
            )}
          </div>
          {error && <div style={{ fontSize: 12, color: '#dc2626', marginTop: 4 }}>{error}</div>}
        </td>
      </tr>

      {expanded && (
        <tr style={{ background: '#f8fafc' }}>
          <td colSpan={5} style={{ padding: '16px 24px', borderBottom: '1px solid var(--border)' }}>
            {/* Gebruikersniveau: het aanbod is wat de organisatie heeft, nooit meer. */}
            <AppToewijzing
              toegewezen={userApps || []}
              aanbod={tenantApps}
              doelNaam={user.full_name || user.email}
              niveau={NIVEAU_GEBRUIKER}
              bezig={loading}
              onToewijzen={handleAssign}
              onIntrekken={handleRevoke}
            />
          </td>
        </tr>
      )}
    </>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Main
// ═══════════════════════════════════════════════════════════════════════════════

export default function OrgAdminDashboard({ onBack, authUser }) {
  const [tenantApps,   setTenantApps]   = useState([])
  const [users,        setUsers]        = useState([])
  const [loading,      setLoading]      = useState(true)
  const [error,        setError]        = useState('')
  const [showCreate,   setShowCreate]   = useState(false)
  const [licentie,     setLicentie]     = useState(null)

  async function load() {
    setLoading(true); setError('')
    try {
      // De licentie is aanvullende informatie; als die niet op te halen is, moet het
      // gebruikersbeheer gewoon blijven werken.
      const [ta, u, lic] = await Promise.all([
        getMyTenantApps(), getOrgUsers(), getOwnLicense().catch(() => null),
      ])
      setTenantApps(ta)
      setUsers(u)
      setLicentie(lic)
    } catch (err) { setError('Kon gegevens niet laden: ' + err.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <Nav right={<NavBack onClick={onBack} />} />

      {showCreate && (
        <CreateUserModal
          onClose={() => setShowCreate(false)}
          onCreated={() => load()}
        />
      )}

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '40px 32px' }}>
        {/* Header */}
        <div style={{ marginBottom: 32, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--blue)', letterSpacing: '.1em', textTransform: 'uppercase', marginBottom: 6 }}>
              Organisatiebeheer · {authUser?.tenant_name}
            </div>
            <h1 style={{ fontSize: 28, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em' }}>
              Gebruikersbeheer
            </h1>
            <p style={{ fontSize: 14, color: 'var(--text2)', marginTop: 6 }}>
              Beheer gebruikers, applicatietoewijzingen en wachtwoorden.
            </p>
          </div>
          <button onClick={() => setShowCreate(true)} style={{ ...btnPrimary, fontSize: 14, padding: '10px 20px', marginTop: 4 }}>
            + Nieuwe gebruiker
          </button>
        </div>

        <ErrBox msg={error} />

        {/* Available apps summary */}
        {tenantApps.length > 0 && (
          <div style={{ marginBottom: 28 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 10 }}>
              Beschikbare applicaties voor uw organisatie
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {tenantApps.map(ta => (
                <span key={ta.id} style={{ display: 'inline-flex', padding: '5px 14px', borderRadius: 20, fontSize: 13, fontWeight: 600, background: '#e0f2fe', color: '#0369a1', border: '1px solid #bae6fd' }}>
                  {ta.application_name}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Licentie — ALLEEN LEZEN.
            Een beheerder die tegen "het maximum aantal actieve gebruikers is bereikt"
            aanloopt, moet kunnen zien waar die grens vandaan komt en hoeveel plaatsen er
            in gebruik zijn. Wijzigen kan alleen Rhadix; daarom staan hier geen knoppen. */}
        {licentie && (
          <div style={{ marginBottom: 28 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 10 }}>
              Licentie
            </div>
            <div style={{ ...card, padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }}>
              {licentie.heeft_licentie ? (
                <>
                  <span style={{ fontSize: 14, fontWeight: 700 }}>{licentie.licentie_naam}</span>
                  <span style={{ fontSize: 13, color: 'var(--text2)' }}>
                    Gebruikers:{' '}
                    <strong style={{ color: isVol(licentie.actieve_gebruikers, licentie.max_users) ? '#b45309' : 'inherit' }}>
                      {gebruikTekst(licentie.actieve_gebruikers, licentie.max_users)}
                    </strong>
                  </span>
                  <span style={{ fontSize: 13, color: 'var(--text2)' }}>
                    Maximum: <strong>{maxUsersTekst(licentie.max_users)}</strong>
                  </span>
                  <span style={{ fontSize: 13, color: 'var(--text3)' }}>
                    {licentie.valid_until
                      ? `Geldig tot ${new Date(licentie.valid_until).toLocaleDateString('nl-NL')}`
                      : 'Geen einddatum'}
                  </span>
                  {isVol(licentie.actieve_gebruikers, licentie.max_users) && (
                    <span style={{ fontSize: 12, color: '#92400e', background: '#fef3c7', borderRadius: 6, padding: '5px 10px' }}>
                      Het maximum is bereikt. Deactiveer eerst een gebruiker, of neem
                      contact op met Rhadix voor een ruimere licentie.
                    </span>
                  )}
                </>
              ) : (
                <>
                  <span style={{ display: 'inline-block', padding: '3px 9px', borderRadius: 999, background: '#fef3c7', color: '#92400e', fontSize: 11, fontWeight: 700 }}>
                    Geen licentie
                  </span>
                  <span style={{ fontSize: 13, color: 'var(--text3)' }}>
                    Er geldt op dit moment geen maximum aantal gebruikers voor uw organisatie.
                  </span>
                </>
              )}
            </div>
          </div>
        )}


        {/* Users table */}
        <div style={card}>
          <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontWeight: 700, fontSize: 15 }}>
              Gebruikers
              <span style={{ marginLeft: 8, fontSize: 13, color: 'var(--text3)', fontWeight: 400 }}>
                ({users.length})
              </span>
            </span>
            <button onClick={load} style={{ fontSize: 13, color: 'var(--blue)', background: 'none', border: 'none', cursor: 'pointer' }}>↻ Vernieuwen</button>
          </div>

          {loading ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text3)', fontSize: 14 }}>Laden…</div>
          ) : users.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text3)', fontSize: 14 }}>Geen gebruikers gevonden.</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>{['Naam', 'E-mail', 'Status', 'Rol', 'Acties'].map(h => <th key={h} style={thStyle}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {users.map((u, i) => (
                  <UserRow
                    key={u.id}
                    user={u}
                    tenantApps={tenantApps}
                    index={i}
                    onRefresh={load}
                    isSelf={u.id === authUser?.id}
                  />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
