# Rhadix Platform — Release Notes v1.4.0

**Release date:** 19 mei 2026
**Branch:** `main`
**Phase:** 2 — Licenses, Applications & Access Control

---

## Wat is er nieuw?

### Licentie- en applicatiebeheer

RHADIX_ADMIN gebruikers kunnen nu volledig beheren welke Rhadix-modules beschikbaar zijn voor welke organisatie:

1. **Applicaties** — de vier vaste modules zijn automatisch aangemaakt bij de databasemigratie:
   - KIK-V Validator (`kikv-validator`)
   - ZIB Validator (`zib-validator`)
   - Algemene Validator (`algemeen-validator`)
   - Reconciliation Engine (`reconciliation`)

2. **Licenties** — maak een licentie aan voor een organisatie met een optionele einddatum en gebruikersgrens.

3. **Applicatietoewijzing aan organisaties** — wijs één of meer modules toe aan een organisatie, eventueel gekoppeld aan een licentie.

### Gebruikersbeheer per organisatie (ORG_ADMIN)

Organisatiebeheerders krijgen een eigen **Beheer**-scherm (knop in de navigatiebalk):

- Overzicht van alle gebruikers in de eigen organisatie.
- Per gebruiker: uitklappen om toegewezen applicaties te zien en toe te wijzen / in te trekken.
- Alleen applicaties die beschikbaar zijn voor de organisatie kunnen worden toegewezen aan gebruikers.

### Toegangsbeveiliging

- **ORG_USER** kan alleen modules gebruiken die door de organisatiebeheerder zijn toegewezen.
- Op de startpagina zijn niet-beschikbare modules voorzien van een **🔒 slotje** en het label "Geen toegang".
- Geprobeerd zonder toegang toch een scan te starten? Er verschijnt een duidelijke melding.
- De **publieke demo-flow** (zonder inloggen) blijft ongewijzigd werken.

### Koppelingen in scangeschiedenis

Elke validatierun van een ingelogde gebruiker legt nu ook `application_id` en `license_id` vast. Dit maakt toekomstige rapportage per module en per licentie mogelijk.

---

## Database-migratie

De migratie `0002_phase2_licenses` wordt automatisch uitgevoerd bij het starten van de applicatie. Er worden geen bestaande gegevens verwijderd of gewijzigd — alle nieuwe kolommen zijn nullable.

---

## Upgraden vanuit v1.3.1

Geen extra stappen vereist. De Alembic-migratie draait automatisch. Herstart de applicatie na het deployen:

```bash
docker-compose up -d --force-recreate backend
```

---

## Wat staat er nog op de roadmap?

- **Fase 3:** Betaling & licentie-automatisering (Stripe / Mollie integratie).
- Verlopen licenties blokkeren automatisch de toegang.
- Gebruikersbeheer: ORG_ADMIN kan nieuwe gebruikers uitnodigen per e-mail.
- Audit log voor alle admin-acties.
