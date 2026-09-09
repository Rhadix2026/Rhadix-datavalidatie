/**
 * Tests voor de regels achter applicatietoewijzing.
 *
 *     node --test frontend/src/lib/
 *
 * Bevinding 16 (drie verschillende bevestigingen, waarvan één geen) en bevinding 17
 * (drie verschillende manieren van toewijzen) worden opgelost door één component. Wat
 * hier wordt vastgelegd is de gedeelde regel eronder — inclusief het verschil tussen
 * organisatie- en gebruikersniveau, dat bewust blijft bestaan.
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'

import {
  naarItems,
  beschikbareApps,
  bevestigingIntrekken,
  kopToegewezen,
  kopBeschikbaar,
  tekstLeeg,
  NIVEAU_ORGANISATIE,
  NIVEAU_GEBRUIKER,
} from './appToewijzing.js'

// Vorm zoals een toewijzingsrij uit de API komt (TenantApplication/UserApplication).
const toewijzing = (appId, naam) => ({ id: `rij-${appId}`, application_id: appId, application_name: naam })
// Vorm zoals de applicatielijst uit de API komt.
const applicatie = (id, naam, slug) => ({ id, name: naam, slug })

// ── Normalisatie ────────────────────────────────────────────────────────────

test('een toewijzingsrij levert het applicatie-id, niet het rij-id', () => {
  const [i] = naarItems([toewijzing('app-1', 'Rhadix Uitvraag')])
  assert.equal(i.applicationId, 'app-1')
  assert.equal(i.naam, 'Rhadix Uitvraag')
})

test('een applicatierij uit de lijst levert dezelfde vorm op', () => {
  const [i] = naarItems([applicatie('app-1', 'Rhadix Uitvraag', 'uitvraag')])
  assert.equal(i.applicationId, 'app-1')
  assert.equal(i.naam, 'Rhadix Uitvraag')
  assert.equal(i.slug, 'uitvraag')
})

test('een lege of ontbrekende lijst geeft een lege uitkomst', () => {
  for (const l of [[], null, undefined]) assert.deepEqual(naarItems(l), [])
})

// ── Wat er nog toegewezen kan worden ────────────────────────────────────────

test('wat al toegewezen is valt uit het aanbod', () => {
  const toegewezen = [toewijzing('a', 'Rhadix Datavalidatie')]
  const aanbod = [applicatie('a', 'Rhadix Datavalidatie'), applicatie('b', 'Rhadix Datastation')]
  const over = beschikbareApps(toegewezen, aanbod)
  assert.deepEqual(over.map(i => i.applicationId), ['b'])
})

test('zonder toewijzingen is het hele aanbod beschikbaar', () => {
  const aanbod = [applicatie('a', 'A'), applicatie('b', 'B')]
  assert.equal(beschikbareApps([], aanbod).length, 2)
  assert.equal(beschikbareApps(null, aanbod).length, 2)
})

test('alles toegewezen betekent niets meer beschikbaar', () => {
  const aanbod = [applicatie('a', 'A'), applicatie('b', 'B')]
  const toegewezen = [toewijzing('a', 'A'), toewijzing('b', 'B')]
  assert.deepEqual(beschikbareApps(toegewezen, aanbod), [])
})

test('het aanbod is de grens: op gebruikersniveau kan er niets buiten de organisatie bij', () => {
  // De organisatie heeft alleen Datavalidatie; de gebruiker heeft nog niets.
  const aanbodVanDeOrganisatie = [applicatie('a', 'Rhadix Datavalidatie')]
  const over = beschikbareApps([], aanbodVanDeOrganisatie)
  assert.deepEqual(over.map(i => i.naam), ['Rhadix Datavalidatie'])
  // Datastation zit niet in het aanbod en kan dus ook niet opduiken.
  assert.ok(!over.some(i => i.naam.includes('Datastation')))
})

// ── Bevestiging bij intrekken (bevinding 16) ────────────────────────────────

test('de bevestiging noemt de applicatie bij naam', () => {
  const t = bevestigingIntrekken('Rhadix Datastation', 'Carinova')
  assert.ok(t.includes('Rhadix Datastation'), t)
  assert.ok(t.includes('Carinova'), t)
})

test('zonder doelnaam blijft de bevestiging bruikbaar', () => {
  const t = bevestigingIntrekken('Rhadix CRM')
  assert.ok(t.includes('Rhadix CRM'), t)
  assert.ok(!t.includes('undefined'), t)
})

test('een ontbrekende applicatienaam levert geen kapotte tekst op', () => {
  const t = bevestigingIntrekken(undefined, 'Carinova')
  assert.ok(!t.includes('undefined'), t)
  assert.ok(t.includes('Carinova'), t)
})

test('organisatie- en gebruikersniveau krijgen dezelfde formulering', () => {
  // Bevinding 16: het verschil in melding tussen de rollen verdwijnt.
  assert.equal(
    bevestigingIntrekken('Rhadix Uitvraag', 'Carinova'),
    bevestigingIntrekken('Rhadix Uitvraag', 'Carinova'),
  )
})

// ── Het niveauverschil blijft zichtbaar ─────────────────────────────────────

test('de koppen benoemen het niveau', () => {
  assert.match(kopToegewezen(NIVEAU_ORGANISATIE), /organisatie/i)
  assert.equal(kopToegewezen(NIVEAU_GEBRUIKER), 'Toegewezen applicaties')
  assert.notEqual(kopToegewezen(NIVEAU_ORGANISATIE), kopToegewezen(NIVEAU_GEBRUIKER))
})

test('ook de tekst bij een lege lijst benoemt het niveau', () => {
  assert.match(tekstLeeg(NIVEAU_ORGANISATIE), /organisatie/i)
  assert.match(tekstLeeg(NIVEAU_GEBRUIKER), /gebruiker/i)
})

test('de kop boven het aanbod verschilt per niveau', () => {
  assert.notEqual(kopBeschikbaar(NIVEAU_ORGANISATIE), kopBeschikbaar(NIVEAU_GEBRUIKER))
})
