FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ATLAS_LIVE_TRADING=false \
    ATLAS_DASHBOARD_ONLY=true \
    ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt \
    && useradd --create-home --uid 10001 atlas

COPY --chown=atlas:atlas app ./app
COPY --chown=atlas:atlas web ./web

USER atlas

EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*'"]
