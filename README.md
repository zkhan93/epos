# epos

A Flask application that parses data from the Indian state Bihar government's
"epos bihar" website and converts it into an API. That API backs a Vue.js 2
frontend presenting the data on a mobile-friendly, responsive site.

Everything runs in **one container**: the API, the static frontend, and the
crawl workers.

## Features

- Parses data from the "epos bihar" and "epds bihar" sites
- Converts it into a simple JSON API
- Frontend built with Vue.js 2, served straight out of `static/`
- Caches pages that are unlikely to change, so repeat views cost nothing
- Deduplicates identical in-flight requests, so two tabs never scrape twice

## Architecture

Requests that need a crawl return a task id immediately and the browser polls
`/tasks/<id>` until the result is ready. That job/poll pattern used to be
Celery + Redis + a separate worker container. Every task is just an HTTP fetch
plus an HTML table parse, so it now runs on a small thread pool inside the web
process (`tasks.py`): one interpreter, no broker, no second image to keep in
sync.

Measured on the same machine, idle, anonymous memory via `memory.stat`:

| | containers | memory | image |
|---|---|---|---|
| web + worker + redis | 3 | 139 MiB | 1.17 GB |
| this | 1 | 44 MiB | 61 MB |

Because task state lives in process memory, the app runs **one** gunicorn
worker with several threads. A `--workers` above 1 is clamped back to 1 with a
warning rather than obeyed: a task queued by one process is invisible to
another, so polls would land on a worker that has never heard of the task and
the spinner would never stop. Scale with `THREADS` instead.

A deployment that still pins the old command
(`gunicorn wsgi:app --bind 0.0.0.0:80 --workers 2 ...`) keeps working — the
worker count is clamped and the healthcheck accepts port 80 — but drop the
`command:` block anyway and let the image's own `CMD` run, so you get the tuned
config instead of gunicorn defaults.

## Running it

```bash
docker compose up -d
```

The container listens on **8080** as a non-root user (it used to be 80 as
root). If you front it with a reverse proxy, point it at 8080 — the Traefik
label in `docker-compose.yml` already does.

Useful environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8080` | Port to listen on |
| `THREADS` | `8` | HTTP worker threads |
| `TASK_WORKERS` | `4` | Threads running crawls |
| `TASK_MAX_QUEUED` | `32` | Queued crawls before requests are refused with 503 |
| `CACHE_DIR` | `/cache` | diskcache directory |
| `CACHE_TTL` | `43200` | Cache lifetime in seconds (12h) |
| `CACHE_SIZE_LIMIT` | `134217728` | Cache size cap in bytes |
| `HTTP_READ_TIMEOUT` | `60` | Per-request timeout against the government site |
| `LOG_POLLS` | `False` | Log the once-a-second `/tasks/<id>` polls |

## Development

```bash
make dev
```

## Tests

The suite runs fully offline — the upstream site is stubbed at the one pooled
`requests.Session`, and any test that tries to reach the network fails loudly.

```bash
pip install -r requirements-dev.txt
make test
```

`tests/test_ui_unchanged.py` is the guard rail that matters: it asserts each
page is served byte-for-byte as it sits in `static/`, and that every path the
frontend links to still routes. The people using this site should never notice
an infrastructure change.

To check the real image end to end — health, byte-identical pages, a live task
going from submit to a terminal state, non-root, and the resulting footprint:

```bash
make build && make smoke
```

## Monitoring

Flower is gone with Celery. `/healthz` is the liveness endpoint and the
container has a `HEALTHCHECK` wired to it.

## Contributing

Fork the repository and open a pull request.

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT)
