"""
Django settings for insta_clone.

Production-ready configuration:
  - Environment variable driven (SECRET_KEY, DATABASE_URL, CLOUDINARY_URL, DEBUG, ALLOWED_HOSTS)
  - Cloudinary SDK native config (no fragile string parsing)
  - Cloudinary for media storage in production
  - WhiteNoise for static files (CompressedManifestStaticFilesStorage)
  - Security headers gated behind DEBUG=False
  - PostgreSQL via DATABASE_URL on Render; SQLite locally
  - ALLOWED_HOSTS raises ImproperlyConfigured when empty in production
  - Critical warning when CLOUDINARY_URL is missing in production
"""

from pathlib import Path
import os
import logging
import dj_database_url
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  CORE
# ─────────────────────────────────────────────

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG      = os.environ.get('DEBUG', 'False') == 'True'

# ─────────────────────────────────────────────
#  ALLOWED_HOSTS  (raises in production if not set)
# ─────────────────────────────────────────────

_raw_hosts = os.environ.get('ALLOWED_HOSTS', '').strip()

if _raw_hosts:
    ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(',') if h.strip()]
elif DEBUG:
    # Local development — allow all
    ALLOWED_HOSTS = ['*']
else:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS environment variable must be set in production.\n"
        "Example: ALLOWED_HOSTS=yourapp.onrender.com"
    )

# Allow Render's SSL domain and any custom domain in CSRF
CSRF_TRUSTED_ORIGINS = [
    f"https://{h}" for h in ALLOWED_HOSTS if not h.startswith('*')
]

# Extra security headers (only in production)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER       = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT           = True
    SESSION_COOKIE_SECURE         = True
    CSRF_COOKIE_SECURE            = True
    SECURE_HSTS_SECONDS           = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD           = True
    SECURE_CONTENT_TYPE_NOSNIFF   = True


# ─────────────────────────────────────────────
#  APPS
# ─────────────────────────────────────────────

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary',
    'cloudinary_storage',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise must come directly after SecurityMiddleware
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS':    [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# ─────────────────────────────────────────────
#  DATABASE
#  Set DATABASE_URL env var on Render.
#  Falls back to SQLite for local development.
# ─────────────────────────────────────────────

_db_url = os.environ.get('DATABASE_URL')
if _db_url:
    DATABASES = {
        'default': dj_database_url.config(
            default=_db_url,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME':   BASE_DIR / 'db.sqlite3',
        }
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ─────────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────────

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL           = '/login/'
LOGIN_REDIRECT_URL  = '/'
LOGOUT_REDIRECT_URL = '/login/'

SESSION_COOKIE_AGE = 1209600  # 2 weeks


# ─────────────────────────────────────────────
#  INTERNATIONALIZATION
# ─────────────────────────────────────────────

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'UTC'
USE_I18N      = True
USE_TZ        = True


# ─────────────────────────────────────────────
#  STATIC FILES  (WhiteNoise)
# ─────────────────────────────────────────────

STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []


# ─────────────────────────────────────────────
#  MEDIA FILES  (Cloudinary in production, local in dev)
#
#  Uses cloudinary SDK native CLOUDINARY_URL parsing:
#    cloudinary.config() reads CLOUDINARY_URL env var automatically.
#  No more fragile manual string-splitting.
# ─────────────────────────────────────────────

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL', '')

if CLOUDINARY_URL:
    import cloudinary

    # Let the SDK parse the URL natively — handles any cloud name format correctly
    cloudinary.config()  # reads CLOUDINARY_URL from environment automatically

    _cfg = cloudinary.config()
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': _cfg.cloud_name,
        'API_KEY':    _cfg.api_key,
        'API_SECRET': _cfg.api_secret,
    }

    STORAGES = {
        'default':     {'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
    }
else:
    if not DEBUG:
        # Production without Cloudinary = uploaded files will vanish on Render redeploy
        logging.getLogger('django').critical(
            "CLOUDINARY_URL is not set in production! "
            "Media uploads will be stored on the ephemeral Render filesystem "
            "and will be LOST on every redeploy. Set CLOUDINARY_URL immediately."
        )

    STORAGES = {
        'default':     {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
    }


# ─────────────────────────────────────────────
#  EMAIL  (console in dev, configure SMTP in prod)
# ─────────────────────────────────────────────

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style':  '{',
        },
    },
    'handlers': {
        'console': {
            'class':     'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level':    'WARNING',
    },
    'loggers': {
        'django': {
            'handlers':  ['console'],
            'level':     'INFO' if DEBUG else 'WARNING',
            'propagate': False,
        },
    },
}
