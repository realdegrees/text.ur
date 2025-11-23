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



# Try to acquire advisory lock without waiting
echo "Attempting to acquire Postgres advisory lock (key: $LOCK_KEY)..."
if psql $PSQL_OPTS -t -A -c "SELECT pg_try_advisory_lock($LOCK_KEY);" | grep -q '^t$'; then
  echo "Database lock acquired. Running Alembic migrations..."
  if ! alembic upgrade head 2>&1 | tee /tmp/alembic_error.log; then
    echo "Alembic migration failed. See error details below."
    cat /tmp/alembic_error.log
  fi
  echo "Releasing Postgres advisory lock..."
  psql $PSQL_OPTS -c "SELECT pg_advisory_unlock($LOCK_KEY);"
else
  echo "Database lock is held by another process. Waiting for it to be released..."
  # Wait until the lock is free (block until available), then immediately release and skip migrations
  psql $PSQL_OPTS -c "SELECT pg_advisory_lock($LOCK_KEY);"
  echo "Database lock released. Skipping migrations."
  psql $PSQL_OPTS -c "SELECT pg_advisory_unlock($LOCK_KEY);"
fi



echo "Starting FastAPI..."
cd ..
unset PGPASSWORD
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
