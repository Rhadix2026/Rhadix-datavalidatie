import { useState, useEffect } from 'react'
import { Nav, NavBack } from '../components/UI'
import {
  rsoListOrganisations, rsoCreateOrganisation,
  rsoListOrgUsers, rsoCreateUser, rsoUpdateUser, rsoToggleUserActive, rsoResetUserPassword,
  rsoListApplications, rsoListOrgApps, rsoAssignApp, rsoRevokeApp,
} from '../services/api'

// ── styles ──────────────────────────────────────────────────────────────────
const card       = { background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)', overflow: 'hidden' }
const thStyle    = { padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.08em', borderBottom: '1px solid var(--border)', background: 'var(--bg)' }
const inp        = { padding: '9px 13px', borderRadius: 'var(--radius)', border: '1.5px solid var(--border)', fontSize: 13, fontFamily: 'var(--font)', width: '100%', boxSizing: 'border-box' }
const btnPrimary = { padding: '9px 18px', background: 'var(--blue)', color: '#fff', border: 'none', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 13, fontWeight: 700, fontFamily: 'var(--font)' }
const btnGhost   = { padding: '7px 14px', background: 'none', color: 'var(--blue)', border: '1.5px solid var(--blue)', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 12, fontWeight: 600, fontFamily: 'var(--font)' }
const overlay    = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }

