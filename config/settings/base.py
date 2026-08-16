import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# Path of this file: config/settings/base.py
# parent -> config/settings
# parent.parent -> config
# parent.parent.parent -> vendor-nest-server (BASE_DIR)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY') or os.getenv('DJANGO_SECRET_KEY', 'django-insecure-docker-vendornest-secret-key-2026')

# Add 'apps' directory to Python path so custom apps can be imported directly
sys.path.insert(0, str(BASE_DIR / 'apps'))

# Debug setting
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary_storage',
    'cloudinary',
    "corsheaders",
    'drf_yasg',
    'rest_framework_simplejwt.token_blacklist',

    # Custom Apps
    'core',
    'ai',
    'categories',
    'dashboard',
    'notifications',
    'orders',
    'payments',
    'products',
    'seller',
    'shipping',
    'users',
    'coupons',
    
    'rest_framework',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.MaintenanceModeMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBUG:
    try:
        import debug_toolbar
        INSTALLED_APPS.append("debug_toolbar")
        MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    except ImportError:
        pass

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ALLOWED_HOSTS = ['*']

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# URLs for Backend and Frontend
BACKEND_URL = os.getenv('BACKEND_URL', 'http://127.0.0.1:8000')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')


# Cloudinary Storage Configuration
CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
    'API_KEY': CLOUDINARY_API_KEY,
    'API_SECRET': CLOUDINARY_API_SECRET,
}

# Modern Django 4.2+ Storage settings
# Use Cloudinary if actual credentials are set, else fallback to FileSystemStorage for local development
if CLOUDINARY_CLOUD_NAME and CLOUDINARY_CLOUD_NAME != "your_cloud_name" and CLOUDINARY_API_KEY != "your_api_key":
    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
DB_HOST = os.getenv('DB_HOST')

# If DATABASE_URL points to an unresolvable Render host (dpg-...) and DB_HOST (Neon DB) is provided, fallback to DB_HOST
if DATABASE_URL and 'dpg-' in DATABASE_URL and DB_HOST:
    DATABASE_URL = None

if DATABASE_URL:
    db_ssl = os.getenv('DB_SSL_REQUIRE', 'False').lower() in ('true', '1')
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=db_ssl
        )
    }
elif os.getenv('DB_PASSWORD'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'neondb'),
            'USER': os.getenv('DB_USER', 'neondb_owner'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST': DB_HOST or 'ep-late-shape-ao12ffaz-pooler.c-2.ap-southeast-1.aws.neon.tech',
            'PORT': os.getenv('DB_PORT', '5432'),
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:9000",
    "https://vendor-nest.vercel.app",
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://.*\.localhost:3000$",
]


# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

# Simple JWT Configuration
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# Swagger Settings for JWT Authentication
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'USE_SESSION_AUTH': False,
}

# ==============================================================================
# SMTP Email Configuration (Gmail SMTP / Custom SMTP / Brevo API)
# ==============================================================================
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'core.email_backends.BrevoEmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1')
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() in ('true', '1')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'eng.tuhin77@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', 'yhfcmcefypwxschm')
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

# API Keys for Brevo and Resend Email Fallback Backends
BREVO_API_KEY = os.getenv('BREVO_API_KEY')
RESEND_API_KEY = os.getenv('RESEND_API_KEY')
# ==============================================================================




# Caching Configuration (Redis with LocMemCache fallback for local dev)
REDIS_URL = os.getenv('REDIS_URL')
if REDIS_URL:
    _is_ssl = REDIS_URL.startswith('rediss://')
    CACHES = {
        'default': {
            'BACKEND': 'core.cache.SafeRedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'socket_timeout': 30.0,
                'socket_connect_timeout': 30.0,
                'health_check_interval': 30,
                # Redis Cloud uses SSL — skip cert verification for dev
                **({'ssl_cert_reqs': None} if _is_ssl else {}),
            }
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'vendor-nest-local-cache',
        }
    }

STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', 'sk_test_mock_secret_key')

# Twilio Settings
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')