# One container for everything: API, static frontend and the crawl workers.
FROM python:3.13-alpine AS build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Every dependency ships a musllinux wheel today; build-base is only a safety
# net so a future version bump compiles instead of failing the build. It stays
# in this stage and never reaches the final image.
RUN apk add --no-cache build-base libffi-dev

COPY requirements.txt /requirements.txt
RUN python -m venv /venv \
    && /venv/bin/pip install -r /requirements.txt


FROM python:3.13-alpine

ENV PATH="/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CACHE_DIR=/cache \
    PORT=8080

COPY --from=build /venv /venv

WORKDIR /app
COPY wsgi.py utils.py tasks.py gunicorn.conf.py ./
COPY app ./app
COPY crawler ./crawler
COPY static ./static

# Ship the bytecode so the first request after a restart does not pay to compile
# it, and so nothing needs to write to /app at runtime.
RUN python -m compileall -q /app \
    && adduser -D -H -u 10001 epos \
    && mkdir -p /cache \
    && chown -R epos:epos /cache

USER epos
EXPOSE 8080

# busybox wget is already in the base image, so this costs far less than
# starting a second Python interpreter every minute.
HEALTHCHECK --interval=60s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- "http://127.0.0.1:${PORT}/healthz" >/dev/null || exit 1

CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]
