# CLAUDE.md — Rhadix projectgeheugen

Dit bestand wordt automatisch gelezen bij elke nieuwe sessie. Het bevat alle projectkennis zodat er geen context verloren gaat bij restarts.

**Instructie voor Claude:** Lees dit bestand aan het begin van elke sessie. Werk de sessie-log bij aan het einde van elke sessie met een korte samenvatting van wat er gedaan is, en commit de update naar main + staging.

---

## Project

**Rhadix Datavalidatie** — een KIK-V / ZIB-validatietool voor zorginstellingen.
- **Repo:** https://github.com/Rhadix2026/Rhadix-datavalidatie
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

**Huidige versie:** v1.5.15

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
- Swap: 2GB `/swapfile` ✓
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
- **Bad gateway productie:** controleer of `.env.production` aanwezig is én `GHCR_ORG=rhadix2026` erin staat

---

## Sessie-log

| Datum | Versie | Wijziging |
|-------|--------|-----------|
| 2026-05-22 | v1.5.15 | SVG logo vervangen door JPG brand assets (logo + boom) in UI.jsx, Landing.jsx, LoginScreen.jsx |
| 2026-05-22 | — | Productie hersteld na bad gateway: .env.production ontbrak, GHCR_ORG miste |
| 2026-05-22 | — | Server gestabiliseerd: 2GB swap toegevoegd, Docker-on-boot bevestigd, restart:always aanwezig |
| 2026-05-22 | — | CLAUDE.md aangemaakt als persistent projectgeheugen |
| 2026-05-21 | v1.5.14 | BIO security hardening (B01-B10) voltooid |
