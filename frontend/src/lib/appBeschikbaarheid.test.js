/**
 * Tests voor de beschikbaarheidsregel van de applicatietegels op het Platform.
 *
 * Draaien met de ingebouwde testrunner van Node — geen extra dependency nodig:
 *
 *     node --test frontend/src/lib/
 *
 * De regel is bewust een pure functie zonder React en zonder `import.meta.env`,
 * juist zodat dit kan.
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'

import {
  appStatus,
  isKlikbaar,
  actieLabel,
  BESCHIKBAAR,
  NIET_UITGEROLD,
  GEEN_TOEGANG,
} from './appBeschikbaarheid.js'

const DV = { id: 'dv', slug: 'datavalidatie' }
const DS = { id: 'ds', slug: 'datastation' }
const CRM = { id: 'crm', slug: 'rhadix-crm' }
const UV = { id: 'u', slug: 'uitvraag' }
const RECON = { id: 'recon', slug: 'reconciliation-engine' }

/** Gebruiker zoals /api/auth/me die teruggeeft. */
const gebruiker = (slugs, role = 'ORG_USER') => ({ role, assigned_app_slugs: slugs })

// ── Scenario 1 en 2: alleen datavalidatie toegewezen ────────────────────────
test('alleen datavalidatie toegewezen: Datavalidatie is beschikbaar', () => {
  const u = gebruiker(['datavalidatie'])
  assert.equal(appStatus(DV, u), BESCHIKBAAR)
  assert.equal(isKlikbaar(appStatus(DV, u)), true)
  assert.equal(actieLabel(appStatus(DV, u)), 'Openen →')
})

test('alleen datavalidatie toegewezen: ds, crm en uitvraag zijn niet beschikbaar', () => {
  const u = gebruiker(['datavalidatie'])
  for (const app of [DS, CRM, UV]) {
    assert.equal(appStatus(app, u), GEEN_TOEGANG, `${app.slug} hoort geen toegang te geven`)
    assert.equal(isKlikbaar(appStatus(app, u)), false, `${app.slug} mag niet aanklikbaar zijn`)
    assert.equal(actieLabel(appStatus(app, u)), 'Geen toegang')
  }
})

test('reconciliation-engine volgt dezelfde generieke regel', () => {
  const zonder = gebruiker(['datavalidatie'])
  const met = gebruiker(['datavalidatie', 'reconciliation-engine'])
  assert.equal(appStatus(RECON, zonder), GEEN_TOEGANG)
  assert.equal(appStatus(RECON, met), BESCHIKBAAR)
})

// ── Scenario 6: geldige toewijzing ──────────────────────────────────────────
test('geldige toewijzing: de applicatie is te openen', () => {
  const u = gebruiker(['datavalidatie', 'datastation'])
  assert.equal(appStatus(DS, u), BESCHIKBAAR)
  assert.equal(actieLabel(appStatus(DS, u)), 'Openen →')
  // en wat níet is toegewezen blijft dicht
  assert.equal(appStatus(CRM, u), GEEN_TOEGANG)
})

test('een lege of ontbrekende claim geeft nergens toegang', () => {
  for (const claim of [[], undefined, null]) {
    const u = { role: 'ORG_USER', assigned_app_slugs: claim }
    for (const app of [DV, DS, CRM, UV]) {
      assert.equal(appStatus(app, u), GEEN_TOEGANG)
    }
  }
})

// ── Scenario 7: platformbeheerder ───────────────────────────────────────────
test('RHADIX_ADMIN houdt toegang tot alles, ook zonder toewijzing', () => {
  const admin = gebruiker([], 'RHADIX_ADMIN')
  for (const app of [DV, DS, CRM, UV, RECON]) {
    assert.equal(appStatus(app, admin), BESCHIKBAAR, `${app.slug} hoort open te staan voor de beheerder`)
  }
})

test('een andere rol krijgt die uitzondering niet', () => {
  for (const rol of ['ORG_ADMIN', 'ORG_USER', 'RSO_ADMIN']) {
    assert.equal(appStatus(DS, gebruiker([], rol)), GEEN_TOEGANG, `${rol} hoort geen bypass te krijgen`)
  }
})

// ── Deploymentstatus staat los van autorisatie ──────────────────────────────
test('niet uitgerold weegt zwaarder dan de toewijzing', () => {
  const app = { id: 'ds', slug: 'datastation', uitgerold: false }
  assert.equal(appStatus(app, gebruiker(['datastation'])), NIET_UITGEROLD)
  assert.equal(appStatus(app, gebruiker([], 'RHADIX_ADMIN')), NIET_UITGEROLD)
  assert.equal(actieLabel(NIET_UITGEROLD), 'Binnenkort')
  assert.equal(isKlikbaar(NIET_UITGEROLD), false)
})

test('uitgerold maar niet toegewezen is iets anders dan niet uitgerold', () => {
  const u = gebruiker(['datavalidatie'])
  assert.equal(appStatus({ id: 'ds', slug: 'datastation', uitgerold: true }, u), GEEN_TOEGANG)
  assert.notEqual(appStatus({ id: 'ds', slug: 'datastation', uitgerold: true }, u), NIET_UITGEROLD)
})

// ── Randgevallen ────────────────────────────────────────────────────────────
test('zonder ingelogde gebruiker toont het portaal het aanbod', () => {
  for (const app of [DV, DS, CRM]) {
    assert.equal(appStatus(app, null), BESCHIKBAAR)
  }
})

test('een tegel zonder slug kent geen autorisatiepoort', () => {
  assert.equal(appStatus({ id: 'iets' }, gebruiker([])), BESCHIKBAAR)
})
