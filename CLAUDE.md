# CLAUDE.md — Rhadix projectgeheugen

Dit bestand wordt automatisch gelezen bij elke nieuwe sessie. Het bevat alle projectkennis zodat er geen context verloren gaat bij restarts.

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
git clone https://<zie .git/config in rhadix-git repo>@github.com/Rhadix2026/Rhadix-datavalidatie.git /tmp/rhadix-work
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

- Docker on boot: enabled
- Restart policy: always op alle containers
- Swap: 2GB /swapfile

---

## Bekende issues

- **Git lock-files:** altijd naar /tmp/ klonen, niet naar gemounte Downloads-map
- **Staging toont oude versie:** main pusht NIET naar staging — altijd handmatig mergen
- **Browser-cache:** na asset-updates hard refresh (Cmd+Shift+R)
- **Bad gateway:** controleer .env.production aanwezig + GHCR_ORG erin

---

## Sessie-log

| Datum | Versie | Wijziging |
|-------|--------|-----------|
| 2026-05-22 | v1.5.15 | SVG vervangen door JPG brand assets |
| 2026-05-22 | — | Server: swap + Docker-on-boot bevestigd |
| 2026-05-22 | — | Productie hersteld na bad gateway |
| 2026-05-21 | v1.5.14 | BIO security hardening (B01-B10) |
