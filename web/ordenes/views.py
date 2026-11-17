"""
Pantallas CRUD de órdenes y detalles.

Ninguna vista toca una base de datos: todas llaman a la API Flask
(ordenes/api.py) y muestran un mensaje claro cuando la API devuelve un error.
"""
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .api import ApiError, llamar
from .forms import DetalleForm, OrdenForm


def salud(request):
    """Lo usa el healthcheck del contenedor web."""
    return HttpResponse("ok", content_type="text/plain")


# ---------------------------------------------------------------------------
# Órdenes
# ---------------------------------------------------------------------------
def lista_ordenes(request):
    ordenes = []
    try:
        ordenes = llamar("GET", "/api/ordenes")
    except ApiError as exc:
        messages.error(request, exc.mensaje)
    return render(request, "ordenes/lista.html", {"ordenes": ordenes})


def crear_orden(request):
    if request.method == "POST":
        form = OrdenForm(request.POST)
        if form.is_valid():
            try:
                orden = llamar("POST", "/api/ordenes", json=form.a_json())
                messages.success(request, f"Orden {orden['id']} creada. Ahora agregue sus detalles.")
                return redirect("ver_orden", orden_id=orden["id"])
            except ApiError as exc:
                messages.error(request, exc.mensaje)
    else:
        form = OrdenForm(initial={"estado": "Pendiente"})
    return render(request, "ordenes/orden_form.html", {"form": form, "titulo": "Nueva orden"})


def ver_orden(request, orden_id, detalle_form=None):
    try:
        orden = llamar("GET", f"/api/ordenes/{orden_id}")
    except ApiError as exc:
        messages.error(request, exc.mensaje)
        return redirect("lista_ordenes")
    return render(request, "ordenes/orden_ver.html", {
        "orden": orden,
        "detalle_form": detalle_form or DetalleForm(),
    })


def editar_orden(request, orden_id):
    try:
        orden = llamar("GET", f"/api/ordenes/{orden_id}")
    except ApiError as exc:
        messages.error(request, exc.mensaje)
        return redirect("lista_ordenes")

    if request.method == "POST":
        form = OrdenForm(request.POST)
        if form.is_valid():
            try:
                llamar("PUT", f"/api/ordenes/{orden_id}", json=form.a_json())
                messages.success(request, f"Orden {orden_id} actualizada.")
                return redirect("ver_orden", orden_id=orden_id)
            except ApiError as exc:
                messages.error(request, exc.mensaje)
    else:
        form = OrdenForm(initial={
            "cliente": orden["cliente"],
            "fecha": orden["fecha"],
            "estado": orden["estado"],
        })
    return render(request, "ordenes/orden_form.html", {
        "form": form,
        "titulo": f"Editar orden {orden_id}",
        "orden": orden,
    })


def eliminar_orden(request, orden_id):
    try:
        orden = llamar("GET", f"/api/ordenes/{orden_id}")
    except ApiError as exc:
        messages.error(request, exc.mensaje)
        return redirect("lista_ordenes")

    if request.method == "POST":
        try:
            llamar("DELETE", f"/api/ordenes/{orden_id}")
            messages.success(request, f"Orden {orden_id} eliminada junto con sus detalles.")
        except ApiError as exc:
            messages.error(request, exc.mensaje)
        return redirect("lista_ordenes")

    return render(request, "ordenes/confirmar.html", {
        "titulo": f"Eliminar orden {orden_id}",
        "texto": (
            f"Se eliminará la orden {orden_id} de {orden['cliente']} "
            f"y sus {len(orden['detalles'])} líneas de detalle."
        ),
        "volver": "ver_orden",
        "volver_id": orden_id,
    })


# ---------------------------------------------------------------------------
# Detalles
# ---------------------------------------------------------------------------
@require_POST
def agregar_detalle(request, orden_id):
    form = DetalleForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Revise los datos del detalle.")
        return ver_orden(request, orden_id, detalle_form=form)
    try:
        respuesta = llamar("POST", f"/api/ordenes/{orden_id}/detalles", json=form.a_json())
        messages.success(
            request,
            f"Detalle agregado. Nuevo total de la orden: L {respuesta['total_orden']:,.2f}.",
        )
    except ApiError as exc:
        messages.error(request, exc.mensaje)
        if exc.codigo == 404:
            return redirect("lista_ordenes")
    return redirect("ver_orden", orden_id=orden_id)


def editar_detalle(request, detalle_id):
    try:
        detalle = llamar("GET", f"/api/detalles/{detalle_id}")
    except ApiError as exc:
        messages.error(request, exc.mensaje)
        return redirect("lista_ordenes")

    if request.method == "POST":
        form = DetalleForm(request.POST)
        if form.is_valid():
            try:
                respuesta = llamar("PUT", f"/api/detalles/{detalle_id}", json=form.a_json())
                messages.success(
                    request,
                    f"Detalle {detalle_id} actualizado. Nuevo total de la orden: "
                    f"L {respuesta['total_orden']:,.2f}.",
                )
                return redirect("ver_orden", orden_id=detalle["orden_id"])
            except ApiError as exc:
                messages.error(request, exc.mensaje)
    else:
        form = DetalleForm(initial={
            "producto": detalle["producto"],
            "cantidad": detalle["cantidad"],
            "precio_unitario": detalle["precio_unitario"],
        })
    return render(request, "ordenes/detalle_form.html", {"form": form, "detalle": detalle})


def eliminar_detalle(request, detalle_id):
    try:
        detalle = llamar("GET", f"/api/detalles/{detalle_id}")
    except ApiError as exc:
        messages.error(request, exc.mensaje)
        return redirect("lista_ordenes")

    if request.method == "POST":
        try:
            respuesta = llamar("DELETE", f"/api/detalles/{detalle_id}")
            messages.success(
                request,
                f"Detalle {detalle_id} eliminado. Nuevo total de la orden: "
                f"L {respuesta['total_orden']:,.2f}.",
            )
        except ApiError as exc:
            messages.error(request, exc.mensaje)
        return redirect("ver_orden", orden_id=detalle["orden_id"])

    return render(request, "ordenes/confirmar.html", {
        "titulo": f"Eliminar detalle {detalle_id}",
        "texto": (
            f"Se eliminará la línea «{detalle['producto']}» "
            f"({detalle['cantidad']} × L {detalle['precio_unitario']:,.2f}) "
            f"de la orden {detalle['orden_id']}. El total se recalculará."
        ),
        "volver": "ver_orden",
        "volver_id": detalle["orden_id"],
    })
