/**
 * eslint.config.js — uitsluitend een vangnet voor ontbrekende imports.
 *
 * Aanleiding: in AdminDashboard.jsx werden drie helpers (licentieStatus, periodeTekst,
 * statusWeergave) wél gebruikt maar niet geïmporteerd. Vite lost vrije identifiers niet
 * op, dus de build slaagde en de fout kwam er pas uit als ReferenceError op het scherm
 * van de beheerder — zichtbaar als een foutscherm bij Beheer → Licenties en bij het
 * openen van het detail van een organisatie mét licentie.
 *
 * Deze configuratie is bewust minimaal: alleen `no-undef` en `no-unused-vars` voor
 * imports. Géén stijlregels, géén opinies over de bestaande code. Het doel is dat een
 * ontbrekende import voortaan in CI wordt gevonden en niet door een tester.
 */
import globals from 'globals'

export default [
  {
    files: ['src/**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: {
        ...globals.browser,
        // JSX wordt door de automatische runtime omgezet; React hoeft niet in scope.
        React: 'readonly',
      },
    },
    linterOptions: {
      // Bestaande `eslint-disable-line`-aantekeningen gaan over regels die deze
      // configuratie niet aanzet (bv. react-hooks). Ze melden als "ongebruikt" zou
      // alleen ruis opleveren, dus dat blijft uit.
      reportUnusedDisableDirectives: false,
    },
    rules: {
      // De kern én het enige doel: een naam die nergens is gedeclareerd of geïmporteerd
      // is een fout. Precies het defect dat hier is opgetreden.
      'no-undef': 'error',
      // `no-unused-vars` staat bewust UIT. Zonder eslint-plugin-react ziet ESLint niet
      // dat <Landing /> de import `Landing` gebruikt, en dan meldt die regel een reeks
      // valse positieven. Een misleidende waarschuwing is schadelijker dan geen.
    },
  },
  {
    // Testbestanden draaien in Node (node:test) of onder vitest.
    files: ['src/**/*.test.{js,jsx}'],
    languageOptions: {
      globals: { ...globals.node, ...globals.browser },
    },
  },
]