function ErrBox({ msg }) {
  if (!msg) return null
  return <div style={{ padding: '9px 13px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 'var(--radius)', fontSize: 13, color: '#dc2626', marginBottom: 12 }}>{msg}</div>
}
function parseErr(err, fallback) { let m = fallback; try { m = JSON.parse(err.message)?.detail || m } catch {} return m }

// ── Create org modal ──────────────────────────────────────────────────────────
function CreateOrgModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ name: '', slug: '', admin_email: '', admin_password: '', admin_full_name: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const set = (k, v) => {
    const next = { ...form, [k]: v }
    if (k === 'name' && !form.slug) next.slug = v.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
    setForm(next)
  }
  async function submit(e) {
    e.preventDefault(); setError(''); setLoading(true)
    try { await rsoCreateOrganisation(form); onCreated(); onClose() }
    catch (err) { setError(parseErr(err, 'Aanmaken mislukt')) } finally { setLoading(false) }
  }
  return (
    <div style={overlay}>
      <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', padding: '32px 36px', width: 460, maxWidth: '90vw' }}>
        <h3 style={{ fontSize: 17, fontWeight: 800, marginBottom: 4 }}>Organisatie toevoegen</h3>
        <p style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 20 }}>Nieuwe zorgorganisatie onder uw samenwerkingsorganisatie.</p>
        <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {[
            { k: 'name', label: 'Organisatienaam', type: 'text', ph: 'Zorggroep Noord', req: true },
            { k: 'slug', label: 'Slug (URL-naam)', type: 'text', ph: 'zorggroep-noord', req: true },
            { k: 'admin_email', label: 'Beheerder e-mail', type: 'email', ph: 'beheer@zorggroep.nl', req: true },
            { k: 'admin_password', label: 'Beheerder wachtwoord', type: 'password', ph: 'min. 12 tekens', req: true },
            { k: 'admin_full_name', label: 'Beheerder naam', type: 'text', ph: '(optioneel)', req: false },
          ].map(f => (
            <label key={f.k} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>{f.label}</span>
              <input type={f.type} required={f.req} value={form[f.k]} onChange={e => set(f.k, e.target.value)} placeholder={f.ph} style={inp} />
            </label>
          ))}
          <ErrBox msg={error} />
          <div style={{ display: 'flex', gap: 12 }}>
            <button type="button" onClick={onClose} style={{ flex: 1, ...btnGhost }}>Annuleren</button>
            <button type="submit" disabled={loading} style={{ flex: 2, ...btnPrimary }}>{loading ? 'Aanmaken…' : 'Aanmaken →'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Create/edit user modal ─────────────────────────────────────────────────────
function UserModal({ tenant, user, onClose, onSaved }) {
  const editing = !!user
  const canRso = tenant.tenant_type === 'RSO'
  const [form, setForm] = useState(editing
    ? { full_name: user.full_name || '', role: user.role }
    : { email: '', password: '', full_name: '', role: 'ORG_USER' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  async function submit(e) {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      if (editing) await rsoUpdateUser(user.id, { full_name: form.full_name, role: form.role })
      else await rsoCreateUser(tenant.id, form)
      onSaved(); onClose()
    } catch (err) { setError(parseErr(err, 'Opslaan mislukt')) } finally { setLoading(false) }
  }
  return (
    <div style={overlay}>
      <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', padding: '32px 36px', width: 440, maxWidth: '90vw' }}>
        <h3 style={{ fontSize: 17, fontWeight: 800, marginBottom: 4 }}>{editing ? 'Gebruiker bewerken' : 'Gebruiker toevoegen'}</h3>
        <p style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 20 }}>{editing ? user.email : <>Nieuwe gebruiker voor <strong>{tenant.name}</strong></>}</p>
        <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {!editing && (
            <>
              <label style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>E-mailadres</span>
                <input type="email" required value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} placeholder="gebruiker@org.nl" style={inp} />
              </label>
              <label style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>Wachtwoord</span>
                <input type="password" required value={form.password} onChange={e => setForm(p => ({ ...p, password: e.target.value }))} placeholder="min. 12 tekens" style={inp} />
              </label>
            </>
          )}
          <label style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>Naam</span>
            <input type="text" value={form.full_name} onChange={e => setForm(p => ({ ...p, full_name: e.target.value }))} placeholder="Volledige naam" style={inp} />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>Rol</span>
            <select value={form.role} onChange={e => setForm(p => ({ ...p, role: e.target.value }))} style={inp}>
              <option value="ORG_USER">Gebruiker</option>
              <option value="ORG_ADMIN">Organisatiebeheerder</option>
              {canRso && <option value="RSO_ADMIN">RSO-beheerder</option>}
            </select>
          </label>
          <ErrBox msg={error} />
          <div style={{ display: 'flex', gap: 10 }}>
            <button type="button" onClick={onClose} style={{ flex: 1, ...btnGhost }}>Annuleren</button>
            <button type="submit" disabled={loading} style={{ flex: 2, ...btnPrimary }}>{loading ? 'Opslaan…' : (editing ? 'Opslaan' : 'Aanmaken')}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Reset password modal ────────────────────────────────────────────────────────
function ResetModal({ user, onClose }) {
  const [pw, setPw] = useState(''); const [loading, setLoading] = useState(false); const [error, setError] = useState(''); const [done, setDone] = useState(false)
  async function submit(e) {
    e.preventDefault(); setError(''); setLoading(true)
    try { await rsoResetUserPassword(user.id, pw); setDone(true) } catch (err) { setError(parseErr(err, 'Reset mislukt')) } finally { setLoading(false) }
  }
  return (
    <div style={overlay}>
      <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', padding: '32px 36px', width: 420, maxWidth: '90vw' }}>
        {done ? (
          <>
            <div style={{ fontSize: 30, marginBottom: 10 }}>✅</div>
            <h3 style={{ fontSize: 16, fontWeight: 800, marginBottom: 8 }}>Wachtwoord ingesteld</h3>
            <p style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 18 }}>Bijgewerkt voor <strong>{user.email}</strong>.</p>
            <button onClick={onClose} style={{ ...btnGhost, width: '100%' }}>Sluiten</button>
          </>
        ) : (
          <>
            <h3 style={{ fontSize: 16, fontWeight: 800, marginBottom: 6 }}>Wachtwoord resetten</h3>
            <p style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 18 }}>Nieuw wachtwoord voor <strong>{user.email}</strong>.</p>
            <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <input type="password" required placeholder="Min. 12 tekens" value={pw} onChange={e => setPw(e.target.value)} style={inp} autoFocus />
              <ErrBox msg={error} />
              <div style={{ display: 'flex', gap: 10 }}>
                <button type="button" onClick={onClose} style={{ flex: 1, ...btnGhost }}>Annuleren</button>
                <button type="submit" disabled={loading} style={{ flex: 2, ...btnPrimary }}>{loading ? 'Resetten…' : 'Instellen'}</button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  )
}

