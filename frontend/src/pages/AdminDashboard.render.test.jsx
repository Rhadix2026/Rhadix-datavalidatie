/**
 * AdminDashboard.render.test.jsx — rendertests voor de Beheer-module.
 *
 * Aanleiding: in AdminDashboard.jsx werden `licentieStatus`, `periodeTekst` en
 * `statusWeergave` gebruikt zonder import. Vite lost vrije identifiers niet op, de
 * build slaagde, en de fout kwam er pas uit als ReferenceError op het scherm van de
 * beheerder. De bestaande frontendtests dekten uitsluitend pure functies in `src/lib`;
 * geen enkel scherm werd ooit gerenderd, dus niets ving dit af.
 *
 * Deze tests renderen de échte Beheer-schermen met een gemockte API. Ze controleren
 * bewust niet de opmaak, maar dát het scherm zonder fout tot stand komt en de kernwaarden
 * toont — precies het gat waar dit defect doorheen glipte.
 *
 * De pure rekenregels blijven in `src/lib/licentieweergave.test.js` (node --test).
 */
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'

// ── De API volledig mocken: deze tests gaan over renderen, niet over netwerk ──
vi.mock('../services/api', () => {
  const leeg = () => Promise.resolve([])
  return {
    getAdminStats:          vi.fn(() => Promise.resolve({ active_tenants: 0, total_users: 0 })),
    getAdminTenants:        vi.fn(leeg),
    getAdminApplications:   vi.fn(leeg),
    getAdminLicenses:       vi.fn(leeg),
    getAdminTenantApps:     vi.fn(leeg),
    getAdminTenantLicenses: vi.fn(leeg),
    getAdminTenantUsers:    vi.fn(leeg),
    getTenantBranding:      vi.fn(() => Promise.resolve(null)),
    createAdminTenant:      vi.fn(), createAdminLicense:   vi.fn(),
    updateAdminLicense:     vi.fn(), deleteAdminLicense:   vi.fn(),
    updateAdminApplication: vi.fn(), assignAppToTenant:    vi.fn(),
    revokeAppFromTenant:    vi.fn(), adminToggleUserActive: vi.fn(),
    adminDeleteUser:        vi.fn(), adminResetUserPassword: vi.fn(),
    adminCreateUser:        vi.fn(), adminUpdateUser:      vi.fn(),
    getAdminTenantImpact:   vi.fn(), adminToggleTenantActive: vi.fn(),
    adminDeleteTenant:      vi.fn(), putTenantBranding:    vi.fn(),
    deleteTenantBranding:   vi.fn(), uploadTenantLogo:     vi.fn(),
    deleteTenantLogo:       vi.fn(), tenantLogoUrl:        vi.fn(() => ''),
  }
})

import AdminDashboard from './AdminDashboard'
import * as api from '../services/api'

// ── Bouwstenen voor testdata ────────────────────────────────────────────────

const DAG = 24 * 60 * 60 * 1000
const dagen = (n) => new Date(Date.now() + n * DAG).toISOString()

const ORG = {
  id: 'org-1', slug: 'noorderboog', name: 'Noorderboog', is_active: true,
  tenant_type: 'ORG', parent_tenant_id: null, created_at: dagen(-200),
  user_count: 3, active_user_count: 2, scan_count: 4,
}

const RSO = {
  id: 'rso-1', slug: 'kik-v', name: 'KIK-V', is_active: true,
  tenant_type: 'RSO', parent_tenant_id: null, created_at: dagen(-40),
  user_count: 1, active_user_count: 1, scan_count: 9,
}

const KIND = {
  id: 'org-2', slug: 'k', name: 'kik-g', is_active: true,
  tenant_type: 'ORG', parent_tenant_id: 'rso-1', created_at: dagen(-2),
  user_count: 2, active_user_count: 2, scan_count: 0,
}

function licentie(over = {}) {
  return {
    id: 'lic-1', tenant_id: 'org-1', tenant_name: 'Noorderboog', tenant_type: 'ORG',
    parent_tenant_name: null, actieve_gebruikers: 2,
    name: 'Jaarlicentie 2026', valid_from: dagen(-30), valid_until: dagen(90),
    max_users: 5, notes: null, is_active: true, created_at: dagen(-30),
    app_slugs: [], ...over,
  }
}

