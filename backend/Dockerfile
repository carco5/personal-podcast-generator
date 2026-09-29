# Built from the repository root. Stages: "web" builds the frontend; "base" is shared; the targets
# are "api" (prestart, the API and the built web app) and "worker" (adds ffmpeg).

FROM node:24-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend

WORKDIR /app/backend

# Dependencies first, in their own cached layer.
COPY backend/pyproject.toml ./
RUN python -c "import tomllib; print(*tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies'], sep='\n')" > requirements.txt \
    && pip install --no-cache-dir -r requirements.txt

# /data is where Compose mounts the audio volume; a new named volume inherits its owner.
RUN useradd --system --no-create-home podcast \
    && mkdir /data \
    && chown podcast /data

FROM base AS api
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY sample.mp3 /app/sample.mp3
COPY --from=web /web/dist /app/frontend/dist
USER podcast
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# The worker target adds ffmpeg, which only the pipeline uses (master, audio checks, tone voice).
FROM base AS worker
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY backend/app ./app
USER podcast
CMD ["python", "-m", "app.worker"]
