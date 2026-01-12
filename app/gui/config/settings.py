"""
Django settings for JobMatch GUI.
Supports 3 modes: local, docker-dev, docker-prod (Cloud Run)
"""

import os
from datetime import timedelta
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment mode: local, dev, prod
ENV_MODE = os.environ.get("ENV_MODE", "local")

# Security
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-dev-only-change-in-production")
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(",")

# CSRF trusted origins for Cloud Run
CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
CSRF_TRUSTED_ORIGINS = [x for x in CSRF_TRUSTED_ORIGINS if x]  # Remove empty strings


# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    # Local apps
    "accounts",
    "api",
]

# Development-only apps (local only, not in Docker)
if ENV_MODE == "local":
    try:
        import django_extensions  # noqa: F401

        INSTALLED_APPS.append("django_extensions")
    except ImportError:
        pass

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Static files in prod
    "corsheaders.middleware.CorsMiddleware",  # CORS must be before CommonMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database configuration
# All modes use PostgreSQL for data consistency between local and Docker
# Local mode connects to Docker PostgreSQL via exposed port (localhost:5433)
# Docker mode connects internally (db:5432)
if ENV_MODE == "local":
    # Local dev: connect to Docker PostgreSQL via exposed port
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "jobmatch"),
            "USER": os.environ.get("POSTGRES_USER", "jobmatch"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "jobmatch"),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5433"),  # Exposed Docker port
        }
    }
else:
    # Docker dev & prod use PostgreSQL via internal network
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "jobmatch"),
            "USER": os.environ.get("POSTGRES_USER", "jobmatch"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "jobmatch"),
            "HOST": os.environ.get("POSTGRES_HOST", "db"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }

    # Cloud SQL connection via Unix socket (Cloud Run)
    if os.environ.get("CLOUD_SQL_CONNECTION_NAME"):
        DATABASES["default"]["HOST"] = f"/cloudsql/{os.environ.get('CLOUD_SQL_CONNECTION_NAME')}"


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Custom user model
AUTH_USER_MODEL = "accounts.User"


# Internationalization
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True


# Static files
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files (uploads)
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Google Cloud Storage for media in prod
if ENV_MODE == "prod" and os.environ.get("GCS_BUCKET_NAME"):
    DEFAULT_FILE_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"
    GS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")
    GS_DEFAULT_ACL = "publicRead"


# Login/Logout redirects
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
LOGIN_URL = "/accounts/login/"


# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Microservices URLs
CV_INGESTION_URL = os.environ.get("CV_INGESTION_URL", "http://localhost:8081")
AI_ASSISTANT_URL = os.environ.get("AI_ASSISTANT_URL", "http://localhost:8084")


# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO" if ENV_MODE == "prod" else "DEBUG",
    },
}


# =============================================================================
# Django REST Framework
# =============================================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",  # For browsable API
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# Add browsable API in development
if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append("rest_framework.renderers.BrowsableAPIRenderer")


# =============================================================================
# Simple JWT Configuration
# =============================================================================
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
}


# =============================================================================
# CORS Configuration
# =============================================================================
# TODO: SECURITY - Restrict CORS origins for production
# In development, allow all origins for easier testing with browser extension
# In production, restrict to specific extension IDs:
#   CORS_ALLOWED_ORIGIN_REGEXES = [
#       r"^chrome-extension://[a-z]{32}$",
#       r"^moz-extension://[a-f0-9-]{36}$",
#   ]
#   CORS_ALLOWED_ORIGINS = [
#       "chrome-extension://YOUR_EXTENSION_ID",
#   ]

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    # Production: restrict to known origins
    CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    CORS_ALLOWED_ORIGINS = [x for x in CORS_ALLOWED_ORIGINS if x]
    # Also allow regex patterns for browser extensions
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^chrome-extension://[a-z]{32}$",
        r"^moz-extension://[a-f0-9-]{36}$",
    ]

# Allow credentials (cookies) if needed for session auth fallback
CORS_ALLOW_CREDENTIALS = True

# Headers allowed in CORS requests
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]


# =============================================================================
# Redis Cache Configuration
# =============================================================================
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "RETRY_ON_TIMEOUT": True,
        },
        "KEY_PREFIX": "jobmatch",
    }
}

# Cache timeouts (in seconds)
CACHE_TTL_MATCHING_RESULTS = 60 * 15  # 15 minutes for matching results
CACHE_TTL_OFFER_DETAILS = 60 * 60  # 1 hour for offer details


# =============================================================================
# DRF Spectacular (OpenAPI/Swagger)
# =============================================================================
SPECTACULAR_SETTINGS = {
    "TITLE": "JobMatch API",
    "DESCRIPTION": "API REST pour l'extension navigateur JobMatch",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
    },
}
