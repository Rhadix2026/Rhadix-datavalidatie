/**
 * appBeschikbaarheid.js — bepaalt per applicatietegel of die beschikbaar is.
 *
 * Bewust twee dingen uit elkaar gehouden, want ze beantwoorden verschillende vragen:
 *
 *   1. DEPLOYMENTSTATUS — "bestaat deze applicatie al?"  (uitgerold ja/nee)
 *   2. AUTORISATIE      — "mag DEZE gebruiker erbij?"    (apps-claim)
 *
 * De claim komt uit `/api/auth/me` als `assigned_app_slugs` en is de vereniging van
 * de organisatiebrede (TenantApplication) en persoonlijke (UserApplication)
 * toewijzingen. Voor RHADIX_ADMIN vervangt de centrale issuer die claim door alle
 * actieve applicaties; die uitzondering blijft hier ongewijzigd van kracht.
 *
 * Dit bestand bevat GEEN React en GEEN `import.meta.env`, zodat de regel als pure
 * functie te testen is met de ingebouwde testrunner van Node (`node --test`) —
 * zonder extra dependency.
 *
 * Let op: dit is presentatielogica. De resource-apps handhaven zelf op de claim
 * (APP_ACCESS_ENFORCE) en blijven een directe aanroep met 403 weigeren. Deze module
 * verandert daar niets aan; ze voorkomt alleen dat het Platform een applicatie
 * aanbiedt waar de gebruiker toch niet in komt.
 */

/** Uitgerold én toegewezen: gewoon te openen. */
export const BESCHIKBAAR = 'beschikbaar'

/** Nog niet uitgerold in deze omgeving. Bestaande statuslogica, los van toewijzing. */
export const NIET_UITGEROLD = 'niet-uitgerold'

/** Wel uitgerold, maar niet aan deze gebruiker toegewezen. */
export const GEEN_TOEGANG = 'geen-toegang'

/** Rol die volgens het centrale model alle actieve applicaties in de claim krijgt. */
const ADMIN_ROL = 'RHADIX_ADMIN'

/**
 * @param {object}  app              tegeldefinitie
 * @param {string} [app.slug]        centrale applicatie-slug; ontbreekt hij, dan valt
 *                                   de tegel buiten de toewijzing (geen autorisatiepoort)
 * @param {boolean} [app.uitgerold]  deploymentstatus; default true
 * @param {object|null} authUser     gebruiker uit /api/auth/me, of null
 * @returns {'beschikbaar'|'niet-uitgerold'|'geen-toegang'}
 */
export function appStatus(app, authUser) {
  if (app.uitgerold === false) return NIET_UITGEROLD

  // Niet ingelogd: het portaal toont het aanbod. De applicatie zelf vraagt daarna
  // om authenticatie; er valt hier nog niets te autoriseren.
  if (!authUser) return BESCHIKBAAR

  // Tegels zonder centrale slug kennen geen toewijzing en blijven ongemoeid.
  if (!app.slug) return BESCHIKBAAR

  // Bestaande uitzondering uit het autorisatiemodel: de platformbeheerder houdt
  // toegang tot alle actieve applicaties.
  if (authUser.role === ADMIN_ROL) return BESCHIKBAAR

  const toegewezen = authUser.assigned_app_slugs || []
  return toegewezen.includes(app.slug) ? BESCHIKBAAR : GEEN_TOEGANG
}

/** Mag er op de tegel geklikt worden? Alleen bij BESCHIKBAAR. */
export function isKlikbaar(status) {
  return status === BESCHIKBAAR
}

/**
 * Label op de tegel. `actie` is het bestaande label voor een beschikbare tegel;
 * de andere twee statussen krijgen hun eigen tekst.
 */
export function actieLabel(status, actie = 'Openen →') {
  if (status === NIET_UITGEROLD) return 'Binnenkort'
  if (status === GEEN_TOEGANG) return 'Geen toegang'
  return actie
}
