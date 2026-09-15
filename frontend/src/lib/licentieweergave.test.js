import { test } from 'node:test'
import assert from 'node:assert/strict'

import {
  gebruikTekst,
  isIngesprongen,
  isVol,
  licentieOverzicht,
  maxUsersTekst,
  organisatieLabel,
  organisatieToelichting,
} from './licentieweergave.js'

// De staging-situatie die de misgreep veroorzaakte: een RSO "KIK-V" met daaronder "kik-g".
const KIKV   = { id: 'r1', name: 'KIK-V', tenant_type: 'RSO', active_user_count: 1 }
const KIKG   = { id: 'o1', name: 'kik-g', tenant_type: 'ORG', parent_tenant_id: 'r1', active_user_count: 3 }
const NOORD  = { id: 'o2', name: 'Noorderboog', tenant_type: 'ORG', active_user_count: 2 }
const BY_ID  = { r1: KIKV, o1: KIKG, o2: NOORD }

test('een RSO is als samenwerkingsorganisatie herkenbaar', () => {
  assert.equal(organisatieToelichting(KIKV), 'samenwerkingsorganisatie (RSO)')
})

test('een onderliggende organisatie noemt de RSO waar hij onder hangt', () => {
  assert.equal(organisatieToelichting(KIKG, BY_ID), 'organisatie onder KIK-V')
})

test('de ouder mag ook rechtstreeks zijn meegeleverd', () => {
  const zonderIndex = { ...KIKG, parent_tenant_name: 'KIK-V' }
  assert.equal(organisatieToelichting(zonderIndex), 'organisatie onder KIK-V')
})

test('een losse organisatie heeft geen ouder in de toelichting', () => {
  assert.equal(organisatieToelichting(NOORD, BY_ID), 'organisatie')
})

test('KIK-V en kik-g leveren verschillende labels op', () => {
  const a = organisatieLabel(KIKV, BY_ID)
  const b = organisatieLabel(KIKG, BY_ID)
  assert.notEqual(a, b)
  assert.match(a, /samenwerkingsorganisatie/)
  assert.match(b, /onder KIK-V/)
})

test('het label telt actieve gebruikers, enkelvoud correct', () => {
  assert.match(organisatieLabel(KIKV, BY_ID), /1 actieve gebruiker$/)
  assert.match(organisatieLabel(KIKG, BY_ID), /3 actieve gebruikers$/)
})

test('zonder aantal blijft het label bruikbaar', () => {
  assert.equal(organisatieLabel({ name: 'X', tenant_type: 'ORG' }), 'X — organisatie')
})

test('geen maximum heet Onbeperkt', () => {
  assert.equal(maxUsersTekst(null), 'Onbeperkt')
  assert.equal(maxUsersTekst(undefined), 'Onbeperkt')
  assert.equal(maxUsersTekst(0), '0')
  assert.equal(maxUsersTekst(4), '4')
})

test('gebruik wordt als "x van y" getoond', () => {
  assert.equal(gebruikTekst(3, 4), '3 van 4')
  assert.equal(gebruikTekst(3, null), '3 (onbeperkt)')
  assert.equal(gebruikTekst(null, 4), '—')
})

test('vol is vanaf het maximum, ook bij overschrijding', () => {
  assert.equal(isVol(3, 4), false)
  assert.equal(isVol(4, 4), true)
  assert.equal(isVol(5, 4), true)
  assert.equal(isVol(5, null), false, 'onbeperkt is nooit vol')
})

test('het overzicht bevat ook organisaties zonder licentie', () => {
  const regels = licentieOverzicht([KIKV, KIKG, NOORD], [
    { id: 'l1', tenant_id: 'r1', name: 'jaar 2026', max_users: 2, is_active: true },
  ])
  assert.equal(regels.length, 3)
  const kikg = regels.find(r => r.tenantId === 'o1')
  assert.equal(kikg.heeftLicentie, false)
  assert.equal(kikg.maxUsers, null)
})

test('een inactieve licentie telt niet als de licentie van de organisatie', () => {
  const regels = licentieOverzicht([NOORD], [
    { id: 'l9', tenant_id: 'o2', name: 'Vorig jaar', max_users: 1, is_active: false },
  ])
  assert.equal(regels[0].heeftLicentie, false)
})

test('een RSO staat boven zijn aangesloten organisaties', () => {
  const regels = licentieOverzicht([NOORD, KIKG, KIKV], [])
  assert.deepEqual(regels.map(r => r.naam), ['KIK-V', 'kik-g', 'Noorderboog'])
})

test('een aangesloten organisatie wordt ingesprongen getoond', () => {
  const regels = licentieOverzicht([KIKV, KIKG, NOORD], [])
  const kikg = regels.find(r => r.tenantId === 'o1')
  const noord = regels.find(r => r.tenantId === 'o2')
  assert.equal(isIngesprongen(kikg, regels), true)
  assert.equal(isIngesprongen(noord, regels), false)
})

test('een kind zonder zichtbare RSO wordt niet ingesprongen', () => {
  const regels = licentieOverzicht([KIKG], [])
  assert.equal(isIngesprongen(regels[0], regels), false)
})

test('de licentie van de RSO wordt niet aan het kind toegekend', () => {
  const regels = licentieOverzicht([KIKV, KIKG], [
    { id: 'l1', tenant_id: 'r1', name: 'jaar 2026', max_users: 2, is_active: true },
  ])
  const rso  = regels.find(r => r.tenantId === 'r1')
  const kind = regels.find(r => r.tenantId === 'o1')
  assert.equal(rso.maxUsers, 2)
  assert.equal(kind.maxUsers, null, 'een RSO-licentie wordt niet geerfd')
})

test('een volle organisatie wordt als vol gemarkeerd', () => {
  const regels = licentieOverzicht([KIKG], [
    { id: 'l2', tenant_id: 'o1', name: 'Krap', max_users: 3, is_active: true },
  ])
  assert.equal(regels[0].vol, true)
})

test('een leeg platform levert een lege lijst op', () => {
  assert.deepEqual(licentieOverzicht([], []), [])
  assert.deepEqual(licentieOverzicht(), [])
})
