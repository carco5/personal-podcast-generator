# One shared base stage and two targets: "api" (prestart and the API) and "worker" (adds ffmpeg).

FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Dependencies first, in their own cached layer.
COPY pyproject.toml ./
RUN python -c "import tomllib; print(*tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies'], sep='\n')" > requirements.txt \
    && pip install --no-cache-dir -r requirements.txt

# /data is where Compose mounts the audio volume; a new named volume inherits its owner.
RUN useradd --system --no-create-home podcast \
    && mkdir /data \
    && chown podcast /data

FROM base AS api
COPY app ./app
COPY migrations ./migrations
USER podcast
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# The worker target adds ffmpeg, which only the pipeline uses (master, audio checks, tone voice).
FROM base AS worker
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY app ./app
USER podcast
CMD ["python", "-m", "app.worker"]
