"""
Configuración del frontend Django.

Este proyecto NO se conecta a SQL Server: todas las operaciones se hacen
llamando a la API Flask, cuya URL se define con la variable de entorno API_URL.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "clave-solo-para-desarrollo-cambiela")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

# URL base de la API (en Docker Compose: http://api:5000, por el nombre del servicio).
API_URL = os.environ.get("API_URL", "http://api:5000").rstrip("/")
API_TIMEOUT = float(os.environ.get("API_TIMEOUT", "10"))

INSTALLED_APPS = [
    "django.contrib.messages",
    "ordenes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ordenes_web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
                "ordenes.context_processors.api",
            ],
        },
    },
]

WSGI_APPLICATION = "ordenes_web.wsgi.application"

# Sin base de datos propia: los datos viven en SQL Server y solo la API los toca.
DATABASES = {}

# Los mensajes (éxito / error) se guardan en una cookie, sin sesiones ni BD.
MESSAGE_STORAGE = "django.contrib.messages.storage.cookie.CookieStorage"

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Tegucigalpa"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
