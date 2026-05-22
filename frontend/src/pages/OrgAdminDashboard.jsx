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
import {
  getMyTenantApps, getOrgUsers, getUserApps, assignAppToUser, revokeAppFromUser,
  createOrgUser, toggleUserActive, deleteOrgUser, resetOrgUserPassword,
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

// ── User row ──────────────────────────────────────────────────────────────────

function UserRow({ user: initialUser, tenantApps, index, onRefresh, isSelf }) {
  const [user,       setUser]      = useState(initialUser)
  const [userApps,   setUserApps]  = useState(null)
  const [expanded,   setExpanded]  = useState(false)
  const [loading,    setLoading]   = useState(false)
  const [error,      setError]     = useState('')
  const [showReset,  setShowReset] = useState(false)
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

  const assignedIds = new Set((userApps || []).map(ua => ua.application_id))
  const availableToAssign = tenantApps.filter(ta => !assignedIds.has(ta.application_id))

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
            <button onClick={() => setShowReset(true)} style={btnWarn} disabled={loading || isSelf} title="Wachtwoord resetten">
              🔑 Reset
            </button>
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
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 10 }}>
              Toegewezen applicaties
            </div>
            {(userApps || []).length === 0 ? (
              <p style={{ fontSize: 13, color: 'var(--text3)', margin: '0 0 16px' }}>Geen applicaties toegewezen.</p>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
                {(userApps || []).map(ua => (
                  <div key={ua.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: '#e0f2fe', borderRadius: 20, padding: '5px 10px 5px 14px', fontSize: 13, fontWeight: 600, color: '#0369a1' }}>
                    {ua.application_name}
                    <button onClick={() => handleRevoke(ua.application_id)} disabled={loading}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', fontSize: 16, lineHeight: 1, padding: 0 }}
                      title="Toegang intrekken">×</button>
                  </div>
                ))}
              </div>
            )}
            {availableToAssign.length > 0 && (
              <>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 10 }}>
                  Beschikbaar om toe te wijzen
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {availableToAssign.map(ta => (
                    <button key={ta.application_id} onClick={() => handleAssign(ta.application_id)}
                      disabled={loading} style={{ ...btnPrimary, opacity: loading ? 0.6 : 1 }}>
                      + {ta.application_name}
                    </button>
                  ))}
                </div>
              </>
            )}
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

  async function load() {
    setLoading(true); setError('')
    try {
      const [ta, u] = await Promise.all([getMyTenantApps(), getOrgUsers()])
      setTenantApps(ta)
      setUsers(u)
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
