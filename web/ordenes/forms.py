from decimal import Decimal

from django import forms

ESTADOS = [("Pendiente", "Pendiente"), ("Pagada", "Pagada"), ("Anulada", "Anulada")]


class OrdenForm(forms.Form):
    cliente = forms.CharField(label="Cliente", max_length=100)
    fecha = forms.DateField(
        label="Fecha",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    estado = forms.ChoiceField(label="Estado", choices=ESTADOS)

    def a_json(self):
        datos = self.cleaned_data
        return {
            "cliente": datos["cliente"],
            "fecha": datos["fecha"].isoformat(),
            "estado": datos["estado"],
        }


class DetalleForm(forms.Form):
    producto = forms.CharField(label="Producto", max_length=100)
    cantidad = forms.IntegerField(label="Cantidad", min_value=1)
    precio_unitario = forms.DecimalField(
        label="Precio unitario (L)", min_value=Decimal("0"), max_digits=10, decimal_places=2
    )

    def a_json(self):
        datos = self.cleaned_data
        return {
            "producto": datos["producto"],
            "cantidad": datos["cantidad"],
            "precio_unitario": str(datos["precio_unitario"]),
        }