/** Render Beheer en wacht tot de organisatielijst er staat. */
async function toonBeheer({ tenants = [], licenses = [] } = {}) {
  api.getAdminTenants.mockResolvedValue(tenants)
  api.getAdminLicenses.mockResolvedValue(licenses)
  api.getAdminStats.mockResolvedValue({ active_tenants: tenants.length, total_users: 0 })
  const beeld = render(<AdminDashboard onBack={() => {}} />)
  if (tenants.length) await screen.findAllByText(tenants[0].name)
  return beeld
}

/** Klap het detail van een organisatie open. */
async function openDetail(naam, { licenses = [], users = [], apps = [] } = {}) {
  api.getAdminTenantLicenses.mockResolvedValue(licenses)
  api.getAdminTenantUsers.mockResolvedValue(users)
  api.getAdminTenantApps.mockResolvedValue(apps)
  // De naam kan op meerdere plekken staan; pak de rij die een Detail-knop bevat.
  const rij = screen.getAllByText(naam)
    .map(el => el.closest('tr'))
    .find(tr => tr && within(tr).queryByRole('button', { name: /Detail/ }))
  within(rij).getByRole('button', { name: /Detail/ }).click()
  await waitFor(() => expect(api.getAdminTenantLicenses).toHaveBeenCalled())
}

/** Wissel naar een ander tabblad. */
async function naarTab(naam) {
  screen.getByRole('button', { name: naam }).click()
  if (naam === 'Licenties') {
    await waitFor(() => expect(api.getAdminLicenses).toHaveBeenCalled())
  } else {
    await waitFor(() => expect(screen.getByText('Organisaties')).toBeTruthy())
  }
}

beforeEach(() => { vi.clearAllMocks() })
afterEach(() => { cleanup() })

// ════════════════════════════════════════════════════════════════════════════
// Beheer → Licenties
// ════════════════════════════════════════════════════════════════════════════

describe('Beheer → Licenties', () => {

  test('het overzicht rendert met organisaties én licenties', async () => {
    await toonBeheer({ tenants: [ORG, RSO, KIND], licenses: [licentie()] })
    await naarTab('Licenties')
    expect(await screen.findByText('Licenties per organisatie')).toBeTruthy()
    expect(screen.getByText('Jaarlicentie 2026')).toBeTruthy()
  })

  test('alle drie de organisaties komen erin voor, ook zonder licentie', async () => {
    await toonBeheer({ tenants: [ORG, RSO, KIND], licenses: [licentie()] })
    await naarTab('Licenties')
    await screen.findByText('Licenties per organisatie')
    for (const naam of ['Noorderboog', 'KIK-V', 'kik-g']) {
      expect(screen.getAllByText(naam).length).toBeGreaterThan(0)
    }
  })

  test('een organisatie zonder licentie toont de status Geen licentie', async () => {
    await toonBeheer({ tenants: [ORG], licenses: [] })
    await naarTab('Licenties')
    await screen.findByText('Licenties per organisatie')
    expect(screen.getAllByText('Geen licentie').length).toBeGreaterThan(0)
  })

  test('een leeg platform rendert zonder fout', async () => {
    await toonBeheer({ tenants: [], licenses: [] })
    await naarTab('Licenties')
    expect(await screen.findByText('Geen organisaties gevonden.')).toBeTruthy()
  })

  test.each([
    ['actief',     { valid_from: dagen(-10), valid_until: dagen(30) },   'Actief'],
    ['toekomstig', { valid_from: dagen(14),  valid_until: dagen(380) },  'Toekomstig'],
    ['verlopen',   { valid_from: dagen(-90), valid_until: dagen(-1) },   'Verlopen'],
    ['geen einddatum', { valid_from: dagen(-10), valid_until: null },    'Actief · geen einddatum'],
  ])('status %s wordt als label getoond', async (_naam, periode, label) => {
    await toonBeheer({ tenants: [ORG], licenses: [licentie(periode)] })
    await naarTab('Licenties')
    await screen.findByText('Licenties per organisatie')
    expect(screen.getAllByText(label).length).toBeGreaterThan(0)
  })

  test('historische licenties staan in een eigen blok', async () => {
    await toonBeheer({
      tenants: [ORG],
      licenses: [licentie(), licentie({ id: 'lic-0', name: 'Vorig jaar', is_active: false })],
    })
    await naarTab('Licenties')
    expect(await screen.findByText('Historische licenties')).toBeTruthy()
    expect(screen.getByText('Vorig jaar')).toBeTruthy()
  })
})

// ════════════════════════════════════════════════════════════════════════════
// Organisatiedetail — de plek waar het defect zichtbaar werd
// ════════════════════════════════════════════════════════════════════════════

