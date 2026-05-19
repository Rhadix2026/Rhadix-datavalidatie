# Rhadix Reconciliation Engine — Patch instructies

## Stap 1: Bestanden kopiëren

Pak de ZIP uit en kopieer naar je project:

```bash
# Backend module
cp -r backend/app/reconciliation/  ~/Downloads/rhadix-v131-deploy/backend/app/reconciliation/

# Frontend pagina
cp frontend/src/pages/reconciliation/ReconciliationDashboard.jsx \
   ~/Downloads/rhadix-v131-deploy/frontend/src/pages/reconciliation/ReconciliationDashboard.jsx
```

## Stap 2: backend/requirements.txt

Voeg deze twee regels toe aan het einde:

```
pandas>=2.2.0
pyyaml>=6.0
```

## Stap 3: backend/app/main.py

Voeg de import toe bij de andere imports bovenaan:

```python
from app.reconciliation.router import router as recon_router
```

Voeg de router toe na de andere `app.include_router(...)` regels:

```python
app.include_router(recon_router, prefix="/api/reconciliation", tags=["Reconciliation"])
```

## Stap 4: Git push

```bash
cd ~/Downloads/rhadix-v131-deploy
git add backend/app/reconciliation/ \
        frontend/src/pages/reconciliation/ReconciliationDashboard.jsx \
        backend/requirements.txt \
        backend/app/main.py
git commit -m "feat: Reconciliation Engine — brondata vs SPARQL vergelijking, DifferenceAnalyzer, dashboard"
git tag v1.4.14
git push origin main
git push origin v1.4.14
```

## Stap 5: Server updaten (na groene GitHub Actions build)

```bash
ssh root@46.224.224.26
cd /opt/rhadix-app
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

## Nieuwe indicator toevoegen

Maak een YAML-bestand aan in `backend/app/reconciliation/rules/`:

```yaml
indicator_id: mijn_indicator
name: Mijn Indicator
source_dataset: mijn_bestand.csv
peildatum: "2024-12-31"
peildatum_field: einddatum
filters:
  - field: status
    operator: eq
    value: "actief"
aggregation:
  function: count
  field: id
tolerance:
  absolute: 0
  percentage: 2.0
```

## API endpoints na deploy

| Methode | URL | Functie |
|---------|-----|---------|
| GET | /api/reconciliation/indicators | Alle indicatoren |
| POST | /api/reconciliation/calculate/{id} | Bereken verwachte waarde |
| POST | /api/reconciliation/reconcile/{id} | Volledige reconciliatie |
| POST | /api/reconciliation/batch | Batch meerdere indicatoren |