// ── Main ────────────────────────────────────────────────────────────────────────
export default function RsoDashboard({ onBack, authUser }) {
  const [orgs, setOrgs] = useState([])
  const [apps, setApps] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState(null)
  const [detail, setDetail] = useState({})       // { tid: { users, apps } }
  const [showCreate, setShowCreate] = useState(false)
  const [userModal, setUserModal] = useState(null)   // { tenant, user? }
  const [resetUser, setResetUser] = useState(null)

  async function load() {
    setLoading(true); setError('')
    try {
      const [o, a] = await Promise.all([rsoListOrganisations(), rsoListApplications()])
      setOrgs(o); setApps(a)
    } catch (err) { setError('Kon gegevens niet laden: ' + parseErr(err, err.message)) }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  async function loadDetail(tid) {
    if (expanded === tid) { setExpanded(null); return }
    setExpanded(tid)
    try {
      const [users, tapps] = await Promise.all([rsoListOrgUsers(tid), rsoListOrgApps(tid)])
      setDetail(p => ({ ...p, [tid]: { users, apps: tapps } }))
    } catch {}
  }
  async function refreshDetail(tid) {
    const [users, tapps] = await Promise.all([rsoListOrgUsers(tid), rsoListOrgApps(tid)])
    setDetail(p => ({ ...p, [tid]: { users, apps: tapps } }))
  }

  async function toggleUser(tid, uid) {
    try { await rsoToggleUserActive(uid); await refreshDetail(tid) }
    catch (err) { alert('Mislukt: ' + parseErr(err, err.message)) }
  }
  async function assignApp(tid, appId) {
    if (!appId) return
    try { await rsoAssignApp(tid, appId); await refreshDetail(tid) }
    catch (err) { alert('Mislukt: ' + parseErr(err, err.message)) }
  }
  async function revokeApp(tid, appId) {
    if (!window.confirm('App-toewijzing intrekken?')) return
    try { await rsoRevokeApp(tid, appId); await refreshDetail(tid) }
    catch (err) { alert('Mislukt: ' + parseErr(err, err.message)) }
  }

  const rsoName = orgs.find(o => o.is_self)?.name || authUser?.tenant_name || 'Samenwerkingsorganisatie'

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <Nav right={<NavBack onClick={onBack} />} />
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '40px 32px' }}>
        <div style={{ marginBottom: 28 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--blue)', letterSpacing: '.1em', textTransform: 'uppercase', marginBottom: 6 }}>RSO-beheer</div>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em' }}>{rsoName}</h1>
          <p style={{ fontSize: 14, color: 'var(--text3)', marginTop: 6 }}>Beheer uw aangesloten organisaties, hun gebruikers en app-toegang.</p>
        </div>

        {error && <ErrBox msg={error} />}

        <div style={card}>
          <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontWeight: 700, fontSize: 15 }}>Organisaties</span>
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={load} style={{ fontSize: 13, color: 'var(--blue)', background: 'none', border: 'none', cursor: 'pointer' }}>↻ Vernieuwen</button>
              <button onClick={() => setShowCreate(true)} style={btnPrimary}>+ Organisatie toevoegen</button>
            </div>
          </div>

          {loading ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text3)', fontSize: 14 }}>Laden…</div>
          ) : orgs.length === 0 ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text3)', fontSize: 14 }}>Nog geen organisaties.</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr>{['Naam', 'Type', 'Gebruikers', 'Scans', 'Status', ''].map(h => <th key={h} style={thStyle}>{h}</th>)}</tr></thead>
              <tbody>
                {orgs.flatMap((t, i) => {
                  const rows = [(
                    <tr key={t.id} style={{ background: t.is_self ? '#eef6ff' : (i % 2 === 0 ? '#fff' : 'var(--bg)') }}>
                      <td style={{ padding: '12px 16px', fontWeight: 600, fontSize: 14, borderBottom: '1px solid var(--border)' }}>
                        {t.name} {t.is_self && <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--blue)', marginLeft: 6 }}>· uw RSO</span>}
                      </td>
                      <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text3)', borderBottom: '1px solid var(--border)' }}>{t.tenant_type === 'RSO' ? 'Samenwerkingsorg.' : 'Organisatie'}</td>
                      <td style={{ padding: '12px 16px', fontSize: 13, color: 'var(--text2)', borderBottom: '1px solid var(--border)' }}>{t.user_count}</td>
                      <td style={{ padding: '12px 16px', fontSize: 13, color: 'var(--text2)', borderBottom: '1px solid var(--border)' }}>{t.scan_count}</td>
                      <td style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
                        <span style={{ display: 'inline-flex', padding: '3px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, background: t.is_active ? '#dcfce7' : '#fee2e2', color: t.is_active ? '#166534' : '#991b1b' }}>{t.is_active ? 'Actief' : 'Inactief'}</span>
                      </td>
                      <td style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
                        <button onClick={() => loadDetail(t.id)} style={btnGhost}>{expanded === t.id ? '▲' : '▼'} Detail</button>
                      </td>
                    </tr>
                  )]
                  if (expanded === t.id) {
                    const d = detail[t.id] || { users: [], apps: [] }
                    const unassigned = apps.filter(a => !(d.apps || []).some(x => x.application_id === a.id))
                    rows.push(
                      <tr key={`${t.id}-d`}>
                        <td colSpan={6} style={{ padding: '20px 24px', background: '#f8fafc', borderBottom: '1px solid var(--border)' }}>
                          {/* Apps */}
                          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 10 }}>Applicaties</div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', marginBottom: 18 }}>
                            {(d.apps || []).length === 0 && <span style={{ fontSize: 13, color: 'var(--text3)' }}>Geen apps toegewezen.</span>}
                            {(d.apps || []).map(ta => (
                              <div key={ta.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: '#e0f2fe', borderRadius: 20, padding: '4px 12px 4px 14px', fontSize: 13, fontWeight: 600, color: '#0369a1' }}>
                                {ta.application_name}
                                <button onClick={() => revokeApp(t.id, ta.application_id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', fontSize: 16, lineHeight: 1, padding: 0 }} title="Intrekken">×</button>
                              </div>
                            ))}
                            {unassigned.length > 0 && (
                              <select defaultValue="" onChange={e => { assignApp(t.id, e.target.value); e.target.value = '' }} style={{ ...inp, width: 'auto', padding: '6px 10px' }}>
                                <option value="">+ App toewijzen…</option>
                                {unassigned.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                              </select>
                            )}
                          </div>

                          {/* Users */}
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '4px 0 10px' }}>
                            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Gebruikers</div>
                            <button onClick={() => setUserModal({ tenant: t })} style={{ ...btnPrimary, padding: '5px 12px', fontSize: 11 }}>+ Gebruiker</button>
                          </div>
                          {(d.users || []).length === 0 ? (
                            <p style={{ fontSize: 13, color: 'var(--text3)', margin: 0 }}>Geen gebruikers.</p>
                          ) : (
                            <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 'var(--radius)', overflow: 'hidden', border: '1px solid var(--border)' }}>
                              <thead><tr>{['Naam', 'E-mail', 'Rol', 'Status', 'Acties'].map(h => <th key={h} style={{ ...thStyle, fontSize: 10, padding: '7px 12px' }}>{h}</th>)}</tr></thead>
                              <tbody>
                                {(d.users || []).map((u, ui) => (
                                  <tr key={u.id} style={{ background: ui % 2 === 0 ? '#fff' : '#f8fafc' }}>
                                    <td style={{ padding: '9px 12px', fontSize: 13, fontWeight: 600, borderBottom: '1px solid var(--border)' }}>{u.full_name || '—'}</td>
                                    <td style={{ padding: '9px 12px', fontSize: 12, color: 'var(--text3)', borderBottom: '1px solid var(--border)' }}>{u.email}</td>
                                    <td style={{ padding: '9px 12px', fontSize: 12, color: 'var(--text3)', borderBottom: '1px solid var(--border)' }}>{u.role}</td>
                                    <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--border)' }}>
                                      <span style={{ display: 'inline-flex', padding: '2px 8px', borderRadius: 20, fontSize: 11, fontWeight: 600, background: u.is_active ? '#dcfce7' : '#fee2e2', color: u.is_active ? '#166534' : '#991b1b' }}>{u.is_active ? 'Actief' : 'Inactief'}</span>
                                    </td>
                                    <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--border)' }}>
                                      <div style={{ display: 'flex', gap: 5 }}>
                                        <button onClick={() => setUserModal({ tenant: t, user: u })} style={{ ...btnGhost, padding: '4px 10px', fontSize: 11 }}>✏️</button>
                                        <button onClick={() => setResetUser(u)} style={{ ...btnGhost, padding: '4px 10px', fontSize: 11 }}>🔑</button>
                                        <button onClick={() => toggleUser(t.id, u.id)} style={u.is_active
                                          ? { padding: '4px 10px', background: 'none', color: '#dc2626', border: '1.5px solid #fecaca', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 11, fontWeight: 600, fontFamily: 'var(--font)' }
                                          : { ...btnGhost, padding: '4px 10px', fontSize: 11 }}>{u.is_active ? 'Deact.' : 'Activ.'}</button>
                                      </div>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          )}
                        </td>
                      </tr>
                    )
                  }
                  return rows
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {showCreate && <CreateOrgModal onClose={() => setShowCreate(false)} onCreated={load} />}
      {userModal && (
        <UserModal tenant={userModal.tenant} user={userModal.user}
          onClose={() => setUserModal(null)}
          onSaved={() => refreshDetail(userModal.tenant.id)} />
      )}
      {resetUser && <ResetModal user={resetUser} onClose={() => setResetUser(null)} />}
    </div>
  )
}
