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

**Huidige versie:** v1.7.0

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

## ✅ SSO op productie — OPGELOST (2026-06-24)

Eén login over alle 4 apps werkt: token op app.rhadix.nl is **RS256** (kid suresync-id-1); uitvraag/datastation/crm geven 200 op `/api/auth/me` met het centrale token. **Oorzaak was** lege `JWT_PRIVATE_KEY` (GitHub-secret `PROD_JWT_PRIVATE_KEY` kwam leeg binnen). **Fix:** privésleutel als one-liner base64 in `/opt/rhadix-app/jwt_private.env` (persistent, chmod 600) + `deploy-production.yml` injecteert dat bestand bij elke deploy (i.p.v. de lege secret). Publieke sleutel staat als default in de 4 prod-composes. priv.pem-backup: bewaar veilig.

### (historie) OPENSTAAND was: SSO op productie afmaken

**Status:** CRM logt wél via SSO in, Uitvraag/Datastation/Datavalidatie nog niet.
**Oorzaak (bevestigd op server):** op datavalidatie-prod is **`JWT_PRIVATE_KEY` leeg**
(`/opt/rhadix-app/.env.production` regel 13 = `JWT_PRIVATE_KEY=` zonder waarde; in de
container lengte 1). `JWT_PUBLIC_KEY` staat er wél (605 tekens). Daardoor tekent de uitgever
met **HS256** i.p.v. RS256 → de resource-apps wijzen het centrale token af (401).
De GitHub-secret `PROD_JWT_PRIVATE_KEY` kwam bij de deploy **leeg** binnen (verkeerd/leeg opgeslagen).

**Fix (kies één):**
1. *Server-direct (snel):* op `46.224.224.26`, in `/opt/rhadix-app`:
   `base64 < /tmp/priv.pem | tr -d '\n'` → in `.env.production` als `JWT_PRIVATE_KEY=<oneliner>` zetten
   (regel vervangen), dan `docker compose -p <PROJ> -f docker-compose.prod.yml --env-file .env.production up -d --force-recreate backend`.
   (PROJ via `docker inspect <backend-container> --format '{{ index .Config.Labels "com.docker.compose.project"}}'`.)
   Werkt alleen als `/tmp/priv.pem` er nog staat.
2. *Vers paar:* nieuw RS256-paar genereren, privé als `JWT_PRIVATE_KEY` op de server + als secret
   `PROD_JWT_PRIVATE_KEY`, en de **nieuwe PUBLIEK** (base64) herbakken als default
   `JWT_PUBLIC_KEY`/`CENTRAL_JWT_PUBLIC_KEY` in de vier prod-composes → 4 mini-releases.
3. *Durabel:* zorg dat secret `PROD_JWT_PRIVATE_KEY` (repo Rhadix-datavalidatie) de **one-liner base64**
   is (begint met `LS0tLS1CRUdJTiBQUklW`, géén enters), dan redeploy → blijft staan bij volgende deploys.

**Verificatie na fix:** login app.rhadix.nl → token-header moet `RS256` zijn → `GET /api/auth/me`
met dat token op uitvraag/datastation/crm geeft 200 + de user (JIT).

**SSO-bedrading (staat al goed):** uitgever = datavalidatie (`JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY`/
`JWT_ISSUER=suresync-id`/`SSO_COOKIE_DOMAIN=.rhadix.nl`); resource-apps = `CENTRAL_JWT_PUBLIC_KEY`
(prod-publieke sleutel als default in compose) + `CENTRAL_JWT_ISSUER=suresync-id`. Cookie `rhadix_sso`
op `.rhadix.nl` wordt al gezet.

**Veiligheid:** een `ghp_`-GitHub-token + admin-wachtwoorden stonden in platte tekst zichtbaar in een
notitiebestand — token intrekken/roteren.


## Sessie-log

