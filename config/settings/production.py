import os
import dj_database_url
from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY') or os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-docker-vendornest-secret-key-2026')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1')

allowed_hosts_raw = os.environ.get('ALLOWED_HOSTS') or os.environ.get('DJANGO_ALLOWED_HOSTS') or '*'
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_raw.split(',') if host.strip()]

# Configure database using DATABASE_URL environment variable
if os.environ.get('DATABASE_URL'):
    db_ssl = os.environ.get('DB_SSL_REQUIRE', 'False').lower() in ('true', '1')
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            ssl_require=db_ssl
        )
    }

# CORS Configuration for Production
cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS')
if cors_origins:
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(',') if origin.strip()]



