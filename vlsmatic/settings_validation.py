"""Static validation settings that never provide a runnable database.

This module exists for environments that cannot load a PostgreSQL driver. The
application, development server, tests, and production all use settings.py and
therefore require PostgreSQL.
"""

from .settings import *  # noqa: F403


DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}
