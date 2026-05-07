const BASE = '/api'

export async function uploadFiles(files, label = '', standard = 'kikv', maxAgeDays = 30) {
  const form = new FormData()
  files.forEach(f => form.append('files', f))
  if (label) form.append('label', label)
  form.append('standard', standard)
  form.append('max_age_days', String(maxAgeDays))
  const res = await fetch(`${BASE}/validate/upload`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getHistory(skip = 0, limit = 50) {
  const res = await fetch(`${BASE}/history/?skip=${skip}&limit=${limit}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getRun(id) {
  const res = await fetch(`${BASE}/history/${id}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getStats() {
  const res = await fetch(`${BASE}/history/stats/summary`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export function exportUrl(runId, format) {
  return `${BASE}/export/${runId}/${format}`
}

/**
 * Genereert een Rhadix Actieplan PDF en triggert een browser-download.
 * @param {Array}       items        — actieplan items (title, color, desc, acties, estimate)
 * @param {number|null} runId        — optioneel: run_id voor scandatum + Rhadix Index
 * @param {string|null} organisation — optionele organisatienaam voor de header
 */
export async function exportActieplan(items, runId = null, organisation = null) {
  const res = await fetch(`${BASE}/export/actieplan`, {
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

/**
 * Haalt de volledige validatieregels op vanuit de backend (rules.py).
 * Bevat allowedValues per veld — gebruik dit i.p.v. hardcoded lijsten in de UI.
 */
export async function getRules() {
  const res = await fetch(`${BASE}/reference/rules`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

/**
 * Haalt het Beschikbaarheidsrapport (JSON) op voor een scan.
 * @param {number} runId            — scan run_id
 * @param {string} organizationName — optionele organisatienaam
 * @param {string} systems          — komma-gescheiden bronsystemen
 */
export async function getBeschikbaarheidsRapport(runId, organizationName = 'Zorginstelling', systems = '') {
  const params = new URLSearchParams({ organization_name: organizationName })
  if (systems) params.set('systems', systems)
  const res = await fetch(`${BASE}/reports/${runId}/beschikbaarheid?${params}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

/**
 * Genereert het Beschikbaarheidsrapport als PDF en triggert een browser-download.
 * @param {number} runId            — scan run_id
 * @param {string} organizationName — optionele organisatienaam
 * @param {string} systems          — komma-gescheiden bronsystemen
 */
export async function exportBeschikbaarheidsRapportPdf(runId, organizationName = 'Zorginstelling', systems = '') {
  const params = new URLSearchParams({ organization_name: organizationName })
  if (systems) params.set('systems', systems)
  const res = await fetch(`${BASE}/reports/${runId}/beschikbaarheid/pdf?${params}`)
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

/**
 * Haalt het KIK-V Readiness rapport (JSON) op voor een scan.
 * @param {number} runId            — scan run_id
 * @param {string} organizationName — optionele organisatienaam
 * @param {string} systems          — komma-gescheiden bronsystemen
 */
export async function getKikvReadinessRapport(runId, organizationName = 'Zorginstelling', systems = '') {
  const params = new URLSearchParams({ organization_name: organizationName })
  if (systems) params.set('systems', systems)
  const res = await fetch(`${BASE}/reports/${runId}/kikv_readiness?${params}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

/**
 * Haalt het Gecombineerd Managementrapport (JSON) op voor een scan.
 * @param {number} runId            — scan run_id
 * @param {string} organizationName — optionele organisatienaam
 * @param {string} systems          — komma-gescheiden bronsystemen
 */
export async function getManagementRapport(runId, organizationName = 'Zorginstelling', systems = '') {
  const params = new URLSearchParams({ organization_name: organizationName })
  if (systems) params.set('systems', systems)
  const res = await fetch(`${BASE}/reports/${runId}/management?${params}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

/**
 * Genereert het Gecombineerd Managementrapport als PDF en triggert een browser-download.
 * @param {number} runId            — scan run_id
 * @param {string} organizationName — optionele organisatienaam
 * @param {string} systems          — komma-gescheiden bronsystemen
 */
export async function exportManagementRapportPdf(runId, organizationName = 'Zorginstelling', systems = '') {
  const params = new URLSearchParams({ organization_name: organizationName })
  if (systems) params.set('systems', systems)
  const res = await fetch(`${BASE}/reports/${runId}/management/pdf?${params}`)
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

/**
 * Genereert het KIK-V Readiness rapport als PDF en triggert een browser-download.
 * @param {number} runId            — scan run_id
 * @param {string} organizationName — optionele organisatienaam
 * @param {string} systems          — komma-gescheiden bronsystemen
 */
export async function exportKikvReadinessRapportPdf(runId, organizationName = 'Zorginstelling', systems = '') {
  const params = new URLSearchParams({ organization_name: organizationName })
  if (systems) params.set('systems', systems)
  const res = await fetch(`${BASE}/reports/${runId}/kikv_readiness/pdf?${params}`)
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
