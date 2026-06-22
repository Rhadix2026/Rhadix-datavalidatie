# CLAUDE.md — Rhadix projectgeheugen

Dit bestand wordt automatisch gelezen bij elke nieuwe sessie. Het bevat alle projectkennis zodat er geen context verloren gaat bij restarts.

**Instructie voor Claude:** Lees dit bestand aan het begin van elke sessie. Werk de sessie-log bij aan het einde van elke sessie met een korte samenvatting van wat er gedaan is, en commit de update naar main + staging.

---

## Project

**Rhadix Datavalidatie** — een KIK-V / ZIB-validatietool voor zorginstellingen.
- **Repos:**
  - https://github.com/Rhadix2026/Rhadix-datavalidatie (deze app)
  - https://github.com/Rhadix2026/rhadix-uitvraag
  - https://github.com/Rhadix2026/Rhadix-datastation
- **Stack:** FastAPI (Python) backend, React/Vite frontend, PostgreSQL, Docker
- **Server:** `46.224.224.26` (Hetzner VPS, Ubuntu, 4GB RAM, 2GB swap)
- **SSH:** `ssh root@46.224.224.26`

---

## Git-credentials (lokaal)

De git-credentials staan opgeslagen in:
```
/Users/renehouwen/Downloads/rhadix-git/.git/config
```
Token: `<zie .git/config in rhadix-git repo>`

**Let op:** Bij git-operaties vanuit de sandbox altijd klonen naar /tmp/ (niet naar de gemounte map) vanwege lock-file problemen:
```bash
git clone https://<token>@github.com/Rhadix2026/Rhadix-datavalidatie.git /tmp/rhadix-work
cd /tmp/rhadix-work
git config user.email "rhadix@rhadix2026.nl"
git config user.name "Rhadix2026"
```

---

## Branch-strategie & deployen

| Branch | Omgeving | Hoe deployen |
|--------|----------|--------------|
| `main` | geen auto-deploy | Alleen via versie-tag |
| `staging` | Staging (poort 5175/8011) | Push naar staging = automatisch |
| `v*.*.*` tag op main | Productie (poort 5174/8010) | Tag aanmaken, GitHub Actions, handmatige goedkeuring |

### Na elke wijziging op main ook naar staging pushen:
```bash
git checkout staging && git merge main --no-edit && git push origin staging && git checkout main
```

### Nieuwe productie-release:
```bash
git tag v1.5.X && git push origin v1.5.X
```

**Huidige versie:** v1.5.27

---

## Server — handmatige herstelcommando's

