from ninja.errors import HttpError
from inventario.models import (
    SalidaAlmacen,
    Producto,
    SalidaAlmacenRevoltosa,
)
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from django.db import transaction

from ..custom_permissions import isStaff


@api_controller("salidas/", tags=["Salidas"], permissions=[isStaff])
class SalidasController:
    @route.delete("{id}/")
    def deleteSalida(self, id: int):
        salida = get_object_or_404(SalidaAlmacen, pk=id)

        productos_vendidos = Producto.objects.filter(salida=salida, venta__isnull=False)

        if productos_vendidos.exists():
            raise HttpError(
                400,
                "No se puede eliminar la salida porque algunos productos ya han sido vendidos.",
            )

        try:
            with transaction.atomic():
                productos = Producto.objects.filter(salida=salida)
                SalidaAlmacenRevoltosa.objects.filter(producto__in=productos).delete()
                productos.update(
                    area_venta=None,
                    salida=None,
                    almacen_revoltosa=False,
                    salida_revoltosa=None,
                )
                salida.delete()

            return {"success": True}
        except Exception as e:
            raise HttpError(500, f"Error inesperado: {str(e)}")
