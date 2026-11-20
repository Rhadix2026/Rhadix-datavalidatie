import { test } from 'node:test'
import assert from 'node:assert/strict'
import { leesDirecteApp, doorstuurAdres, DIRECTE_APPS } from './directeToegang.js'

const ADRESSEN = { 'rhadix-makelaarsportaal': 'https://makelaarsportaal-test.rhadix.nl' }
const makelaar = { role: 'ORG_USER', assigned_app_slugs: ['rhadix-makelaarsportaal'] }

test('alleen bekende slugs worden herkend', () => {
  assert.equal(leesDirecteApp('?app=rhadix-makelaarsportaal'), 'rhadix-makelaarsportaal')
  assert.equal(leesDirecteApp('?app=uitvraag'), null)
  assert.equal(leesDirecteApp('?app=https://evil.example'), null)
  assert.equal(leesDirecteApp('?app=//evil.example'), null)
  assert.equal(leesDirecteApp('?app=__proto__'), null)
  assert.equal(leesDirecteApp('?app=constructor'), null)
  assert.equal(leesDirecteApp(''), null)
  assert.equal(leesDirecteApp(undefined), null)
})

test('doorsturen naar het vaste adres bij toegang', () => {
  assert.equal(doorstuurAdres('rhadix-makelaarsportaal', makelaar, ADRESSEN), 'https://makelaarsportaal-test.rhadix.nl')
})

test('platformbeheerder volgt de bestaande uitzondering', () => {
  assert.equal(doorstuurAdres('rhadix-makelaarsportaal', { role: 'RHADIX_ADMIN', assigned_app_slugs: [] }, ADRESSEN), ADRESSEN['rhadix-makelaarsportaal'])
})

test('geen toegang: niet doorsturen (gewoon het overzicht)', () => {
  assert.equal(doorstuurAdres('rhadix-makelaarsportaal', { role: 'ORG_USER', assigned_app_slugs: ['uitvraag'] }, ADRESSEN), null)
  assert.equal(doorstuurAdres('rhadix-makelaarsportaal', { role: 'ORG_ADMIN' }, ADRESSEN), null)
})

test('niet ingelogd, onbekende slug of geen geldig adres: niet doorsturen', () => {
  assert.equal(doorstuurAdres('rhadix-makelaarsportaal', null, ADRESSEN), null)
  assert.equal(doorstuurAdres('uitvraag', makelaar, { uitvraag: 'https://uitvraag.rhadix.nl' }), null)
  assert.equal(doorstuurAdres(null, makelaar, ADRESSEN), null)
  assert.equal(doorstuurAdres('rhadix-makelaarsportaal', makelaar, {}), null)                       // niet uitgerold
  assert.equal(doorstuurAdres('rhadix-makelaarsportaal', makelaar, { 'rhadix-makelaarsportaal': '' }), null)
  assert.equal(doorstuurAdres('rhadix-makelaarsportaal', makelaar, { 'rhadix-makelaarsportaal': 'javascript:alert(1)' }), null)
  assert.equal(doorstuurAdres('rhadix-makelaarsportaal', makelaar, { 'rhadix-makelaarsportaal': 'http://makelaarsportaal-test.rhadix.nl' }), null)
  assert.equal(doorstuurAdres('rhadix-makelaarsportaal', makelaar, { 'rhadix-makelaarsportaal': 'https://x.nl/pad?y=1' }), null)
})

test('lijst is bevroren', () => {
  assert.ok(Object.isFrozen(DIRECTE_APPS))
})
