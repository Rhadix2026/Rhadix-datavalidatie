# Rhadix Validator

Volledige webapplicatie voor het valideren van AFAS Profit HRM exports tegen het KIK-V Modelgegevensset referentieontwerp.

## Stack

| Laag      | Technologie                        |
|-----------|------------------------------------|
| Frontend  | React 18 + Vite + React Router     |
| Backend   | Python 3.12 + FastAPI + SQLAlchemy |
| Database  | PostgreSQL 16                      |
| Export    | openpyxl (Excel) + ReportLab (PDF) |
| Deploy    | Docker Compose                     |

## Functionaliteit

- **Multi-bestand upload** — sleep meerdere CSV/Excel bestanden tegelijk
- **Automatische schema-herkenning** — op bestandsnaam én kolominhoud
- **Per-bestand validatie** — type, formaat, verplichte velden, geldige waarden
- **Cross-bestand controles** — referentiële integriteit tussen bestanden
- **Validatiegeschiedenis** — alle runs opgeslagen in PostgreSQL
- **Export** — rapport als Excel (.xlsx) of PDF
- **Referentie browser** — alle KIK-V velden en AFAS-mappings doorzoekbaar

## Snel starten met Docker

```bash
git clone <repo>
cd kikv-app
docker-compose up --build
```

App beschikbaar op:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Lokaal ontwikkelen

### Backend

```bash
cd backend

# Maak virtualenv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Installeer dependencies
pip install -r requirements.txt

# Stel database in (PostgreSQL moet draaien)
cp .env.example .env
# Pas DATABASE_URL aan in .env

# Start backend
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend draait op http://localhost:5173 en proxyt `/api` naar de backend.

## Projectstructuur

```
kikv-app/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + CORS
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── models/
│   │   │   └── models.py        # ValidationRun model
│   │   ├── routers/
│   │   │   ├── validate.py      # POST /api/validate/upload
│   │   │   ├── history.py       # GET/DELETE /api/history
│   │   │   ├── reference.py     # GET /api/reference
│   │   │   └── export.py        # GET /api/export/{id}/excel|pdf
│   │   └── services/
│   │       └── validator.py     # Alle validatielogica + KIK-V regels
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Routing + sidebar nav
│   │   ├── index.css            # Design tokens
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx    # Statistieken + overzicht
│   │   │   ├── Validator.jsx    # Upload + validatie flow
│   │   │   ├── History.jsx      # Lijst van alle runs
│   │   │   ├── RunDetail.jsx    # Detail van één run
│   │   │   └── Reference.jsx    # KIK-V velden browser
│   │   ├── components/
│   │   │   └── UI.jsx           # Gedeelde UI componenten
│   │   └── services/
│   │       └── api.js           # API calls naar backend
│   ├── vite.config.js
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
│
└── docker-compose.yml
```

## Gevalideerde bestanden

| Bestand            | Verplichte kolommen                                  |
|--------------------|------------------------------------------------------|
| Medewerker         | PersoneelsNummer, GeboorteDatum                     |
| Werkovereenkomst   | DienstverbandNummer, PersoneelsNummer, OvereenkomstType, StartDatum |
| Functie            | Functie                                              |
| KwalificatieNiveau | Code                                                 |
| KwaliteitsGraden   | Kwaliteit                                            |
| Verzuim            | PersoneelsNummer, Startmoment                        |

## Cross-bestand controles

- Werkovereenkomst → personen niet in Medewerker
- Medewerkers zonder werkovereenkomst
- Verzuim → personen niet in Medewerker
- KwalificatieNiveau codes niet in KwaliteitsGraden
- Functie kwalificatieniveaus niet in referentietabel

## API endpoints

| Methode | URL                          | Beschrijving               |
|---------|------------------------------|----------------------------|
| POST    | /api/validate/upload         | Upload en valideer bestanden|
| GET     | /api/history/                | Lijst van alle runs        |
| GET     | /api/history/{id}            | Detail van één run         |
| DELETE  | /api/history/{id}            | Verwijder run              |
| GET     | /api/history/stats/summary   | Statistieken               |
| GET     | /api/reference/fields        | KIK-V veldmapping          |
| GET     | /api/reference/schemas       | Bestandsschema's           |
| GET     | /api/export/{id}/excel       | Exporteer als Excel        |
| GET     | /api/export/{id}/pdf         | Exporteer als PDF          |
| GET     | /api/docs                    | Swagger UI                 |