| Datum | Versie | Wijziging |
|-------|--------|-----------|
| 2026-06-29 | CRM v0.1.4 | Taken-/workflowmodule + mailserver naar CRM-PRODUCTIE. Mail-env toegevoegd aan CRM docker-compose (prod+staging) en deploy-workflows lezen `/opt/crm-app/mail.env` in (zoals DV). PUBLIC_BASE_URL per omgeving via compose-default (prod=crm.rhadix.nl, staging=crm-staging.rhadix.nl); SMTP/MAIL_ENABLED default UIT. tasks-tabel komt bij deploy via bootstrap `create_all`. staging->main gemerged, tag v0.1.4 (deploy wacht op goedkeuring). 24 tests groen. OPEN bij Rene: `mail.env` plaatsen op server voor zowel CRM (`/opt/crm-app/mail.env`) als Datavalidatie (`/opt/rhadix-app/mail.env`) met de Scaleway-SMTP-creds; CRM hoeft GEEN PUBLIC_BASE_URL in mail.env (compose regelt per omgeving). |
| 2026-06-29 | — | CRM-data naar PRODUCTIE gemigreerd (via CRM-API, idempotent script `scripts/crm_data_migratie.py`). 169 organisaties verrijkt (website/plaats/KvK/e-mail/LinkedIn/bron/betrouwbaarheid; 162 met website/kvk/plaats — 7 bewust leeg zonder openbare bron) en 219 contactpersonen aangemaakt (prod 68->287). Match op organisatienaam; accounthouder_id bewust niet meegenomen (UUID's verschillen per omgeving). Cloudflare blokkeerde kale urllib (fout 1010) -> browser-User-Agent toegevoegd. Inloggegevens via env, niet in git. OPEN bij Rene: prod-mail Datavalidatie (mail.env), en deploy-goedkeuringen v1.7.0/v0.1.3 in GitHub Actions controleren. |
| 2026-06-29 | CRM v0.1.3 | CRM gelijktrekken + taken-module geport. (1) CRM staging->main gemerged (schone auto-merge, SSO-prodsleutel CENTRAL_JWT_PUBLIC_KEY behouden): genereer-krachtenveld-knop + KvK/plaats + e-mail/LinkedIn/accounthouder naar prod; tag v0.1.3 (deploy wacht op goedkeuring). 18 tests groen. (2) Taken-/workflowmodule + generieke mailer vanuit Datavalidatie geport naar CRM op staging-branch: task_models met dialect-neutraal GUID-type (CRM heeft geen Alembic -> tabel via bootstrap Base.metadata.create_all), /api/tasks-router (rol RHADIX_ADMIN->PLATFORM_ADMIN, app_slug=rhadix-crm), Taken-tab+pagina (scope mine/created/all, prioriteit/toewijzen/status/deadline) + API-functies. 6 nieuwe tests; CRM-suite 24 groen, frontend-build schoon. OPEN: CRM-data staging->prod migreren (verrijking zit in staging-DB; via CRM-API herladen — wacht op staging+prod login/URL's); prod-mail Datavalidatie activeren (mail.env met prod PUBLIC_BASE_URL op server); v1.7.0 (DV) + v0.1.3 (CRM) prod-deploys goedkeuren in GitHub Actions. Ook opgeleverd: functioneel Word-document 'Rhadix_Index_validatiechecks.docx' (validatiechecks + Rhadix Index-formules) voor externe review. |
| 2026-06-29 | v1.7.0 | RELEASE — staging en productie gelijkgetrokken. `staging`->`main` gemerged (schone auto-merge, geen conflicten): main krijgt de taken-/workflow-module + Scaleway-mailer + AFAS-fixes (openpyxl `read_only`-fallback, robuuste datumparser zonder dag/maand te gokken, `normalize_verzuimtype`); SSO-prodconfig (RS256/JWT, `SSO_COOKIE_DOMAIN=.rhadix.nl`) én mail-config blijven beide behouden in `docker-compose.prod.yml` + `deploy-production.yml`. staging daarna fast-forward gelijkgetrokken aan main (branches identiek). 179 tests groen. Tag v1.7.0 -> prod-deploy via GitHub Actions (handmatige goedkeuring). NB: prod-mail pas actief na zetten `mail.env` met prod `PUBLIC_BASE_URL` (zie Taken_email_activatie_Scaleway.md). |
| 2026-06-26 | — | VOLGENDE STAPPEN (nu echte e-mail werkt): (1) generieke "wachtwoord vergeten"-flow — reset-link via mail met aflopende token, herbruikbaar over de 4 apps; (2) gebruikersbeheer met ECHTE adressen + uitnodigings-/welkomstmail ("stel je wachtwoord in"-link i.p.v. handmatig ww door beheerder); (3) nep/placeholder-e-mailadressen opruimen/vervangen door echte. LET OP bij (3): eerst OVERZICHT placeholder vs echt maken; admin@rhadix.nl en bestaande ECHTE accounts NIET raken (admin-login moet blijven werken); demo-accounts achter demo-vlag laten of bewust opruimen; AVG dataminimaal. Reeds open: CRM-port takenmodule (#48) en prod-release taken+CRM-verrijking. |
| 2026-06-26 | — | TAKEN/WORKFLOW-MODULE + e-mailnotificaties (staging, Datavalidatie). Generieke, app-onafhankelijke takenlijst op gebruikersniveau: nieuwe `tasks`-tabel (tenant-gescoped; assignee/created_by→users; status/prioriteit/deadline; source_type/ref/label voor koppeling AFAS/CRM). `/api/tasks` router (lijst mine/created/all, summary-badge, assignable-users, create, bulk, patch, delete) — toewijzen alleen binnen eigen organisatie; ORG_ADMIN ziet via tabblad 'Hele organisatie' alles binnen de tenant, gewone gebruiker alleen eigen toegewezen/aangemaakt; strikt tenant-gescoped (ook RHADIX_ADMIN). Frontend: 'Mijn taken'-widget + knop op Landing (alleen ingelogd), volwaardige takenpagina, en herbruikbare 'Maak taken van bevindingen'-knop op AFAS-resultaat (Algemeen + KIK-V; bulk → taken, errors=prioriteit Hoog). E-MAIL: generieke env-gestuurde SMTP-mailer (`app/services/mailer.py`, default UIT), toewijzingsmail bij create/bulk/herverdeling (alleen naar een ander; dataminimaal: enkel taaktitel + toewijzer + inloglink, géén zorgdata). Leverancier **Scaleway Transactional Email** (EU-soeverein/Parijs, ISO 27001, AVG-DPA) — rhadix.nl geverifieerd (SPF/DKIM/MX in Cloudflare; bestaande strikte DMARC behouden). Mail-config via persistent `/opt/rhadix-app/mail.env` (door deploy-workflow ingelezen, overleeft redeploys; compose geeft MAIL_*/SMTP_*/PUBLIC_BASE_URL door aan backend). Fixes onderweg: tasks-tabel ontbrak (Alembic-migratie stil mislukt → startup-vangnet `_ensure_tasks_table` checkfirst); enum→native_enum=False (Postgres 500 bij insert); compose-projectnaam `-p rhadix-staging` nodig bij handmatige `up`. 179 tests groen. Mail getest: komt binnen. TODO: prod-activatie (zelfde mail.env met prod PUBLIC_BASE_URL) en module porten naar CRM. |
| 2026-06-26 | — | CRM-dataverrijking VOLTOOID (staging): alle 17 RSO's + 152 VVT-aanbieders verrijkt met website/plaats/KvK/gepubliceerde e-mail + bestuurders (raad van bestuur/directie) als contactpersoon. Totaal 293 contactpersonen met bron-URL en zekerheid (202 Hoog / 49 Middel / 41 Laag). Discipline: uitsluitend openbare bronnen (eigen bestuurspagina's > vakmedia), géén afgeleide e-mails, géén gokwerk, NULL waar niets gevonden. 151/152 VVT met website ('Lante' = geen bron, vermoedelijk typefout in bronlijst). Geladen via API (PATCH org + POST contactpersonen, idempotent). Datakwaliteit-flags vastgelegd in `bron_opmerking`/`opmerking`: vermoedelijke dubbelingen over regio's (Thebe, TanteLouise, Zorgwaard, Lelie zorggroep, Zorgspectrum Het Zand, IJsselheem=Woonzorgconcern IJsselheem, ZGR=Zorggroep Raalte), vermoedelijk geen VVT (MediReva, ONS welzijn, WijZijn Traverse Groep), bestuurder bewust NULL bij vacature/niet-openbaar (Daelzicht, Joris Zorg, Lunet, Ananz, Zorg in Oktober, De Posten, Radar), Cicero-naam 'Midden-Limburg' onjuist (Brunssum). Topaz-regel (E. Kalbfleisch) gecorrigeerd na constatering overstap naar De Zorgcirkel. Verificatie-overzicht: `Rhadix_CRM_verificatielijst.xlsx`. NB: verrijking staat in de staging-DB (data, niet in git). |
| 2026-06-24 | — | SSO op productie werkend: RS256-token over alle 4 apps. JWT_PRIVATE_KEY was leeg (lege secret); opgelost via persistent `/opt/rhadix-app/jwt_private.env` + deploy-workflow leest dat bestand. Geverifieerd: uitvraag/datastation/crm geven 200 op /api/auth/me met centraal token. |
| 2026-06-24 | v1.6.2/3 · u v0.7.3 · ds v1.0.3 · crm v0.1.2 | SSO-bedrading op productie uitgerold over alle 4 apps (RS256-uitgever datavalidatie + resource-apps + SSO-cookie .rhadix.nl). OPEN: JWT_PRIVATE_KEY leeg op datavalidatie-prod → token nog HS256 → alleen CRM-SSO werkt; morgen fixen (zie OPENSTAAND-sectie). Vers prod-sleutelpaar; publieke sleutel als default in 4 prod-composes. |
| 2026-06-23 | v1.6.1 | FIX: CRM-tegel actief op prod-portal (CRM_ACTIVE=true; in v1.6.0 stond per ongeluk !IS_PROD door ongestagede sed). |
| 2026-06-23 | v1.6.0 | RELEASE flow+marketing naar prod: gestripte Rhadix-Index-landing (PlatformLanding) + kaart-grid-portal op app.rhadix.nl; CRM als 4e tegel (crm.rhadix.nl). Marketing rhadix.nl (/var/www/rhadix/index.html): Inloggen->Rhadix platform, Probeer-knoppen weg, Klaar om te starten?. SureSync-merklaag + centrale identiteit meegekomen maar omgevings-gegated (dormant op prod). 159 tests groen. |
| 2026-06-23 | v1.5.28/29 | Admin-wachtwoord platformbreed -> Rhadixvoordezorg26! (DV v1.5.28 + v1.5.29 _ensure_admin dwingt af op bestaande admin; Datastation v1.0.2, Uitvraag v0.7.2, CRM v0.1.1). Nieuwe app Rhadix-crm live (crm.rhadix.nl + crm-staging). nginx live-config = /etc/nginx/sites-enabled/rhadix (aparte kopie, GEEN symlink); marketing = static /var/www/rhadix. |
| 2026-06-23 | — | Platform-flow conform 'wijzigingen flow.docx': scherm 1 = gestripte Datavalidatie-landing (hero + Rhadix Index-teller, alleen Inloggen, geen scan/reconciliatie/stappen); scherm 2 = portal als kaart-grid (3 app-tegels) met gedeelde Nav Dashboard/Beheer (Nav-knop 'Admin'->'Beheer'). OPEN: via Beheer moet admin org-beheerders+gebruikers toevoegen en apps koppelen via de licentiemodule — wacht op spec van Rene's collega. Alles op staging. |
| 2026-06-19 | — | Platform-flow: 'Rhadix platform'-entree = PlatformLanding met de **Rhadix Index** centraal + de drie applicaties 'in dienst van de index' + Inloggen. Na inloggen → portal (AppPortal) in Validatie-stijl met **Dashboard/Beheer/Terug**-nav. Marketingsite-CTA's vereenvoudigd naar 'Rhadix platform'. Unified identity (SureSync ID, RS256/JWKS/SSO) staat actief op staging (app-/uitvraag-/datastation-staging.rhadix.nl). Alles staging. |
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
