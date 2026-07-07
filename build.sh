#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files and run migrations
python manage.py collectstatic --no-input
python manage.py migrate
