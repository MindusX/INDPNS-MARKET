from .base import *  # noqa: F401,F403
from .base import env, env_bool

ENVIRONMENT = "development"
DEBUG = env_bool("DEBUG", True)
SECRET_KEY = env("SECRET_KEY") or "dev-only-insecure-key-never-use-in-production"
ALLOWED_HOSTS = ["*"] if DEBUG else ALLOWED_HOSTS  # noqa: F405
STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}  # noqa: F405
