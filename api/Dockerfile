# Imagen de la API REST (Flask + pymssql)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 1) Primero las dependencias: esta capa queda en caché mientras
#    requirements.txt no cambie, aunque se modifique el código.
COPY requirements.txt .
RUN pip install -r requirements.txt

# 2) Después el código de la aplicación.
COPY app.py .

# 3) Usuario sin privilegios.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "2", "--access-logfile", "-", "app:app"]
