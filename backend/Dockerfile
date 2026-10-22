# Used by docker-compose locally and by Render when the service runtime is "Docker"
# (Render: Root Directory = backend, Dockerfile Path = ./Dockerfile).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# WeasyPrint (PDF export) needs Pango/HarfBuzz. Arabic fonts are bundled in app/pdf/fonts.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libharfbuzz-subset0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
# Render injects $PORT; locally it defaults to 8000. Migrations are a no-op when the schema is current.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
