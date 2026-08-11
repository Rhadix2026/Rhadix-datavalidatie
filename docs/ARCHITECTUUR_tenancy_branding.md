# Rhadix — identiteit, dataschotten & branding per component

**Doel van deze notitie.** Vastleggen hoe de Rhadix-componenten zich verhouden tot drie
onafhankelijke vragen die vaak door elkaar lopen:

1. **Identiteit** — reist de organisatie-identiteit (bv. KIK-V) mee als je vanuit het platform
   doorklikt?
2. **Dataschotten** — is opgeslagen data afgeschermd *per organisatie* (multi-tenant)?
3. **Branding** — reist de huisstijl/het logo van de organisatie mee in de UI?

Deze drie staan **los van elkaar**. Je kunt als KIK-V ingelogd zijn (identiteit), in een app
werken die je data per organisatie afschermt (dataschot), terwijl je tóch de generieke
Rhadix-huisstijl ziet (branding). Precies dat is bij de sub-apps het geval, en dat leidt tot
verwarring als je de drie op één hoop gooit.

## Hoe de identiteit reist (SSO)

Het platform (Datavalidatie-backend) is de centrale identiteitsuitgever ("SureSync ID").
Bij inloggen wordt een RS256-getekend token gezet als cookie `rhadix_sso` op domein
`.rhadix.nl`, met o.a. de claims `email`, `name`, `role`, `tenant_name` en `apps`.

De resource-apps (Uitvraag, Datastation, CRM) verifiëren dat token met de **publieke** sleutel
(`CENTRAL_JWT_PUBLIC_KEY`, issuer `suresync-id`) — ze kunnen dus verifiëren maar niet zelf
tokens maken. Uit de claims wordt ter plekke een lokale gebruiker/tenant aangemaakt of
gesynchroniseerd (JIT-provisioning). In Uitvraag is dat letterlijk zichtbaar:

```
tname = claims.get("tenant_name") or "SureSync"
# → tenant met slug/naam = tenant_name uit het centrale token
```
(`rhadix-uitvraag/backend/app/auth/dependencies.py`, `_provision_from_claims`)

**Gevolg:** voor `rhouwen@zinl.nl` met platform-organisatie "KIK-V" wordt in de sub-apps
`current.tenant.name = "KIK-V"`. De identiteit is dus **niet** afgeleid van het e-maildomein
(`zinl.nl`) en **niet** een vaste gedeelde tenant — KIK-V reist mee.

## Overzicht per component

| Component | Identiteit reist mee | Dataschotten per organisatie | Branding reist mee |
|---|---|---|---|
| **Datavalidatie** (platform) | Ja — is de uitgever | **Ja** — `tenant_id` op validaties, overal gefilterd | **Ja** — leest `/auth/me` + BrandingContext |
| **Uitvraag** | Ja (JIT uit token) | **Ja** — uitvragen/antwoorden gefilterd op `tenant_id` | **Nee** — eigen hardcoded Rhadix-stijl |
| **Datastation** | Ja (JIT uit token) | **Nee** — één gedeeld station, geen `tenant_id` | **Nee** — eigen hardcoded Rhadix-stijl |
| **CRM** | Ja (JIT uit token) | **Gemengd** — taken tenant-afgeschermd; directory gedeeld | **Nee** — eigen Rhadix-stijl |
| **Reconciliation Engine** | Ja — deel van platform-backend | **N.v.t.** — stateless, geen opslag | Volgt platform-UI |

## Toelichting per component

**Datavalidatie (platform).** Per organisatie afgeschermd: validatieruns dragen `tenant_id`
en elke gevoelige query filtert daarop; tenant-isolatie is expliciet ingebouwd en getest.
De per-org branding (preset/kleuren/logo, met overerving org → RSO → platform → Rhadix-default)
leeft hier: `/auth/me` levert de effectieve branding, de platform-frontend zet daarmee de
CSS-variabelen en het logo.

**Uitvraag.** Óók per organisatie. Elke uitvraag krijgt `tenant_id = current.tenant_id`
(`routers/uitvragen.py:87`) en alle lees-queries filteren daarop (`:146`, `:156`, `:221`).
Uitzondering: het register van zorgaanbieders is een gedeeld/globaal register (geen
tenant-filter, `:81–83`). De KIK-V-huisstijl reist hier **niet** mee — de app heeft z'n eigen
navy Rhadix-header en logo en leest de tenant-branding niet op.

**Datastation.** Bewust **niet** per organisatie: `DatastationVraag` heeft geen `tenant_id`,
de inbox-queries (`routers/datastation.py:215`, `:229`, `:243`) filteren op niets, en de
RDF-store is één proces-globale singleton (`datastation/store.py:103`). De inkomende
endpoints (`/beantwoord`, `/vragen`, `/vragen/{id}/resultaat`) zijn zelfs bewust publiek
(server-to-server; Uitvraag post er rechtstreeks naartoe). Het veld `afnemer` is puur een
label ("Aangevraagd door …") en schermt niets af. Conceptueel klopt dit: een datastation
hóórt bij één zorgaanbieder, de data blijft bij de bron — in de demo is dat één station voor
iedereen. Branding: eigen hardcoded Rhadix-stijl.

**CRM.** Gemengd. Taken zijn tenant-afgeschermd en strikt geïsoleerd; de adres-/relatie-
directory (organisaties + contactpersonen) is een centraal beheerde, gedeelde master —
geen per-klant-data. Branding: eigen Rhadix-stijl.

**Reconciliation Engine.** Zit fysiek ín de platform/Datavalidatie-backend
(`rhadix/backend/app/reconciliation/`, gemount op `/api/reconciliation`) en staat als
app-tegel "reconciliation-engine" in dezelfde app-lijst. Het is een **stateless
reken-/vergelijkingsengine**: de endpoints (`calculate/{indicator}`, `reconcile/{indicator}`,
`sparql-reconcile`, `batch`, `happy-flow/batch`) nemen een geüpload bestand of een
SPARQL-endpoint, rekenen verwachte vs. actuele indicatorwaarden op recordniveau uit en geven
het resultaat terug. Er wordt niets per-tenant weggeschreven, dus "per organisatie" is niet van
toepassing — het is schotloos omdat er geen opslag is, niet omdat het gedeeld is zoals het
datastation. Omdat het bij de platform-backend hoort, volgt het de platform-UI (en dus wél de
branding), niet een aparte sub-app-stijl.

## Belangrijk voor het "afnemer"-gedrag in de inbox

De `afnemer` wordt **op het moment van versturen** per vraag vastgelegd (uit
`current.tenant.name` in Uitvraag, doorgestuurd naar het datastation). Bestaande inbox-rijen
die vóór deze wijziging zijn aangemaakt, houden hun oude waarde (bv. het e-mailadres) — die
veranderen niet met terugwerkende kracht. Alleen een **verse uitvraag, verstuurd nadat de
Uitvraag-backend opnieuw is gedeployed**, krijgt de organisatienaam ("KIK-V") mee.

---
*Bronnen (lokale repo's): `rhadix-uitvraag/backend/app/auth/dependencies.py`,
`rhadix-uitvraag/backend/app/routers/uitvragen.py`,
`Rhadix-datastation/backend/app/routers/datastation.py`,
`Rhadix-datastation/backend/app/models/datastation_models.py`,
`Rhadix-datastation/backend/app/datastation/store.py`,
`rhadix/backend/app/reconciliation/router.py`, `rhadix/backend/app/main.py`,
en de projectdocumentatie in `rhadix/CLAUDE.md` / `SAAS_DESIGN.md`.*
