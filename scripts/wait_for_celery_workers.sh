#!/bin/bash
set -e

until timeout 10 celery -A app.celery inspect ping; do
    >&2 echo "Celery workers not available"
done

echo "Starting flower"
exec "$@"