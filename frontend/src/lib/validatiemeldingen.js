/**
 * validatiemeldingen.js — de regels achter de weergave van validatiemeldingen.
 *
 * De validatie-API geeft per bestand een `file_results`-element terug met daarin
 * `issues`, elk met `severity`, `type`, `field`, `count`, `message` en `examples`.
 * Die structuur is gelijk voor JSON, XML en CSV: de meldingen komen uit
 * `validate_algemeen`, dat op headers en rijen werkt en niet op het bestandsformaat.
 *
 * De weergave zelf staat in `IssueRow` en `FileCard` (AlgemeenDashboard.jsx) en wordt
 * gedeeld met de multi-bronflow. Hier staan alleen de pure regels eromheen, zodat ze
 * te testen zijn met de ingebouwde testrunner van Node — zelfde patroon als
 * appBeschikbaarheid.js, sessie.js en appToewijzing.js.
 */

/**
 * Alle meldingen uit een validatierespons, ongeacht waar ze in de boom zitten.
 *
 * De respons kent per standaard een iets andere vorm (`file_results`, `benchmark`,
 * cross-checks), daarom een recursieve doorloop op de sleutel `issues`.
 */
export function verzamelMeldingen(respons, acc = []) {
  if (!respons || typeof respons !== 'object') return acc
  if (Array.isArray(respons)) {
    respons.forEach(x => verzamelMeldingen(x, acc))
    return acc
  }
  for (const [sleutel, waarde] of Object.entries(respons)) {
    if (sleutel === 'issues' && Array.isArray(waarde)) {
      waarde.forEach(i => { if (i && i.severity) acc.push(i) })
    } else if (waarde && typeof waarde === 'object') {
      verzamelMeldingen(waarde, acc)
    }
  }
  return acc
}

/** Aantal meldingen per ernst — de getallen op de badges. */
export function telPerErnst(meldingen) {
  const lijst = meldingen || []
  return {
    errors: lijst.filter(i => i.severity === 'error').length,
    warnings: lijst.filter(i => i.severity === 'warning').length,
  }
}

/** De bestanden uit een validatierespons, in de volgorde waarin de API ze geeft. */
export function bestandenUit(respons) {
  return (respons && Array.isArray(respons.file_results)) ? respons.file_results : []
}

/** Heeft dit bestand meldingen? Zo niet, dan hoort er geen detailblok te komen. */
export function heeftMeldingen(bestand) {
  return ((bestand && bestand.issues) || []).length > 0
}

/**
 * Kop boven de voorbeelden. Toont het volledige aantal zodra er meer meldingen zijn
 * dan er voorbeelden worden meegestuurd, zodat zichtbaar blijft dat er is afgekapt.
 */
export function voorbeeldenLabel(count, getoond) {
  const totaal = Number(count)
  const n = Number(getoond)
  if (Number.isFinite(totaal) && Number.isFinite(n) && totaal > n) {
    return `Voorbeelden (eerste ${n} van ${totaal})`
  }
  return 'Voorbeelden'
}
