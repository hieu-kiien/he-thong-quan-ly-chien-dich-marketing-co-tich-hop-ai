"""Test settings."""

from .base import *  # noqa: F403


SECRET_KEY = "test-secret-key"
DEBUG = False

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
