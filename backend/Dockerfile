FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# BIO 12.6.2 — draai als non-root user.
# Zorg dat de data-map (incl. het profielen-volume) schrijfbaar is voor die user:
# een vers named volume erft de eigenaar van deze image-map, dus zonder chown
# kan de non-root backend geen nieuwe profielen wegschrijven (Permission denied → 502).
RUN addgroup --system rhadix && adduser --system --ingroup rhadix rhadix \
 && mkdir -p /app/data/profiles \
 && chown -R rhadix:rhadix /app/data
USER rhadix

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
