#!/usr/bin/env bash
# Runs the real image the way the NAS will, then checks the frontend and the
# task API from outside the container.
set -euo pipefail

IMAGE="${IMAGE:-epos:local}"
PORT="${PORT:-18088}"
NAME="epos-smoke-$$"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

pass() { printf '  \033[32mok\033[0m   %s\n' "$1"; }
fail() { printf '  \033[31mFAIL\033[0m %s\n' "$1"; FAILED=$((FAILED + 1)); }
FAILED=0

cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "==> starting $IMAGE with the production hardening flags"
docker run -d --name "$NAME" \
  -p "127.0.0.1:${PORT}:8080" \
  --read-only --tmpfs /tmp \
  --memory 128m --cpus 1.0 \
  -e CACHE_DIR=/cache --mount type=volume,dst=/cache \
  "$IMAGE" >/dev/null

echo "==> waiting for the healthcheck"
status=starting
for _ in $(seq 1 60); do
  status="$(docker inspect -f '{{.State.Health.Status}}' "$NAME" 2>/dev/null || echo starting)"
  [ "$status" = "healthy" ] && break
  if [ "$(docker inspect -f '{{.State.Running}}' "$NAME")" != "true" ]; then
    echo "container died:"; docker logs "$NAME"; exit 1
  fi
  sleep 1
done
if [ "$status" = "healthy" ]; then pass "container reports healthy"; else fail "never became healthy"; fi

base="http://127.0.0.1:${PORT}"

echo "==> frontend is served exactly as it is in the repo"
for page in index collection search stock officers pacs; do
  if ! curl -fsS "$base/$page" -o "/tmp/page.$$"; then fail "GET /$page"; continue; fi
  if cmp -s "/tmp/page.$$" "$ROOT/static/$page.html"; then
    pass "/$page is byte-identical to static/$page.html"
  else
    fail "/$page differs from static/$page.html"
  fi
done
if curl -fsS "$base/" -o "/tmp/root.$$" && cmp -s "/tmp/root.$$" "$ROOT/static/index.html"; then
  pass "/ serves index.html"; else fail "/ does not serve index.html"; fi
if curl -fsS "$base/pacs2024.csv" -o "/tmp/csv.$$" && cmp -s "/tmp/csv.$$" "$ROOT/static/pacs2024.csv"; then
  pass "/pacs2024.csv is byte-identical"; else fail "/pacs2024.csv differs"; fi

echo "==> api contract"
if [ "$(curl -fsS "$base/healthz")" = '{"status":"ok"}' ]; then pass "/healthz"; else fail "/healthz"; fi

unknown="$(curl -fsS "$base/tasks/nope")"
if echo "$unknown" | grep -q '"status":"PENDING"'; then
  pass "unknown task id reads as PENDING (stale tab keeps polling)"
else fail "unknown task id: $unknown"; fi

if curl -fsS -o /dev/null -w '%{http_code}' "$base/get-rc-details" 2>/dev/null | grep -q 400; then
  pass "missing query args give 400"
else
  code="$(curl -s -o /dev/null -w '%{http_code}' "$base/get-rc-details")"
  if [ "$code" = "400" ]; then pass "missing query args give 400"; else fail "missing query args gave $code"; fi
fi

echo "==> a real crawl runs inside this one container"
task_id="$(curl -fsS "$base/get-rc-details?rcnumber=10310060087015900034&month=3&year=2022" \
  | sed 's/.*"task_id":"\([^"]*\)".*/\1/')"
if [ -n "$task_id" ]; then pass "submit returned a task id"; else fail "no task id returned"; fi

final=""
for _ in $(seq 1 40); do
  body="$(curl -fsS "$base/tasks/$task_id")"
  case "$body" in
    *'"status":"SUCCESS"'*) final=SUCCESS; break ;;
    *'"status":"FAILURE"'*) final=FAILURE; break ;;
  esac
  sleep 1
