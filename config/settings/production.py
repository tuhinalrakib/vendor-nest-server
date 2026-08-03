import os
import dj_database_url
from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY') or os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-docker-vendornest-secret-key-2026')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1')

allowed_hosts_raw = os.environ.get('ALLOWED_HOSTS') or os.environ.get('DJANGO_ALLOWED_HOSTS')
if allowed_hosts_raw and allowed_hosts_raw.strip() and allowed_hosts_raw != '*':
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_raw.split(',') if host.strip()] + ['*', '.onrender.com']
else:
    ALLOWED_HOSTS = ['*']

# Configure database using DATABASE_URL environment variable
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    db_ssl = os.environ.get('DB_SSL_REQUIRE', 'False').lower() in ('true', '1')
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=db_ssl
        )
    }

# CORS Configuration
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = True

cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS')
if cors_origins:
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(',') if origin.strip()]



