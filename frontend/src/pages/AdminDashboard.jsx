import { useState, useEffect } from 'react'
import { Nav, NavBack } from '../components/UI'
import {
  getAdminStats, getAdminTenants, createAdminTenant,
  getAdminApplications, updateAdminApplication,
  getAdminLicenses, createAdminLicense, updateAdminLicense, deleteAdminLicense,
  getAdminTenantApps, assignAppToTenant, revokeAppFromTenant,
  getAdminTenantLicenses, getAdminTenantUsers,
  adminToggleUserActive, adminDeleteUser, adminResetUserPassword,
  adminCreateUser, adminUpdateUser,
  getAdminTenantImpact, adminToggleTenantActive, adminDeleteTenant,
  getTenantBranding, putTenantBranding, deleteTenantBranding,
  uploadTenantLogo, deleteTenantLogo, tenantLogoUrl,
} from '../services/api'

// Toewijsbare producten = de portaal-tegels. Validatie-sub-modules (KIK-V/ZIB/Algemeen
// Validator) zijn interne toegangschakelaars en worden niet in de lijst getoond.
const PRODUCT_SLUGS = new Set(['datavalidatie', 'uitvraag', 'datastation', 'rhadix-crm', 'reconciliation-engine'])

const BRAND_PRESETS = {
  rhadix: { label: 'Rhadix (standaard)', primary_color: '#1A2847', accent_color: '#1A2847' },
  kikv:   { label: 'KIK-V',              primary_color: '#bd285f', accent_color: '#2e6896' },
  custom: { label: 'Aangepast',          primary_color: '#1A2847', accent_color: '#1A2847' },
}

// ── Shared styles ─────────────────────────────────────────────────────────────
const card       = { background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)', overflow: 'hidden' }
const thStyle    = { padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.08em', borderBottom: '1px solid var(--border)', background: 'var(--bg)' }
const inputStyle = { padding: '9px 13px', borderRadius: 'var(--radius)', border: '1.5px solid var(--border)', fontSize: 13, fontFamily: 'var(--font)', width: '100%', boxSizing: 'border-box' }
const btnPrimary = { padding: '9px 18px', background: 'var(--blue)', color: '#fff', border: 'none', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 13, fontWeight: 700, fontFamily: 'var(--font)' }
const btnGhost   = { padding: '7px 14px', background: 'none', color: 'var(--blue)', border: '1.5px solid var(--blue)', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 12, fontWeight: 600, fontFamily: 'var(--font)' }

function ErrBox({ msg }) {
  if (!msg) return null
  return <div style={{ padding: '9px 13px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 'var(--radius)', fontSize: 13, color: '#dc2626', marginBottom: 12 }}>{msg}</div>
}

function Badge({ active }) {
  return (
    <span style={{ display: 'inline-flex', padding: '3px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, background: active ? '#dcfce7' : '#fee2e2', color: active ? '#166534' : '#991b1b' }}>
      {active ? 'Actief' : 'Inactief'}
    </span>
  )
}

// ── Stat card ─────────────────────────────────────────────────────────────────
function StatCard({ label, value, color = 'var(--blue)' }) {
  return (
    <div style={{ ...card, padding: '20px 24px', boxShadow: '0 1px 4px rgba(0,0,0,.06)' }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.1em', marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 32, fontWeight: 900, color, lineHeight: 1 }}>{value ?? '—'}</div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Modals
// ═══════════════════════════════════════════════════════════════════════════════

function CreateTenantModal({ onClose, onCreated, tenants = [] }) {
  const [form,    setForm]    = useState({ name: '', slug: '', admin_email: '', admin_password: '', admin_full_name: '', tenant_type: 'ORG', parent_tenant_id: '' })
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  const rsos = tenants.filter(t => (t.tenant_type || 'ORG') === 'RSO')

  const set = (k, v) => {
    const next = { ...form, [k]: v }
    if (k === 'name' && !form.slug)
      next.slug = v.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
    if (k === 'tenant_type' && v === 'RSO') next.parent_tenant_id = ''   // een RSO valt niet onder een RSO
    setForm(next)
  }

  async function handleSubmit(e) {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      const payload = { ...form, parent_tenant_id: form.parent_tenant_id || null }
      const r = await createAdminTenant(payload); onCreated(r); onClose()
    }
    catch (err) { let m = 'Aanmaken mislukt'; try { m = JSON.parse(err.message)?.detail || m } catch {} setError(m) }
    finally { setLoading(false) }
  }

  const isRso = form.tenant_type === 'RSO'
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', padding: '36px 40px', width: 480, maxWidth: '90vw' }}>
        <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 24 }}>Nieuwe organisatie aanmaken</h3>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>Type</span>
            <select value={form.tenant_type} onChange={e => set('tenant_type', e.target.value)} style={inputStyle}>
              <option value="ORG">Zorgorganisatie</option>
              <option value="RSO">Samenwerkingsorganisatie (RSO)</option>
            </select>
          </label>
          {!isRso && rsos.length > 0 && (
            <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>Valt onder RSO (optioneel)</span>
              <select value={form.parent_tenant_id} onChange={e => set('parent_tenant_id', e.target.value)} style={inputStyle}>
                <option value="">— geen —</option>
                {rsos.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
              </select>
            </label>
          )}
          {[
            { k: 'name',            label: 'Organisatienaam',   type: 'text',     ph: isRso ? 'RSO Noord' : 'Zorggroep Noord' },
            { k: 'slug',            label: 'Slug (URL-naam)',   type: 'text',     ph: isRso ? 'rso-noord' : 'zorggroep-noord' },
            { k: 'admin_email',     label: isRso ? 'RSO-beheerder e-mail' : 'Admin e-mailadres', type: 'email',    ph: 'admin@zorggroep.nl' },
            { k: 'admin_password',  label: 'Beheerder wachtwoord',  type: 'password', ph: 'min. 12 tekens' },
            { k: 'admin_full_name', label: 'Beheerder naam',        type: 'text',     ph: 'Jan de Vries (optioneel)' },
          ].map(({ k, label, type, ph }) => (
            <label key={k} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>{label}</span>
              <input type={type} required={k !== 'admin_full_name'} value={form[k]} onChange={e => set(k, e.target.value)} placeholder={ph} style={inputStyle} />
            </label>
          ))}
          {isRso && <p style={{ fontSize: 12, color: 'var(--text3)', margin: 0 }}>De beheerder krijgt de rol <strong>RSO-beheerder</strong> en kan zelf organisaties + gebruikers toevoegen.</p>}
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

function DeleteTenantModal({ tenant, onClose, onDeleted }) {
  const [impact,  setImpact]  = useState(null)
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  useEffect(() => {
    getAdminTenantImpact(tenant.id).then(setImpact).catch(() => setImpact({}))
  }, [tenant.id])

  async function handleDelete() {
    setError(''); setLoading(true)
    try { await adminDeleteTenant(tenant.id, confirm); onDeleted(); onClose() }
    catch (err) { let m = 'Verwijderen mislukt'; try { m = JSON.parse(err.message)?.detail || m } catch {} setError(m) }
    finally { setLoading(false) }
  }

  const row = (label, val) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '4px 0' }}>
      <span style={{ color: 'var(--text3)' }}>{label}</span><strong>{val}</strong>
    </div>
  )
  const match = confirm.trim() === tenant.name

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', padding: '32px 36px', width: 480, maxWidth: '90vw' }}>
        <h3 style={{ fontSize: 17, fontWeight: 800, marginBottom: 4, color: '#dc2626' }}>Organisatie definitief verwijderen</h3>
        <p style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 18 }}>
          <strong>{tenant.name}</strong> en alle onderstaande gegevens worden permanent verwijderd. Dit kan niet ongedaan worden gemaakt.
        </p>
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 'var(--radius)', padding: '12px 16px', marginBottom: 18 }}>
          {!impact ? <span style={{ fontSize: 13, color: 'var(--text3)' }}>Impact laden…</span> : (
            <>
              {row('Gebruikers', impact.user_count ?? 0)}
              {row('Licenties', impact.license_count ?? 0)}
              {row('App-toewijzingen', impact.app_count ?? 0)}
              {row('Taken', impact.task_count ?? 0)}
              <div style={{ borderTop: '1px dashed #fecaca', margin: '6px 0' }} />
              {row('Scans (blijven bewaard, geanonimiseerd)', impact.scan_count ?? 0)}
            </>
          )}
        </div>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 5, marginBottom: 14 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>Typ ter bevestiging de organisatienaam: <code style={{ color: '#dc2626' }}>{tenant.name}</code></span>
          <input value={confirm} onChange={e => setConfirm(e.target.value)} placeholder={tenant.name}
            style={{ padding: '9px 13px', borderRadius: 'var(--radius)', border: '1.5px solid var(--border)', fontSize: 13, fontFamily: 'var(--font)', width: '100%', boxSizing: 'border-box' }} autoFocus />
        </label>
        <ErrBox msg={error} />
        <div style={{ display: 'flex', gap: 10 }}>
          <button type="button" onClick={onClose} style={{ flex: 1, ...btnGhost }}>Annuleren</button>
          <button type="button" onClick={handleDelete} disabled={!match || loading}
            style={{ flex: 2, padding: '9px 18px', background: match ? '#dc2626' : '#fca5a5', color: '#fff', border: 'none', borderRadius: 'var(--radius)', cursor: match ? 'pointer' : 'not-allowed', fontSize: 13, fontWeight: 700, fontFamily: 'var(--font)' }}>
            {loading ? 'Verwijderen…' : 'Definitief verwijderen'}
          </button>
        </div>
      </div>
    </div>
  )
}

