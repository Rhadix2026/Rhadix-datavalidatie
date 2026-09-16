/**
 * licentieweergave.js — hoe organisaties en hun licentie worden getoond.
 *
 * De licentiemodule bestond al vóór RSO's en onderliggende organisaties. In een platform
 * met een samenwerkingsorganisatie "KIK-V" en een aangesloten organisatie "kik-g" zijn
 * twee regels met alleen een naam niet uit elkaar te houden — en dat is precies hoe een
 * grens per ongeluk bij de verkeerde organisatie terechtkwam. Alle keuzelijsten en
 * overzichten gebruiken daarom deze functies.
 *
 * Hier staat ook de weergave van de licentiestatus (bevinding 6). De backend bepaalt de
 * status; deze module vertaalt hem naar tekst en kleur, en kan hem desnoods zelf afleiden
 * uit de datums voor schermen die alleen de ruwe licentie hebben.
 *
 * Pure functies zonder React, zodat ze met `node --test src/lib/` te testen zijn.
 */

// De vier toestanden, gelijk aan `backend/app/auth/licentieweergave.py`.
export const GEEN_LICENTIE = 'geen_licentie'
export const TOEKOMSTIG    = 'toekomstig'
export const ACTIEF        = 'actief'
export const VERLOPEN      = 'verlopen'

/** Een datum-of-tijdstip terugbrengen tot een kalenderdag (UTC), of null. */
function alsDag(waarde) {
  if (!waarde) return null
  const d = waarde instanceof Date ? waarde : new Date(waarde)
  if (Number.isNaN(d.getTime())) return null
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())
}

/**
 * De toestand van een licentie, op DAGNIVEAU.
 *
 * "Geldig tot 31-12" betekent dat die dag er nog bij hoort; een vergelijking op tijdstip
 * zou de licentie op de eerste seconde van haar laatste dag al laten verlopen. Dezelfde
 * regel als in de backend.
 */
export function licentieStatus({ valid_from, valid_until, heeft_licentie = true } = {}, nu = new Date()) {
  if (!heeft_licentie) return GEEN_LICENTIE
  const vandaag = alsDag(nu)
  const start   = alsDag(valid_from)
  const eind    = alsDag(valid_until)
  if (start !== null && start > vandaag) return TOEKOMSTIG
  if (eind  !== null && eind  < vandaag) return VERLOPEN
  return ACTIEF
}

/** Tekst en kleur voor het statuslabel in de schermen. */
export function statusWeergave(status, geenEinddatum = false) {
  switch (status) {
    case VERLOPEN:
      return { label: 'Verlopen',   achtergrond: '#fee2e2', tekst: '#991b1b' }
    case TOEKOMSTIG:
      return { label: 'Toekomstig', achtergrond: '#e0e7ff', tekst: '#3730a3' }
    case GEEN_LICENTIE:
      return { label: 'Geen licentie', achtergrond: '#fef3c7', tekst: '#92400e' }
    default:
      return {
        label: geenEinddatum ? 'Actief · geen einddatum' : 'Actief',
        achtergrond: '#dcfce7', tekst: '#166534',
      }
  }
}

/** Een licentieperiode als leesbare tekst: "1-1-2026 t/m 31-12-2026". */
export function periodeTekst(validFrom, validUntil) {
  const nl = (d) => new Date(d).toLocaleDateString('nl-NL')
  if (!validFrom && !validUntil) return '—'
  if (!validUntil) return `vanaf ${nl(validFrom)} · geen einddatum`
  if (!validFrom)  return `t/m ${nl(validUntil)}`
  return `${nl(validFrom)} t/m ${nl(validUntil)}`
}

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
 * Gaat uitsluitend over aantallen; de geldigheidsperiode staat los en komt via
 * `licentieStatus()`.
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
export function licentieOverzicht(tenants = [], licenses = [], nu = new Date()) {
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
      status: lic ? licentieStatus(lic, nu) : GEEN_LICENTIE,
      geenEinddatum: Boolean(lic) && !lic.valid_until,
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
