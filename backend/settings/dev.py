from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-e4y9b=67i@ic%hy1-@_wnaabbf(0-n0w++c5n#u10#05!*c4h%"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]

CORS_ALLOW_CREDENTIALS = True

#change it in production!
CORS_ALLOW_ALL_ORIGINS = True


CSRF_TRUSTED_ORIGINS = [
    "https://*.technuob.com",
    "https://*.vercel.app/",
]


# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


try:
    # pyrefly: ignore [missing-import]
    from .local import *
except ImportError:
    pass
from .local_logging import LOGGING
