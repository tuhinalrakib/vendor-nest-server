#!/bin/sh

set -e

# Wait for PostgreSQL database if host is provided
if [ "$DATABASE_URL" ]; then
    echo "Waiting for PostgreSQL database..."
    sleep 2
fi

echo "Running Django database migrations..."
python manage.py migrate --noinput

echo "Checking & Creating Superuser if not exists..."
python manage.py shell <<EOF
import os
from django.contrib.auth import get_user_model

User = get_user_model()
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin77@gmail.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '12345As@')
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin77')

if not User.objects.filter(email=email).exists() and not User.objects.filter(username=username).exists():
    print(f"Creating superuser {email}...")
    User.objects.create_superuser(username=username, email=email, password=password)
    print("Superuser created successfully!")
else:
    print("Superuser already exists.")
EOF

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear || true

echo "Starting Django server..."
exec "$@"
