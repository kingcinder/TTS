# syntax=docker/dockerfile:1.7
FROM python:3.10.14-slim AS base

ENV PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends bash ffmpeg sox libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY containers/requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock

# Preinstall CPU-only PyTorch stack (no CUDA) to avoid runtime downloads
ARG TORCH_CPU_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --index-url ${TORCH_CPU_INDEX_URL} \
    torch==2.3.1 torchaudio==2.3.1 torchvision==0.18.1

COPY . /app

RUN useradd --create-home appuser && \
    chown -R appuser:appuser /app
USER appuser

ENV TTS_LOG_FILE=/app/artifacts/logs/container-run.jsonl \
    TTS_OUTPUT_DIR=/app/artifacts/outputs/demo \
    TTS_MODEL_DIR=/app/artifacts/models/xtts_v2 \
    PYTHONPATH=/app

ENTRYPOINT ["bash","-lc","./run.sh"]

HEALTHCHECK --interval=1m --timeout=10s --start-period=30s --retries=3 \
  CMD bash -lc 'test -f "${TTS_OUTPUT_DIR}/render.wav" || exit 1'
