# Rhadix — Deployment & DTAP Documentatie

## Overzicht

Rhadix gebruikt een DTAP-strategie met drie omgevingen, elk volledig gescheiden van elkaar.

| Omgeving | Branch | Server | Frontend | Backend | Database |
|---|---|---|---|---|---|
| Development | `develop` | Lokaal | localhost:5174 | localhost:8010 | lokaal |
| Staging | `staging` | 46.224.224.26 | :5175 | :8011 | `kikv_staging` |
| Productie | `main` | 46.224.224.26 | :5174 | :8010 | `kikv_validator` |

**Visuele indicator:** Staging toont een oranje balk bovenaan. Productie heeft geen banner.

---

## Branch-strategie

```
develop  ──(PR)──▶  staging  ──(PR + tag)──▶  main
   │                   │                         │
   │             Auto-deploy               Handmatige
   │             naar staging              goedkeuring
   │                                       vereist
   └─ feature/... branches (optioneel)
```

### Werkproces

1. Ontwikkel op `develop` (of een feature branch)
2. Open een Pull Request van `develop` → `staging`
3. Na merge: staging wordt automatisch gedeployed en getest
4. Valideer de wijzigingen op staging (http://46.224.224.26:5175)
5. Open een Pull Request van `staging` → `main`
6. Maak een versie-tag aan: `git tag v1.x.x && git push origin main --tags`
7. GitHub vraagt om handmatige goedkeuring → keur goed in de Actions UI
8. Productie wordt gedeployed

---

## CI/CD Pipelines

### 1. `ci.yml` — Automatische tests

**Triggert bij:** push of PR naar `develop`, `staging` of `main`

Voert uit:
- Pytest op alle tests in `backend/tests/`
- Docker build smoke test (backend + frontend, geen push)

### 2. `deploy-staging.yml` — Staging deployment

**Triggert bij:** push naar `staging` branch

Stappen:
1. Pytest uitvoeren (faalt → geen deploy)
2. Docker images bouwen met tag `:staging` en `VITE_RHADIX_ENV=staging`
3. Images pushen naar GHCR
4. SSH naar server → `.env.staging` schrijven → `docker compose up -d`
5. Health check op `http://localhost:8011/api/health`

### 3. `deploy-production.yml` — Productie deployment

**Triggert bij:** versie-tag (`v*.*.*`) of handmatig via workflow_dispatch

Stappen:
1. Pytest uitvoeren (faalt → geen deploy)
2. Docker images bouwen met versie-tag én `:latest`
3. **⏸ Wacht op handmatige goedkeuring** (GitHub Environment: production)
4. SSH naar server → `.env.production` schrijven → `docker compose up -d`
5. Health check op `http://localhost:8010/api/health`

### 4. `rollback-staging.yml` — Rollback staging

**Triggert:** alleen handmatig via GitHub Actions UI

Gebruik: Actions → Rollback — Staging → Run workflow → voer tag in

---

## Benodigde GitHub Secrets

### Repository-niveau (Settings → Secrets and variables → Actions)

Geen — alle secrets zijn per environment ingesteld.

### Environment: `staging` (Settings → Environments → staging)

| Secret | Beschrijving | Voorbeeld |
|---|---|---|
| `STAGING_SSH_HOST` | IP-adres van de VPS | `46.224.224.26` |
| `STAGING_SSH_USER` | SSH-gebruikersnaam | `root` |
| `STAGING_SSH_KEY` | Volledige SSH private key | `-----BEGIN OPENSSH...` |
| `STAGING_DB_PASSWORD` | Wachtwoord staging-database | sterk wachtwoord |
| `STAGING_LICENSE_KEY` | Licentiecsleutel | `XXXX-XXXX-XXXX-XXXX` |

### Environment: `production` (Settings → Environments → production)

| Secret | Beschrijving |
|---|---|
| `PROD_SSH_HOST` | IP-adres productie-server |
| `PROD_SSH_USER` | SSH-gebruikersnaam |
| `PROD_SSH_KEY` | SSH private key |
| `PROD_DB_PASSWORD` | Productie-databasewachtwoord |
| `PROD_LICENSE_KEY` | Productielijcentiesleutel |

### SSH-sleutel uitlezen (Mac)

```bash
cat ~/.ssh/id_ed25519   # of id_rsa
```

Kopieer de volledige inhoud inclusief `-----BEGIN OPENSSH PRIVATE KEY-----`
en `-----END OPENSSH PRIVATE KEY-----`.

### Production Environment instellen (eenmalig)

1. Ga naar: github.com/Rhadix2026/Rhadix-datavalidatie → Settings → Environments
2. Klik **New environment** → naam: `production`
3. Vink aan: **Required reviewers** → voeg je GitHub-gebruiker toe
4. Voeg de 5 secrets toe (zie tabel hierboven)
5. Sla op

---

## Rollback-procedure

### Rollback staging (via GitHub Actions)

```
GitHub → Actions → "Rollback — Staging" → Run workflow
→ Voer image-tag in (bijv. v1.4.21)
→ Voer reden in
→ Run workflow
```

De workflow controleert of de tag bestaat, rolt terug en doet een health check.

### Rollback staging (handmatig via SSH)

```bash
ssh root@46.224.224.26

# Zet de gewenste versie
sed -i '/^STAGING_IMAGE_TAG=/d' /opt/rhadix-app/.env.staging
echo "STAGING_IMAGE_TAG=v1.4.21" >> /opt/rhadix-app/.env.staging

# Herstart
docker compose -f /opt/rhadix-app/docker-compose.staging.yml \
  --env-file /opt/rhadix-app/.env.staging \
  pull && up -d

# Controleer
curl -s http://localhost:8011/api/health
```

### Rollback productie (handmatig via SSH)

```bash
ssh root@46.224.224.26

# Pas de versie aan in de productie env-file
sed -i 's/^RHADIX_VERSION=.*/RHADIX_VERSION=v1.4.21/' /opt/rhadix-app/.env.production

# Herstart met de oude versie
docker compose -f /opt/rhadix-app/docker-compose.prod.yml \
  --env-file /opt/rhadix-app/.env.production \
  pull

docker compose -f /opt/rhadix-app/docker-compose.prod.yml \
  --env-file /opt/rhadix-app/.env.production \
  up -d

# Controleer
curl -s http://localhost:8010/api/health
```

### Rollback via git (als code moet worden teruggedraaid)

```bash
# Bekijk recente tags
git tag --sort=-version:refname | head -10

# Revert op main en maak nieuwe tag
git checkout main
git revert HEAD --no-edit
git tag v1.4.23-rollback
git push origin main --tags
# → Productie deploy workflow start, vraagt goedkeuring
```

---

## Server-configuratie

### Bestandsstructuur op de server

```
/opt/rhadix-app/
├── docker-compose.prod.yml       # Productie stack definitie
├── docker-compose.staging.yml    # Staging stack definitie
├── .env.production               # Productie variabelen (chmod 600, NIET in git)
└── .env.staging                  # Staging variabelen  (chmod 600, NIET in git)
```

### Docker volumes

| Volume | Omgeving | Inhoud |
|---|---|---|
| `rhadix_pgdata` | Productie | Productiedatabase (NOOIT aanraken) |
| `rhadix_staging_pgdata` | Staging | Testdatabase (mag gereset worden) |

### Handige commando's op de server

```bash
# Status bekijken
docker ps --filter "name=rhadix"

# Logs bekijken
docker logs rhadix-backend --tail 50
docker logs rhadix-staging-backend --tail 50

# Productie herstarten (zonder update)
docker compose -f /opt/rhadix-app/docker-compose.prod.yml \
  --env-file /opt/rhadix-app/.env.production restart

# Staging database resetten (ALLEEN staging!)
docker compose -f /opt/rhadix-app/docker-compose.staging.yml \
  --env-file /opt/rhadix-app/.env.staging down -v
docker compose -f /opt/rhadix-app/docker-compose.staging.yml \
  --env-file /opt/rhadix-app/.env.staging up -d
```

---

## Lokale ontwikkeling

```bash
# Clone de repo
git clone https://github.com/Rhadix2026/Rhadix-datavalidatie.git
cd Rhadix-datavalidatie
git checkout develop

# Start lokaal
docker compose up -d

# Tests uitvoeren
cd backend
pip install -r requirements-dev.txt
pytest tests/ -v

# Feature branch workflow
git checkout -b feature/mijn-wijziging
# ... werk ...
git push origin feature/mijn-wijziging
# → Open PR naar develop op GitHub
```

---

## Versie-tags

Versies volgen Semantic Versioning: `vMAJOR.MINOR.PATCH`

```bash
# Nieuwe versie taggen (na merge naar main)
git checkout main
git pull origin main
git tag v1.5.0
git push origin main --tags
# → Deploy-production workflow start automatisch
```

---

## Noodprocedure: productie volledig herstarten

```bash
ssh root@46.224.224.26
cd /opt/rhadix-app

# Stop alles
docker compose -f docker-compose.prod.yml --env-file .env.production down

# Herstart
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# Controleer
docker ps --filter "name=rhadix-"
curl -s http://localhost:8010/api/health
```
