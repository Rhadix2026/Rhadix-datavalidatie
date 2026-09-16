/**
 * Tests voor de centrale uitlog-URL.
 *
 * Draaien met de ingebouwde testrunner van Node — geen extra dependency nodig:
 *
 *     node --test frontend/src/lib/
 *
 * Wat hier wordt vastgelegd is de afspraak tussen de vier frontends en de uitgever:
 * uitloggen gaat naar één en dezelfde route op Datavalidatie, nooit naar een
 * applicatie-eigen adres. Het gedrag van die route zelf (cookie intrekken,
 * doorsturen naar het Platform) staat in backend/tests/test_logout_sessie.py.
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'

import { centraleLogoutUrl, LOGOUT_PAD } from './sessie.js'

test('binnen Datavalidatie is het een relatieve URL naar de eigen backend', () => {
  assert.equal(centraleLogoutUrl(), '/api/auth/logout')
  assert.equal(centraleLogoutUrl(''), '/api/auth/logout')
  assert.equal(centraleLogoutUrl(undefined), '/api/auth/logout')
})

test('vanuit een resource-app wijst hij naar het Platform', () => {
  assert.equal(centraleLogoutUrl('https://app.rhadix.nl'), 'https://app.rhadix.nl/api/auth/logout')
  assert.equal(centraleLogoutUrl('https://app-staging.rhadix.nl'),
               'https://app-staging.rhadix.nl/api/auth/logout')
})

test('een afsluitende slash in de basis levert geen dubbele slash op', () => {
  assert.equal(centraleLogoutUrl('https://app.rhadix.nl/'), 'https://app.rhadix.nl/api/auth/logout')
  assert.equal(centraleLogoutUrl('https://app.rhadix.nl///'), 'https://app.rhadix.nl/api/auth/logout')
})

test('wijst nooit naar de applicatie zelf', () => {
  // De kern van bevinding 9: uitloggen vanuit Uitvraag of CRM mag niet op het
  // eigen domein blijven hangen.
  for (const platform of ['https://app.rhadix.nl', 'https://app-staging.rhadix.nl']) {
    const url = centraleLogoutUrl(platform)
    for (const app of ['uitvraag.rhadix.nl', 'crm.rhadix.nl', 'datastation.rhadix.nl']) {
      assert.ok(!url.includes(app), `${url} verwijst naar de applicatie in plaats van het Platform`)
    }
  }
})

test('alle applicaties komen op dezelfde route uit', () => {
  const vanuitPlatform = centraleLogoutUrl()
  const vanuitApp = centraleLogoutUrl('https://app.rhadix.nl')
  assert.ok(vanuitPlatform.endsWith(LOGOUT_PAD))
  assert.ok(vanuitApp.endsWith(LOGOUT_PAD))
  assert.equal(LOGOUT_PAD, '/api/auth/logout')
})
