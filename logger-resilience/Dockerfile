FROM python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends mosquitto-clients docker-cli \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY scripts/resilience_lib ./scripts/resilience_lib
COPY scripts/resilience_watcher.py scripts/resilience_watcher.py
COPY scripts/probe_logger.py scripts/probe_logger.py

CMD ["python3", "scripts/resilience_watcher.py"]
