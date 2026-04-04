#!/bin/bash
# Entrypoint script for Docker container

set -e

echo "Waiting for PostgreSQL..."
while ! nc -z $DB_HOST ${DB_PORT:-5432}; do
    sleep 0.1
done
echo "PostgreSQL started"

echo "Waiting for Redis..."
while ! nc -z ${REDIS_HOST:-redis} 6379; do
    sleep 0.1
done
echo "Redis started"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Starting application..."
exec "$@"