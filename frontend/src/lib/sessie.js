/**
 * sessie.js — waar 'uitloggen' naartoe gaat.
 *
 * Uitloggen is geen handeling in de frontend. Het centrale `rhadix_sso`-cookie op
 * `.rhadix.nl` wordt uitgegeven door Rhadix Datavalidatie en kan alleen daar weer
 * worden ingetrokken; de resource-apps accepteren dat cookie als volwaardig bewijs
 * van identiteit. Wist een applicatie alleen zijn eigen state, dan logt de
 * eerstvolgende paginalading de gebruiker gewoon weer in.
 *
 * Alle vier de applicaties navigeren daarom naar dezelfde centrale uitgang. Die
 * trekt het cookie in en stuurt door naar het Platform — waarmee de gebruiker ook
 * niet meer achterblijft op een applicatie-URL.
 *
 * Bewust een pure functie zonder React en zonder `import.meta.env`, zodat de regel
 * te testen is met de ingebouwde testrunner van Node (`node --test`), zonder extra
 * dependency. Datavalidatie is zelf het Platform en geeft daarom geen basis mee;
 * de andere drie geven `platformUrl()` mee.
 */

/** Pad van de centrale uitgang op de uitgever (Datavalidatie). */
export const LOGOUT_PAD = '/api/auth/logout'

/**
 * @param {string} [platformBasis] herkomst van het Platform, bv. 'https://app.rhadix.nl'.
 *                                 Leeg laten binnen Datavalidatie zelf: dan is het
 *                                 een relatieve URL naar de eigen backend.
 * @returns {string} URL waar naartoe genavigeerd moet worden om uit te loggen.
 */
export function centraleLogoutUrl(platformBasis) {
  const basis = String(platformBasis || '').replace(/\/+$/, '')
  return basis + LOGOUT_PAD
}
