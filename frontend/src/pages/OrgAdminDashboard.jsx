/**
 * OrgAdminDashboard — ORG_ADMIN screen for managing user-app assignments.
 *
 * Shows:
 *   - Applications available to this organisation
 *   - All users in the organisation with their assigned apps
 *   - Buttons to assign / revoke apps per user
 */
import { useState, useEffect } from 'react'
import { Nav, NavBack } from '../components/UI'
import { getMyTenantApps, getOrgUsers, getUserApps, assignAppToUser, revokeAppFromUser } from '../services/api'

// ── Shared styles ─────────────────────────────────────────────────────────────
const card       = { background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)', overflow: 'hidden' }
const thStyle    = { padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.08em', borderBottom: '1px solid var(--border)', background: 'var(--bg)' }
const btnPrimary = { padding: '6px 14px', background: 'var(--blue)', color: '#fff', border: 'none', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 12, fontWeight: 700, fontFamily: 'var(--font)' }
const btnGhost   = { padding: '5px 12px', background: 'none', color: 'var(--blue)', border: '1.5px solid var(--blue)', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 12, fontWeight: 600, fontFamily: 'var(--font)' }
const btnDanger  = { padding: '5px 12px', background: 'none', color: '#dc2626', border: '1.5px solid #fecaca', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 12, fontWeight: 600, fontFamily: 'var(--font)' }

function ErrBox({ msg }) {
  if (!msg) return null
  return <div style={{ padding: '9px 13px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 'var(--radius)', fontSize: 13, color: '#dc2626', marginBottom: 12 }}>{msg}</div>
}

// ── User row ──────────────────────────────────────────────────────────────────

function UserRow({ user, tenantApps, index }) {
  const [userApps,  setUserApps]  = useState(null)   // null = not loaded yet
  const [expanded,  setExpanded]  = useState(false)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState('')

  async function toggle() {
    if (!expanded && userApps === null) {
      setLoading(true)
      try { setUserApps(await getUserApps(user.id)) } catch (e) { setError(e.message) }
      finally { setLoading(false) }
    }
    setExpanded(e => !e)
  }

  const assignedIds = new Set((userApps || []).map(ua => ua.application_id))
  const availableToAssign = tenantApps.filter(ta => !assignedIds.has(ta.application_id))

  async function handleAssign(appId) {
    setLoading(true); setError('')
    try {
      await assignAppToUser(user.id, appId)
      setUserApps(await getUserApps(user.id))
    } catch (err) {
      let m = 'Toewijzing mislukt'; try { m = JSON.parse(err.message)?.detail || m } catch {} setError(m)
    } finally { setLoading(false) }
  }

  async function handleRevoke(appId) {
    setLoading(true); setError('')
    try {
      await revokeAppFromUser(user.id, appId)
      setUserApps(await getUserApps(user.id))
    } catch (err) {
      let m = 'Intrekken mislukt'; try { m = JSON.parse(err.message)?.detail || m } catch {} setError(m)
    } finally { setLoading(false) }
  }

  const rowBg = index % 2 === 0 ? '#fff' : 'var(--bg)'

  return (
    <>
      <tr style={{ background: rowBg }}>
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
          {user.role}
        </td>
        <td style={{ padding: '12px 16px', borderBottom: expanded ? 'none' : '1px solid var(--border)' }}>
          <button onClick={toggle} style={btnGhost}>
            {loading ? '…' : expanded ? '▲ Sluit' : '▼ Applicaties'}
          </button>
        </td>
      </tr>

      {expanded && (
        <tr style={{ background: '#f8fafc' }}>
          <td colSpan={5} style={{ padding: '16px 24px', borderBottom: '1px solid var(--border)' }}>
            <ErrBox msg={error} />

            {/* Currently assigned */}
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
                    <button
                      onClick={() => handleRevoke(ua.application_id)}
                      disabled={loading}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', fontSize: 16, lineHeight: 1, padding: 0 }}
                      title="Toegang intrekken"
                    >×</button>
                  </div>
                ))}
              </div>
            )}

            {/* Add more */}
            {availableToAssign.length > 0 && (
              <>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 10 }}>
                  Beschikbaar om toe te wijzen
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {availableToAssign.map(ta => (
                    <button
                      key={ta.application_id}
                      onClick={() => handleAssign(ta.application_id)}
                      disabled={loading}
                      style={{ ...btnPrimary, opacity: loading ? 0.6 : 1 }}
                    >
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
  const [tenantApps, setTenantApps] = useState([])
  const [users,      setUsers]      = useState([])
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState('')

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
      <Nav right={<NavBack onClick={onBack} dark />} />

      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '40px 32px' }}>
        {/* Header */}
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--blue)', letterSpacing: '.1em', textTransform: 'uppercase', marginBottom: 6 }}>
            Organisatiebeheer · {authUser?.tenant_name}
          </div>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em' }}>
            Applicatietoewijzingen
          </h1>
          <p style={{ fontSize: 14, color: 'var(--text2)', marginTop: 6 }}>
            Wijs beschikbare applicaties toe aan gebruikers in uw organisatie.
          </p>
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
            <span style={{ fontWeight: 700, fontSize: 15 }}>Gebruikers</span>
            <button onClick={load} style={{ fontSize: 13, color: 'var(--blue)', background: 'none', border: 'none', cursor: 'pointer' }}>↻ Vernieuwen</button>
          </div>

          {loading ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text3)', fontSize: 14 }}>Laden…</div>
          ) : users.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text3)', fontSize: 14 }}>Geen gebruikers gevonden.</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>{['Naam', 'E-mail', 'Status', 'Rol', ''].map(h => <th key={h} style={thStyle}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {users.map((u, i) => (
                  <UserRow key={u.id} user={u} tenantApps={tenantApps} index={i} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
