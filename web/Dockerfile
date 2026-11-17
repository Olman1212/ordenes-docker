# Imagen del frontend (Django + requests)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 1) Dependencias primero para aprovechar la caché de capas.
COPY requirements.txt .
RUN pip install -r requirements.txt

# 2) Código del proyecto Django.
COPY . .

# 3) Usuario sin privilegios.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "ordenes_web.wsgi:application"]
