#!/bin/sh
set -e

echo "Running docker-entrypoint.sh..."
echo "Loading environment variables..."
if [ -f /annotation-software/app/.env ]; then
  set -a
  # shellcheck disable=SC1091
  . /annotation-software/app/.env
  set +a
  echo "Environment variables loaded from .env file."
else
  echo "No .env file found, using system environment variables."
fi

echo "Waiting for Postgres..."
export PGPASSWORD="$POSTGRES_PASSWORD"
# Keep DATABASE_URL in SQLAlchemy form for Alembic/SQLAlchemy usage. psql doesn't
# understand the SQLAlchemy-specific "+psycopg2" suffix, so create an explicit
# option string for psql calls below.
export DATABASE_URL="postgresql+psycopg2://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB"
echo "DATABASE_URL is set to: $DATABASE_URL"


PSQL_OPTS="-h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB"
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
  sleep 2
done


echo "Applying migrations..."

# Use Postgres advisory lock to ensure only one container runs migrations at a time
LOCK_KEY=12345
cd /annotation-software/database



echo "Attempting to acquire Postgres advisory lock (key: $LOCK_KEY)..."

# Create a FIFO and temporary file to coordinate with a persistent psql session.
FIFO=$(mktemp -u)
OUTFILE=$(mktemp)
mkfifo "$FIFO"

# Start a background psql session: first run pg_try_advisory_lock, then read further
# commands from the FIFO (so the psql process stays alive and can hold the lock).
( echo "SELECT pg_try_advisory_lock($LOCK_KEY);" ; cat "$FIFO" ) | psql $PSQL_OPTS -t -A > "$OUTFILE" 2>/tmp/psql_lock.err &
LOCK_PSQL_PID=$!

# Wait for the initial result (up to 120s)
for i in $(seq 1 120); do
  if [ -s "$OUTFILE" ]; then
    break
  fi
  sleep 1
done

if [ ! -s "$OUTFILE" ]; then
  echo "Timed out waiting for lock result. Check /tmp/psql_lock.err for details."
  kill "$LOCK_PSQL_PID" 2>/dev/null || true
  rm -f "$FIFO" "$OUTFILE"
  exit 1
fi

LOCK_RES=$(head -n1 "$OUTFILE" | tr -d '[:space:]')

if [ "$LOCK_RES" = "t" ]; then
  OWN_LOCK=1
  echo "Database lock acquired. Running Alembic migrations..."

  cleanup() {
    if [ "${OWN_LOCK:-0}" = "1" ]; then
      echo "Releasing Postgres advisory lock..."
      echo "SELECT pg_advisory_unlock($LOCK_KEY);" > "$FIFO" || true
      wait "$LOCK_PSQL_PID" 2>/dev/null || true
    else
      kill "$LOCK_PSQL_PID" 2>/dev/null || true
    fi
    rm -f "$FIFO" "$OUTFILE"
  }

  trap cleanup EXIT INT TERM

  if ! alembic upgrade head 2>&1 | tee /tmp/alembic_error.log; then
    echo "Alembic migration failed. See error details below."
    cat /tmp/alembic_error.log
    exit 1
  fi

  # Success: release lock and cleanup now
  trap - EXIT
  cleanup
  echo "Migrations complete."
else
  echo "Database lock is held by another process. Waiting for it to be released..."
  # This background psql session did not obtain the lock; stop it and wait for lock release
  kill "$LOCK_PSQL_PID" 2>/dev/null || true
  rm -f "$FIFO" "$OUTFILE"
  # Block until lock is free, then immediately release it and skip migrations
  psql $PSQL_OPTS -c "SELECT pg_advisory_lock($LOCK_KEY); SELECT pg_advisory_unlock($LOCK_KEY);"
  echo "Database lock released. Skipping migrations."
fi



echo "Starting FastAPI..."
cd ..
unset PGPASSWORD
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
