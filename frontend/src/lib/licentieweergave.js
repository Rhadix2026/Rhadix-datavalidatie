/**
 * licentieweergave.js — hoe organisaties en hun licentie worden getoond.
 *
 * De licentiemodule bestond al vóór RSO's en onderliggende organisaties. In een platform
 * met een samenwerkingsorganisatie "KIK-V" en een aangesloten organisatie "kik-g" zijn
 * twee regels met alleen een naam niet uit elkaar te houden — en dat is precies hoe een
 * grens per ongeluk bij de verkeerde organisatie terechtkwam. Alle keuzelijsten en
 * overzichten gebruiken daarom deze functies.
 *
 * Pure functies zonder React, zodat ze met `node --test src/lib/` te testen zijn.
 */

/** Toelichting achter een organisatienaam: wat voor organisatie is dit, en waar hangt hij? */
export function organisatieToelichting(tenant, tenantsById = {}) {
  if (!tenant) return ''
  const type = (tenant.tenant_type || 'ORG').toUpperCase()
  if (type === 'RSO') return 'samenwerkingsorganisatie (RSO)'
  if (type === 'PLATFORM') return 'platformorganisatie'

  const ouderNaam = tenant.parent_tenant_name
    || (tenant.parent_tenant_id ? tenantsById[tenant.parent_tenant_id]?.name : null)
  return ouderNaam ? `organisatie onder ${ouderNaam}` : 'organisatie'
}

/** Volledig label voor een keuzelijst: "kik-g — organisatie onder KIK-V · 3 actieve gebruikers". */
export function organisatieLabel(tenant, tenantsById = {}) {
  if (!tenant) return ''
  const delen = [organisatieToelichting(tenant, tenantsById)]
  const actief = tenant.active_user_count
  if (typeof actief === 'number') {
    delen.push(`${actief} ${actief === 1 ? 'actieve gebruiker' : 'actieve gebruikers'}`)
  }
  return `${tenant.name} — ${delen.join(' · ')}`
}

/** 'Onbeperkt' als er geen maximum is. */
export function maxUsersTekst(maxUsers) {
  return maxUsers == null ? 'Onbeperkt' : String(maxUsers)
}

/**
 * Hoeveel plaatsen zijn er in gebruik.
 *
 * Geeft bewust géén oordeel over de geldigheidsdatum — of een verlopen licentie iets
 * betekent is bevinding 6 en nog niet besloten.
 */
export function gebruikTekst(actieveGebruikers, maxUsers) {
  if (typeof actieveGebruikers !== 'number') return '—'
  if (maxUsers == null) return `${actieveGebruikers} (onbeperkt)`
  return `${actieveGebruikers} van ${maxUsers}`
}

/** Zit de organisatie op of over de grens? Alleen om de regel te kunnen markeren. */
export function isVol(actieveGebruikers, maxUsers) {
  if (maxUsers == null || typeof actieveGebruikers !== 'number') return false
  return actieveGebruikers >= maxUsers
}

/**
 * Het beheeroverzicht per ORGANISATIE in plaats van per licentie.
 *
 * Een overzicht dat alleen licenties toont, laat organisaties zonder licentie helemaal
 * weg — juist die wil een beheerder zien. Iedere organisatie krijgt hier een regel; de
 * licentie is een eigenschap ervan, niet het uitgangspunt.
 *
 * Sortering: RSO's eerst, met hun aangesloten organisaties er direct onder; losse
 * organisaties daarna. Alles alfabetisch binnen die groepen.
 */
export function licentieOverzicht(tenants = [], licenses = []) {
  const actieveLicentiePerTenant = {}
  for (const lic of licenses) {
    if (lic.is_active) actieveLicentiePerTenant[lic.tenant_id] = lic
  }
  const tenantsById = Object.fromEntries(tenants.map(t => [t.id, t]))

  const regels = tenants.map(t => {
    const lic = actieveLicentiePerTenant[t.id] || null
    const actief = t.active_user_count ?? null
    return {
      tenant: t,
      tenantId: t.id,
      naam: t.name,
      toelichting: organisatieToelichting(t, tenantsById),
      tenantType: (t.tenant_type || 'ORG').toUpperCase(),
      parentTenantId: t.parent_tenant_id || null,
      licentie: lic,
      heeftLicentie: Boolean(lic),
      actieveGebruikers: actief,
      maxUsers: lic ? lic.max_users : null,
      vol: lic ? isVol(actief, lic.max_users) : false,
    }
  })

  // Sorteersleutel: de RSO en zijn kinderen delen dezelfde groepsnaam, zodat ze bij
  // elkaar blijven staan; binnen de groep staat de RSO zelf bovenaan.
  const groepsnaam = (r) => {
    if (r.tenantType === 'RSO') return r.naam.toLowerCase()
    if (r.parentTenantId && tenantsById[r.parentTenantId]) {
      return tenantsById[r.parentTenantId].name.toLowerCase()
    }
    return r.naam.toLowerCase()
  }
  return regels.sort((a, b) => {
    const ga = groepsnaam(a), gb = groepsnaam(b)
    if (ga !== gb) return ga < gb ? -1 : 1
    if (a.tenantType === 'RSO' && b.tenantType !== 'RSO') return -1
    if (b.tenantType === 'RSO' && a.tenantType !== 'RSO') return 1
    return a.naam.toLowerCase() < b.naam.toLowerCase() ? -1 : 1
  })
}

/** Is deze organisatie een kind van een RSO die ook in het overzicht staat? (voor inspringen) */
export function isIngesprongen(regel, regels) {
  if (!regel.parentTenantId) return false
  return regels.some(r => r.tenantId === regel.parentTenantId && r.tenantType === 'RSO')
}
