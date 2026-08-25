"""Local development settings."""

import os

from .base import *  # noqa: F403


SECRET_KEY = os.getenv("SECRET_KEY", "local-development-secret-key")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
