#!/bin/bash
# Reset database script

echo "⚠️  WARNING: This will delete all data in the database!"
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

# Load environment variables
source .env

# Drop and recreate database
echo "Dropping database..."
docker compose exec -T db psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS taxi_db;"

echo "Creating database..."
docker compose exec -T db psql -U postgres -d postgres -c "CREATE DATABASE taxi_db OWNER postgres;"

echo "Enabling PostGIS..."
docker compose exec -T db psql -U postgres -d taxi_db -c "CREATE EXTENSION IF NOT EXISTS postgis;"

echo "Running migrations..."
docker compose exec api python manage.py migrate

echo "Creating superuser..."
docker compose exec api python manage.py initial_setup --skip-migrations

echo "✓ Database reset completed!"