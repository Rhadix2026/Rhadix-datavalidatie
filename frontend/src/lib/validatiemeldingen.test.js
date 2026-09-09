/**
 * Tests voor de weergaveregels van validatiemeldingen.
 *
 *     node --test frontend/src/lib/
 *
 * Achtergrond: sinds 3 augustus (commit a082c1e) gaat ook één gekozen bron naar de
 * multi-bronpagina. Dat scherm telde de meldingen alleen en gooide ze daarna weg, dus
 * de badges bleven staan en de details verdwenen. De weergave zelf — IssueRow en
 * FileCard — bestond al en wordt nu gedeeld; hier staan de pure regels eromheen.
 *
 * De voorbeelddata komt uit de echte AFAS Profit-set: twee fouten en twee
 * waarschuwingen op Profit_Employees.json, de andere vijf bestanden zonder meldingen.
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'

import {
  verzamelMeldingen,
  telPerErnst,
  bestandenUit,
  heeftMeldingen,
  voorbeeldenLabel,
} from './validatiemeldingen.js'

// Zoals de validatie-API het teruggeeft voor de zes Profit-bestanden.
const RESPONS = {
  standard: 'algemeen',
  summary: { total_files: 6, total_rows: 47888, error_count: 4, warn_count: 2 },
  file_results: [
    {
      filename: 'Profit_Employees.json', label: 'AFAS Medewerkers', rows: 3110,
      issues: [
        { severity: 'error', type: 'invalid_bsn', field: 'BSN', count: 2,
          message: "2 van 2527 waarden in 'BSN' voldoen niet aan het bsn-formaat.",
          examples: [{ row: 2, value: '1234567' }, { row: 3, value: '123456789' }] },
        { severity: 'error', type: 'invalid_date', field: 'DateOfBirth', count: 2,
          message: "2 van 3110 waarden in 'DateOfBirth' voldoen niet aan het date-formaat.",
          examples: [{ row: 2, value: '199-02-23' }, { row: 3, value: '19995-06-14' }] },
        { severity: 'warning', type: 'prescan', field: 'Mobile', count: 14,
          message: 'Mobile — Telefoonnummer (NL E.164)',
          examples: [{ row: 1, value: '06-1234567' }, { row: 225, value: '+380673598676' }] },
        { severity: 'warning', type: 'prescan', field: 'Phone', count: 49,
          message: 'Phone — Telefoonnummer (NL E.164)',
          examples: [{ row: 74, value: 'geen' }, { row: 104, value: 'Happy Nurse - PNIL' }] },
      ],
    },
    { filename: 'Profit_Employers.json', label: 'AFAS Werkgevers', rows: 2, issues: [] },
    { filename: 'Profit_Functions.json', label: 'AFAS Functies', rows: 196, issues: [] },
    { filename: 'Profit_Illness.json', label: 'AFAS Verzuim', rows: 32599, issues: [] },
    { filename: 'Profit_OrganizationChart.json', label: 'AFAS Organigram', rows: 301, issues: [] },
    { filename: 'Profit_Timetable.json', label: 'AFAS Werkroosters', rows: 11680, issues: [] },
  ],
}

// ── De vier meldingen uit de echte set ──────────────────────────────────────

test('de echte set levert precies twee fouten en twee waarschuwingen', () => {
  const { errors, warnings } = telPerErnst(verzamelMeldingen(RESPONS))
  assert.equal(errors, 2)
  assert.equal(warnings, 2)
})

test('de meldingen dragen veld, aantal, tekst en voorbeelden', () => {
  const meldingen = verzamelMeldingen(RESPONS)
  assert.equal(meldingen.length, 4)
  for (const m of meldingen) {
    assert.ok(m.severity, 'severity ontbreekt')
    assert.ok(m.type, 'type ontbreekt')
    assert.ok(m.field, 'field ontbreekt')
    assert.ok(Number.isFinite(m.count), 'count ontbreekt')
    assert.ok(m.message, 'message ontbreekt')
    assert.ok(Array.isArray(m.examples) && m.examples.length > 0, 'examples ontbreken')
    assert.ok(Number.isFinite(m.examples[0].row))
    assert.ok('value' in m.examples[0])
  }
})

test('de twee fouten zijn de BSN- en de datumcontrole', () => {
  const fouten = verzamelMeldingen(RESPONS).filter(m => m.severity === 'error')
  assert.deepEqual(fouten.map(m => [m.type, m.field]),
                   [['invalid_bsn', 'BSN'], ['invalid_date', 'DateOfBirth']])
})

test('de twee waarschuwingen zijn de telefooncontroles', () => {
  const waarschuwingen = verzamelMeldingen(RESPONS).filter(m => m.severity === 'warning')
  assert.deepEqual(waarschuwingen.map(m => [m.type, m.field]),
                   [['prescan', 'Mobile'], ['prescan', 'Phone']])
})

// ── Welke bestanden krijgen een detailblok ──────────────────────────────────

test('alle zes bestanden komen terug, in volgorde', () => {
  assert.equal(bestandenUit(RESPONS).length, 6)
  assert.equal(bestandenUit(RESPONS)[0].filename, 'Profit_Employees.json')
})

test('alleen het bestand mét meldingen krijgt een detailblok', () => {
  const met = bestandenUit(RESPONS).filter(heeftMeldingen)
  assert.equal(met.length, 1)
  assert.equal(met[0].filename, 'Profit_Employees.json')
})

test('een bestand zonder meldingen krijgt geen detailblok', () => {
  for (const b of bestandenUit(RESPONS).slice(1)) {
    assert.equal(heeftMeldingen(b), false, `${b.filename} zou geen detailblok mogen krijgen`)
  }
})

test('ontbrekende of lege respons levert geen bestanden en geen meldingen', () => {
  for (const leeg of [null, undefined, {}, { file_results: null }]) {
    assert.deepEqual(bestandenUit(leeg), [])
    assert.deepEqual(verzamelMeldingen(leeg), [])
    assert.deepEqual(telPerErnst(verzamelMeldingen(leeg)), { errors: 0, warnings: 0 })
  }
})

// ── "eerste N van M" ────────────────────────────────────────────────────────

test('meer meldingen dan voorbeelden toont het volledige aantal', () => {
  assert.equal(voorbeeldenLabel(49, 2), 'Voorbeelden (eerste 2 van 49)')
  assert.equal(voorbeeldenLabel(14, 2), 'Voorbeelden (eerste 2 van 14)')
})

test('alle meldingen zichtbaar toont geen aantal', () => {
  assert.equal(voorbeeldenLabel(2, 2), 'Voorbeelden')
  assert.equal(voorbeeldenLabel(1, 1), 'Voorbeelden')
})

test('minder voorbeelden dan meldingen is de enige reden voor de toevoeging', () => {
  assert.equal(voorbeeldenLabel(2, 5), 'Voorbeelden')
})

test('ontbrekende aantallen leveren geen kapotte tekst op', () => {
  for (const label of [voorbeeldenLabel(undefined, 2), voorbeeldenLabel(5, undefined),
                       voorbeeldenLabel(null, null)]) {
    assert.equal(label, 'Voorbeelden')
    assert.ok(!label.includes('undefined') && !label.includes('NaN'))
  }
})

// ── Meerdere bronnen naast elkaar ───────────────────────────────────────────

test('per bron worden alleen de eigen bestanden geteld', () => {
  const afas = RESPONS
  const ons = {
    file_results: [
      { filename: 'medewerker_ons.csv', label: 'ONS Medewerkers', rows: 40,
        issues: [{ severity: 'warning', type: 'prescan', field: 'Mobile', count: 3,
                   message: 'Mobile — Telefoonnummer (NL E.164)',
                   examples: [{ row: 5, value: 'onbekend' }] }] },
    ],
  }
  assert.deepEqual(telPerErnst(verzamelMeldingen(afas)), { errors: 2, warnings: 2 })
  assert.deepEqual(telPerErnst(verzamelMeldingen(ons)), { errors: 0, warnings: 1 })
  assert.equal(bestandenUit(ons)[0].filename, 'medewerker_ons.csv')
})

test('meldingen dieper in de respons tellen ook mee', () => {
  const genest = { benchmark: { file_results: [{ filename: 'x.csv',
    issues: [{ severity: 'error', type: 't', field: 'f', count: 1, message: 'm', examples: [] }] }] } }
  assert.equal(verzamelMeldingen(genest).length, 1)
})
