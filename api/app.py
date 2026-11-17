"""
API REST de órdenes (Flask + SQL Server).

Es el único servicio que se conecta a la base de datos. El servidor es el
nombre del servicio "db" de Docker Compose y todos los datos de conexión
vienen de variables de entorno.
"""
import os
from datetime import date
from decimal import Decimal, InvalidOperation

import pymssql
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
app.json.ensure_ascii = False
app.json.sort_keys = False

DB_CONFIG = {
    "server": os.environ.get("DB_HOST", "db"),
    "port": int(os.environ.get("DB_PORT", "1433")),
    "user": os.environ.get("DB_USER", "sa"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "OrdenesDB"),
    "login_timeout": 5,
    "timeout": 15,
    "charset": "UTF-8",
}

ESTADOS = ("Pendiente", "Pagada", "Anulada")


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def conectar():
    return pymssql.connect(as_dict=True, **DB_CONFIG)


def error(mensaje, codigo):
    return jsonify({"error": mensaje}), codigo


def a_json(fila):
    """Convierte Decimal y date a tipos que JSON entiende."""
    resultado = {}
    for clave, valor in fila.items():
        if isinstance(valor, Decimal):
            valor = float(valor)
        elif isinstance(valor, date):
            valor = valor.isoformat()
        resultado[clave] = valor
    return resultado


def cuerpo_json():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return None
    return datos


def validar_orden(datos, parcial=False):
    """Devuelve (valores, mensaje_de_error)."""
    valores = {}

    if "cliente" in datos or not parcial:
        cliente = str(datos.get("cliente") or "").strip()
        if not cliente:
            return None, "El campo 'cliente' es obligatorio."
        if len(cliente) > 100:
            return None, "El campo 'cliente' admite como máximo 100 caracteres."
        valores["cliente"] = cliente

    if "fecha" in datos and datos.get("fecha") not in (None, ""):
        try:
            valores["fecha"] = date.fromisoformat(str(datos["fecha"])).isoformat()
        except ValueError:
            return None, "El campo 'fecha' debe tener el formato AAAA-MM-DD."
    elif not parcial:
        valores["fecha"] = date.today().isoformat()

    if "estado" in datos or not parcial:
        estado = str(datos.get("estado") or "Pendiente").strip()
        if estado not in ESTADOS:
            return None, f"El campo 'estado' debe ser uno de: {', '.join(ESTADOS)}."
        valores["estado"] = estado

    if parcial and not valores:
        return None, "Envíe al menos uno de los campos: cliente, fecha, estado."
    return valores, None


def validar_detalle(datos, parcial=False):
    """Devuelve (valores, mensaje_de_error)."""
    valores = {}

    if "producto" in datos or not parcial:
        producto = str(datos.get("producto") or "").strip()
        if not producto:
            return None, "El campo 'producto' es obligatorio."
        if len(producto) > 100:
            return None, "El campo 'producto' admite como máximo 100 caracteres."
        valores["producto"] = producto

    if "cantidad" in datos or not parcial:
        try:
            cantidad = int(str(datos.get("cantidad")))
        except (TypeError, ValueError):
            return None, "El campo 'cantidad' debe ser un número entero."
        if cantidad <= 0:
            return None, "El campo 'cantidad' debe ser mayor que 0."
        valores["cantidad"] = cantidad

    if "precio_unitario" in datos or not parcial:
        try:
            precio = Decimal(str(datos.get("precio_unitario"))).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            return None, "El campo 'precio_unitario' debe ser un número."
        if not precio.is_finite() or precio < 0:
            return None, "El campo 'precio_unitario' debe ser 0 o mayor."
        valores["precio_unitario"] = precio

    if parcial and not valores:
        return None, "Envíe al menos uno de los campos: producto, cantidad, precio_unitario."
    return valores, None


def recalcular_total(cursor, orden_id):
    """El total de la orden es la suma de los subtotales de sus detalles."""
    cursor.execute(
        """
        UPDATE ordenes
           SET total = ISNULL((SELECT SUM(subtotal) FROM orden_detalle WHERE orden_id = %s), 0)
         WHERE id = %s
        """,
        (orden_id, orden_id),
    )


def buscar_orden(cursor, orden_id):
    cursor.execute(
        "SELECT id, cliente, fecha, estado, total FROM ordenes WHERE id = %s",
        (orden_id,),
    )
    return cursor.fetchone()


def buscar_detalles(cursor, orden_id):
    cursor.execute(
        """
        SELECT id, orden_id, producto, cantidad, precio_unitario, subtotal
          FROM orden_detalle
         WHERE orden_id = %s
         ORDER BY id
        """,
        (orden_id,),
    )
    return [a_json(fila) for fila in cursor.fetchall()]