function AssignAppModal({ tenant, applications, onClose, onAssigned }) {
  const [appId,   setAppId]   = useState('')
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  async function handleSubmit(e) {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      await assignAppToTenant(tenant.id, { application_id: appId, license_id: null })
      onAssigned(); onClose()
    } catch (err) {
      let m = 'Toewijzing mislukt'; try { m = JSON.parse(err.message)?.detail || m } catch {} setError(m)
    } finally { setLoading(false) }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', padding: '32px 36px', width: 420, maxWidth: '90vw' }}>
        <h3 style={{ fontSize: 16, fontWeight: 800, marginBottom: 20 }}>Applicatie toewijzen aan {tenant.name}</h3>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>Applicatie</span>
            <select required value={appId} onChange={e => setAppId(e.target.value)} style={inputStyle}>
              <option value="">— kies applicatie —</option>
              {applications.filter(a => PRODUCT_SLUGS.has(a.slug)).map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </label>
          <ErrBox msg={error} />
          <div style={{ display: 'flex', gap: 12 }}>
            <button type="button" onClick={onClose} style={{ flex: 1, ...btnGhost }}>Annuleren</button>
            <button type="submit" disabled={loading || !appId} style={{ flex: 2, ...btnPrimary }}>{loading ? 'Bezig…' : 'Toewijzen →'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function CreateLicenseModal({ tenants, onClose, onCreated }) {
  const [form,    setForm]    = useState({ tenant_id: '', name: '', valid_until: '', max_users: '', notes: '' })
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  async function handleSubmit(e) {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      const payload = {
        tenant_id:   form.tenant_id,
        name:        form.name,
        valid_until: form.valid_until || null,
        max_users:   form.max_users ? parseInt(form.max_users) : null,
        notes:       form.notes || null,
      }
      const r = await createAdminLicense(payload)
      onCreated(r); onClose()
    } catch (err) {
      let m = 'Aanmaken mislukt'; try { m = JSON.parse(err.message)?.detail || m } catch {} setError(m)
    } finally { setLoading(false) }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', padding: '32px 36px', width: 460, maxWidth: '90vw' }}>
        <h3 style={{ fontSize: 16, fontWeight: 800, marginBottom: 20 }}>Nieuwe licentie aanmaken</h3>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>Organisatie</span>
            <select required value={form.tenant_id} onChange={e => setForm(f => ({ ...f, tenant_id: e.target.value }))} style={inputStyle}>
              <option value="">— kies organisatie —</option>
              {tenants.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </label>
          {[
            { k: 'name',        label: 'Licentienaam',            type: 'text',   ph: 'Jaarlicentie 2026', req: true },
            { k: 'valid_until', label: 'Geldig tot (optioneel)',  type: 'date',   ph: '',                  req: false },
            { k: 'max_users',   label: 'Max. gebruikers (opt.)',  type: 'number', ph: 'onbeperkt',         req: false },
            { k: 'notes',       label: 'Notities (optioneel)',    type: 'text',   ph: '',                  req: false },
          ].map(({ k, label, type, ph, req }) => (
            <label key={k} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>{label}</span>
              <input type={type} required={req} value={form[k]} onChange={e => setForm(f => ({ ...f, [k]: e.target.value }))} placeholder={ph} style={inputStyle} />
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

// ═══════════════════════════════════════════════════════════════════════════════
// Tab: Organisations
// ═══════════════════════════════════════════════════════════════════════════════

// ── Admin Reset Password Modal ────────────────────────────────────────────────
function AdminResetPasswordModal({ user, onClose }) {
  const [password, setPassword] = useState('')
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')
  const [done,     setDone]     = useState(false)
  const overlayStyle2 = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }
  const inputStyle2 = { padding: '9px 13px', borderRadius: 'var(--radius)', border: '1.5px solid var(--border)', fontSize: 13, fontFamily: 'var(--font)', width: '100%', boxSizing: 'border-box' }

  async function handleSubmit(e) {
    e.preventDefault(); setError(''); setLoading(true)
    try { await adminResetUserPassword(user.id, password); setDone(true) }
    catch (err) { let m = 'Reset mislukt'; try { m = JSON.parse(err.message)?.detail || m } catch {} setError(m) }
    finally { setLoading(false) }
  }

  return (
    <div style={overlayStyle2}>
      <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', padding: '32px 36px', width: 420, maxWidth: '90vw' }}>
        {done ? (
          <>
            <div style={{ fontSize: 32, marginBottom: 12 }}>✅</div>
            <h3 style={{ fontSize: 16, fontWeight: 800, marginBottom: 8 }}>Wachtwoord ingesteld</h3>
            <p style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 20 }}>Het wachtwoord voor <strong>{user.email}</strong> is bijgewerkt.</p>
            <button onClick={onClose} style={{ ...btnGhost, width: '100%' }}>Sluiten</button>
          </>
        ) : (
          <>
            <h3 style={{ fontSize: 16, fontWeight: 800, marginBottom: 6 }}>Wachtwoord resetten</h3>
            <p style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 20 }}>Nieuw wachtwoord voor <strong>{user.email}</strong>.</p>
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <input type="password" required placeholder="Min. 12 tekens" value={password}
                onChange={e => setPassword(e.target.value)} style={inputStyle2} autoFocus />
              <ErrBox msg={error} />
              <div style={{ display: 'flex', gap: 10 }}>
                <button type="button" onClick={onClose} style={{ flex: 1, ...btnGhost }}>Annuleren</button>
                <button type="submit" disabled={loading} style={{ flex: 2, ...btnPrimary }}>{loading ? 'Resetten…' : 'Wachtwoord instellen'}</button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  )
}

// ── Admin Create User Modal ───────────────────────────────────────────────────
function AdminCreateUserModal({ tenant, onClose, onCreated }) {
  const [form,    setForm]    = useState({ email: '', password: '', full_name: '', role: 'ORG_USER' })
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')
  const overlay = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }
  const inp     = { padding: '9px 13px', borderRadius: 'var(--radius)', border: '1.5px solid var(--border)', fontSize: 13, fontFamily: 'var(--font)', width: '100%', boxSizing: 'border-box' }

  async function handleSubmit(e) {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      await adminCreateUser(tenant.id, form)
      onCreated(); onClose()
    } catch (err) { let m = 'Aanmaken mislukt'; try { m = JSON.parse(err.message)?.detail || m } catch {} setError(m) }
    finally { setLoading(false) }
  }

  return (
    <div style={overlay}>
      <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', padding: '32px 36px', width: 440, maxWidth: '90vw' }}>
        <h3 style={{ fontSize: 17, fontWeight: 800, marginBottom: 4 }}>Gebruiker toevoegen</h3>
        <p style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 22 }}>Nieuwe gebruiker voor <strong>{tenant.name}</strong></p>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {[
            { k: 'email',     label: 'E-mailadres', type: 'email',    ph: 'gebruiker@org.nl', req: true },
            { k: 'full_name', label: 'Naam',        type: 'text',     ph: 'Volledige naam',   req: false },
            { k: 'password',  label: 'Wachtwoord',  type: 'password', ph: 'Min. 8 tekens',    req: true },
          ].map(f => (
            <label key={f.k} style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>{f.label}</span>
              <input type={f.type} required={f.req} placeholder={f.ph} value={form[f.k]}
                onChange={e => setForm(p => ({ ...p, [f.k]: e.target.value }))} style={inp} />
            </label>
          ))}
          <label style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>Rol</span>
            <select value={form.role} onChange={e => setForm(p => ({ ...p, role: e.target.value }))} style={inp}>
              <option value="ORG_USER">ORG_USER — gebruiker</option>
              <option value="ORG_ADMIN">ORG_ADMIN — beheerder</option>
            </select>
          </label>
          <ErrBox msg={error} />
          <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
            <button type="button" onClick={onClose} style={{ flex: 1, ...btnGhost }}>Annuleren</button>
            <button type="submit" disabled={loading} style={{ flex: 2, ...btnPrimary }}>{loading ? 'Aanmaken…' : 'Gebruiker aanmaken'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Admin Edit User Modal ─────────────────────────────────────────────────────
function AdminEditUserModal({ user, onClose, onSaved }) {
  const [form,    setForm]    = useState({ full_name: user.full_name || '', role: user.role })
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')
  const overlay = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }
  const inp     = { padding: '9px 13px', borderRadius: 'var(--radius)', border: '1.5px solid var(--border)', fontSize: 13, fontFamily: 'var(--font)', width: '100%', boxSizing: 'border-box' }

  async function handleSubmit(e) {
    e.preventDefault(); setError(''); setLoading(true)
    try { await adminUpdateUser(user.id, form); onSaved(); onClose() }
    catch (err) { let m = 'Opslaan mislukt'; try { m = JSON.parse(err.message)?.detail || m } catch {} setError(m) }
    finally { setLoading(false) }
  }

  return (
    <div style={overlay}>
      <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', padding: '32px 36px', width: 420, maxWidth: '90vw' }}>
        <h3 style={{ fontSize: 17, fontWeight: 800, marginBottom: 4 }}>Gebruiker bewerken</h3>
        <p style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 22 }}>{user.email}</p>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>Naam</span>
            <input type="text" placeholder="Volledige naam" value={form.full_name}
              onChange={e => setForm(p => ({ ...p, full_name: e.target.value }))} style={inp} />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>Rol</span>
            <select value={form.role} onChange={e => setForm(p => ({ ...p, role: e.target.value }))} style={inp}>
              <option value="ORG_USER">ORG_USER — gebruiker</option>
              <option value="ORG_ADMIN">ORG_ADMIN — beheerder</option>
            </select>
          </label>
          <ErrBox msg={error} />
          <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
            <button type="button" onClick={onClose} style={{ flex: 1, ...btnGhost }}>Annuleren</button>
            <button type="submit" disabled={loading} style={{ flex: 2, ...btnPrimary }}>{loading ? 'Opslaan…' : 'Opslaan'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Look & feel editor (per tenant) ─────────────────────────────────────────────
function BrandingEditor({ tenant }) {
  const [form,    setForm]    = useState({ preset: 'rhadix', primary_color: '#1A2847', accent_color: '#1A2847', wordmark: '' })
  const [hasLogo, setHasLogo] = useState(false)
  const [logoVer, setLogoVer] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving,  setSaving]  = useState(false)
  const [msg,     setMsg]     = useState('')
  const [error,   setError]   = useState('')

  async function load() {
    setLoading(true)
    try {
      const b = await getTenantBranding(tenant.id)
      setForm({
        preset: b.preset || (b.primary_color ? 'custom' : 'rhadix'),
        primary_color: b.primary_color || '#1A2847',
        accent_color:  b.accent_color  || b.primary_color || '#1A2847',
        wordmark: b.wordmark || '',
      })
      setHasLogo(!!b.has_logo); setLogoVer(b.logo_version)
    } catch (e) { setError(parseErrLocal(e)) } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [tenant.id])

  function pickPreset(p) {
    const preset = BRAND_PRESETS[p]
    if (p === 'custom') { setForm(f => ({ ...f, preset: p })); return }
    setForm(f => ({ ...f, preset: p, primary_color: preset.primary_color, accent_color: preset.accent_color }))
  }

  async function save() {
    setSaving(true); setError(''); setMsg('')
    try {
      await putTenantBranding(tenant.id, { preset: form.preset, primary_color: form.primary_color, accent_color: form.accent_color, wordmark: form.wordmark || null })
      setMsg('Opgeslagen. Gebruikers zien de nieuwe look bij hun volgende login.')
    } catch (e) { setError(parseErrLocal(e)) } finally { setSaving(false) }
  }
  async function resetBranding() {
    if (!window.confirm('Look-and-feel wissen? Deze organisatie erft dan weer van de RSO/Rhadix.')) return
    setSaving(true); setError(''); setMsg('')
    try { await deleteTenantBranding(tenant.id); await load(); setMsg('Gewist — erft weer over.') }
    catch (e) { setError(parseErrLocal(e)) } finally { setSaving(false) }
  }
  async function onLogo(e) {
    const file = e.target.files?.[0]; if (!file) return
    setSaving(true); setError(''); setMsg('')
    try { const r = await uploadTenantLogo(tenant.id, file); setHasLogo(true); setLogoVer(r.logo_version); setMsg('Logo geüpload.') }
    catch (err) { setError(parseErrLocal(err)) } finally { setSaving(false); e.target.value = '' }
  }
  async function removeLogo() {
    setSaving(true); setError('')
    try { await deleteTenantLogo(tenant.id); setHasLogo(false); setLogoVer(null); setMsg('Logo verwijderd.') }
    catch (err) { setError(parseErrLocal(err)) } finally { setSaving(false) }
  }

  if (loading) return <p style={{ fontSize: 13, color: 'var(--text3)' }}>Look & feel laden…</p>

  const lbl = { fontSize: 12, fontWeight: 600, color: 'var(--text2)', marginBottom: 4 }
  return (
    <div>
      <ErrBox msg={error} />
      {msg && <div style={{ padding: '8px 12px', background: '#ecfdf5', border: '1px solid #a7f3d0', borderRadius: 'var(--radius)', fontSize: 12, color: '#065f46', marginBottom: 12 }}>{msg}</div>}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, alignItems: 'flex-end' }}>
        <div>
          <div style={lbl}>Preset</div>
          <select value={form.preset} onChange={e => pickPreset(e.target.value)} style={{ ...inputStyle, width: 200 }}>
            {Object.entries(BRAND_PRESETS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
        </div>
        <div>
          <div style={lbl}>Primaire kleur</div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input type="color" value={form.primary_color} onChange={e => setForm(f => ({ ...f, preset: 'custom', primary_color: e.target.value }))} style={{ width: 42, height: 34, border: '1px solid var(--border)', borderRadius: 6, background: 'none' }} />
            <input value={form.primary_color} onChange={e => setForm(f => ({ ...f, preset: 'custom', primary_color: e.target.value }))} style={{ ...inputStyle, width: 100 }} />
          </div>
        </div>
        <div>
          <div style={lbl}>Accent (navbalk)</div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input type="color" value={form.accent_color} onChange={e => setForm(f => ({ ...f, preset: 'custom', accent_color: e.target.value }))} style={{ width: 42, height: 34, border: '1px solid var(--border)', borderRadius: 6, background: 'none' }} />
            <input value={form.accent_color} onChange={e => setForm(f => ({ ...f, preset: 'custom', accent_color: e.target.value }))} style={{ ...inputStyle, width: 100 }} />
          </div>
        </div>
        <div>
          <div style={lbl}>Wordmerk (balk)</div>
          <input value={form.wordmark} onChange={e => setForm(f => ({ ...f, wordmark: e.target.value }))} placeholder="bv. KIK-V" style={{ ...inputStyle, width: 160 }} />
        </div>
      </div>

      {/* Preview + logo */}
      <div style={{ display: 'flex', gap: 20, alignItems: 'center', marginTop: 16, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: form.accent_color, borderRadius: 8, padding: '8px 14px' }}>
          {hasLogo && <img src={tenantLogoUrl(tenant.id, logoVer)} alt="logo" style={{ height: 26 }} />}
          {form.wordmark && <span style={{ color: '#fff', fontWeight: 800, fontSize: 15 }}>{form.wordmark}</span>}
          <button style={{ background: form.primary_color, color: '#fff', border: 'none', borderRadius: 6, padding: '5px 12px', fontSize: 12, fontWeight: 700 }}>Voorbeeld</button>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <label style={{ ...btnGhost, cursor: 'pointer' }}>
            {hasLogo ? 'Logo vervangen' : 'Logo uploaden'}
            <input type="file" accept="image/png,image/jpeg,image/svg+xml,image/webp,image/gif" onChange={onLogo} style={{ display: 'none' }} />
          </label>
          {hasLogo && <button onClick={removeLogo} style={{ ...btnGhost, color: '#dc2626', borderColor: '#fecaca' }}>Logo weg</button>}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
        <button onClick={save} disabled={saving} style={btnPrimary}>{saving ? 'Bezig…' : '✓ Look & feel opslaan'}</button>
        <button onClick={resetBranding} disabled={saving} style={btnGhost}>Wissen (erven)</button>
      </div>
      <p style={{ fontSize: 11, color: 'var(--text3)', marginTop: 8 }}>Logo max. 512 KB (PNG/JPG/SVG/WebP). Wijzigingen worden geborgd; gebruikers zien ze bij hun volgende login.</p>
    </div>
  )
}
function parseErrLocal(err) { let m = err.message; try { m = JSON.parse(err.message)?.detail || m } catch {} return m }

function TabOrganisations({ stats, tenants, applications, onReload }) {
  const [showCreate,     setShowCreate]     = useState(false)
  const [assignTenant,   setAssignTenant]   = useState(null)
  const [expandedTid,    setExpandedTid]    = useState(null)
  const [tenantApps,     setTenantApps]     = useState({})
  const [tenantLicenses, setTenantLicenses] = useState({})
  const [tenantUsers,    setTenantUsers]    = useState({})
  const [resetUser,      setResetUser]      = useState(null)
  const [createUserTenant, setCreateUserTenant] = useState(null)
  const [editUser,         setEditUser]         = useState(null)
  const [deleteTenant,     setDeleteTenant]     = useState(null)

  async function handleToggleTenant(t) {
    const next = !t.is_active
    if (!window.confirm(next ? `Organisatie "${t.name}" activeren?` : `Organisatie "${t.name}" deactiveren? Alle gebruikers worden op inactief gezet.`)) return
    try { await adminToggleTenantActive(t.id, next); onReload() }
    catch (err) { let m = err.message; try { m = JSON.parse(err.message)?.detail || m } catch {} alert('Mislukt: ' + m) }
  }

  async function loadTenantDetails(tid) {
    if (expandedTid === tid) { setExpandedTid(null); return }
    setExpandedTid(tid)
    try {
      const [apps, lics, users] = await Promise.all([
        getAdminTenantApps(tid), getAdminTenantLicenses(tid), getAdminTenantUsers(tid),
      ])
      setTenantApps(p => ({ ...p, [tid]: apps }))
      setTenantLicenses(p => ({ ...p, [tid]: lics }))
      setTenantUsers(p => ({ ...p, [tid]: users }))
    } catch {}
  }

  async function handleToggleUser(tid, userId) {
    try {
      const updated = await adminToggleUserActive(userId)
      setTenantUsers(p => ({ ...p, [tid]: p[tid].map(u => u.id === userId ? { ...u, is_active: updated.is_active } : u) }))
    } catch (err) { alert('Fout: ' + err.message) }
  }

  async function handleDeleteUser(tid, userId) {
    if (!window.confirm('Gebruiker definitief verwijderen?')) return
    try {
      await adminDeleteUser(userId)
      setTenantUsers(p => ({ ...p, [tid]: p[tid].filter(u => u.id !== userId) }))
    } catch (err) { alert('Verwijderen mislukt: ' + err.message) }
  }

  async function handleRevoke(tenantId, appId) {
    if (!window.confirm('Weet u zeker dat u deze applicatietoewijzing wilt verwijderen?')) return
    try {
      await revokeAppFromTenant(tenantId, appId)
      const apps = await getAdminTenantApps(tenantId)
      setTenantApps(p => ({ ...p, [tenantId]: apps }))
    } catch (err) { alert('Intrekken mislukt: ' + err.message) }
  }

  return (
    <>
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 16, marginBottom: 32 }}>
          <StatCard label="Organisaties"      value={stats.active_tenants} color="var(--blue)" />
          <StatCard label="Gebruikers"        value={stats.total_users}    color="#7c3aed" />
          <StatCard label="Scans totaal"      value={stats.total_scans}    color="#059669" />
          <StatCard label="Gem. Rhadix Index" value={stats.avg_score ? `${stats.avg_score}%` : '—'} color="#d97706" />
        </div>
      )}

      <div style={card}>
        <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Organisaties</span>
          <div style={{ display: 'flex', gap: 10 }}>
            <button onClick={onReload} style={{ fontSize: 13, color: 'var(--blue)', background: 'none', border: 'none', cursor: 'pointer' }}>↻ Vernieuwen</button>
            <button onClick={() => setShowCreate(true)} style={btnPrimary}>+ Organisatie toevoegen</button>
          </div>
        </div>

        {tenants.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text3)', fontSize: 14 }}>Geen organisaties gevonden.</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>{['Naam', 'Slug', 'Gebruikers', 'Scans', 'Status', 'Aangemaakt', ''].map(h => <th key={h} style={thStyle}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {tenants.flatMap((t, i) => {
                const rows = [(
                  <tr key={t.id}>
                    <td style={{ padding: '12px 16px', fontWeight: 600, fontSize: 14, borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? '#fff' : 'var(--bg)' }}>{t.name}</td>
                    <td style={{ padding: '12px 16px', fontSize: 13, color: 'var(--text3)', fontFamily: 'monospace', borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? '#fff' : 'var(--bg)' }}>{t.slug}</td>
                    <td style={{ padding: '12px 16px', fontSize: 13, color: 'var(--text2)', borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? '#fff' : 'var(--bg)' }}>{t.user_count}</td>
                    <td style={{ padding: '12px 16px', fontSize: 13, color: 'var(--text2)', borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? '#fff' : 'var(--bg)' }}>{t.scan_count}</td>
                    <td style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? '#fff' : 'var(--bg)' }}><Badge active={t.is_active} /></td>
                    <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text3)', borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? '#fff' : 'var(--bg)' }}>{new Date(t.created_at).toLocaleDateString('nl-NL')}</td>
                    <td style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? '#fff' : 'var(--bg)' }}>
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        <button onClick={() => loadTenantDetails(t.id)} style={btnGhost}>{expandedTid === t.id ? '▲' : '▼'} Detail</button>
                        <button onClick={() => setAssignTenant(t)} style={btnGhost}>+ App</button>
                        <button onClick={() => handleToggleTenant(t)} style={{ ...btnGhost, color: t.is_active ? '#d97706' : '#059669', borderColor: t.is_active ? '#fcd34d' : '#6ee7b7' }}>{t.is_active ? 'Deactiveren' : 'Activeren'}</button>
                        <button onClick={() => setDeleteTenant(t)} style={{ padding: '7px 14px', background: 'none', color: '#dc2626', border: '1.5px solid #fecaca', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 12, fontWeight: 600, fontFamily: 'var(--font)' }}>🗑️ Verwijderen</button>
                      </div>
                    </td>
                  </tr>
                )]
                if (expandedTid === t.id) {
                  rows.push(
                    <tr key={`${t.id}-detail`}>
                      <td colSpan={7} style={{ padding: '20px 24px', background: '#f8fafc', borderBottom: '1px solid var(--border)' }}>

                        {/* Apps */}
                        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 10 }}>Toegewezen applicaties</div>
                        {(tenantApps[t.id] || []).length === 0 ? (
                          <p style={{ fontSize: 13, color: 'var(--text3)', margin: '0 0 16px' }}>Geen applicaties toegewezen.</p>
                        ) : (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
                            {(tenantApps[t.id] || []).map(ta => (
                              <div key={ta.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: '#e0f2fe', borderRadius: 20, padding: '4px 12px 4px 14px', fontSize: 13, fontWeight: 600, color: '#0369a1' }}>
                                {ta.application_name}
                                <button onClick={() => handleRevoke(t.id, ta.application_id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', fontSize: 16, lineHeight: 1, padding: 0 }} title="Intrekken">×</button>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Licenses */}
                        {(tenantLicenses[t.id] || []).length > 0 && (
                          <>
                            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.08em', margin: '4px 0 8px' }}>Licenties</div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
                              {(tenantLicenses[t.id] || []).map(l => (
                                <span key={l.id} style={{ fontSize: 12, fontWeight: 600, background: l.is_active ? '#dcfce7' : '#fee2e2', color: l.is_active ? '#166534' : '#991b1b', borderRadius: 20, padding: '3px 12px' }}>
                                  {l.name}{l.valid_until ? ` · t/m ${new Date(l.valid_until).toLocaleDateString('nl-NL')}` : ' · onbeperkt'}
                                </span>
                              ))}
                            </div>
                          </>
                        )}

                        {/* Users */}
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '4px 0 10px' }}>
                          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Gebruikers</div>
                          <button onClick={() => setCreateUserTenant(t)} style={{ ...btnPrimary, padding: '5px 12px', fontSize: 11 }}>+ Gebruiker</button>
                        </div>
                        {(tenantUsers[t.id] || []).length === 0 ? (
                          <p style={{ fontSize: 13, color: 'var(--text3)', margin: 0 }}>Geen gebruikers.</p>
                        ) : (
                          <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 'var(--radius)', overflow: 'hidden', border: '1px solid var(--border)' }}>
                            <thead>
                              <tr>{['Naam', 'E-mail', 'Rol', 'Status', 'Acties'].map(h => <th key={h} style={{ ...thStyle, fontSize: 10, padding: '7px 12px' }}>{h}</th>)}</tr>
                            </thead>
                            <tbody>
                              {(tenantUsers[t.id] || []).map((u, ui) => (
                                <tr key={u.id} style={{ background: ui % 2 === 0 ? '#fff' : '#f8fafc' }}>
                                  <td style={{ padding: '9px 12px', fontSize: 13, fontWeight: 600, borderBottom: '1px solid var(--border)' }}>{u.full_name || '—'}</td>
                                  <td style={{ padding: '9px 12px', fontSize: 12, color: 'var(--text3)', borderBottom: '1px solid var(--border)' }}>{u.email}</td>
                                  <td style={{ padding: '9px 12px', fontSize: 12, color: 'var(--text3)', borderBottom: '1px solid var(--border)' }}>{u.role}</td>
                                  <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--border)' }}>
                                    <span style={{ display: 'inline-flex', padding: '2px 8px', borderRadius: 20, fontSize: 11, fontWeight: 600, background: u.is_active ? '#dcfce7' : '#fee2e2', color: u.is_active ? '#166534' : '#991b1b' }}>
                                      {u.is_active ? 'Actief' : 'Inactief'}
                                    </span>
                                  </td>
                                  <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--border)' }}>
                                    <div style={{ display: 'flex', gap: 5 }}>
                                      <button onClick={() => setEditUser(u)} style={{ ...btnGhost, padding: '4px 10px', fontSize: 11 }}>✏️</button>
                                      <button onClick={() => setResetUser(u)} style={{ ...btnGhost, padding: '4px 10px', fontSize: 11 }}>🔑</button>
                                      <button onClick={() => handleToggleUser(t.id, u.id)} style={{ ...(u.is_active ? { padding: '4px 10px', background: 'none', color: '#dc2626', border: '1.5px solid #fecaca', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 11, fontWeight: 600, fontFamily: 'var(--font)' } : { ...btnGhost, padding: '4px 10px', fontSize: 11 }) }}>
                                        {u.is_active ? 'Deact.' : 'Activ.'}
                                      </button>
                                      <button onClick={() => handleDeleteUser(t.id, u.id)} style={{ padding: '4px 8px', background: 'none', color: '#dc2626', border: '1.5px solid #fecaca', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 11, fontWeight: 600, fontFamily: 'var(--font)' }}>🗑️</button>
                                    </div>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}

                        {/* Look & feel */}
                        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.08em', margin: '22px 0 12px' }}>Look &amp; feel</div>
                        <BrandingEditor tenant={t} />
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

      {resetUser && <AdminResetPasswordModal user={resetUser} onClose={() => setResetUser(null)} />}
      {deleteTenant && <DeleteTenantModal tenant={deleteTenant} onClose={() => setDeleteTenant(null)} onDeleted={onReload} />}
      {showCreate && <CreateTenantModal tenants={tenants} onClose={() => setShowCreate(false)} onCreated={onReload} />}
      {createUserTenant && (
        <AdminCreateUserModal
          tenant={createUserTenant}
          onClose={() => setCreateUserTenant(null)}
          onCreated={async () => {
            const users = await getAdminTenantUsers(createUserTenant.id)
            setTenantUsers(p => ({ ...p, [createUserTenant.id]: users }))
            onReload()
          }}
        />
      )}
      {editUser && (
        <AdminEditUserModal
          user={editUser}
          onClose={() => setEditUser(null)}
          onSaved={async () => {
            const tid = editUser.tenant_id || expandedTid
            if (tid) {
              const users = await getAdminTenantUsers(tid)
              setTenantUsers(p => ({ ...p, [tid]: users }))
            }
          }}
        />
      )}
      {assignTenant && (
        <AssignAppModal
          tenant={assignTenant}
          applications={applications}
          onClose={() => setAssignTenant(null)}
          onAssigned={async () => {
            if (expandedTid === assignTenant.id) {
              const apps = await getAdminTenantApps(assignTenant.id)
              setTenantApps(p => ({ ...p, [assignTenant.id]: apps }))
            }
          }}
        />
      )}
    </>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Tab: Licenses
// ═══════════════════════════════════════════════════════════════════════════════

function EditLicenseModal({ license, onClose, onSaved }) {
  const [form, setForm] = useState({
    name: license.name || '',
    valid_until: license.valid_until ? license.valid_until.slice(0, 10) : '',
    max_users: license.max_users != null ? String(license.max_users) : '',
    notes: license.notes || '',
    is_active: license.is_active,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  async function submit(e) {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      await updateAdminLicense(license.id, {
        name: form.name,
        valid_until: form.valid_until || null,
        max_users: form.max_users ? parseInt(form.max_users) : null,
        notes: form.notes || null,
        is_active: form.is_active,
      })
      onSaved(); onClose()
    } catch (err) { let m = 'Opslaan mislukt'; try { m = JSON.parse(err.message)?.detail || m } catch {} setError(m) }
    finally { setLoading(false) }
  }
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', padding: '32px 36px', width: 460, maxWidth: '90vw' }}>
        <h3 style={{ fontSize: 16, fontWeight: 800, marginBottom: 20 }}>Licentie bewerken</h3>
        <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {[
            { k: 'name', label: 'Licentienaam', type: 'text' },
            { k: 'valid_until', label: 'Geldig tot (leeg = onbeperkt)', type: 'date' },
            { k: 'max_users', label: 'Max. gebruikers (leeg = onbeperkt)', type: 'number' },
            { k: 'notes', label: 'Notities', type: 'text' },
          ].map(({ k, label, type }) => (
            <label key={k} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>{label}</span>
              <input type={type} value={form[k]} onChange={e => setForm(f => ({ ...f, [k]: e.target.value }))} style={inputStyle} />
            </label>
          ))}
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>Status</span>
            <select value={String(form.is_active)} onChange={e => setForm(f => ({ ...f, is_active: e.target.value === 'true' }))} style={inputStyle}>
              <option value="true">Actief</option><option value="false">Inactief</option>
            </select>
          </label>
          <ErrBox msg={error} />
          <div style={{ display: 'flex', gap: 12 }}>
            <button type="button" onClick={onClose} style={{ flex: 1, ...btnGhost }}>Annuleren</button>
            <button type="submit" disabled={loading} style={{ flex: 2, ...btnPrimary }}>{loading ? 'Opslaan…' : 'Opslaan'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function TabLicenses({ tenants }) {
  const [licenses,   setLicenses]   = useState([])
  const [loading,    setLoading]    = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [editLicense, setEditLicense] = useState(null)
  const [error,      setError]      = useState('')

  async function load() {
    setLoading(true)
    try { setLicenses(await getAdminLicenses()) } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  async function handleDelete(l) {
    if (!window.confirm(`Licentie "${l.name}" verwijderen?`)) return
    try { await deleteAdminLicense(l.id); load() }
    catch (err) { let m = err.message; try { m = JSON.parse(err.message)?.detail || m } catch {} alert('Verwijderen mislukt: ' + m) }
  }

  const tenantMap = Object.fromEntries(tenants.map(t => [t.id, t.name]))

  return (
    <>
      <div style={card}>
        <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Licenties</span>
          <div style={{ display: 'flex', gap: 10 }}>
            <button onClick={load} style={{ fontSize: 13, color: 'var(--blue)', background: 'none', border: 'none', cursor: 'pointer' }}>↻ Vernieuwen</button>
            <button onClick={() => setShowCreate(true)} style={btnPrimary}>+ Licentie aanmaken</button>
          </div>
        </div>
        <ErrBox msg={error} />
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text3)', fontSize: 14 }}>Laden…</div>
        ) : licenses.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text3)', fontSize: 14 }}>Geen licenties gevonden.</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>{['Naam', 'Organisatie', 'Geldig tot', 'Max. gebruikers', 'Applicaties', 'Status', 'Aangemaakt', ''].map(h => <th key={h} style={thStyle}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {licenses.map((l, i) => (
                <tr key={l.id} style={{ background: i % 2 === 0 ? '#fff' : 'var(--bg)' }}>
                  <td style={{ padding: '12px 16px', fontWeight: 600, fontSize: 14, borderBottom: '1px solid var(--border)' }}>{l.name}</td>
                  <td style={{ padding: '12px 16px', fontSize: 13, borderBottom: '1px solid var(--border)' }}>{tenantMap[l.tenant_id] ?? l.tenant_id}</td>
                  <td style={{ padding: '12px 16px', fontSize: 13, color: 'var(--text3)', borderBottom: '1px solid var(--border)' }}>{l.valid_until ? new Date(l.valid_until).toLocaleDateString('nl-NL') : 'Onbeperkt'}</td>
                  <td style={{ padding: '12px 16px', fontSize: 13, color: 'var(--text2)', borderBottom: '1px solid var(--border)' }}>{l.max_users ?? 'Onbeperkt'}</td>
                  <td style={{ padding: '12px 16px', fontSize: 13, color: 'var(--text2)', borderBottom: '1px solid var(--border)' }}>{(l.app_slugs || []).join(', ') || '—'}</td>
                  <td style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)' }}><Badge active={l.is_active} /></td>
                  <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text3)', borderBottom: '1px solid var(--border)' }}>{new Date(l.created_at).toLocaleDateString('nl-NL')}</td>
                  <td style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button onClick={() => setEditLicense(l)} style={btnGhost}>Bewerken</button>
                      <button onClick={() => handleDelete(l)} style={{ padding: '7px 14px', background: 'none', color: '#dc2626', border: '1.5px solid #fecaca', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 12, fontWeight: 600, fontFamily: 'var(--font)' }}>🗑️</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {showCreate && <CreateLicenseModal tenants={tenants} onClose={() => setShowCreate(false)} onCreated={load} />}
      {editLicense && <EditLicenseModal license={editLicense} onClose={() => setEditLicense(null)} onSaved={load} />}
    </>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Tab: Applications
// ═══════════════════════════════════════════════════════════════════════════════

function TabApplications({ applications, onReload }) {
  const [editing, setEditing] = useState(null)
  const [form,    setForm]    = useState({})
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  function startEdit(app) {
    setEditing(app.id)
    setForm({ name: app.name, description: app.description || '', is_active: app.is_active, sort_order: String(app.sort_order) })
    setError('')
  }

  async function saveEdit(appId) {
    setLoading(true); setError('')
    try {
      await updateAdminApplication(appId, { ...form, sort_order: parseInt(form.sort_order) })
      onReload(); setEditing(null)
    } catch (err) {
      let m = 'Opslaan mislukt'; try { m = JSON.parse(err.message)?.detail || m } catch {} setError(m)
    } finally { setLoading(false) }
  }

  return (
    <div style={card}>
      <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontWeight: 700, fontSize: 15 }}>Applicaties / modules</span>
        <button onClick={onReload} style={{ fontSize: 13, color: 'var(--blue)', background: 'none', border: 'none', cursor: 'pointer' }}>↻ Vernieuwen</button>
      </div>
      <ErrBox msg={error} />
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>{['Naam', 'Slug', 'Omschrijving', 'Volgorde', 'Status', ''].map(h => <th key={h} style={thStyle}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {applications.map((app, i) => editing === app.id ? (
            <tr key={app.id} style={{ background: '#f0f9ff' }}>
              <td style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)' }}><input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} style={{ ...inputStyle, width: 160 }} /></td>
              <td style={{ padding: '10px 16px', fontSize: 12, color: 'var(--text3)', fontFamily: 'monospace', borderBottom: '1px solid var(--border)' }}>{app.slug}</td>
              <td style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)' }}><input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} style={inputStyle} /></td>
              <td style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)' }}><input type="number" value={form.sort_order} onChange={e => setForm(f => ({ ...f, sort_order: e.target.value }))} style={{ ...inputStyle, width: 60 }} /></td>
              <td style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)' }}>
                <select value={String(form.is_active)} onChange={e => setForm(f => ({ ...f, is_active: e.target.value === 'true' }))} style={{ ...inputStyle, width: 100 }}>
                  <option value="true">Actief</option><option value="false">Inactief</option>
                </select>
              </td>
              <td style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button onClick={() => saveEdit(app.id)} disabled={loading} style={btnPrimary}>{loading ? '…' : '✓ Opslaan'}</button>
                  <button onClick={() => setEditing(null)} style={btnGhost}>✕</button>
                </div>
              </td>
            </tr>
          ) : (
            <tr key={app.id} style={{ background: i % 2 === 0 ? '#fff' : 'var(--bg)' }}>
              <td style={{ padding: '12px 16px', fontWeight: 600, fontSize: 14, borderBottom: '1px solid var(--border)' }}>{app.name}</td>
              <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text3)', fontFamily: 'monospace', borderBottom: '1px solid var(--border)' }}>{app.slug}</td>
              <td style={{ padding: '12px 16px', fontSize: 13, color: 'var(--text2)', borderBottom: '1px solid var(--border)' }}>{app.description || '—'}</td>
              <td style={{ padding: '12px 16px', fontSize: 13, borderBottom: '1px solid var(--border)' }}>{app.sort_order}</td>
              <td style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)' }}><Badge active={app.is_active} /></td>
              <td style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)' }}><button onClick={() => startEdit(app)} style={btnGhost}>Bewerken</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Main dashboard
// ═══════════════════════════════════════════════════════════════════════════════

const TABS = ['Organisaties', 'Licenties', 'Applicaties']

export default function AdminDashboard({ onBack }) {
  const [activeTab,    setActiveTab]    = useState('Organisaties')
  const [stats,        setStats]        = useState(null)
  const [tenants,      setTenants]      = useState([])
  const [applications, setApplications] = useState([])
  const [loading,      setLoading]      = useState(true)
  const [error,        setError]        = useState('')

  async function load() {
    setLoading(true); setError('')
    try {
      const [s, t, a] = await Promise.all([getAdminStats(), getAdminTenants(), getAdminApplications()])
      setStats(s); setTenants(t); setApplications(a)
    } catch (err) { setError('Kon gegevens niet laden: ' + err.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <Nav right={<NavBack onClick={onBack} />} />

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '40px 32px' }}>
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--blue)', letterSpacing: '.1em', textTransform: 'uppercase', marginBottom: 6 }}>Rhadix Admin</div>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em' }}>Platform overzicht</h1>
        </div>

        {error && <ErrBox msg={error} />}

        {/* Tab bar */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 28, borderBottom: '2px solid var(--border)' }}>
          {TABS.map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)} style={{
              padding: '10px 20px', background: 'none', border: 'none', cursor: 'pointer',
              fontSize: 14, fontWeight: 700, fontFamily: 'var(--font)',
              color: activeTab === tab ? 'var(--blue)' : 'var(--text3)',
              borderBottom: activeTab === tab ? '2px solid var(--blue)' : '2px solid transparent',
              marginBottom: -2,
            }}>
              {tab}
            </button>
          ))}
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text3)' }}>Laden…</div>
        ) : (
          <>
            {activeTab === 'Organisaties' && <TabOrganisations stats={stats} tenants={tenants} applications={applications} onReload={load} />}
            {activeTab === 'Licenties'    && <TabLicenses tenants={tenants} />}
            {activeTab === 'Applicaties'  && <TabApplications applications={applications} onReload={load} />}
          </>
        )}
      </div>
    </div>
  )
}
