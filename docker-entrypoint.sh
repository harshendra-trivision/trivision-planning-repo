#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
echo "Waiting for the database to be ready"
retries=30
until pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-frepple}" -q; do
  sleep 1
  ((retries--))
  if [ $retries -eq 0 ]; then
    echo "Cannot connect to PostgreSQL on ${POSTGRES_HOST}:${POSTGRES_PORT:-5432}"
    exit 1
  fi
done

# Create the databases (skip if they already exist)
/usr/share/frepple/venv/bin/python /app/frepplectl.py createdatabase --skip-if-exists

# Run migrations
/usr/share/frepple/venv/bin/python /app/frepplectl.py migrate --noinput

# Start Django development server (same as local dev)
echo "Starting Django development server on 0.0.0.0:${PORT:-8000}"
exec /usr/share/frepple/venv/bin/python /app/frepplectl.py runserver "0.0.0.0:${PORT:-8000}"
