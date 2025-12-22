#!/bin/bash
# Run Django in local mode (SQLite)

set -e

export ENV_MODE=local
export DEBUG=True

echo "=== JobMatch GUI - Mode Local ==="

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -q

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Create superuser if not exists
echo "Creating superuser (skip if exists)..."
python manage.py shell -c "
from accounts.models import User
if not User.objects.filter(email='admin@jobmatch.local').exists():
    User.objects.create_superuser('admin', 'admin@jobmatch.local', 'admin')
    print('Superuser created: admin@jobmatch.local / admin')
else:
    print('Superuser already exists')
" 2>/dev/null || true

# Run server
PORT=${PORT:-8000}

echo ""
echo "Starting server at http://localhost:$PORT"
echo "Admin: http://localhost:$PORT/admin (admin@jobmatch.local / admin)"
echo ""
python manage.py runserver 0.0.0.0:$PORT
