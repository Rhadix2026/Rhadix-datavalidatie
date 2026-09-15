/**
 * navigatie.js — waar de terugknop van een dashboard naartoe gaat (bevinding 2).
 *
 * De drie dashboards hadden een VAST terugdoel (`systems`, het bronscherm van
 * Datavalidatie), terwijl ze via meerdere schermen bereikbaar zijn:
 *
 *   portaal            → Dashboard          → terug hoorde naar het portaal
 *   bronscherm         → Dashboard          → terug hoort naar het bronscherm
 *   platformdashboard  → organisatie        → terug hoort naar het platformdashboard
 *
 * Wie vanaf het portaal op Dashboard klikte, belandde met terug dus in Datavalidatie.
 * Precies de melding.
 *
 * Deze module bevat alleen de doelbepaling, als pure functie, zodat het gedrag te testen
 * is zonder de hele App-toestandsmachine. De bedrading zelf staat in `App.jsx` en volgt
 * het patroon dat daar al bestaat voor `actualityBackStep` en `profilesBackStep`.
 *
 * Bewust NIET gedaan: browser-historie of een algemene navigatielaag. Dat zou de
 * bestaande terugroutes raken, en juist die zijn met bevinding 1 en 4 vastgesteld.
 */

/** Waar de terugknop uitkomt als er geen herkomst is vastgelegd. */
export const STANDAARD_TERUG = 'systems'

/** De stappen die een eigen herkomst bijhouden. */
export const DASHBOARD_STAPPEN = ['user_dashboard', 'org_dashboard', 'platform_dashboard']

/**
 * Het terugdoel van een dashboard.
 *
 * @param {string} herkomst  de stap waar de gebruiker vandaan kwam, of null/undefined
 * @param {string} huidige   de stap waarop de gebruiker nu staat
 * @returns {string} de stap waar de terugknop naartoe moet
 *
 * Twee vangnetten, allebei om een terug-lus te voorkomen:
 *   - een herkomst die gelijk is aan het huidige scherm zou de gebruiker op zichzelf
 *     laten terugvallen; dan wint het standaarddoel;
 *   - een lege of onbekende herkomst levert eveneens het standaarddoel op, zodat het
 *     gedrag gelijk is aan vóór deze wijziging.
 */
export function terugDoel(herkomst, huidige) {
  if (!herkomst || typeof herkomst !== 'string') return STANDAARD_TERUG
  if (herkomst === huidige) return STANDAARD_TERUG
  return herkomst
}

/**
 * Is deze herkomst bruikbaar als terugdoel voor dit dashboard?
 *
 * Alleen om bij het vastleggen al te kunnen weigeren wat later toch zou worden
 * genegeerd; `terugDoel` blijft de enige bepaling die telt.
 */
export function geldigeHerkomst(herkomst, huidige) {
  return terugDoel(herkomst, huidige) === herkomst
}
