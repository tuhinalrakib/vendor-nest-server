import os
import dj_database_url
from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY') or os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-docker-vendornest-secret-key-2026')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1')

allowed_hosts_raw = os.environ.get('ALLOWED_HOSTS') or os.environ.get('DJANGO_ALLOWED_HOSTS')
if allowed_hosts_raw and allowed_hosts_raw.strip() and allowed_hosts_raw != '*':
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_raw.split(',') if host.strip()] + ['*', '.onrender.com', '.vercel.app']
else:
    ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = [
    'https://*.vercel.app',
    'https://*.onrender.com',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS')
if csrf_origins:
    CSRF_TRUSTED_ORIGINS.extend([origin.strip() for origin in csrf_origins.split(',') if origin.strip()])


# Configure database using DATABASE_URL environment variable
DATABASE_URL = os.environ.get('DATABASE_URL')
DB_HOST = os.environ.get('DB_HOST')

if DATABASE_URL and 'dpg-' in DATABASE_URL and DB_HOST:
    DATABASE_URL = None

if DATABASE_URL:
    db_ssl = os.environ.get('DB_SSL_REQUIRE', 'False').lower() in ('true', '1')
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=db_ssl
        )
    }
elif DB_HOST:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'postgres'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
            'HOST': DB_HOST,
            'PORT': os.environ.get('DB_PORT', '5432'),
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    }

# Ensure debug_toolbar is disabled when DEBUG is False
if not DEBUG:
    if "debug_toolbar" in INSTALLED_APPS:
        INSTALLED_APPS.remove("debug_toolbar")
    MIDDLEWARE = [m for m in MIDDLEWARE if m != "debug_toolbar.middleware.DebugToolbarMiddleware"]

# CORS Configuration
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = True

cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS')
if cors_origins:
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(',') if origin.strip()]



