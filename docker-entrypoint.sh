#!/bin/bash
set -e

# Configure djangosettings if custom config dir is writable
if [ -w "$FREPPLE_CONFIGDIR/djangosettings.py" ] 2>/dev/null; then
  sed -i "s/SECRET_KEY.*/SECRET_KEY = \"$(openssl rand -hex 32)\"/g" "$FREPPLE_CONFIGDIR/djangosettings.py" 2>/dev/null || true
fi

# Wait for PostgreSQL if host is configured
if [ -n "$POSTGRES_HOST" ]; then
  echo "Waiting for PostgreSQL at $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
  for i in $(seq 1 30); do
    if pg_isready -h "$POSTGRES_HOST" -p "${POSTGRES_PORT:-5432}" -U "$POSTGRES_USER" 2>/dev/null; then
      echo "PostgreSQL is ready"
      break
    fi
    if [ $i -eq 30 ]; then
      echo "PostgreSQL not available after 30 attempts"
      exit 1
    fi
    sleep 1
  done
fi

# Create database and run migrations
frepplectl createdatabase --skip-if-exists 2>/dev/null || true
frepplectl migrate --noinput

# Execute command
exec "$@"
