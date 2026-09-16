import { test } from 'node:test'
import assert from 'node:assert/strict'

import {
  DASHBOARD_STAPPEN,
  STANDAARD_TERUG,
  geldigeHerkomst,
  terugDoel,
} from './navigatie.js'

// ── De ingangen uit de melding ─────────────────────────────────────────────

test('vanaf het portaal keert het dashboard terug naar het portaal', () => {
  // De melding: inloggen, Dashboard, terug -> kwam uit in Datavalidatie.
  assert.equal(terugDoel('portal', 'user_dashboard'), 'portal')
})

test('vanaf het bronscherm blijft het gedrag ongewijzigd', () => {
  assert.equal(terugDoel('systems', 'user_dashboard'), 'systems')
})

test('de drilldown keert terug naar het platformdashboard', () => {
  assert.equal(terugDoel('platform_dashboard', 'org_dashboard'), 'platform_dashboard')
})

test('het organisatiedashboard vanaf het bronscherm gaat naar het bronscherm', () => {
  assert.equal(terugDoel('systems', 'org_dashboard'), 'systems')
})

test('het platformdashboard gaat terug naar het bronscherm', () => {
  assert.equal(terugDoel('systems', 'platform_dashboard'), 'systems')
})

// ── Standaardgedrag: zonder herkomst verandert er niets ────────────────────

test('zonder vastgelegde herkomst geldt het bestaande doel', () => {
  assert.equal(STANDAARD_TERUG, 'systems')
  for (const stap of DASHBOARD_STAPPEN) {
    assert.equal(terugDoel(null, stap), 'systems')
    assert.equal(terugDoel(undefined, stap), 'systems')
    assert.equal(terugDoel('', stap), 'systems')
  }
})

test('een onzinnige herkomst valt terug op het standaarddoel', () => {
  assert.equal(terugDoel(42, 'user_dashboard'), 'systems')
  assert.equal(terugDoel({}, 'user_dashboard'), 'systems')
})

// ── De lus die een gedeelde herkomst zou opleveren ─────────────────────────

test('een scherm keert nooit naar zichzelf terug', () => {
  // Zou het platformdashboard 'platform_dashboard' als herkomst krijgen — wat gebeurt
  // als je één gedeelde variabele voor alle drie de dashboards gebruikt — dan bleef de
  // terugknop op hetzelfde scherm hangen.
  assert.equal(terugDoel('platform_dashboard', 'platform_dashboard'), 'systems')
  assert.equal(terugDoel('user_dashboard', 'user_dashboard'), 'systems')
  assert.equal(terugDoel('org_dashboard', 'org_dashboard'), 'systems')
})

test('de drilldown-route loopt niet rond', () => {
  // platform -> organisatie -> terug -> platform -> terug -> bronscherm.
  const orgHerkomst      = 'platform_dashboard'
  const platformHerkomst = 'systems'

  assert.equal(terugDoel(orgHerkomst, 'org_dashboard'), 'platform_dashboard')
  assert.equal(terugDoel(platformHerkomst, 'platform_dashboard'), 'systems')
})

test('geldigeHerkomst weigert precies wat terugDoel zou negeren', () => {
  assert.equal(geldigeHerkomst('portal', 'user_dashboard'), true)
  assert.equal(geldigeHerkomst('user_dashboard', 'user_dashboard'), false)
  assert.equal(geldigeHerkomst(null, 'user_dashboard'), false)
})

// ── Bevindingen 1 en 4 mogen niet veranderen ───────────────────────────────

test('de terugroutes van bevinding 1 en 4 lopen niet via deze functie', () => {
  // Bevinding 4: bronscherm -> portaal. Bevinding 1: validatie -> bronscherm.
  // Die zitten op eigen onBack-regels in App.jsx en komen hier niet voorbij; deze test
  // legt vast dat die stappen geen herkomst bijhouden.
  assert.equal(DASHBOARD_STAPPEN.includes('systems'), false)
  assert.equal(DASHBOARD_STAPPEN.includes('upload'), false)
  assert.equal(DASHBOARD_STAPPEN.includes('multi_validatie'), false)
  assert.equal(DASHBOARD_STAPPEN.includes('portal'), false)
})

test('alleen de drie dashboards houden een herkomst bij', () => {
  assert.deepEqual(DASHBOARD_STAPPEN, ['user_dashboard', 'org_dashboard', 'platform_dashboard'])
})

// ── Volledige loop over de echte ingangen ──────────────────────────────────

test('elke ingang levert het scherm op waar de gebruiker vandaan kwam', () => {
  const ingangen = [
    { vanaf: 'portal',            naar: 'user_dashboard',     verwacht: 'portal' },
    { vanaf: 'systems',           naar: 'user_dashboard',     verwacht: 'systems' },
    { vanaf: 'systems',           naar: 'org_dashboard',      verwacht: 'systems' },
    { vanaf: 'systems',           naar: 'platform_dashboard', verwacht: 'systems' },
    { vanaf: 'platform_dashboard', naar: 'org_dashboard',     verwacht: 'platform_dashboard' },
  ]
  for (const { vanaf, naar, verwacht } of ingangen) {
    assert.equal(terugDoel(vanaf, naar), verwacht, `${vanaf} -> ${naar}`)
  }
})
