# syntax=docker/dockerfile:1.7-labs

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash curl jq procps iproute2 \
    ca-certificates git build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip setuptools wheel

# PyTorch nightly with CUDA 13.0 support (Blackwell / sm_120)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --pre --index-url https://download.pytorch.org/whl/nightly/cu130 \
        torch torchvision torchaudio

COPY api/requirements-base.txt /tmp/requirements-base.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r /tmp/requirements-base.txt

FROM base AS runtime

WORKDIR /opt/app

COPY api/requirements.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r /tmp/requirements.txt

COPY api/app /opt/app/app

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
