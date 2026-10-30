from .base import *  # noqa: F403

DEBUG = True
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}
