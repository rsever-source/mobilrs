FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY cloud-run-migration/excel_vlookup_api.py ./excel_vlookup_api.py
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

CMD exec uvicorn excel_vlookup_api:app --host 0.0.0.0 --port ${PORT:-8080}
