from .settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

TEST_RUNNER = "django.test.runner.DiscoverRunner"

# Disable production HTTPS redirects during isolated tests
SECURE_SSL_REDIRECT = False