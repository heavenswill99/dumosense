
"""
Django settings for the DumoSense backend.

Shared MVP backend for:
- DumoSense Waitlist
- MindGuard
- Health Reserve
- Accounts and Authentication
- Assessments
- Consent
- Events
- Intelligence
- Governance
"""

from pathlib import Path
from datetime import timedelta
import os

from dotenv import load_dotenv


# ============================================================
# BASE CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = os.getenv(
    "DJANGO_DEBUG", "False"
).strip().lower() == "true"


# ============================================================
# HOSTS AND DOMAINS
# ============================================================

ALLOWED_HOSTS = [
    "dumosense-backend.onrender.com",
    "api.dumosense.com",
    "localhost",
    "127.0.0.1",
]

CORS_ALLOWED_ORIGINS = [
    "https://dumosense.com",
    "https://www.dumosense.com",
]

CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    "https://dumosense.com",
    "https://www.dumosense.com",
    "https://api.dumosense.com",
]


# ============================================================
# INSTALLED APPLICATIONS
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party applications
    "rest_framework",
    "corsheaders",
    "rest_framework_simplejwt.token_blacklist",

    # DumoSense applications
    "accounts",
    "assessments",
    "consent",
    "mindguard",
    "health_reserve",
    "events",
    "intelligence",
    "governance",
    "waitlist",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URLS, TEMPLATES AND WSGI
# ============================================================

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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


# ============================================================
# CUSTOM USER MODEL
# ============================================================

AUTH_USER_MODEL = "accounts.User"


# ============================================================
# DJANGO REST FRAMEWORK
# ============================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "accounts.authentication.CookieJWTAuthentication",
    ),

    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),

    "DEFAULT_THROTTLE_RATES": {
        "waitlist": "10/hour",
        "login": "5/min",
        "registration": "5/hour",
        "password_reset": "5/hour",
    },
}


# ============================================================
# JWT AUTHENTICATION
# ============================================================

SIMPLE_JWT = {
    "USER_ID_FIELD": "user_id",
    "USER_ID_CLAIM": "user_id",

    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),

    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}


# ============================================================
# DATABASE - AIVEN MYSQL
# ============================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",

        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),

        "HOST": os.getenv(
            "DB_HOST", "127.0.0.1"
        ),

        "PORT": os.getenv(
            "DB_PORT", "3306"
        ),

        "CONN_MAX_AGE": 60,

        "OPTIONS": {
            "charset": "utf8mb4",
        },

        "TEST": {
            "NAME": "test_dumosense_dev",
        },
    }
}


# ============================================================
# DATABASE SSL CERTIFICATE
# ============================================================

db_ssl_ca = os.getenv("DB_SSL_CA", "").strip()

if db_ssl_ca:
    ca_path = Path(db_ssl_ca)

    if not ca_path.is_absolute():
        ca_path = BASE_DIR / ca_path

    if not ca_path.is_file():
        raise RuntimeError(
            f"Database SSL CA certificate not found: {ca_path}"
        )

    DATABASES["default"]["OPTIONS"]["ssl"] = {
        "ca": str(ca_path),
    }

elif not DEBUG:
    raise RuntimeError(
        "DB_SSL_CA must be configured in production."
    )


# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
        "OPTIONS": {
            "min_length": 10,
        },
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True
USE_TZ = True


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"


# ============================================================
# PRODUCTION SECURITY
# ============================================================

SECURE_SSL_REDIRECT = not DEBUG

# Render terminates HTTPS at its reverse proxy.
# Only use this when the app is reached through
# a trusted proxy that sets X-Forwarded-Proto correctly.
SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)

SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_CONTENT_TYPE_NOSNIFF = True

SECURE_REFERRER_POLICY = (
    "strict-origin-when-cross-origin"
)

X_FRAME_OPTIONS = "DENY"

# Keep HSTS disabled until HTTPS is fully verified.
# Enable gradually after production testing.
SECURE_HSTS_SECONDS = int(
    os.getenv("DJANGO_HSTS_SECONDS", "0")
)

SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False


# ============================================================
# EMAIL - RESEND
# ============================================================

RESEND_API_KEY = os.getenv(
    "RESEND_API_KEY", ""
).strip()

# Official DumoSense sender
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "hello@dumosense.com",
).strip()

WAITLIST_FROM_NAME = os.getenv(
    "WAITLIST_FROM_NAME",
    "DumoSense",
)

WAITLIST_FROM_EMAIL = DEFAULT_FROM_EMAIL

WAITLIST_WEBSITE_URL = os.getenv(
    "WAITLIST_WEBSITE_URL",
    "https://dumosense.com",
)


# Production: Resend
# Development: Console email backend
EMAIL_BACKEND = os.getenv(
    "DJANGO_EMAIL_BACKEND",
    (
        "django.core.mail.backends.console.EmailBackend"
        if DEBUG
        else "waitlist.email_backend.ResendEmailBackend"
    ),
)


# ============================================================
# TEST CONFIGURATION
# ============================================================

TEST_RUNNER = "config.test_runner.DumosenseTestRunner"


# ============================================================
# LOGGING
# ============================================================

LOGGING = {
    "version": 1,

    "disable_existing_loggers": False,

    "formatters": {
        "standard": {
            "format": (
                "[{levelname}] "
                "{asctime} "
                "{name}: {message}"
            ),
            "style": "{",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },

    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },

        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },

        "waitlist": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },

        "accounts": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
