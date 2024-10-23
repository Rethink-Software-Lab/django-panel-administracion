from ninja.errors import HttpError
from inventario.models import (
    ProductoInfo,
    SalidaAlmacenRevoltosa,
    Producto,
    User,
    AreaVenta,
)
from ..schema import AddSalidaRevoltosaSchema, ProductoInfoSalidaAlmacenRevoltosaSchema
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Count

from ..custom_permissions import isStaff


@api_controller("salidas-revoltosa/", tags=["SalidasRevoltosa"], permissions=[isStaff])
class SalidasRevoltosaController:

    @route.get("", response=ProductoInfoSalidaAlmacenRevoltosaSchema)
    def get_salidas_revoltosa(self):
        try:
            salidas = (
                SalidaAlmacenRevoltosa.objects.all()
                .order_by("-created_at")
                .annotate(cantidad=Count("producto"))
                .values(
                    "id",
                    "usuario__username",
                    "created_at",
                    "producto__info__descripcion",
                    "cantidad",
                )
            )

            productos = (
                ProductoInfo.objects.filter(
                    producto__area_venta__isnull=True,
                    producto__almacen_revoltosa=True,
                    producto__ajusteinventario__isnull=True,
                )
                .only("codigo", "categoria")
                .distinct()
            )

            return {"salidas": salidas, "productos": productos}
        except Exception as e:
            raise HttpError(500, f"Error al obtener las salidas: {str(e)}")

    @route.post("")
    def add_salida_revoltosa(self, request, data: AddSalidaRevoltosaSchema):
        dataDict = data.model_dump()

        producto_info = get_object_or_404(
            ProductoInfo, codigo=dataDict["producto_info"]
        )

        area_revoltosa = get_object_or_404(AreaVenta, nombre="Revoltosa")

        usuario_search = get_object_or_404(User, pk=request.auth["id"])

        if producto_info.categoria.nombre == "Zapatos":

            ids_unicos = list(dict.fromkeys(dataDict["zapatos_id"]))

            ids_count = Producto.objects.filter(id__in=ids_unicos).count()

            if ids_count < len(ids_unicos):
                raise HttpError(400, "Algunos ids no existen")

            filtro1 = Producto.objects.filter(pk__in=ids_unicos, info=producto_info)

            if filtro1.count() < len(ids_unicos):
                raise HttpError(400, "Los ids deben ser de un único producto")

            filtro2 = filtro1.filter(venta__isnull=True)

            if filtro2.count() < len(ids_unicos):
                raise HttpError(400, "Algunos productos ya han sido vendidos.")

            filtro3 = filtro2.filter(area_venta__isnull=True)

            if filtro3.count() < len(ids_unicos):
                raise HttpError(400, "Algunos productos ya están en un área de venta.")

            productos = filtro3.filter(
                almacen_revoltosa=True,
                ajusteinventario__isnull=True,
            )

            if productos.count() < len(ids_unicos):
                raise HttpError(400, "Algunos productos no están en el almacén.")

            try:
                with transaction.atomic():
                    salida = SalidaAlmacenRevoltosa.objects.create(
                        usuario=usuario_search
                    )
                    productos.update(
                        area_venta=area_revoltosa,
                        almacen_revoltosa=False,
                        salida_revoltosa=salida,
                    )

                    return {"success": True}
            except Exception as e:
                raise HttpError(500, f"Algo salió mal al agregar la salida: {str(e)}")

        elif dataDict["cantidad"] and dataDict["cantidad"] > 0:

            with transaction.atomic():
                cantidad = dataDict["cantidad"]
                salida = SalidaAlmacenRevoltosa.objects.create(usuario=usuario_search)

                productos = Producto.objects.filter(
                    venta__isnull=True,
                    area_venta__isnull=True,
                    almacen_revoltosa=True,
                    info=producto_info,
                    ajusteinventario__isnull=True,
                )[:cantidad]

                if productos.count() < cantidad:
                    raise HttpError(
                        400,
                        f"No hay {producto_info.descripcion} suficientes para esta accion",
                    )

                prods = [
                    Producto(
                        id=producto.pk,
                        area_venta=area_revoltosa,
                        almacen_revoltosa=False,
                        salida_revoltosa=salida,
                    )
                    for producto in productos
                ]

                Producto.objects.bulk_update(
                    prods,
                    fields=["area_venta", "almacen_revoltosa", "salida_revoltosa"],
                )

                return {"success": True}

        else:
            raise HttpError(400, "Cantidad requerida en productos != Zapatos")

    @route.delete("{id}/")
    def deleteSalida(self, id: int):
        salida = get_object_or_404(SalidaAlmacenRevoltosa, pk=id)

        productos_vendidos = Producto.objects.filter(
            salida_revoltosa=salida, venta__isnull=False
        ).exists()

        if productos_vendidos:
            raise HttpError(
                400,
                "No se puede eliminar la salida porque algunos productos ya han sido vendidos.",
            )

        try:
            with transaction.atomic():
                Producto.objects.filter(salida_revoltosa=salida).update(
                    area_venta=None, salida_revoltosa=None, almacen_revoltosa=True
                )
                salida.delete()

            return {"success": True}
        except Exception as e:
            raise HttpError(500, f"Error inesperado: {str(e)}")
