"""Cliente de la API Flask. Es la única vía de acceso a los datos."""
import requests
from django.conf import settings


class ApiError(Exception):
    def __init__(self, mensaje, codigo=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


def llamar(metodo, ruta, json=None):
    url = f"{settings.API_URL}{ruta}"
    try:
        respuesta = requests.request(metodo, url, json=json, timeout=settings.API_TIMEOUT)
    except requests.RequestException:
        raise ApiError(
            f"No se pudo conectar con la API ({settings.API_URL}). "
            "Verifique que el servicio api esté en ejecución."
        )

    try:
        datos = respuesta.json()
    except ValueError:
        datos = None

    if respuesta.status_code >= 400:
        mensaje = datos.get("error") if isinstance(datos, dict) else None
        raise ApiError(
            f"La API respondió {respuesta.status_code}: {mensaje or 'error sin detalle.'}",
            respuesta.status_code,
        )
    return datos