def orden_completa(cursor, orden_id):
    orden = buscar_orden(cursor, orden_id)
    if orden is None:
        return None
    orden = a_json(orden)
    orden["detalles"] = buscar_detalles(cursor, orden_id)
    return orden


def buscar_detalle(cursor, detalle_id):
    cursor.execute(
        """
        SELECT id, orden_id, producto, cantidad, precio_unitario, subtotal
          FROM orden_detalle
         WHERE id = %s
        """,
        (detalle_id,),
    )
    return cursor.fetchone()


# ---------------------------------------------------------------------------
# Manejo de errores: todas las respuestas son JSON
# ---------------------------------------------------------------------------
@app.errorhandler(HTTPException)
def error_http(exc):
    return error(exc.description, exc.code)


@app.errorhandler(pymssql.Error)
def error_base_datos(exc):
    app.logger.exception("Error de base de datos")
    return error("No se pudo completar la operación en la base de datos.", 500)


# ---------------------------------------------------------------------------
# Salud
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    try:
        with conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT 1 AS ok")
                cursor.fetchone()
        return jsonify({"status": "ok", "servicio": "api", "base_de_datos": "ok"}), 200
    except pymssql.Error:
        return jsonify({"status": "error", "servicio": "api", "base_de_datos": "sin conexión"}), 503


