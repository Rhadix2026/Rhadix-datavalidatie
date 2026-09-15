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

// ── Bevinding 6: geldigheid ────────────────────────────────────────────────

import {
  ACTIEF, GEEN_LICENTIE, TOEKOMSTIG, VERLOPEN,
  licentieStatus, periodeTekst, statusWeergave,
} from './licentieweergave.js'

const VANDAAG = new Date('2026-09-15T12:00:00Z')

test('een lopende licentie is actief', () => {
  assert.equal(licentieStatus({ valid_from: '2026-01-01', valid_until: '2026-12-31' }, VANDAAG), ACTIEF)
})

test('zonder einddatum is de licentie actief', () => {
  assert.equal(licentieStatus({ valid_from: '2026-01-01', valid_until: null }, VANDAAG), ACTIEF)
})

test('de laatste dag telt nog mee', () => {
  assert.equal(licentieStatus({ valid_from: '2026-01-01', valid_until: '2026-09-15' }, VANDAAG), ACTIEF)
})

test('de dag na de einddatum is verlopen', () => {
  assert.equal(licentieStatus({ valid_from: '2026-01-01', valid_until: '2026-09-14' }, VANDAAG), VERLOPEN)
})

test('middernacht laat de licentie niet vervallen', () => {
  // Het datumveld levert middernacht; een vergelijking op tijdstip zou hier fout gaan.
  assert.equal(licentieStatus({ valid_from: '2026-01-01', valid_until: '2026-09-15T00:00:00Z' }, VANDAAG), ACTIEF)
})

test('de eerste dag telt al mee', () => {
  assert.equal(licentieStatus({ valid_from: '2026-09-15', valid_until: null }, VANDAAG), ACTIEF)
})

test('de dag voor de begindatum is toekomstig', () => {
  assert.equal(licentieStatus({ valid_from: '2026-09-16', valid_until: null }, VANDAAG), TOEKOMSTIG)
})

test('een licentie van precies een dag is die dag actief', () => {
  assert.equal(licentieStatus({ valid_from: '2026-09-15', valid_until: '2026-09-15' }, VANDAAG), ACTIEF)
})

test('toekomstig gaat voor verlopen bij een omgekeerde periode', () => {
  assert.equal(licentieStatus({ valid_from: '2027-01-01', valid_until: '2026-01-01' }, VANDAAG), TOEKOMSTIG)
})

test('geen licentie levert de eigen status op', () => {
  assert.equal(licentieStatus({ heeft_licentie: false }, VANDAAG), GEEN_LICENTIE)
  assert.equal(licentieStatus({}, VANDAAG), ACTIEF, 'zonder datums is er niets dat hem tegenhoudt')
})

test('een onleesbare datum wordt genegeerd in plaats van fataal', () => {
  assert.equal(licentieStatus({ valid_from: 'kaas', valid_until: null }, VANDAAG), ACTIEF)
})

test('elke status heeft een eigen label en kleur', () => {
  assert.equal(statusWeergave(ACTIEF).label, 'Actief')
  assert.equal(statusWeergave(VERLOPEN).label, 'Verlopen')
  assert.equal(statusWeergave(TOEKOMSTIG).label, 'Toekomstig')
  assert.equal(statusWeergave(GEEN_LICENTIE).label, 'Geen licentie')
  const kleuren = new Set([ACTIEF, VERLOPEN, TOEKOMSTIG, GEEN_LICENTIE].map(s => statusWeergave(s).achtergrond))
  assert.equal(kleuren.size, 4, 'de vier statussen moeten visueel te onderscheiden zijn')
})

test('geen einddatum wordt in het label vermeld', () => {
  assert.equal(statusWeergave(ACTIEF, true).label, 'Actief · geen einddatum')
  assert.equal(statusWeergave(VERLOPEN, true).label, 'Verlopen')
})

test('de periode wordt leesbaar weergegeven', () => {
  assert.match(periodeTekst('2026-01-01', '2026-12-31'), /1-1-2026 t\/m 31-12-2026/)
  assert.match(periodeTekst('2026-01-01', null), /geen einddatum/)
  assert.equal(periodeTekst(null, null), '—')
})

test('het overzicht draagt de status per organisatie', () => {
  const regels = licentieOverzicht(
    [KIKV, KIKG],
    [
      { id: 'l1', tenant_id: 'r1', name: 'verlopen', valid_from: '2026-01-01', valid_until: '2026-09-01', is_active: true },
      { id: 'l2', tenant_id: 'o1', name: 'toekomst', valid_from: '2026-12-01', valid_until: null, is_active: true },
    ],
    VANDAAG,
  )
  assert.equal(regels.find(r => r.tenantId === 'r1').status, VERLOPEN)
  assert.equal(regels.find(r => r.tenantId === 'o1').status, TOEKOMSTIG)
})

test('een organisatie zonder licentie krijgt de status geen licentie', () => {
  const regels = licentieOverzicht([NOORD], [], VANDAAG)
  assert.equal(regels[0].status, GEEN_LICENTIE)
  assert.equal(regels[0].geenEinddatum, false)
})

test('een licentie zonder einddatum wordt als zodanig gemarkeerd', () => {
  const regels = licentieOverzicht([NOORD], [
    { id: 'l3', tenant_id: 'o2', name: 'eeuwig', valid_from: '2026-01-01', valid_until: null, is_active: true },
  ], VANDAAG)
  assert.equal(regels[0].status, ACTIEF)
  assert.equal(regels[0].geenEinddatum, true)
})
