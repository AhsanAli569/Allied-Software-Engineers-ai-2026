FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# libpq is needed at runtime by asyncpg's C extension build deps on some platforms;
# gcc is only needed to build wheels that don't ship prebuilt ones for this base image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# /data/storage is created (with correct ownership) here, before it's ever mounted as a
# volume — Docker copies a fresh named volume's initial contents/ownership from whatever
# already exists at the mount point in the image, so this is what makes the non-root
# `aseai` user able to write there once docker-compose mounts backend-storage on top of it.
RUN chmod +x entrypoint.sh \
    && mkdir -p /data/storage \
    && useradd --create-home --uid 1000 aseai \
    && chown -R aseai:aseai /app /data/storage
USER aseai

EXPOSE 8000

# Shell form so $PORT is expanded at runtime (Render injects it; defaults to 8000 for
# docker-compose.prod.yml, which doesn't set it).
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/v1/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]





