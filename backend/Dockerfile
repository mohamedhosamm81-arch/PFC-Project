# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

# Dependencies are installed before application code so routine code changes
# reuse the cached layer.
COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt \
    && python -m pip check

# Run as an unprivileged account.
RUN groupadd --gid 10001 pfc \
    && useradd --uid 10001 --gid pfc --create-home --shell /usr/sbin/nologin pfc

COPY --chown=pfc:pfc alembic.ini ./
COPY --chown=pfc:pfc alembic ./alembic
COPY --chown=pfc:pfc app ./app
COPY --chown=pfc:pfc entrypoint.sh ./

RUN chmod 0755 /app/entrypoint.sh \
    && mkdir -p /app/var \
    && chown -R pfc:pfc /app

USER pfc

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=5 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=4).status == 200 else 1)"

ENTRYPOINT ["/app/entrypoint.sh"]
