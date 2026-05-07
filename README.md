# Rhadix v131 — Deployment

## Wat is nieuw in v131
- KIK-V Profielimport uit GitLab (tag 1.3.4)
- Gereedheidsmatrix per indicator (fully / partially / blocked)
- OWL structurele validatie + SPARQL use-case scores
- Traceerbaarheid drilldown (17 velden per issue)
- Data Actualiteit Score met histogram

## Poorten
| Service   | Extern         | Intern |
|-----------|----------------|--------|
| Frontend  | localhost:5174 | 80     |
| Backend   | localhost:8010 | 8000   |
| Database  | localhost:5433 | 5432   |

## Vereisten
- Docker Desktop (of Docker Engine + Compose plugin)
- Poorten 5174, 8010 en 5433 vrij op je machine

## Opstarten
```bash
./start.sh
```
Open daarna http://localhost:5174

## Stoppen
```bash
./stop.sh
```

## Volledig herinstalleren (database wissen + opnieuw bouwen)
```bash
./reset.sh
```

## Logs bekijken
```bash
docker compose -p rhadix-v131 logs -f
docker compose -p rhadix-v131 logs -f backend
docker compose -p rhadix-v131 logs -f frontend
```

## Naast v127 draaien
v131 gebruikt project-naam `rhadix-v131` en volume `rhadix_v131_pgdata`.
v127 gebruikt project-naam `rhadix-v127` en volume `rhadix_v127_pgdata`.
Ze delen geen containers, volumes of netwerken en conflicteren niet.

## KIK-V Profielimport gebruiken
1. Zorg dat je internetverbinding hebt (GitLab is publiek toegankelijk)
2. Ga naar "KIK-V Profielimport" via de landingspagina
3. Klik "+ Nieuw importeren" — standaard instellingen zijn correct
4. Na import: upload bronbestanden en klik "Analyseer gereedheid"

## Handmatig (zonder script)
```bash
docker compose -p rhadix-v131 up --build -d      # starten
docker compose -p rhadix-v131 down               # stoppen
docker compose -p rhadix-v131 down -v            # stoppen + database wissen
```