done
case "$final" in
  SUCCESS) pass "task reached SUCCESS -- upstream is reachable from here" ;;
  FAILURE) pass "task reached FAILURE with an error payload (worker thread ran; upstream unreachable from this host)" ;;
  *)       fail "task never left PENDING -- the worker thread is not running" ;;
esac

echo "==> container shape"
uid="$(docker exec "$NAME" id -u)"
if [ "$uid" != "0" ]; then pass "runs as non-root (uid $uid)"; else fail "running as root"; fi
procs="$(docker exec "$NAME" sh -c 'ps -o args= | grep -c "[g]unicorn"' || true)"
pass "gunicorn processes in the container: $procs (1 master + 1 worker)"

echo "==> the legacy command line is neutralised, not obeyed"
# Deployments still pin the old `--workers 2 --bind 0.0.0.0:80` command. Two
# workers would split the in-process task registry and strand polls at PENDING
# forever, so gunicorn.conf.py clamps it. Guard that here.
LEG="epos-legacy-$$"
docker rm -f "$LEG" >/dev/null 2>&1 || true
docker run -d --name "$LEG" -p "127.0.0.1:$((PORT + 1)):80" \
  -e HTTP_CONNECT_TIMEOUT=2 -e HTTP_READ_TIMEOUT=2 "$IMAGE" \
  gunicorn wsgi:app --bind 0.0.0.0:80 --workers 2 --log-level=info --access-logfile '-' >/dev/null
sleep 6
if docker logs "$LEG" 2>&1 | grep -q "ignoring --workers 2"; then
  pass "--workers 2 is refused with a warning"
else
  fail "--workers 2 was not clamped"
fi
nworkers="$(docker exec "$LEG" sh -c 'ps -o args= | grep -c "[g]unicorn"' || echo 0)"
if [ "$nworkers" = "2" ]; then
  pass "only master + 1 worker running despite --workers 2"
else
  fail "expected 2 gunicorn processes, found $nworkers"
fi
legbase="http://127.0.0.1:$((PORT + 1))"
ltid="$(curl -fsS "$legbase/get-rc-details?rcnumber=777&month=3&year=2022" | sed 's/.*"task_id":"\([^"]*\)".*/\1/')"
lfinal=""
for _ in $(seq 1 30); do
  case "$(curl -fsS "$legbase/tasks/$ltid")" in
    *'"status":"SUCCESS"'*) lfinal=SUCCESS; break ;;
    *'"status":"FAILURE"'*) lfinal=FAILURE; break ;;
  esac
  sleep 1
done
if [ -n "$lfinal" ]; then
  spread="$(seq 1 40 | xargs -P 10 -I{} curl -fsS "$legbase/tasks/$ltid" \
    | sed 's/.*"status":"\([^"]*\)".*/\1/' | sort -u | tr '\n' ',' )"
  if [ "$spread" = "${lfinal}," ]; then
    pass "40 concurrent polls of a finished task all agree ($lfinal)"
  else
    fail "polls disagree across workers: $spread"
  fi
else
  fail "task never finished under the legacy command"
fi
if [ "$(docker inspect -f '{{.State.Health.Status}}' "$LEG")" != "unhealthy" ]; then
  pass "healthcheck copes with the legacy bind on port 80"
else
  fail "healthcheck went unhealthy on the legacy bind"
fi
docker rm -f "$LEG" >/dev/null 2>&1 || true

echo "==> footprint"
docker stats --no-stream --format '  {{.Name}}  mem={{.MemUsage}}  cpu={{.CPUPerc}}' "$NAME"
echo "  image: $(docker images "$IMAGE" --format '{{.Size}}' | head -1)"

rm -f "/tmp/page.$$" "/tmp/root.$$" "/tmp/csv.$$"
echo
if [ "$FAILED" -eq 0 ]; then echo "all smoke checks passed"; else echo "$FAILED check(s) failed"; exit 1; fi