Als productie down is:
```bash
ssh root@46.224.224.26
cd /opt/rhadix-app
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

Inhoud .env.production als die ontbreekt:
```
GHCR_ORG=rhadix2026
DB_PASSWORD=<zie PROD_DB_PASSWORD in GitHub Secrets>
JWT_SECRET_KEY=<zie PROD_JWT_SECRET_KEY in GitHub Secrets>
RHADIX_LICENSE_KEY=<zie PROD_LICENSE_KEY in GitHub Secrets>
```

---

## Server-configuratie (stabiel)

- Docker on boot: `systemctl is-enabled docker` → enabled ✓
- Restart policy: `restart: always` op alle containers ✓
- Swap: 2GB `/swapfile` — controleer na reboot of swap in /etc/fstab staat!
- Geen OOM-history

---

## Codebase — belangrijke bestanden

| Bestand | Inhoud |
|---------|--------|
| `frontend/src/components/UI.jsx` | Nav, RhadixLogo, TreeDecoration componenten |
| `frontend/src/pages/Landing.jsx` | Landingspagina |
| `frontend/src/pages/LoginScreen.jsx` | Loginpagina |
| `frontend/src/App.jsx` | Routing + state (`step`) |
| `frontend/src/index.css` | CSS-variabelen (`--blue-hero`, `--blue-dark`, etc.) |
| `frontend/public/rhadix-logo.jpg` | Brand logo JPG (68KB, donkere achtergrond) |
| `frontend/public/rhadix-boom.jpg` | Brand boom JPG (84KB, donkere achtergrond) |
| `landing/index.html` | Marketing website (rhadix.nl) — apart van de Vite app |

---

## Bekende issues & oplossingen

- **Git lock-files in sandbox:** altijd naar `/tmp/` klonen, nooit naar gemounte Downloads-map
- **Staging toont oude versie:** pushes naar `main` deployen NIET naar staging — altijd handmatig mergen naar `staging` branch na een main-push
- **Browser-cache (immutable assets):** na logo/asset-updates altijd hard refresh `Cmd+Shift+R`
- **Auth-bootstrap (was destructieve testopzet):** bij startup wordt `admin@rhadix.nl` **niet-destructief** geborgd (aangemaakt als die ontbreekt; nooit `TRUNCATE` van users). `AUTH_RESET=0` slaat het over. Wachtwoord stond hardcoded en is gelekt — bij gelegenheid wijzigen.
- **AFAS-import JSON:** de import-kant accepteert sinds 2026-06-17 ook AFAS GetConnector JSON (`{skip,take,rows}`), naast XML. JSON- en XML-parser leveren identieke rijen (pariteit getest).
- **Bad gateway productie:** controleer of `.env.production` aanwezig is én `GHCR_ORG=rhadix2026` erin staat

---

## Sessie-log

| Datum | Versie | Wijziging |
|-------|--------|-----------|
| 2026-06-18 | — | Fase 1 stap 1b+1c: Uitvraag+Datastation accepteren centraal SureSync ID-token (RS256 via CENTRAL_JWT_PUBLIC_KEY of cookie) met JIT-provisioning + rol-mapping; lokale login blijft fallback. Centraal: product-Applications (datavalidatie/uitvraag/datastation) idempotent geseed (`_ensure_apps`) voor centrale toegangssturing. Identiteit brand-agnostisch (Rhadix+SureSync). Aanzetten = RSA-sleutels in env + gedeeld domein (*.rhadix.nl). Suites groen. |
| 2026-06-18 | — | Fase 1 centrale identiteit (SureSync ID), stap 1: token SSO-klaar gemaakt. Verrijkte claims (tenant_name, name, email, apps, iss). RS256/JWKS **optioneel** (env JWT_PRIVATE_KEY/JWT_PUBLIC_KEY; anders HS256 — bestaand gedrag intact), nieuw endpoint GET /api/auth/jwks. SSO-cookie 'rhadix_sso' op gedeeld domein als SSO_COOKIE_DOMAIN gezet is (bv. .rhadix.nl). Alles additief; 159 tests groen. Activeren = RSA-sleutels + SSO_COOKIE_DOMAIN in deploy-env zetten. |
| 2026-06-18 | — | White-label merk-laag (staging-only): `brand.js` (rhadix default + suresync), `index.css` `:root[data-brand=suresync]` provisorisch teal-palet, App.jsx brand-state (URL `?brand=`/sessionStorage) zet `data-brand` op <html>, AppPortal merk-bewust logo/sub + 'SureSync'-knop (gegate op VITE_RHADIX_ENV != production). Volledig omkeerbaar; productie ongewijzigd. SureSync-kleuren/logo nog VOORLOPIG (wachten op brand guide). |
| 2026-06-18 | v1.5.27 | RELEASE: AFAS-herkenning Werkgevers/Functies/Organigram (3 templates toegevoegd), geslacht 'X' toegestaan, en navy-palet-herstel meegenomen naar productie. 157 tests groen. |
| 2026-06-18 | — | AFAS-import fix: 3 ontbrekende connectoren toegevoegd aan AFAS_TEMPLATES (employers/Werkgevers, functions/Functies, organisation/Organigram). Die gaven 'Bestandstype niet herkend'. Herkenning nu ook op officiële `GetConnector_Profit_*`-namen + header-signature. Velden geverifieerd tegen aangeleverde AFAS-templates (5/6 identiek; Organigram-template was foutief een kopie van Werkgevers — echte org-chart-velden gebruikt). 156 tests groen. |
| 2026-06-17 | v1.5.26 | RELEASE: palet-regressie hersteld — productie weer navy (groen alleen op staging via data-env). |
| 2026-06-17 | — | Fix palet-regressie: door eerdere `-X theirs` staging->main merges was het staging-groene palet op productie beland. index.css nu omgevings-gestuurd: `:root` = navy (prod), `:root[data-env=staging]` = salie groen; main.jsx zet data-env uit VITE_RHADIX_ENV. Identiek op beide branches -> merge kan palet niet meer wisselen. |
| 2026-06-17 | v1.5.25 | RELEASE: Datastation-knop op productie geactiveerd -> https://datastation.rhadix.nl (Datastation kreeg eigen prod-deploy v1.0.0 + nginx-vhost 5180/8016 + Cloudflare DNS). Tevens portal staging Datastation-URL gecorrigeerd 5176->5181 (5176 was Uitvraag-prod). |
| 2026-06-17 | v1.5.24 | RELEASE naar productie: staging -> main gemerged. Bevat: AFAS GetConnector JSON-import (parse_json_bytes), niet-destructieve auth-bootstrap (geen TRUNCATE), werkende demo-login achter DEMO_SEED/staging, Beheer-knop op landing, portal-volgorde DV/Uitvraag/Datastation met omgevings-afhankelijke URL's (Datastation prod='Binnenkort'). 153 tests groen. |
| 2026-06-17 | — | Portal-URL's omgevings-afhankelijk via VITE_RHADIX_ENV: Uitvraag prod=https://uitvraag.rhadix.nl / staging=:5177; Datastation staging=:5176 actief, prod='Binnenkort' (Rhadix-datastation heeft nog geen prod-release: geen tags). Voorbereiding release v1.5.24. |
| 2026-06-17 | — | Demo achter eigen vlag: backend `_ensure_demo_user` nu gegate door `DEMO_SEED` (expliciet wint; default alleen seeden als `RHADIX_ENV=staging`) i.p.v. AUTH_RESET. Frontend: 'Demo toegang'-blok op loginscherm alleen tonen buiten productie (VITE_RHADIX_ENV != production). Prod blijft schoon, staging houdt demo. env-examples: DEMO_SEED gedocumenteerd. Suite 153 passed. |
| 2026-06-17 | — | Demo + beheer: demo-login werkend gemaakt — `_ensure_demo_user` seedt idempotent demo1@rhadix.nl (ORG_ADMIN) in tenant 'rhadix-demo' met app-toegang (TenantApplication+UserApplication voor alle actieve apps). Beheer-knop toegevoegd aan Landing-header (RHADIX_ADMIN->Admin/AdminDashboard, ORG_ADMIN->OrgAdminDashboard); header negeerde onAdmin/onOrgAdmin eerder. Suite 153 passed. |
| 2026-06-17 | — | Portal (AppPortal.jsx): volgorde Datavalidatie -> Uitvraag -> Datastation, alle knoppen 'Inloggen', Datastation geactiveerd (env VITE_DATASTATION_URL, fallback poort 5176, bevestigd door Rene). Uitvraag/Datastation-URL per omgeving via VITE_*. |
| 2026-06-17 | — | Alignment + security: destructieve `_reset_single_admin` (TRUNCATE users + hardcoded admin elke herstart) vervangen door niet-destructieve `_ensure_admin` (admin geborgd, gebruikers behouden). AppPortal Uitvraag-knop label 'Openen'->'Inloggen' op staging (gelijk aan main; URL blijft env-specifiek). Token uit git-remote verwijderd. Repo-divergentie in kaart: staging 22 vóór op main, main 2 (Uitvraag-knop + testopzet). Plan: staging=bron -> release naar prod na test. Suite 153 passed. |
| 2026-06-17 | — | Import-kant: JSON-parser (`parse_json_bytes`) toegevoegd voor AFAS GetConnector-formaat `{skip,take,rows}` + losse dict/array; `json` toegevoegd aan parse_upload, extensie-allowlist en frontend accept-filters (Upload.jsx, ReconciliationDashboard.jsx). 5 nieuwe tests incl. XML/JSON-pariteit; pariteit bevestigd op 6 echte connector-bestanden (Werkgevers, Organigram, Functies, Medewerkergegevens, roosters, verzuimverloop). Volledige suite 153 passed. Repo-URL's (3) vastgelegd. |
| 2026-06-09 | — | Reconciliation Engine — "SPARQL loslaten op de data": nieuwe `rdf_store.py` (kolom→concept mapping → RDF-triples → triple store). **Fuseki** als triple store toegevoegd aan alle docker-compose-bestanden (stain/jena-fuseki:5.1.0, -Xmx512m, intern netwerk) met **rdflib in-memory fallback**. Nieuwe endpoints: GET /concepts, POST /preview-columns, POST /sparql-reconcile. Frontend: SparqlOnDataPanel in manual-tab (kolom→concept mapping-UI, record-class + ID-kolom keuze, triples genereren + SPARQL draaien, resultaat + vergelijking met berekeningsregel). XML-fix in Happy Flow drag-drop. Env-var FUSEKI_PASSWORD/STAGING_FUSEKI_PASSWORD. |
| 2026-05-26 | — | Reconciliation Engine: happy flow batch-feature gebouwd. 24 YAML-regels voor alle CSV-typen (medewerker, werkovereenkomst, client, verzuim, financieel, vestiging, functie, kostenplaats). Nieuw endpoint POST /api/reconciliation/happy-flow/batch + GET /happy-flow/rules. Frontend: tabblad "Happy Flow batch" met multi-file upload, auto-detectie op bestandsnaam, SPARQL-koppeling vanuit uitwisselprofiel. DayFirst=True fix voor dd/MM/yyyy datumnotatie. |
| 2026-05-22 | v1.5.15 | SVG logo vervangen door JPG brand assets (logo + boom) in UI.jsx, Landing.jsx, LoginScreen.jsx |
| 2026-05-22 | — | Productie hersteld na bad gateway: .env.production ontbrak, GHCR_ORG miste |
| 2026-05-22 | — | Server gestabiliseerd: 2GB swap toegevoegd, Docker-on-boot bevestigd, restart:always aanwezig |
| 2026-05-23 | — | Productie hersteld (502), swap-persistent fix, deploy workflow verbeterd met automatische rollback |
| 2026-05-22 | v1.5.19 | Terug-knop (→ login) + Dashboard-knop volgorde in nav landing page |
| 2026-05-22 | v1.5.18 | Terug naar rhadix.nl knop toegevoegd aan nav |
| 2026-05-22 | v1.5.17 | NavBack import fix UserDashboard (wit scherm), staging groen kleurenpalet hersteld |
| 2026-05-22 | v1.5.16 | Staging gereset naar main, pipeline hersteld (staging=groen, prod=navy) |
| 2026-05-22 | — | CLAUDE.md aangemaakt als persistent projectgeheugen |
| 2026-05-21 | v1.5.14 | BIO security hardening (B01-B10) voltooid |
