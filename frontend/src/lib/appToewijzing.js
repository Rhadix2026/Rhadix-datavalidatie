/**
 * appToewijzing.js — de regels achter het toewijzen en intrekken van applicaties.
 *
 * Drie beheerschermen doen dezelfde handeling op een ander object:
 *
 *   AdminDashboard    (RHADIX_ADMIN) — applicaties van een ORGANISATIE
 *   RsoDashboard      (RSO_ADMIN)    — applicaties van een aangesloten ORGANISATIE
 *   OrgAdminDashboard (ORG_ADMIN)    — applicaties van een GEBRUIKER
 *
 * Dat niveauverschil is geen slordigheid maar het autorisatiemodel: een
 * organisatietoewijzing (TenantApplication) en een persoonlijke toewijzing
 * (UserApplication) zijn verschillende dingen, met verschillende endpoints en
 * verschillende rechten. Dat blijft hier volledig intact — alleen de bediening en de
 * teksten worden gelijk.
 *
 * Bewust een pure module zonder React en zonder `import.meta.env`, zodat de regels te
 * testen zijn met de ingebouwde testrunner van Node (`node --test`), zonder extra
 * dependency. Zelfde patroon als appBeschikbaarheid.js en sessie.js.
 */

/** Toewijzing op organisatieniveau (TenantApplication). */
export const NIVEAU_ORGANISATIE = 'organisatie'

/** Toewijzing op gebruikersniveau (UserApplication), binnen wat de organisatie heeft. */
export const NIVEAU_GEBRUIKER = 'gebruiker'

/**
 * Breng een lijst uit de API terug tot { applicationId, naam }.
 *
 * De drie schermen krijgen hun lijsten in twee vormen: een toewijzingsrij draagt
 * `application_id` + `application_name`, terwijl het aanbod uit de applicatielijst
 * `id` + `name` draagt. Beide komen hier op dezelfde vorm uit, zodat het component
 * er niet drie keer een eigen afleiding op na hoeft te houden.
 */
export function naarItems(lijst) {
  return (lijst || []).map(x => ({
    applicationId: x.application_id ?? x.id,
    naam: x.application_name ?? x.name ?? '(naamloos)',
    slug: x.application_slug ?? x.slug ?? null,
  }))
}

/**
 * Wat kan er nog worden toegewezen: het aanbod min wat al is toegewezen.
 *
 * @param {Array} toegewezen huidige toewijzingen
 * @param {Array} aanbod     wat er toegewezen mág worden — op gebruikersniveau is dat
 *                           per definitie wat de organisatie heeft, niet alles
 */
export function beschikbareApps(toegewezen, aanbod) {
  const bezet = new Set(naarItems(toegewezen).map(i => i.applicationId))
  return naarItems(aanbod).filter(i => !bezet.has(i.applicationId))
}

/**
 * Bevestiging bij intrekken — één tekst voor alle drie de schermen, mét de naam van
 * de applicatie. Voorheen had elk scherm een eigen formulering en één scherm vroeg
 * helemaal niets.
 */
export function bevestigingIntrekken(appNaam, doelNaam) {
  const app = appNaam || 'deze applicatie'
  return doelNaam
    ? `Toegang tot «${app}» intrekken voor ${doelNaam}?`
    : `Toegang tot «${app}» intrekken?`
}

/** Kop boven de toegewezen applicaties; benoemt het niveau zodat dat zichtbaar blijft. */
export function kopToegewezen(niveau) {
  return niveau === NIVEAU_ORGANISATIE
    ? 'Applicaties van deze organisatie'
    : 'Toegewezen applicaties'
}

/** Kop boven wat nog toegewezen kan worden. */
export function kopBeschikbaar(niveau) {
  return niveau === NIVEAU_ORGANISATIE
    ? 'Beschikbaar om toe te wijzen aan deze organisatie'
    : 'Beschikbaar om toe te wijzen'
}

/** Tekst als er niets is toegewezen. */
export function tekstLeeg(niveau) {
  return niveau === NIVEAU_ORGANISATIE
    ? 'Nog geen applicaties toegewezen aan deze organisatie.'
    : 'Nog geen applicaties toegewezen aan deze gebruiker.'
}
