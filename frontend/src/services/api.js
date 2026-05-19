const BASE = '/api'

// ---------------------------------------------------------------------------
// Auth token store — set by useAuth hook after login
// ---------------------------------------------------------------------------
let _token = null

export function setAuthToken(token) { _token = token }
export function getAuthToken()      { return _token   }
export function clearAuthToken()    { _token = null   }

function authHeaders(extra = {}) {
  return _token
    ? { Authorization: `Bearer ${_token}`, ...extra }
    : { ...extra }
}

async function apiFetch(url, options = {}) {
  const { headers = {}, ...rest } = options
  const res = await fetch(url, {
    ...rest,
    headers: { ...authHeaders(), ...headers },
  })
  if (res.status === 401) {
    // Token expired or invalid — clear it so the auth guard redirects to login
    clearAuthToken()
    window.dispatchEvent(new CustomEvent('rhadix:unauthorized'))
  }
  return res
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export async function login(email, password) {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()   // { access_token, token_type }
}

export async function getMe() {
  const res = await apiFetch(`${BASE}/auth/me`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

export async function uploadFiles(files, label = '', standard = 'kikv', maxAgeDays = 30) {
  const form = new FormData()
  files.forEach(f => form.append('files', f))
  if (label) form.append('label', label)
  form.append('standard', standard)
  form.append('max_age_days', String(maxAgeDays))
  const res = await apiFetch(`${BASE}/validate/upload`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ---------------------------------------------------------------------------
// History
// ---------------------------------------------------------------------------

export async function getHistory(skip = 0, limit = 50) {
  const res = await apiFetch(`${BASE}/history/?skip=${skip}&limit=${limit}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getRun(id) {
  const res = await apiFetch(`${BASE}/history/${id}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getStats() {
  const res = await apiFetch(`${BASE}/history/stats/summary`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------

export function exportUrl(runId, format) {
  // Append token as query param for direct browser download links
  const base = `${BASE}/export/${runId}/${format}`
  return _token ? `${base}?token=${_token}` : base
}

/**
 * Genereert een Rhadix Actieplan PDF en triggert een browser-download.
 */
export async function exportActieplan(items, runId = null, organisation = null) {
  const res = await apiFetch(`${BASE}/export/actieplan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items, run_id: runId, organisation }),
  })
  if (!res.ok) throw new Error(await res.text())
  const blob = await res.blob()
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = `Rhadix_Actieplan_${new Date().toISOString().slice(0, 10)}.pdf`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// ---------------------------------------------------------------------------
// Reference
// ---------------------------------------------------------------------------

export async function getRules() {
  const res = await apiFetch(`${BASE}/reference/rules`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ---------------------------------------------------------------------------
// Reports (JSON)
// ---------------------------------------------------------------------------

export async function getBeschikbaarheidsRapport(runId, organizationName = 'Zorginstelling', systems = '') {
  const params = new URLSearchParams({ organization_name: organizationName })
  if (systems) params.set('systems', systems)
  const res = await apiFetch(`${BASE}/reports/${runId}/beschikbaarheid?${params}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function exportBeschikbaarheidsRapportPdf(runId, organizationName = 'Zorginstelling', systems = '') {
  const params = new URLSearchParams({ organization_name: organizationName })
  if (systems) params.set('systems', systems)
  const res = await apiFetch(`${BASE}/reports/${runId}/beschikbaarheid/pdf?${params}`)
  if (!res.ok) throw new Error(await res.text())
  const blob = await res.blob()
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = `Rhadix_Beschikbaarheidsrapport_${new Date().toISOString().slice(0, 10)}.pdf`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export async function getKikvReadinessRapport(runId, organizationName = 'Zorginstelling', systems = '') {
  const params = new URLSearchParams({ organization_name: organizationName })
  if (systems) params.set('systems', systems)
  const res = await apiFetch(`${BASE}/reports/${runId}/kikv_readiness?${params}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getManagementRapport(runId, organizationName = 'Zorginstelling', systems = '') {
  const params = new URLSearchParams({ organization_name: organizationName })
  if (systems) params.set('systems', systems)
  const res = await apiFetch(`${BASE}/reports/${runId}/management?${params}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function exportManagementRapportPdf(runId, organizationName = 'Zorginstelling', systems = '') {
  const params = new URLSearchParams({ organization_name: organizationName })
  if (systems) params.set('systems', systems)
  const res = await apiFetch(`${BASE}/reports/${runId}/management/pdf?${params}`)
  if (!res.ok) throw new Error(await res.text())
  const blob = await res.blob()
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = `Rhadix_Managementrapport_${new Date().toISOString().slice(0, 10)}.pdf`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export async function exportKikvReadinessRapportPdf(runId, organizationName = 'Zorginstelling', systems = '') {
  const params = new URLSearchParams({ organization_name: organizationName })
  if (systems) params.set('systems', systems)
  const res = await apiFetch(`${BASE}/reports/${runId}/kikv_readiness/pdf?${params}`)
  if (!res.ok) throw new Error(await res.text())
  const blob = await res.blob()
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = `Rhadix_KIKVReadiness_${new Date().toISOString().slice(0, 10)}.pdf`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// ---------------------------------------------------------------------------
// Admin (RHADIX_ADMIN only)
// ---------------------------------------------------------------------------

export async function getAdminStats() {
  const res = await apiFetch(`${BASE}/admin/stats`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getAdminTenants() {
  const res = await apiFetch(`${BASE}/admin/tenants/`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function createAdminTenant(data) {
  const res = await apiFetch(`${BASE}/admin/tenants/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getAdminTenantUsers(tenantId) {
  const res = await apiFetch(`${BASE}/admin/tenants/${tenantId}/users`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ---------------------------------------------------------------------------
// Applications (RHADIX_ADMIN)
// ---------------------------------------------------------------------------

export async function getAdminApplications() {
  const res = await apiFetch(`${BASE}/admin/applications/`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function createAdminApplication(data) {
  const res = await apiFetch(`${BASE}/admin/applications/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function updateAdminApplication(appId, data) {
  const res = await apiFetch(`${BASE}/admin/applications/${appId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ---------------------------------------------------------------------------
// Licenses (RHADIX_ADMIN)
// ---------------------------------------------------------------------------

export async function getAdminLicenses() {
  const res = await apiFetch(`${BASE}/admin/licenses/`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getAdminTenantLicenses(tenantId) {
  const res = await apiFetch(`${BASE}/admin/licenses/tenant/${tenantId}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function createAdminLicense(data) {
  const res = await apiFetch(`${BASE}/admin/licenses/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function updateAdminLicense(licenseId, data) {
  const res = await apiFetch(`${BASE}/admin/licenses/${licenseId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// ---------------------------------------------------------------------------
// Tenant ↔ Application assignments (RHADIX_ADMIN)
// ---------------------------------------------------------------------------

export async function getAdminTenantApps(tenantId) {
  const res = await apiFetch(`${BASE}/admin/tenants/${tenantId}/applications`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function assignAppToTenant(tenantId, data) {
  const res = await apiFetch(`${BASE}/admin/tenants/${tenantId}/applications`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function revokeAppFromTenant(tenantId, appId) {
  const res = await apiFetch(`${BASE}/admin/tenants/${tenantId}/applications/${appId}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(await res.text())
}

// ---------------------------------------------------------------------------
// Org admin — user-app assignments (ORG_ADMIN)
// ---------------------------------------------------------------------------

export async function getMyTenantApps() {
  const res = await apiFetch(`${BASE}/org/me/apps`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getOrgUsers() {
  const res = await apiFetch(`${BASE}/org/users`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getUserApps(userId) {
  const res = await apiFetch(`${BASE}/org/users/${userId}/apps`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function assignAppToUser(userId, applicationId) {
  const res = await apiFetch(`${BASE}/org/users/${userId}/apps`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, application_id: applicationId }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function revokeAppFromUser(userId, appId) {
  const res = await apiFetch(`${BASE}/org/users/${userId}/apps/${appId}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(await res.text())
}