describe('Beheer → Organisaties → Detail', () => {

  test('ZONDER licentie: toont Geen licentie en de knop om er een toe te kennen', async () => {
    await toonBeheer({ tenants: [ORG] })
    await openDetail('Noorderboog', { licenses: [] })
    expect(await screen.findByText('Licentie')).toBeTruthy()
    expect(screen.getAllByText('Geen licentie').length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: 'Licentie toekennen' })).toBeTruthy()
  })

  test('MET actieve licentie: toont naam, status, maximum en gebruik', async () => {
    // Dit scenario crashte: de actief-tak roept licentieStatus en periodeTekst aan.
    await toonBeheer({ tenants: [ORG] })
    await openDetail('Noorderboog', { licenses: [licentie({ max_users: 5 })] })
    expect(await screen.findByText('Jaarlicentie 2026')).toBeTruthy()
    expect(screen.getAllByText('Actief').length).toBeGreaterThan(0)
    expect(screen.getByText('5')).toBeTruthy()          // max_users
    expect(screen.getByText('2 van 5')).toBeTruthy()    // in gebruik
  })

  test('MET toekomstige licentie: toont de status en de uitleg dat er niemand bij kan', async () => {
    await toonBeheer({ tenants: [ORG] })
    await openDetail('Noorderboog', {
      licenses: [licentie({ valid_from: dagen(14), valid_until: dagen(380) })],
    })
    expect(await screen.findByText('Toekomstig')).toBeTruthy()
    expect(screen.getByText(/geen gebruiker worden toegevoegd of opnieuw geactiveerd/)).toBeTruthy()
  })

  test('MET verlopen licentie: toont de status en dezelfde uitleg', async () => {
    await toonBeheer({ tenants: [ORG] })
    await openDetail('Noorderboog', {
      licenses: [licentie({ valid_from: dagen(-90), valid_until: dagen(-1) })],
    })
    expect(await screen.findByText('Verlopen')).toBeTruthy()
    expect(screen.getByText(/Bestaande gebruikers houden toegang/)).toBeTruthy()
  })

  test('actieve licentie ZONDER einddatum', async () => {
    await toonBeheer({ tenants: [ORG] })
    await openDetail('Noorderboog', { licenses: [licentie({ valid_until: null })] })
    expect(await screen.findByText('Actief · geen einddatum')).toBeTruthy()
  })

  test('max_users gevuld toont het getal', async () => {
    await toonBeheer({ tenants: [ORG] })
    await openDetail('Noorderboog', { licenses: [licentie({ max_users: 5 })] })
    await screen.findByText('Jaarlicentie 2026')
    expect(screen.getByText('5')).toBeTruthy()
    expect(screen.getByText('2 van 5')).toBeTruthy()
  })

  test('max_users null toont Onbeperkt', async () => {
    await toonBeheer({ tenants: [ORG] })
    await openDetail('Noorderboog', { licenses: [licentie({ max_users: null })] })
    await screen.findByText('Jaarlicentie 2026')
    expect(screen.getByText('Onbeperkt')).toBeTruthy()
    expect(screen.getByText('2 (onbeperkt)')).toBeTruthy()
  })

  test('historische licentie wordt onder de actieve vermeld', async () => {
    await toonBeheer({ tenants: [ORG] })
    await openDetail('Noorderboog', {
      licenses: [licentie(), licentie({ id: 'lic-0', name: 'Vorig jaar', is_active: false })],
    })
    expect(await screen.findByText(/Historisch \(inactief\): Vorig jaar/)).toBeTruthy()
  })

  test('een organisatie onder een RSO meldt dat de RSO-licentie niet meetelt', async () => {
    await toonBeheer({ tenants: [KIND] })
    await openDetail('kik-g', { licenses: [] })
    expect(await screen.findByText(/samenwerkingsorganisatie telt hier niet voor/)).toBeTruthy()
  })
})

// ════════════════════════════════════════════════════════════════════════════
// Gebruikers binnen het detail — volle en niet-volle licentie
// ════════════════════════════════════════════════════════════════════════════

