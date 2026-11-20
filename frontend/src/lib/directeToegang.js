/**
 * directeToegang.js — rechtstreekse ingang voor één applicatie via het Platform.
 *
 * Een resource-app (nu alleen het Rhadix Makelaarsportaal) stuurt een gebruiker die
 * nog niet is ingelogd naar het Platform met `?app=<slug>`. Het Platform toont dan
 * direct het inlogscherm (geen algemene landingspagina) en stuurt na het inloggen —
 * of bij een al geldige sessie — meteen door naar die applicatie, zonder het
 * applicatieoverzicht te tonen.
 *
 * Veiligheid (geen open redirect):
 *   - de URL-parameter bevat alleen een SLUG, nooit een adres;
 *   - alleen slugs uit DIRECTE_APPS worden herkend; al het andere wordt genegeerd;
 *   - het doeladres komt uit de vaste configuratie van het Platform (zelfde adres als
 *     de tegel in het applicatieoverzicht), niet uit de aanvraag;
 *   - doorsturen alleen als de app in deze omgeving is uitgerold én de gebruiker hem
 *     volgens de bestaande regel (apps-claim) mag openen. Anders gewoon het overzicht.
 *
 * Geen React en geen import.meta.env: pure functies, te testen met `node --test`.
 */
import { appStatus, BESCHIKBAAR } from './appBeschikbaarheid.js'

/** Applicaties met een rechtstreekse ingang: slug → weergavenaam. */
export const DIRECTE_APPS = Object.freeze({
  'rhadix-makelaarsportaal': 'Rhadix Makelaarsportaal',
})

/**
 * Merkvarianten van het inlogscherm voor een rechtstreekse ingang (`?app=<slug>&merk=<merk>`).
 * Alleen opmaak: logo, kleuren en lettertype van het makelaarskantoor. Authenticatie en
 * doorsturen blijven precies gelijk. Alleen merken uit deze vaste lijst worden herkend; het
 * logo staat ongewijzigd in public/merken/<merk>/.
 */
export const MERKEN = Object.freeze({
  morskieft: Object.freeze({
    naam: 'Morskieft',
    logo: '/merken/morskieft/logo.svg',          // aangeleverd SVG-logo (wit), ongewijzigd
    logoAlt: 'Morskieft – De Twentsche Makelaar',
    donker: '#0B233A', neutraal: '#EEEDE3', accent: '#EEA868',  // Morskieft-styleguide
    label: 'Makelaarsportaal',
  }),
})

/** Leest `?merk=` — alleen samen met een herkende rechtstreekse ingang en alleen een bekend merk. */
export function leesMerk(search, directeApp) {
  if (!directeApp) return null
  try {
    const merk = new URLSearchParams(search || '').get('merk')
    return merk && Object.prototype.hasOwnProperty.call(MERKEN, merk) ? merk : null
  } catch {
    return null
  }
}

/** Leest `?app=` uit een querystring; geeft de slug alleen terug als die bekend is. */
export function leesDirecteApp(search) {
  try {
    const slug = new URLSearchParams(search || '').get('app')
    return slug && Object.prototype.hasOwnProperty.call(DIRECTE_APPS, slug) ? slug : null
  } catch {
    return null
  }
}

/**
 * Waarheen na het inloggen? Geeft het vaste adres van de app terug, of null (dan het
 * gewone applicatieoverzicht).
 *
 * @param {string|null} slug       resultaat van leesDirecteApp
 * @param {object|null} authUser   gebruiker uit /api/auth/me
 * @param {Record<string,string>} adressen  slug → vast https-adres uit de configuratie
 */
export function doorstuurAdres(slug, authUser, adressen) {
  if (!slug || !authUser || !Object.prototype.hasOwnProperty.call(DIRECTE_APPS, slug)) return null
  const adres = adressen?.[slug]
  if (typeof adres !== 'string' || !/^https:\/\/[a-z0-9.-]+(:\d+)?\/?$/i.test(adres)) return null
  if (appStatus({ slug, uitgerold: true }, authUser) !== BESCHIKBAAR) return null
  return adres
}