# ---------------------------------------------------------------------------
# Órdenes
# ---------------------------------------------------------------------------
@app.get("/api/ordenes")
def listar_ordenes():
    with conectar() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT o.id, o.cliente, o.fecha, o.estado, o.total,
                       (SELECT COUNT(*) FROM orden_detalle d WHERE d.orden_id = o.id) AS num_detalles
                  FROM ordenes o
                 ORDER BY o.id
                """
            )
            ordenes = [a_json(fila) for fila in cursor.fetchall()]
    return jsonify(ordenes), 200


@app.get("/api/ordenes/<int:orden_id>")
def ver_orden(orden_id):
    with conectar() as conexion:
        with conexion.cursor() as cursor:
            orden = orden_completa(cursor, orden_id)
    if orden is None:
        return error(f"La orden {orden_id} no existe.", 404)
    return jsonify(orden), 200


@app.post("/api/ordenes")
def crear_orden():
    datos = cuerpo_json()
    if datos is None:
        return error("El cuerpo de la petición debe ser un objeto JSON.", 400)
    valores, mensaje = validar_orden(datos)
    if mensaje:
        return error(mensaje, 400)

    # Detalles opcionales al crear la orden.
    detalles = datos.get("detalles") or []
    if not isinstance(detalles, list):
        return error("El campo 'detalles' debe ser una lista.", 400)
    detalles_validos = []
    for numero, detalle in enumerate(detalles, start=1):
        if not isinstance(detalle, dict):
            return error(f"El detalle {numero} debe ser un objeto JSON.", 400)
        valores_detalle, mensaje = validar_detalle(detalle)
        if mensaje:
            return error(f"Detalle {numero}: {mensaje}", 400)
        detalles_validos.append(valores_detalle)

    with conectar() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ordenes (cliente, fecha, estado, total)
                OUTPUT INSERTED.id
                VALUES (%s, %s, %s, 0)
                """,
                (valores["cliente"], valores["fecha"], valores["estado"]),
            )
            orden_id = cursor.fetchone()["id"]
            for d in detalles_validos:
                cursor.execute(
                    """
                    INSERT INTO orden_detalle (orden_id, producto, cantidad, precio_unitario, subtotal)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (orden_id, d["producto"], d["cantidad"], d["precio_unitario"],
                     d["cantidad"] * d["precio_unitario"]),
                )
            recalcular_total(cursor, orden_id)
            conexion.commit()
            orden = orden_completa(cursor, orden_id)
    return jsonify(orden), 201


@app.put("/api/ordenes/<int:orden_id>")
def actualizar_orden(orden_id):
    datos = cuerpo_json()
    if datos is None:
        return error("El cuerpo de la petición debe ser un objeto JSON.", 400)
    valores, mensaje = validar_orden(datos, parcial=True)
    if mensaje:
        return error(mensaje, 400)

    with conectar() as conexion:
        with conexion.cursor() as cursor:
            if buscar_orden(cursor, orden_id) is None:
                return error(f"La orden {orden_id} no existe.", 404)
            columnas = ", ".join(f"{columna} = %s" for columna in valores)
            cursor.execute(
                f"UPDATE ordenes SET {columnas} WHERE id = %s",
                (*valores.values(), orden_id),
            )
            conexion.commit()
            orden = orden_completa(cursor, orden_id)
    return jsonify(orden), 200


@app.delete("/api/ordenes/<int:orden_id>")
def eliminar_orden(orden_id):
    with conectar() as conexion:
        with conexion.cursor() as cursor:
            if buscar_orden(cursor, orden_id) is None:
                return error(f"La orden {orden_id} no existe.", 404)
            cursor.execute("DELETE FROM orden_detalle WHERE orden_id = %s", (orden_id,))
            detalles_borrados = cursor.rowcount
            cursor.execute("DELETE FROM ordenes WHERE id = %s", (orden_id,))
            conexion.commit()
    return jsonify({
        "mensaje": f"Orden {orden_id} eliminada junto con sus detalles.",
        "detalles_eliminados": detalles_borrados,
    }), 200


# ---------------------------------------------------------------------------
# Detalles de una orden
# ---------------------------------------------------------------------------
@app.get("/api/ordenes/<int:orden_id>/detalles")
def listar_detalles(orden_id):
    with conectar() as conexion:
        with conexion.cursor() as cursor:
            if buscar_orden(cursor, orden_id) is None:
                return error(f"La orden {orden_id} no existe.", 404)
            detalles = buscar_detalles(cursor, orden_id)
    return jsonify(detalles), 200


@app.post("/api/ordenes/<int:orden_id>/detalles")
def agregar_detalle(orden_id):
    datos = cuerpo_json()
    if datos is None:
        return error("El cuerpo de la petición debe ser un objeto JSON.", 400)
    valores, mensaje = validar_detalle(datos)
    if mensaje:
        return error(mensaje, 400)

    with conectar() as conexion:
        with conexion.cursor() as cursor:
            if buscar_orden(cursor, orden_id) is None:
                return error(f"La orden {orden_id} no existe.", 404)
            cursor.execute(
                """
                INSERT INTO orden_detalle (orden_id, producto, cantidad, precio_unitario, subtotal)
                OUTPUT INSERTED.id
                VALUES (%s, %s, %s, %s, %s)
                """,
                (orden_id, valores["producto"], valores["cantidad"], valores["precio_unitario"],
                 valores["cantidad"] * valores["precio_unitario"]),
            )
            detalle_id = cursor.fetchone()["id"]
            recalcular_total(cursor, orden_id)
            conexion.commit()
            detalle = a_json(buscar_detalle(cursor, detalle_id))
            total = float(buscar_orden(cursor, orden_id)["total"])
    return jsonify({"detalle": detalle, "total_orden": total}), 201


# ---------------------------------------------------------------------------
# Detalles por id
# ---------------------------------------------------------------------------
@app.get("/api/detalles/<int:detalle_id>")
def ver_detalle(detalle_id):
    with conectar() as conexion:
        with conexion.cursor() as cursor:
            detalle = buscar_detalle(cursor, detalle_id)
    if detalle is None:
        return error(f"El detalle {detalle_id} no existe.", 404)
    return jsonify(a_json(detalle)), 200


@app.put("/api/detalles/<int:detalle_id>")
def actualizar_detalle(detalle_id):
    datos = cuerpo_json()
    if datos is None:
        return error("El cuerpo de la petición debe ser un objeto JSON.", 400)
    valores, mensaje = validar_detalle(datos, parcial=True)
    if mensaje:
        return error(mensaje, 400)

    with conectar() as conexion:
        with conexion.cursor() as cursor:
            actual = buscar_detalle(cursor, detalle_id)
            if actual is None:
                return error(f"El detalle {detalle_id} no existe.", 404)
            producto = valores.get("producto", actual["producto"])
            cantidad = valores.get("cantidad", actual["cantidad"])
            precio = valores.get("precio_unitario", actual["precio_unitario"])
            cursor.execute(
                """
                UPDATE orden_detalle
                   SET producto = %s, cantidad = %s, precio_unitario = %s, subtotal = %s
                 WHERE id = %s
                """,
                (producto, cantidad, precio, cantidad * precio, detalle_id),
            )
            recalcular_total(cursor, actual["orden_id"])
            conexion.commit()
            detalle = a_json(buscar_detalle(cursor, detalle_id))
            total = float(buscar_orden(cursor, actual["orden_id"])["total"])
    return jsonify({"detalle": detalle, "total_orden": total}), 200


@app.delete("/api/detalles/<int:detalle_id>")
def eliminar_detalle(detalle_id):
    with conectar() as conexion:
        with conexion.cursor() as cursor:
            actual = buscar_detalle(cursor, detalle_id)
            if actual is None:
                return error(f"El detalle {detalle_id} no existe.", 404)
            cursor.execute("DELETE FROM orden_detalle WHERE id = %s", (detalle_id,))
            recalcular_total(cursor, actual["orden_id"])
            conexion.commit()
            total = float(buscar_orden(cursor, actual["orden_id"])["total"])
    return jsonify({
        "mensaje": f"Detalle {detalle_id} eliminado.",
        "orden_id": actual["orden_id"],
        "total_orden": total,
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