describe('Beheer → Organisaties → Detail → gebruikers', () => {

  const gebruikers = [
    { id: 'u-1', email: 'a@example.org', full_name: 'Actieve Gebruiker', role: 'ORG_ADMIN', is_active: true },
    { id: 'u-2', email: 'b@example.org', full_name: 'Slapende Gebruiker', role: 'ORG_USER',  is_active: false },
  ]

  test('de gebruikerstabel rendert met actieve en inactieve gebruikers', async () => {
    await toonBeheer({ tenants: [ORG] })
    await openDetail('Noorderboog', { licenses: [licentie()], users: gebruikers })
    expect(await screen.findByText('a@example.org')).toBeTruthy()
    expect(screen.getByText('Actieve Gebruiker')).toBeTruthy()
    expect(screen.getByText('Slapende Gebruiker')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Deact.' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Activ.' })).toBeTruthy()
  })

  test('zonder gebruikers verschijnt een nette melding', async () => {
    await toonBeheer({ tenants: [ORG] })
    await openDetail('Noorderboog', { licenses: [licentie()], users: [] })
    expect(await screen.findByText('Geen gebruikers.')).toBeTruthy()
  })

  test('VOLLE licentie: gebruik wordt als vol getoond en de tabel blijft werken', async () => {
    await toonBeheer({ tenants: [{ ...ORG, active_user_count: 5 }] })
    await openDetail('Noorderboog', { licenses: [licentie({ max_users: 5 })], users: gebruikers })
    await screen.findByText('Jaarlicentie 2026')
    expect(screen.getByText('5 van 5')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Deact.' })).toBeTruthy()
  })

  test('NIET-VOLLE licentie: gebruik onder het maximum', async () => {
    await toonBeheer({ tenants: [{ ...ORG, active_user_count: 2 }] })
    await openDetail('Noorderboog', { licenses: [licentie({ max_users: 5 })], users: gebruikers })
    await screen.findByText('Jaarlicentie 2026')
    expect(screen.getByText('2 van 5')).toBeTruthy()
  })

  test('de knop om een gebruiker toe te voegen is aanwezig', async () => {
    await toonBeheer({ tenants: [ORG] })
    await openDetail('Noorderboog', { licenses: [licentie()], users: gebruikers })
    expect(await screen.findByRole('button', { name: '+ Gebruiker' })).toBeTruthy()
  })
})

// ════════════════════════════════════════════════════════════════════════════
// Licentie bewerken
// ════════════════════════════════════════════════════════════════════════════

describe('Beheer → licentie bewerken', () => {

  async function openBewerken(over = {}) {
    await toonBeheer({ tenants: [ORG], licenses: [licentie(over)] })
    await naarTab('Licenties')
    await screen.findByText('Licenties per organisatie')
    screen.getAllByRole('button', { name: 'Bewerken' })[0].click()
    return await screen.findByText('Licentie bewerken')
  }

  test('de bewerkdialoog opent met de velden en de organisatie erbij', async () => {
    // Dit scenario crashte: de dialoog toont een live statusbadge (licentieStatus +
    // statusWeergave) naast de organisatienaam.
    await openBewerken()
    expect(screen.getAllByText('Noorderboog').length).toBeGreaterThan(0)
    expect(screen.getByText('Licentienaam')).toBeTruthy()
    expect(screen.getByText('Geldig vanaf')).toBeTruthy()
    expect(screen.getByText('Geldig tot (leeg = geen einddatum)')).toBeTruthy()
    expect(screen.getByText('Max. gebruikers (leeg = onbeperkt)')).toBeTruthy()
  })

  test('de statusbadge in de dialoog volgt de ingevulde periode', async () => {
    await openBewerken({ valid_from: dagen(-90), valid_until: dagen(-1) })
    expect(screen.getAllByText('Verlopen').length).toBeGreaterThan(0)
  })

  test('een licentie zonder einddatum opent zonder fout', async () => {
    await openBewerken({ valid_until: null })
    expect(screen.getAllByText('Actief · geen einddatum').length).toBeGreaterThan(0)
  })

  test('een licentie zonder maximum opent zonder fout', async () => {
    await openBewerken({ max_users: null })
    expect(screen.getByText('Licentie bewerken')).toBeTruthy()
  })
})

// ════════════════════════════════════════════════════════════════════════════
// Het vangnet zelf
// ════════════════════════════════════════════════════════════════════════════

describe('Vangnet', () => {

  test('alle helpers uit licentieweergave zijn in AdminDashboard beschikbaar', async () => {
    // Het defect was dat drie van deze helpers wel werden aangeroepen maar niet
    // geïmporteerd. Een ReferenceError zou hier als render-fout naar boven komen.
    await toonBeheer({ tenants: [ORG, RSO, KIND], licenses: [licentie()] })
    await naarTab('Licenties')
    await screen.findByText('Licenties per organisatie')
    await naarTab('Organisaties')
    await openDetail('Noorderboog', { licenses: [licentie()] })
    expect(await screen.findByText('Jaarlicentie 2026')).toBeTruthy()
  })
})
