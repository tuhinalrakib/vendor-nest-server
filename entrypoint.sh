#!/bin/sh

set -e

# Wait for PostgreSQL container if host is provided
if [ "$DATABASE_URL" ]; then
    echo "Waiting for PostgreSQL database..."
    # Extract host and port if needed or wait for DB container
    sleep 2
fi

echo "Running Django database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear || true

echo "Starting Django server..."
exec "$@"
