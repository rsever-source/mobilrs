FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# KORUMA: Aşağıdakilerden biri eksikse build burada DURUR, deploy'a hiç geçilmez.
#  - logo dosyaları image'da olmalı
#  - erişilebilirlik, atla bağlantısı, KVKK, sohbet ve logo kodu excel_vlookup_api.py içinde olmalı
#  - eski/stale cloud-run-migration/ klasörü image'a girmemiş olmalı
RUN test -f logo.png && test -f favicon.png && test -f apple-touch-icon.png \
 && grep -qF "accessibilityToggle" excel_vlookup_api.py \
 && grep -qF "skip-link" excel_vlookup_api.py \
 && grep -qF "klaklak.com" excel_vlookup_api.py \
 && grep -qF '"/kvkk"' excel_vlookup_api.py \
 && grep -qF "/logo.png" excel_vlookup_api.py \
 && test ! -e cloud-run-migration

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

CMD exec uvicorn excel_vlookup_api:app --host 0.0.0.0 --port ${PORT:-8080}
