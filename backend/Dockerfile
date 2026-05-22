FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# BIO 12.6.2 — draai als non-root user
RUN addgroup --system rhadix && adduser --system --ingroup rhadix rhadix
USER rhadix

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
