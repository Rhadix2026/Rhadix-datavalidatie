# Rhadix — SaaS Platform Architectuurontwerp

> **Status:** Ontwerp — nog niet geïmplementeerd  
> **Versie:** 1.0  
> **Datum:** mei 2026

---

## Inhoudsopgave

1. [Huidige situatie (nulmeting)](#1-huidige-situatie-nulmeting)
2. [Databaseontwerp](#2-databaseontwerp)
3. [API-endpoints](#3-api-endpoints)
4. [Frontend routes & schermen](#4-frontend-routes--schermen)
5. [Beveiligingsmodel](#5-beveiligingsmodel)
6. [Implementatiefases](#6-implementatiefases)
7. [Migratiestrategie](#7-migratiestrategie)

---

## 1. Huidige situatie (nulmeting)

### Backend
- **FastAPI** + **SQLAlchemy** + **PostgreSQL**
- Één model: `ValidationRun` (id, created_at, label, files, results, total_rows, error_count, warn_count, score, status)
- 7 routers: `validate`, `history`, `reference`, `export`, `reports`, `profiles`, `reconciliation`
- **Geen authenticatie** — alle endpoints volledig open
- `Base.metadata.create_all()` bij opstarten (geen Alembic)

### Frontend
- **React + Vite**, state-machine navigatie via `step`-variabele in `App.jsx`
- **Geen React Router**, geen URL-gebaseerde navigatie
- **Geen login-scherm** — landing toont direct "Start nieuwe scan"
- Alle state in-memory (verloren bij refresh)

### Conclusie
De huidige codebase is een single-tenant tool zonder enige isolatie. Alles draait als één anonieme gebruiker.

---

## 2. Databaseontwerp

### 2.1 Overzicht van nieuwe tabellen

```
tenants
  └── users (N per tenant)
  └── api_keys (N per tenant)
  └── validation_runs (N per tenant)  ← bestaande tabel uitbreiden
  └── licenses (1 per tenant)

roles (systeem-enum: RHADIX_ADMIN, ORG_ADMIN, ORG_USER)
user_roles (users ↔ roles, per tenant)

audit_logs (alle acties gelogd)
```

### 2.2 Tabel: `tenants`

| Kolom | Type | Omschrijving |
|---|---|---|
| `id` | UUID PK | |
| `slug` | VARCHAR(63) UNIQUE | URL-vriendelijke naam, bijv. `zorggroep-noord` |
| `name` | VARCHAR(255) | Weergavenaam |
| `is_active` | BOOLEAN | Soft-disable zonder data-verlies |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

### 2.3 Tabel: `users`

| Kolom | Type | Omschrijving |
|---|---|---|
| `id` | UUID PK | |
| `tenant_id` | UUID FK → tenants | Welke organisatie |
| `email` | VARCHAR(255) UNIQUE | Login-identifier |
| `password_hash` | VARCHAR(255) | bcrypt, nullable (SSO-only users) |
| `full_name` | VARCHAR(255) | |
| `role` | ENUM | `RHADIX_ADMIN`, `ORG_ADMIN`, `ORG_USER` |
| `is_active` | BOOLEAN | Account in-/uitschakelen |
| `last_login_at` | TIMESTAMPTZ | |
| `created_at` | TIMESTAMPTZ | |

### 2.4 Tabel: `licenses`

| Kolom | Type | Omschrijving |
|---|---|---|
| `id` | UUID PK | |
| `tenant_id` | UUID FK → tenants UNIQUE | 1-op-1 |
| `license_key` | VARCHAR(64) UNIQUE | Gegenereerde sleutel |
| `plan` | ENUM | `STARTER`, `PROFESSIONAL`, `ENTERPRISE` |
| `max_users` | INTEGER | Null = onbeperkt |
| `max_scans_per_month` | INTEGER | Null = onbeperkt |
| `features` | JSONB | `{"reconciliation": true, "export_pdf": true, ...}` |
| `valid_from` | DATE | |
| `valid_until` | DATE | Null = nooit verlopen |
| `is_active` | BOOLEAN | |

### 2.5 Tabel: `api_keys`

| Kolom | Type | Omschrijving |
|---|---|---|
| `id` | UUID PK | |
| `tenant_id` | UUID FK → tenants | |
| `created_by` | UUID FK → users | |
| `name` | VARCHAR(255) | Beschrijvende naam, bijv. "CI/CD pipeline" |
| `key_hash` | VARCHAR(255) | SHA-256 van de sleutel (plain nooit opgeslagen) |
| `prefix` | VARCHAR(8) | Eerste 8 tekens voor identificatie (bijv. `rhdx_abc1`) |
| `last_used_at` | TIMESTAMPTZ | |
| `expires_at` | TIMESTAMPTZ | Null = niet verlopen |
| `is_active` | BOOLEAN | |
| `created_at` | TIMESTAMPTZ | |

### 2.6 Tabel: `validation_runs` — uitbreiding

Huidige kolommen blijven. Toevoegen:

| Kolom | Type | Omschrijving |
|---|---|---|
| `tenant_id` | UUID FK → tenants NOT NULL | Eigenaarsisolatie |
| `created_by` | UUID FK → users NULLABLE | Null bij API-key-runs |
| `standard` | VARCHAR(32) | `kikv`, `zib`, `algemeen` (al in code, nog niet in DB) |

### 2.7 Tabel: `audit_logs`

| Kolom | Type | Omschrijving |
|---|---|---|
| `id` | BIGSERIAL PK | |
| `tenant_id` | UUID NULLABLE | Null voor platform-acties |
| `user_id` | UUID NULLABLE | |
| `action` | VARCHAR(128) | bijv. `user.login`, `scan.upload`, `api_key.create` |
| `resource_type` | VARCHAR(64) | bijv. `validation_run` |
| `resource_id` | VARCHAR(64) | |
| `ip_address` | INET | |
| `user_agent` | TEXT | |
| `meta` | JSONB | Extra context |
| `created_at` | TIMESTAMPTZ | |

### 2.8 Plannen (toekomst, fase 4+)

- `invitations` — uitnodigingen per e-mail
- `scan_quotas` — maandelijkse teller per tenant
- `webhooks` — callbacks bij scan-voltooiing

---

## 3. API-endpoints

### 3.1 Authenticatie (`/api/auth/`)

| Methode | Pad | Beschrijving | Auth vereist |
|---|---|---|---|
| `POST` | `/api/auth/login` | E-mail + wachtwoord → JWT + refresh token | Nee |
| `POST` | `/api/auth/refresh` | Refresh token → nieuw JWT | Refresh token |
| `POST` | `/api/auth/logout` | Invalideer refresh token | JWT |
| `POST` | `/api/auth/forgot-password` | Stuur reset-e-mail | Nee |
| `POST` | `/api/auth/reset-password` | Reset met token uit e-mail | Reset token |
| `GET` | `/api/auth/me` | Huidig gebruikersprofiel | JWT |

### 3.2 Gebruikersbeheer (`/api/users/`) — ORG_ADMIN+

| Methode | Pad | Beschrijving |
|---|---|---|
| `GET` | `/api/users/` | Lijst gebruikers binnen eigen tenant |
| `POST` | `/api/users/` | Nieuwe gebruiker aanmaken (+ uitnodigingsmail) |
| `GET` | `/api/users/{id}` | Gebruiker ophalen |
| `PATCH` | `/api/users/{id}` | Naam/rol bijwerken |
| `DELETE` | `/api/users/{id}` | Soft-delete (is_active=false) |

### 3.3 Tenant-beheer (`/api/admin/`) — RHADIX_ADMIN only

| Methode | Pad | Beschrijving |
|---|---|---|
| `GET` | `/api/admin/tenants/` | Alle organisaties |
| `POST` | `/api/admin/tenants/` | Nieuwe organisatie aanmaken |
| `PATCH` | `/api/admin/tenants/{id}` | Naam/slug aanpassen |
| `DELETE` | `/api/admin/tenants/{id}` | Deactiveren |
| `GET` | `/api/admin/tenants/{id}/license` | Licentiedetails |
| `PUT` | `/api/admin/tenants/{id}/license` | Licentie aanmaken/bijwerken |
| `GET` | `/api/admin/stats` | Platform-statistieken |

### 3.4 API-sleutels (`/api/api-keys/`) — ORG_ADMIN+

| Methode | Pad | Beschrijving |
|---|---|---|
| `GET` | `/api/api-keys/` | Sleutels van eigen tenant |
| `POST` | `/api/api-keys/` | Nieuwe sleutel genereren (plain tekst éénmalig getoond) |
| `DELETE` | `/api/api-keys/{id}` | Sleutel intrekken |

### 3.5 Bestaande routers — aanpassingen

Alle bestaande endpoints (`/api/upload`, `/api/history`, `/api/export`, etc.) krijgen:
- Verplichte JWT of API-key authenticatie
- Automatische `tenant_id`-filtering (gebruiker ziet alleen eigen data)
- Geen wijziging in request/response-formaat (backwards compatible)

---

## 4. Frontend routes & schermen

### 4.1 Routestructuur

De huidige state-machine-navigatie blijft intact voor de scan-flow. Er komen nieuwe schermen bij voor auth en beheer. React Router wordt **niet** geïntroduceerd — de bestaande aanpak wordt uitgebreid.

```
App.jsx
  ├── step === 'login'           → LoginScreen
  ├── step === 'forgot-password' → ForgotPasswordScreen
  ├── step === 'reset-password'  → ResetPasswordScreen
  │
  ├── [bestaande stappen — ongewijzigd]
  │   landing → systems → upload → beschikbaarheid → ...
  │
  └── step === 'settings'        → SettingsShell
        ├── tab === 'profile'    → ProfileTab
        ├── tab === 'users'      → UsersTab       (ORG_ADMIN)
        ├── tab === 'api-keys'   → ApiKeysTab     (ORG_ADMIN)
        ├── tab === 'license'    → LicenseTab     (ORG_ADMIN)
        └── tab === 'admin'      → AdminTab       (RHADIX_ADMIN)
```

### 4.2 Nieuwe schermen

#### `LoginScreen`
- E-mailadres + wachtwoord
- "Wachtwoord vergeten"-link
- Foutmeldingen (onjuiste combinatie, account geblokkeerd)
- Na succesvol inloggen: naar `landing` step

#### `ForgotPasswordScreen`
- Voer e-mailadres in → bevestigingsmelding (altijd, ook bij onbekend adres)

#### `ResetPasswordScreen`
- Token uit URL (`?token=...`) + nieuw wachtwoord + bevestiging
- Validatie: minimaal 12 tekens

#### `SettingsShell`
- Navigatiebalk links met tabs
- Breadcrumb: Instellingen → [tab]

#### `ProfileTab`
- Naam aanpassen
- Wachtwoord wijzigen (oud + nieuw + bevestiging)
- Inloggeschiedenis (laatste 5 sessies)

#### `UsersTab` (ORG_ADMIN)
- Tabel: naam, e-mail, rol, status, laatste login
- Knop "Gebruiker uitnodigen" → modal met e-mail + rol-selectie
- Acties per rij: rol wijzigen, account in-/uitschakelen

#### `ApiKeysTab` (ORG_ADMIN)
- Tabel: naam, prefix (`rhdx_abc1...`), aangemaakt door, laatste gebruik, verloopt
- Knop "Nieuwe sleutel" → modal met naam + optionele vervaldatum
- Na aanmaken: eenmalige weergave van de volledige sleutel (kopieerknop)
- Actie per rij: intrekken

#### `LicenseTab` (ORG_ADMIN)
- Huidig plan, geldigheid, gebruik (scans deze maand / maximum)
- Ingeschakelde functies (visuele kaarten per feature)
- Knop "Upgrade aanvragen" → mailto/contact

#### `AdminTab` (RHADIX_ADMIN — alleen zichtbaar voor Rhadix-medewerkers)
- Tabel alle tenants: naam, plan, actieve gebruikers, scans, status
- Per tenant: licentie bewerken, gebruikers inzien, deactiveren
- Platform-statistieken: totaal scans, actieve tenants, errors

### 4.3 Aanpassing `Nav`-component

De bestaande `Nav` (in `UI.jsx`) krijgt:
- Rechtsboven: gebruikersnaam + rol-badge + dropdown
  - "Instellingen" → `setStep('settings')`
  - "Uitloggen" → token wissen + `setStep('login')`
- Na uitloggen/token-verlopen: automatisch terug naar `login`

### 4.4 Auth-guard in `App.jsx`

```jsx
// Vóór alle bestaande steps:
if (!authToken && step !== 'login' && step !== 'forgot-password' && step !== 'reset-password') {
  return <LoginScreen onLogin={handleLogin} />
}
```

---

## 5. Beveiligingsmodel

### 5.1 Authenticatie

- **JWT** (HS256), gesigneerd met een `SECRET_KEY` env-variabele
- Access token: geldig **15 minuten**
- Refresh token: geldig **30 dagen**, opgeslagen in `httpOnly` cookie
- Bij elke request: JWT gevalideerd op `exp`, `tenant_id`, `user_id`, `role`

### 5.2 API-sleutels

- Formaat: `rhdx_` + 43 random Base64URL-tekens (256 bit entropie)
- Opgeslagen als SHA-256 hash — plain text nooit persistent
- Bij request via header: `Authorization: Bearer rhdx_...`
- Middleware detecteert prefix `rhdx_` en schakelt naar API-key-validatie

### 5.3 Rollen & rechten

| Actie | ORG_USER | ORG_ADMIN | RHADIX_ADMIN |
|---|:---:|:---:|:---:|
| Scans uitvoeren | ✓ | ✓ | ✓ |
| Eigen scanhistorie bekijken | ✓ | ✓ | ✓ |
| Alle scans van tenant bekijken | — | ✓ | ✓ |
| Gebruikers beheren | — | ✓ | ✓ |
| API-sleutels beheren | — | ✓ | ✓ |
| Licentie bekijken | — | ✓ | ✓ |
| Alle tenants beheren | — | — | ✓ |
| Licenties aanmaken/aanpassen | — | — | ✓ |

### 5.4 Tenant-isolatie

Elke database-query voor gevoelige data krijgt verplicht een `tenant_id`-filter:

```python
# FastAPI dependency — altijd injecteren
async def get_current_tenant(token: str = Depends(oauth2_scheme)) -> Tenant:
    payload = verify_jwt(token)
    return db.query(Tenant).filter_by(id=payload["tenant_id"]).first()

# In elke router:
@router.get("/api/history")
def get_history(tenant: Tenant = Depends(get_current_tenant), db = Depends(get_db)):
    return db.query(ValidationRun).filter_by(tenant_id=tenant.id).all()
```

Cross-tenant data-lekkage is hierdoor structureel onmogelijk, ook bij fouten in applicatiecode.

### 5.5 Licentiecontrole

FastAPI-middleware controleert bij elke upload:
1. Is de licentie actief en niet verlopen?
2. Is het maandlimiet voor scans niet overschreden?
3. Heeft dit plan toegang tot de gevraagde feature (bijv. reconciliation)?

```python
async def check_license(tenant: Tenant = Depends(get_current_tenant)):
    license = db.query(License).filter_by(tenant_id=tenant.id).first()
    if not license or not license.is_active:
        raise HTTPException(403, "Licentie niet actief")
    if license.valid_until and license.valid_until < date.today():
        raise HTTPException(403, "Licentie verlopen")
    # Quota check: tel scans deze maand
    ...
```

### 5.6 Wachtwoordbeleid

- Minimaal 12 tekens, geen verdere complexiteitseis (NIST-aanbeveling)
- bcrypt met cost factor 12
- Reset-tokens: 64 random bytes, SHA-256 gehasht, geldig 1 uur, eenmalig gebruik

### 5.7 Overige beveiligingsmaatregelen

- **Rate limiting** op auth-endpoints (max. 10 pogingen/minuut per IP)
- **CORS** beperkt tot bekende origins (configureerbaar per omgeving)
- **Audit log** voor alle mutatieve acties
- Wachtwoord-reset e-mails bevatten nooit de gebruikersnaam of hint

---

## 6. Implementatiefases

### Fase 1 — Authenticatiefundament (2–3 weken)

**Doel:** Niemand kan de app gebruiken zonder in te loggen. Data blijft bereikbaar.

**Backend:**
- Alembic opzetten voor databasemigraties
- Tabellen `tenants`, `users`, `licenses` aanmaken
- `validation_runs` uitbreiden met `tenant_id` en `created_by`
- JWT-authenticatie middleware (`/api/auth/login`, `/api/auth/me`, `/api/auth/refresh`, `/api/auth/logout`)
- Alle bestaande routers beveiligen met `Depends(get_current_user)`
- Eén initiële tenant + admin-gebruiker via seed-script

**Frontend:**
- `LoginScreen` component
- `useAuth` hook: JWT opslaan, auto-refresh, logout
- Auth-guard in `App.jsx`
- Uitlogknop in `Nav`

**Wat nog NIET gedaan wordt:** gebruikersbeheer-UI, uitnodigingen, licentiecontrole.

**Deliverable:** App werkt alleen na inloggen. Bestaande functionaliteit ongewijzigd.

---

### Fase 2 — Multi-tenancy & gebruikersbeheer (2–3 weken)

**Doel:** Meerdere organisaties kunnen de app gebruiken met volledige data-isolatie.

**Backend:**
- `tenant_id`-filter op alle queries (middleware-level)
- `POST /api/users/` — gebruiker aanmaken
- `GET/PATCH/DELETE /api/users/{id}` — beheer binnen eigen tenant
- Basisversie wachtwoordreset (e-mail via SMTP)
- Eenvoudige licentiecontrole (actief/verlopen)

**Frontend:**
- `SettingsShell` met tabs
- `UsersTab` — overzicht + aanmaken + deactiveren
- `ProfileTab` — naam + wachtwoord wijzigen
- `ForgotPasswordScreen` + `ResetPasswordScreen`

**Deliverable:** ORG_ADMIN kan eigen gebruikers beheren. Data volledig geïsoleerd per tenant.

---

### Fase 3 — Licenties & API-sleutels (1–2 weken)

**Doel:** Commerciële controle en programmatische toegang.

**Backend:**
- Licentietabel volledig implementeren (plannen, features, quota)
- Quota-teller per maand per tenant
- Feature-flags per endpoint (bijv. reconciliation alleen bij PROFESSIONAL+)
- `POST/GET/DELETE /api/api-keys/` endpoints

**Frontend:**
- `LicenseTab` — plan, gebruik, functies
- `ApiKeysTab` — sleutels genereren en intrekken

**Deliverable:** Licentiemodel actief, API-sleutels beschikbaar voor integraties.

---

### Fase 4 — Admin-paneel & audit (1–2 weken)

**Doel:** Rhadix-medewerkers kunnen tenants beheren zonder directe database-toegang.

**Backend:**
- `RHADIX_ADMIN`-role en beveiligde `/api/admin/` router
- `audit_logs`-tabel en logging-middleware
- Platform-statistieken endpoint

**Frontend:**
- `AdminTab` (alleen zichtbaar bij RHADIX_ADMIN)
- Tenant-overzicht, licentie bewerken, statistieken

**Deliverable:** Volledig SaaS-beheerplatform operationeel.

---

### Fase 5 — Uitnodigingsflow & verfijning (optioneel, 1–2 weken)

- E-mailuitnodigingen met token-gebaseerde onboarding
- SSO / SAML 2.0 voor enterprise-klanten
- Webhook-callbacks bij scan-voltooiing
- Verbeterde quota-meldingen in de frontend
- Factuurgeschiedenis (Stripe-integratie)

---

## 7. Migratiestrategie

### 7.1 Bestaande data

De huidige `validation_runs`-tabel bevat runs zonder `tenant_id`. Aanpak:

```sql
-- 1. Maak een "legacy"-tenant aan
INSERT INTO tenants (id, slug, name) VALUES (gen_random_uuid(), 'legacy', 'Legacy Data');

-- 2. Koppel alle bestaande runs aan die tenant
UPDATE validation_runs SET tenant_id = '<legacy-tenant-id>' WHERE tenant_id IS NULL;

-- 3. Maak kolom verplicht
ALTER TABLE validation_runs ALTER COLUMN tenant_id SET NOT NULL;
```

### 7.2 Database-migraties

- Alembic wordt opgezet **vóór** de eerste schema-wijziging (fase 1)
- Elke fase levert één of meer Alembic-revisies op
- Migraties draaien automatisch bij deployment via `alembic upgrade head` in de deploy-workflow
- Rollback via `alembic downgrade -1` — alle nieuwe kolommen zijn initieel nullable

### 7.3 Backwards-compatibiliteit API

- Bestaande request/response-formaten wijzigen **niet**
- Alleen de autorisatie-laag wordt toegevoegd
- Staging wordt als testbed gebruikt voor elke fase vóór productie
- Eventuele breaking changes worden als `v2`-prefix uitgebracht (bijv. `/api/v2/upload`)

### 7.4 Geheimen

Nieuwe omgevingsvariabelen per fase:

**Fase 1:**
```
JWT_SECRET_KEY=<256-bit random>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
```

**Fase 2:**
```
SMTP_HOST=...
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
SMTP_FROM=noreply@rhadix.nl
FRONTEND_URL=https://rhadix.nl  # voor reset-links
```

Worden toegevoegd aan de GitHub Environments (staging + production) als secrets.

### 7.5 Volgorde van uitrol

```
1. Migratie draaien op staging   →  valideren
2. Fase op staging deployen      →  handmatig testen
3. PR staging → main openen
4. Migratie draaien op productie →  goedkeuring vereist
5. Deploy naar productie         →  health check
6. Bestaande gebruikers informeren
```

---

## Bijlage: Technologiekeuzes

| Onderdeel | Keuze | Reden |
|---|---|---|
| JWT-bibliotheek | `python-jose` + `passlib[bcrypt]` | Standaard in FastAPI-ecosystem |
| Migraties | `alembic` | De facto standaard voor SQLAlchemy |
| Wachtwoordhashing | `bcrypt` (cost 12) | Veilig, wijd ondersteund |
| E-mail | `fastapi-mail` | Async, integreert met FastAPI |
| UUIDs | PostgreSQL `gen_random_uuid()` | Geen informatielekken in IDs |
| Token-opslag (frontend) | `httpOnly` cookie (refresh) + memory (access) | XSS-resistent |
