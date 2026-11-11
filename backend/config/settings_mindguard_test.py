"""Standalone offline settings: do not import production settings or load .env.

Use only for disposable automated tests, never to serve the application.
"""
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "mindguard-isolated-test-key-never-use-in-production"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]
ROOT_URLCONF = "config.urls"  # Exercise the actual application's route registration.
AUTH_USER_MODEL = "accounts.User"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "corsheaders", "rest_framework_simplejwt.token_blacklist",
    "accounts", "assessments", "consent", "mindguard", "intelligence",
    # Loaded so config.urls is unchanged; the runner creates no product tables
    # outside the explicit MindGuard allowlist.
    "health_reserve", "events", "governance",
]
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:",
    "TEST": {"NAME": ":memory:"},
}}
DATABASE_ROUTERS = []
TEST_RUNNER = "config.mindguard_test_runner.IsolatedMindGuardRunner"
MINDGUARD_ISOLATED_TESTS = True
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("accounts.authentication.CookieJWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}
SIMPLE_JWT = {
    "USER_ID_FIELD": "user_id", "USER_ID_CLAIM": "user_id",
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15), "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True, "BLACKLIST_AFTER_ROTATION": True,
}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
STATIC_URL = "/static/"
USE_TZ = True
TIME_ZONE = "UTC"
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
