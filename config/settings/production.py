from .base import *  # noqa: F403

from django.core.exceptions import ImproperlyConfigured

if SECRET_KEY in {"unsafe-development-key-change-me", "replace-with-a-long-random-secret"}:
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY before using production settings.")

DEBUG = False
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
