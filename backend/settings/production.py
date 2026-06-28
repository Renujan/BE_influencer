import os
# pyrefly: ignore [missing-import]
import dj_database_url
from .base import *

DEBUG = False

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-prod-fallback-key-change-this-in-env")

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

CSRF_TRUSTED_ORIGINS = [origin for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if origin]

# Configure database using DATABASE_URL if available
db_from_env = dj_database_url.config(conn_max_age=600)
if db_from_env:
    DATABASES["default"] = db_from_env

# Add WhiteNoise middleware right after SecurityMiddleware for static files
if "django.middleware.security.SecurityMiddleware" in MIDDLEWARE:
    sec_index = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")
    MIDDLEWARE.insert(sec_index + 1, "whitenoise.middleware.WhiteNoiseMiddleware")

# Use WhiteNoise storage to compress and cache static files
STORAGES["staticfiles"]["BACKEND"] = "whitenoise.storage.CompressedManifestStaticFilesStorage"

try:
    # pyrefly: ignore [missing-import]
    from .local import *
except ImportError:
    pass

