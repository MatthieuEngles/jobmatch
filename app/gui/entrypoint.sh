#!/bin/bash
# Entrypoint for Docker containers

set -e

echo "=== JobMatch GUI - Docker Entrypoint ==="
echo "ENV_MODE: $ENV_MODE"

# Wait for database (dev mode)
if [ "$ENV_MODE" = "dev" ]; then
    echo "Waiting for PostgreSQL..."
    while ! nc -z ${POSTGRES_HOST:-db} ${POSTGRES_PORT:-5432}; do
        sleep 1
    done
    echo "PostgreSQL is ready!"
fi

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start server
if [ "$ENV_MODE" = "prod" ]; then
    echo "Starting Gunicorn (production)..."
    exec gunicorn config.wsgi:application \
        --bind 0.0.0.0:${PORT:-8080} \
        --workers ${GUNICORN_WORKERS:-2} \
        --threads ${GUNICORN_THREADS:-4} \
        --timeout 120 \
        --access-logfile - \
        --error-logfile -
else
    echo "Starting Django dev server..."
    exec python manage.py runserver 0.0.0.0:${PORT:-8080}
fi
