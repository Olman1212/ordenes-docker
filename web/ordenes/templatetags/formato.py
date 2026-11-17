from datetime import date

from django import template

register = template.Library()


@register.filter
def moneda(valor):
    try:
        return f"L {float(valor):,.2f}"
    except (TypeError, ValueError):
        return valor


@register.filter
def fecha_corta(valor):
    try:
        return date.fromisoformat(str(valor)).strftime("%d/%m/%Y")
    except ValueError:
        return valor
