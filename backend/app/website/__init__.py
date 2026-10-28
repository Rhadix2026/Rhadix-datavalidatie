"""
app.website — Opslag en verwerking van aanvragen via de Rhoderlanden-website.

Twee publieke endpoints leveren hier aan: het Readiness-rapport
(`routers/readiness.py`) en het contactformulier, inclusief "Bespreek mijn
uitslag" (`routers/contact.py`). Elke aanvraag wordt eerst vastgelegd en pas
daarna verwerkt: mail aan de bezoeker, melding aan ons, registratie in het CRM.
Een stap die mislukt, wordt later opnieuw geprobeerd; de aanvraag zelf gaat
niet meer verloren omdat een mail of het CRM hapert.

Afbakening
----------
Dit pakket heeft een **eigen engine en een eigen schema** (`website`). Het
importeert `app.database` en `app.models` niet en kan de tabellen van
Datavalidatie dus niet lezen of schrijven. Met `WEBSITE_DATABASE_URL` kan het
een eigen databaserol krijgen die alleen dat schema mag gebruiken.

Modules:

* `instellingen` — interne adressen en controle van de mailconfiguratie;
* `opslag`       — engine, tabellen en het vastleggen van stappen;
* `verwerking`   — de stappen zelf, de herhaaltaak en het dagoverzicht.
"""
